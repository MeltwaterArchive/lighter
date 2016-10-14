#!/usr/bin/env python
import os
import sys
import argparse
import logging
import hashlib
import yaml
import urllib
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
from lighter.graphite import Graphite

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

def process_env(filename, env):
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

    return result

def verify_secrets(services, enforce):
    for service in services:
        # Check for unencrypted secrets
        for key, value in service.config.get('env', {}).iteritems():
            # Skip secretary keys
            if isinstance(value, secretary.KeyValue):
                continue

            if (('password' in key.lower() or 'pwd' in key.lower() or 'key' in key.lower() or 'token' in key.lower()) and
                    'public' not in key.lower() and 'id' not in key.lower() and 'routing' not in key.lower()) and len(secretary.extractEnvelopes(value)) == 0:
                if enforce:
                    raise RuntimeError('Found unencrypted secret in %s: %s' % (service.filename, key))
                else:
                    logging.warn('Found unencrypted secret in %s: %s' % (service.filename, key))

def apply_canary(canaryGroup, service):
    if not canaryGroup:
        return

    mangledGroup = util.mangle(canaryGroup)
    config = service.config
    config['id'] = '%s-canary-%s-%s' % (config.get('id', ''), mangledGroup, hashlib.md5('%s-%s' % (canaryGroup, service.filename)).hexdigest())
    config['instances'] = 1

    # Rewrite service ports and add label for meltwater/proxymatic to read
    config['labels'] = config.get('labels', {})
    ports = config.get('ports', [])
    for port, i in zip(ports, range(len(ports))):
        config['labels']['com.meltwater.proxymatic.port.%d.servicePort' % i] = str(port)
        config['ports'][i] = 0

    mappings = util.toList(util.rget(config, 'container', 'docker', 'portMappings'))
    for mapping, i in zip(mappings, range(len(mappings))):
        config['labels']['com.meltwater.proxymatic.port.%d.servicePort' % i] = str(mapping['servicePort'])
        mapping['servicePort'] = 0

    # Apply canary label to task so old canaries can be destroyed
    config['labels']['com.meltwater.lighter.filename'] = service.filename
    config['labels']['com.meltwater.lighter.canary.group'] = mangledGroup

    # Apply canary label to container so container metrics can be aggregated
    if util.rget(config, 'container', 'docker'):
        config['container']['docker']['parameters'] = config['container']['docker'].get('parameters', [])
        config['container']['docker']['parameters'].append({'key': 'label', 'value': 'com.meltwater.lighter.canary.group='+mangledGroup})

def cleanup_canaries(marathonurl, canaryGroup, keepServices, noop=False):
    mangledGroup = util.mangle(canaryGroup)

    # Fetch list of current canaries
    apps = get_marathon_apps(marathonurl, 'com.meltwater.lighter.canary.group==' + mangledGroup)

    # Destroy canaries that are no longer present
    keep = set([service.config['id'] for service in keepServices])
    for app in apps:
        if app['labels']['com.meltwater.lighter.canary.group'] != mangledGroup:
            raise RuntimeError("Got canary %s not matching group %s" % (app['id'], mangledGroup))

        if app['id'] not in keep:
            if not noop:
                get_marathon_app(get_marathon_appurl(marathonurl, app['id']), method='DELETE')
            logging.info("Destroyed old canary %s", app['id'])

def parse_service(filename, canaryGroup=None, profiles=[]):
    logging.info("Processing %s", filename)
    # Start from a service section if it exists
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
            document = merge_with_service(candidate, document)
        path = path[0:path.rindex('/')]

    # Merge profile .yml files into document
    document = merge_with_profiles(document, profiles)

    variables = util.FixedVariables(document.get('variables', {}))

    # Environment variables has higher precedence
    variables = util.EnvironmentVariables(variables)

    # Replace variables in entire document
    document = util.replace(document, variables, raiseError=False, escapeVar=False)

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
        config['env'] = process_env(filename, config['env'])

    # Generate deploy keys and encrypt secrets
    config = secretary.apply(document, config)
    checksum = util.checksum(config)

    # Include hash of config to detect if an element has been removed
    config['labels'] = config.get('labels', {})
    config['labels']['com.meltwater.lighter.checksum'] = checksum

    # Add docker labels to aggregate container metrics on
    if util.rget(config, 'container', 'docker'):
        config['container']['docker']['parameters'] = config['container']['docker'].get('parameters', [])
        config['container']['docker']['parameters'].append({'key': 'label', 'value': 'com.meltwater.lighter.appid='+config['id']})

    service = Service(filename, document, config)

    # Apply canarying to avoid collisions on id and servicePort
    apply_canary(canaryGroup, service)

    return service

def parse_services(filenames, canaryGroup=None, profiles=[]):
    # return [parse_service(filename) for filename in filenames]
    return Parallel(n_jobs=8, backend="threading")(delayed(parse_service)(filename, canaryGroup, profiles) for filename in filenames) if filenames else []

def write_services(targetdir, services):
    for service in services:
        # Write json file to disk for logging purposes
        outputfile = os.path.join(targetdir, service.filename + '.json')

        # Exception if directory exists, e.g. because another thread created it concurrently
        try:
            os.makedirs(os.path.dirname(outputfile))
        except OSError:
            pass

        with open(outputfile, 'w') as fd:
            fd.write(util.toJson(service.config, indent=4))

def merge_with_profiles(document, profiles):
    for profile in profiles:
        document = merge_with_service(profile, document)
    return document

def merge_with_service(override_file, document):
    if not os.path.exists(override_file):
        raise RuntimeError('Could not read file %s' % override_file)

    with open(override_file, 'r') as fd2:
        document = util.merge(yaml.load(fd2), document)
    return document

