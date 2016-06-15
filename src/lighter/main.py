#!/usr/bin/env python
import os
import sys
import argparse
import logging
import yaml
import urllib2
import json
from copy import copy
from urlparse import urlparse
from joblib import Parallel, delayed
from lighter.hipchat import HipChat
import lighter.util as util
import lighter.maven as maven
import lighter.docker as docker
import lighter.secretary as secretary
from lighter.newrelic import NewRelic
from lighter.datadog import Datadog

def parsebool(value):
    truevals = set(['true', '1'])
    falsevals = set(['false', '0'])
    stripped = str(value).lower().strip()
    if stripped in truevals:
        return True
    if stripped in falsevals:
        return False

    logging.error("Invalid boolean value '%s'", value)
    sys.exit(1)

def parseint(value):
    try:
        return int(value)
    except:
        logging.error("Invalid integer value '%s'", value)
        sys.exit(1)

def parselist(value):
    return filter(bool, value.split(','))

class Service(object):
    def __init__(self, filename, document, config):
        self.filename = filename
        self.document = document
        self.config = config

    @property
    def id(self):
        return self.config.get('id', '')

    @property
    def image(self):
        return util.rget(self.config, 'container', 'docker', 'image') or ''

    @property
    def environment(self):
        return util.rget(self.document, 'facts', 'environment') or 'default'

    @property
    def uniqueVersion(self):
        return util.rget(self.document, 'variables', 'lighter.uniqueVersion') or \
            (self.image.split(':')[1] if ':' in self.image else 'latest')

    @property
    def checksum(self):
        return self.config['labels']['com.meltwater.lighter.checksum']

def process_env(filename, verifySecrets, env):
    result = copy(env)
    for key, value in env.iteritems():
        # Can't support non-string keys consistently
        if not isinstance(key, (str, unicode)):
            raise ValueError("Only string dict keys are supported, please use quotes around the key '%s' in %s" % (key, filename))

        # Coerce types to string and serialize non-scalars
        if not isinstance(value, (str, unicode)):
            if isinstance(value, bool):
                value = 'true' if value else 'false'
            elif isinstance(value, (int, float)):
                value = str(value)
            else:
                value = json.dumps(value)

            result[key] = value

        # Check for unencrypted secrets
        if (('password' in key.lower() or 'pwd' in key.lower() or 'key' in key.lower() or 'token' in key.lower()) and
                'public' not in key.lower() and 'id' not in key.lower() and 'routing' not in key.lower()) and len(secretary.extractEnvelopes(value)) == 0:
            if verifySecrets:
                raise RuntimeError('Found unencrypted secret in %s: %s' % (filename, key))
            else:
                logging.warn('Found unencrypted secret in %s: %s' % (filename, key))

    return result

