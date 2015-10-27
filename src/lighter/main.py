#!/usr/bin/env python
import os, sys, optparse, logging
from urlparse import urlparse
from pprint import pprint
import yaml, urllib2, json, ntpath
from lighter.hipchat import HipChat
import lighter.util as util
import lighter.maven as maven

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
        for nextValue, prevValue in zip(sorted(nextVersion), sorted(prevConfig)):
            if not compare_service_versions(nextValue, prevValue, path):
                return False
    elif nextVersion != prevConfig:
        logging.debug("Value has changed at %s (%s != %s)", path, nextVersion, prevConfig)
        return False
    return True

class Service(object):
    def __init__(self, document, config):
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

def parse_file(filename):
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

        # Fetch json template from maven
        coord = document['maven']
        resolver = maven.ArtifactResolver(coord['repository'], coord['groupid'], coord['artifactid'])
        version = coord.get('version') or resolver.resolve(coord['resolve'])
        config = resolver.get(version)

        # Merge overrides into json template
        config = util.merge(config, document.get('override', {}))

        # Substitute variables into the config
        config = util.replace(config, document.get('variables', {}))

        return Service(document, config)

def get_marathon_url(url, id):
    return url.rstrip('/') + '/v2/apps/' + id.strip('/') + '?force=true'

def get_marathon_app(url):
    try:
        return util.get_json(url)['app']
    except urllib2.URLError, e:
        logging.debug(str(e))
        return {}

def deploy(marathonurl, noop, files):
    parsedMarathonUrl = urlparse(marathonurl)

    services = []
    for file in files:
        logging.info("Processing %s", file)
        service = parse_file(file)
        services.append(service)

    for service in services:
        appurl = get_marathon_url(marathonurl, service.config['id'])
        modified = True

        # See if service config has changed
        prevConfig = get_marathon_app(appurl)
        if compare_service_versions(service.config, prevConfig):
            logging.debug("Service already deployed with same config: %s", file)
            modified = False

        # Deploy new service config
        if not noop:
            logging.debug("Deploying %s", file)
            util.get_json(appurl, data=service.config, method='PUT')

        # Send HipChat notification
        if modified and not noop:
            hipchat = HipChat(
                util.rget(service.document,'hipchat','url'), 
                util.rget(service.document,'hipchat','token')).rooms(
                    util.rget(service.document,'hipchat','rooms'))
            hipchat.notify("Deployed <b>%s</b> using image <b>%s</b> to <b>%s</b> (%s)" % 
                (service.id, service.image, service.environment, parsedMarathonUrl.netloc))

        # Write json file to disk for logging purposes
        basedir = '/tmp/lighter'
        outputfile = os.path.join(basedir, file + '.json')
        if not os.path.exists(os.path.dirname(outputfile)):
            os.makedirs(os.path.dirname(outputfile))
        with open(outputfile, 'w') as fd:
            fd.write(json.dumps(service.config, indent=4))

if __name__ == '__main__':
    parser = optparse.OptionParser(
        usage='docker run --rm -v "`pwd`:/site" meltwater/lighter:latest [options]... production/service.yml production/service2.yml',
        description='Marathon deployment tool')

    parser.add_option('-m', '--marathon', dest='marathon', help='Marathon url, e.g. "http://marathon-host:8080/"',
                      default=os.environ.get('MARATHON_URL', ''))

    parser.add_option('-n', '--noop', dest='noop', help='Execute dry-run without modifying Marathon',
                      action='store_true', default=parsebool(os.environ.get('MARATHON_URL', 'false')))

    parser.add_option('-v', '--verbose', dest='verbose', help='Increase logging verbosity',
                      action="store_true", default=parsebool(os.environ.get('VERBOSE', False)))

    (options, args) = parser.parse_args()

    if options.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    if not options.marathon:
        parser.print_help()
        sys.exit(1)

    deploy(options.marathon, options.noop, args)
