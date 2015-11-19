#!/usr/bin/env python
import os, sys, argparse, logging
import yaml, urllib2, json, ntpath
from urlparse import urlparse
from lighter.hipchat import HipChat
import lighter.util as util
import lighter.maven as maven
from lighter.newrelic import NewRelic


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

def compare_service_versions(nextVersion, prevConfig, path=''):
    if isinstance(nextVersion, dict):
        for key, value in nextVersion.items():
            keypath = path + '/' + key
            if key not in prevConfig:
                logging.debug("New key found %s", keypath)
                return False
            if not compare_service_versions(value, prevConfig[key], keypath):
                return False
    elif isinstance(nextVersion, list):
        if len(nextVersion) != len(prevConfig):
            logging.debug("List have changed at %s", path)
            return False
        for nextValue, prevValue in zip(nextVersion, prevConfig):
            if not compare_service_versions(nextValue, prevValue, path):
                return False
    elif nextVersion != prevConfig:
        if isinstance(nextVersion, int) and isinstance(prevConfig, int) and nextVersion == 0 and path == '/ports':
            return True
        logging.debug("Value has changed at %s (%s != %s)", path, nextVersion, prevConfig)
        return False
    return True

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
        return util.rget(self.config,'container','docker','image') or ''
    
    @property
    def environment(self):
        return util.rget(self.document,'facts','environment') or 'default'

    @property
    def uniqueVersion(self):
        return util.rget(self.document, 'variables', 'lighter.uniqueVersion') or \
               (self.image.split(':')[1] if ':' in self.image else 'latest')

def parse_service(filename):
    with open(filename, 'r') as fd:
        document = yaml.load(fd)

        # Merge globals.yml files into document
        path = os.path.dirname(os.path.abspath(filename))
        while '/' in path:
            candidate = os.path.join(path, 'globals.yml')
            if os.path.exists(candidate):
                with open(candidate, 'r') as fd2:
                    document = util.merge(yaml.load(fd2), document)
            path = path[0:path.rindex('/')]

        # Start from a service section if it exists
        config = document.get('service', {})

        # Fetch and merge json template from maven
        if util.rget(document,'maven','version') or util.rget(document,'maven','resolve'):
            coord = document['maven']
            
            resolver = maven.ArtifactResolver(coord['repository'], coord['groupid'], coord['artifactid'], coord.get('classifier'))
            version = coord.get('version') or resolver.resolve(coord['resolve'])
            
            artifact = resolver.fetch(version)
            document['variables'] = util.merge(
                document.get('variables', {}), 
                {'lighter.version': artifact.version, 'lighter.uniqueVersion': artifact.uniqueVersion})
            config = util.merge(config, artifact.body)

        # Merge overrides into json template
        config = util.merge(config, document.get('override', {}))

        # Substitute variables into the config
        config = util.replace(config, document.get('variables', {}))

        return Service(filename, document, config)

def parse_services(filenames, targetdir=None):
    services = []
    for filename in filenames:
        logging.info("Processing %s", filename)
        service = parse_service(filename)
        services.append(service)

        # Write json file to disk for logging purposes
        if targetdir:
            outputfile = os.path.join(targetdir, service.filename + '.json')
            if not os.path.exists(os.path.dirname(outputfile)):
                os.makedirs(os.path.dirname(outputfile))
            with open(outputfile, 'w') as fd:
                fd.write(json.dumps(service.config, indent=4))

    return services

def get_marathon_url(url, id, force=False):
    return url.rstrip('/') + '/v2/apps/' + id.strip('/') + (force and '?force=true' or '')

def get_marathon_app(url):
    try:
        return util.jsonRequest(url)['app']
    except urllib2.URLError, e:
        logging.debug(str(e))
        return {}

def deploy(marathonurl, filenames, noop=False, force=False, targetdir=None):
    parsedMarathonUrl = urlparse(marathonurl)
    services = parse_services(filenames, targetdir)

    for service in services:
        try:
            appurl = get_marathon_url(marathonurl, service.config['id'], force)

            # See if service config has changed
            prevConfig = get_marathon_app(appurl)
            if compare_service_versions(service.config, prevConfig):
                logging.debug("Service already deployed with same config: %s", service.filename)
                continue

            # Skip deployment if noop flag is given
            if noop:
                continue

            # Deploy new service config
            logging.info("Deploying %s", service.filename)
            util.jsonRequest(appurl, data=service.config, method='PUT')

            # Send HipChat notification
            hipchat = HipChat(
                util.rget(service.document,'hipchat','token'), 
                util.rget(service.document,'hipchat','url'),
                util.rget(service.document,'hipchat','rooms'))
            hipchat.notify("Deployed <b>%s</b> with image <b>%s</b> to <b>%s</b> (%s)" % 
                (service.id, service.image, service.environment, parsedMarathonUrl.netloc))

            # Send NewRelic deployment notification
            newrelic = NewRelic(util.rget(service.document, 'newrelic', 'token'))
            newrelic.notify(
                util.rget(service.config, 'env', 'NEW_RELIC_APP_NAME'),
                service.uniqueVersion
            )

        except urllib2.HTTPError, e:
            raise RuntimeError("Failed to deploy %s HTTP %d (%s)" % (service.filename, e.code, e)), None, sys.exc_info()[2]
        except urllib2.URLError, e:
            raise RuntimeError("Failed to deploy %s (%s)" % (service.filename, e)), None, sys.exc_info()[2]

def verify(filenames, targetdir=None):
    parse_services(filenames, targetdir)

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
    
    deploy_parser.add_argument('-m', '--marathon', required=True, dest='marathon', help='Marathon url, e.g. "http://marathon-host:8080/"',
                      default=os.environ.get('MARATHON_URL', ''))
    deploy_parser.add_argument('-f', '--force', dest='force', help='Force deployment even if the service is already affected by a running deployment [default: %(default)s]',
                      action='store_true', default=False)
    deploy_parser.add_argument('filenames', metavar='YMLFILE', nargs='+',
                       help='Service files to expand and deploy')
    
    # Create the parser for the "verify" command
    deploy_parser = subparsers.add_parser('verify', 
        prog='lighter',
        usage='%(prog)s verify YMLFILE...',
        help='Verify and generate Marathon configuration files',
        description='Verify and generate Marathon configuration files')
    
    deploy_parser.add_argument('filenames', metavar='YMLFILE', nargs='+',
                       help='Service files to expand and deploy')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    try:
        if args.command == 'deploy':
            deploy(args.marathon, noop=args.noop, force=args.force, filenames=args.filenames, targetdir=args.targetdir)
        elif args.command == 'verify':
            verify(args.filenames, targetdir=args.targetdir)
    except RuntimeError, e:
        logging.error(str(e))
        sys.exit(1)