def parse_service(filename, targetdir=None, verifySecrets=False):
    logging.info("Processing %s", filename)
    with open(filename, 'r') as fd:
        try:
            document = yaml.load(fd)
        except yaml.YAMLError as e:
            raise RuntimeError("Error parsing file %s: %s" % (filename, e))

    # Merge globals.yml files into document
    path = os.path.dirname(os.path.abspath(filename))
    while '/' in path:
        candidate = os.path.join(path, 'globals.yml')
        if os.path.exists(candidate):
            with open(candidate, 'r') as fd2:
                document = util.merge(yaml.load(fd2), document)
        path = path[0:path.rindex('/')]

    # Start from a service section if it exists
    variables = util.FixedVariables(document.get('variables', {}))

    # Environment variables has higher precedence
    variables = util.EnvironmentVariables(variables)

    # Replace variables in entire document
    document = util.replace(document, variables, raiseError=False, escapeVar=False)

    # Start from a service section if it exists
    config = document.get('service', {})

    # Allow resolving version/uniqueVersion variables from docker registry
    variables = docker.ImageVariables.create(
        variables, document, util.rget(config, 'container', 'docker', 'image'))

    # Fetch and merge json template from maven
    if util.rget(document, 'maven', 'version') or util.rget(document, 'maven', 'resolve'):
        coord = document['maven']
        versionspec = coord.get('version')
        if not versionspec:
            versionspec = coord['resolve']
            logging.warn("The 'resolve:' tag is deprecated, please switch to 'version:' which is a drop-in replacement in %s" % filename)

        resolver = maven.ArtifactResolver(coord['repository'], coord['groupid'], coord['artifactid'], coord.get('classifier'))
        version = resolver.resolve(versionspec)

        artifact = resolver.fetch(version)
        config = util.merge(config, artifact.body)
        variables = maven.ArtifactVariables(variables, artifact)

    # Merge overrides into json template
    config = util.merge(config, document.get('override', {}))

    # Substitute variables into the config
    try:
        config = util.replace(config, variables)
    except KeyError as e:
        raise RuntimeError('Failed to parse %s with the following message: %s' % (filename, str(e.message)))

    if 'env' in config:
        config['env'] = process_env(filename, verifySecrets, config['env'])

    # Generate deploy keys and encrypt secrets
    config = secretary.apply(document, config)
    checksum = util.checksum(config)

    # Include hash of config to detect if an element has been removed
    config['labels'] = config.get('labels', {})
    config['labels']['com.meltwater.lighter.checksum'] = checksum

    # Include a docker label to sort on
    if util.rget(config, 'container', 'docker'):
        config['container']['docker']['parameters'] = config['container']['docker'].get('parameters', [])
        config['container']['docker']['parameters'].append({'key': 'label', 'value': 'com.meltwater.lighter.appid='+config['id']})

    # Write json file to disk for logging purposes
    if targetdir:
        outputfile = os.path.join(targetdir, filename + '.json')

        # Exception if directory exists, e.g. because another thread created it concurrently
        try:
            os.makedirs(os.path.dirname(outputfile))
        except OSError as e:
            pass

        with open(outputfile, 'w') as fd:
            fd.write(util.toJson(config, indent=4))

    return Service(filename, document, config)

def parse_services(filenames, targetdir=None, verifySecrets=False):
    # return [parse_service(filename, targetdir) for filename in filenames]
    return Parallel(n_jobs=8, backend="threading")(delayed(parse_service)(filename, targetdir, verifySecrets) for filename in filenames)

def get_marathon_url(url, id, force=False):
    return url.rstrip('/') + '/v2/apps/' + id.strip('/') + (force and '?force=true' or '')

def get_marathon_app(url):
    try:
        return util.jsonRequest(url)['app']
    except urllib2.HTTPError as e:
        logging.debug(str(e))
        if e.code == 404:
            return {}
        else:
            raise RuntimeError("Failed to get app info %s HTTP %d (%s) - Response: %s" % (url, e.code, e, e.read())), None, sys.exc_info()[2]
    except urllib2.URLError as e:
        logging.debug(str(e))
        raise RuntimeError("Failed to get app info %s (%s)" % (url, e)), None, sys.exc_info()[2]