def get_marathon_appurl(url, id, force=False):
    return url.rstrip('/') + '/v2/apps/' + id.strip('/') + (force and '?force=true' or '')

def get_marathon_app(url, method='GET'):
    try:
        response = util.jsonRequest(url, method=method)
        if method == 'GET':
            return response['app']
        return response
    except urllib2.HTTPError as e:
        logging.debug(str(e))
        if e.code == 404:
            return {}
        else:
            raise RuntimeError("Failed to %s app %s HTTP %d (%s) - Response: %s" % (method, url, e.code, e, e.read())), None, sys.exc_info()[2]
    except urllib2.URLError as e:
        logging.debug(str(e))
        raise RuntimeError("Failed to %s app %s (%s)" % (method, url, e)), None, sys.exc_info()[2]

def get_marathon_apps(url, labelFilter):
    appsurl = url.rstrip('/') + '/v2/apps?' + urllib.urlencode({'label': labelFilter})

    try:
        return util.jsonRequest(appsurl)['apps']
    except urllib2.HTTPError as e:
        logging.debug(str(e))
        if e.code == 404:
            return {}
        else:
            raise RuntimeError("Failed to fetch apps %s HTTP %d (%s) - Response: %s" % (url, e.code, e, e.read())), None, sys.exc_info()[2]
    except urllib2.URLError as e:
        logging.debug(str(e))
        raise RuntimeError("Failed to fetch apps %s (%s)" % (url, e)), None, sys.exc_info()[2]

def notify(targetMarathonUrl, service):
    parsedMarathonUrl = urlparse(targetMarathonUrl)
    tags = ["environment:%s" % service.environment, "service:%s" % service.id]
    title = "Deployed %s to the %s environment" % (service.id, service.environment)

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
        service.uniqueVersion)

    # Send Datadog deployment notification
    datadog = Datadog(
        util.rget(service.document, 'datadog', 'token'),
        util.toList(util.rget(service.document, 'datadog', 'tags')))
    datadog.notify(
        aggregation_key="%s_%s" % (service.environment, service.id),
        title=title,
        message="%%%%%% \n Lighter deployed **%s** with image **%s** to **%s** (%s) \n %%%%%%" % (
            service.id, service.image, service.environment, parsedMarathonUrl.netloc),
        tags=tags)

    # Send Graphite deployment notification
    prefix = (util.rget(service.document, 'graphite', 'prefix') or 'lighter').strip('.')
    metricname = '%s.%s.%s.deployments' % (
        prefix, service.environment,
        '.'.join(filter(bool, service.id.split('/'))))

    graphite = Graphite(
        util.rget(service.document, 'graphite', 'address'),
        util.rget(service.document, 'graphite', 'url'),
        util.toList(util.rget(service.document, 'graphite', 'tags')))
    graphite.notify(
        metricname=metricname,
        title=title,
        message="Lighter deployed %s with image %s to %s (%s)" % (
            service.id, service.image, service.environment, parsedMarathonUrl.netloc),
        tags=tags)

def deploy(marathonurl, filenames, noop=False, force=False, canaryGroup=None, profiles=[]):
    services = parse_services(filenames, canaryGroup, profiles)

    for service in services:
        try:
            targetMarathonUrl = marathonurl or util.rget(service.document, 'marathon', 'url')
            if not targetMarathonUrl:
                raise RuntimeError("No Marathon URL defined for service %s" % service.filename)

            # See if service config has changed by comparing the checksum
            appurl = get_marathon_appurl(targetMarathonUrl, service.config['id'], force)
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

            # Send deployment notifications
            notify(targetMarathonUrl, service)
        except urllib2.HTTPError as e:
            raise RuntimeError("Failed to deploy %s HTTP %d (%s) - Response: %s" % (service.filename, e.code, e, e.read())), None, sys.exc_info()[2]
        except urllib2.URLError as e:
            raise RuntimeError("Failed to deploy %s (%s)" % (service.filename, e)), None, sys.exc_info()[2]

    return services

def verify(filenames, canaryGroup=None, profiles=[]):
    return parse_services(filenames, canaryGroup, profiles)


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
    parser.add_argument('-p', '--profile', dest='profiles', default=[], action='append', help='Extra profile files to be merged with service definitions.')

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

    deploy_parser.add_argument('--canary-group', dest='canaryGroup', help='Unique name for this group of canaries [default: %(default)s]',
                               default=None)
    deploy_parser.add_argument('--canary-cleanup', dest='canaryCleanup', help='Destroy canaries that are no longer present [default: %(default)s]',
                               action='store_true', default=False)

    deploy_parser.add_argument('filenames', metavar='YMLFILE', nargs='*',
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
        services = []
        if args.command == 'deploy':
            services = deploy(args.marathon, noop=args.noop, force=args.force, filenames=args.filenames, canaryGroup=args.canaryGroup, profiles=args.profiles)

            # Destroy canaries that are no longer rendered
            if args.canaryGroup and args.canaryCleanup:
                if not args.marathon:
                    raise RuntimeError("Canary cleanup requires Marathon URL to be given on the command line")
                cleanup_canaries(args.marathon, args.canaryGroup, services, args.noop)
        elif args.command == 'verify':
            services = verify(args.filenames, profiles=args.profiles)

            # Check for unencrypted secrets
            verify_secrets(services, args.verifySecrets)

        # Dump rendered files to disk
        if args.targetdir:
            write_services(args.targetdir, services)
    except RuntimeError as e:
        logging.error(str(e))
        sys.exit(1)