def deploy(marathonurl, filenames, noop=False, force=False, targetdir=None):
    services = parse_services(filenames, targetdir)

    for service in services:
        try:
            targetMarathonUrl = marathonurl or util.rget(service.document, 'marathon', 'url')
            if not targetMarathonUrl:
                raise RuntimeError("No Marathon URL defined for service %s" % service.filename)

            parsedMarathonUrl = urlparse(targetMarathonUrl)
            appurl = get_marathon_url(targetMarathonUrl, service.config['id'], force)

            # See if service config has changed by comparing the checksum
            prevVersion = get_marathon_app(appurl)
            if util.rget(prevVersion, 'labels', 'com.meltwater.lighter.checksum') == service.checksum:
                logging.info("Service already deployed with same config: %s", service.filename)
                continue

            # Skip deployment if noop flag is given
            if noop:
                continue

            # Deploy new service config
            logging.info("Deploying %s", service.filename)
            util.jsonRequest(appurl, data=service.config, method='PUT')

            # Send HipChat notification
            hipchat = HipChat(
                util.rget(service.document, 'hipchat', 'token'),
                util.rget(service.document, 'hipchat', 'url'),
                util.rget(service.document, 'hipchat', 'rooms'))
            hipchat.notify("Deployed <b>%s</b> with image <b>%s</b> to <b>%s</b> (%s)" %
                           (service.id, service.image, service.environment, parsedMarathonUrl.netloc))

            # Send NewRelic deployment notification
            newrelic = NewRelic(util.rget(service.document, 'newrelic', 'token'))
            newrelic.notify(
                util.rget(service.config, 'env', 'NEW_RELIC_APP_NAME'),
                service.uniqueVersion
            )

            # Send Datadog deployment notification
            datadog = Datadog(util.rget(service.document, 'datadog', 'token'))
            datadog.notify(
                id=service.id,
                title="Deployed %s to the %s environment" % (service.id, service.environment),
                message="%%%%%% \n Lighter deployed **%s** with image **%s** to **%s** (%s) \n %%%%%%" % (
                    service.id, service.image, service.environment, parsedMarathonUrl.netloc),
                tags=["environment:%s" % service.environment, "service:%s" % service.id])

        except urllib2.HTTPError as e:
            raise RuntimeError("Failed to deploy %s HTTP %d (%s) - Response: %s" % (service.filename, e.code, e, e.read())), None, sys.exc_info()[2]
        except urllib2.URLError as e:
            raise RuntimeError("Failed to deploy %s (%s)" % (service.filename, e)), None, sys.exc_info()[2]

def verify(filenames, targetdir=None, verifySecrets=False):
    parse_services(filenames, targetdir, verifySecrets)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='lighter',
        usage='%(prog)s COMMAND [OPTIONS]...',
        description='Marathon deployment tool')
    subparsers = parser.add_subparsers(help='Available commands', dest='command')

    parser.add_argument('-n', '--noop', dest='noop', help='Execute dry-run without modifying Marathon [default: %(default)s]',
                        action='store_true', default=False)
    parser.add_argument('-v', '--verbose', dest='verbose', help='Increase logging verbosity [default: %(default)s]',
                        action="store_true", default=False)
    parser.add_argument('-t', '--targetdir', dest='targetdir', help='Directory to output rendered config files',
                        default=None)

    # Create the parser for the "deploy" command
    deploy_parser = subparsers.add_parser('deploy',
                                          prog='lighter',
                                          usage='%(prog)s deploy [OPTIONS]... YMLFILE...',
                                          help='Deploy services to Marathon',
                                          description='Deploy services to Marathon')

    deploy_parser.add_argument('-m',
                               '--marathon',
                               dest='marathon',
                               help='Marathon URL like "http://marathon-host:8080/". Overrides default Marathon URL\'s provided in config files',
                               default=os.environ.get('MARATHON_URL', ''))
    deploy_parser.add_argument('-f', '--force',
                               dest='force',
                               help='Force deployment even if the service is already affected by a running deployment [default: %(default)s]',
                               action='store_true', default=False)
    deploy_parser.add_argument('filenames', metavar='YMLFILE', nargs='+',
                               help='Service files to expand and deploy')

    # Create the parser for the "verify" command
    verify_parser = subparsers.add_parser('verify',
                                          prog='lighter',
                                          usage='%(prog)s verify YMLFILE...',
                                          help='Verify and generate Marathon configuration files',
                                          description='Verify and generate Marathon configuration files')

    verify_parser.add_argument('filenames', metavar='YMLFILE', nargs='+',
                               help='Service files to expand and deploy')

    verify_parser.add_argument('--verify-secrets', dest='verifySecrets', help='Fail verification if unencrypted secrets are found [default: %(default)s]',
                               action='store_true', default=False)

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    try:
        if args.command == 'deploy':
            deploy(args.marathon, noop=args.noop, force=args.force, filenames=args.filenames, targetdir=args.targetdir)
        elif args.command == 'verify':
            verify(args.filenames, targetdir=args.targetdir, verifySecrets=args.verifySecrets)
    except RuntimeError as e:
        logging.error(str(e))
        sys.exit(1)
