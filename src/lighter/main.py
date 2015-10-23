#!/usr/bin/env python
import os, sys, optparse, logging
from pprint import pprint
import yaml, urllib2, json, ntpath
from lighter.hipchat import HipChat
from lighter.util import *

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

def parse_file(filename):
    with open(filename, 'r') as fd:
        document = yaml.load(fd)

        # Merge globals.yml files into document
        path = os.path.dirname(os.path.abspath(filename))
        while '/' in path:
            candidate = os.path.join(path, 'globals.yml')
            if os.path.exists(candidate):
                with open(candidate, 'r') as fd2:
                    document = merge(yaml.load(fd2), document)
            path = path[0:path.rindex('/')]

        # Fetch json template from maven
        maven = document['maven']
        config = get_json('{0}/{1}/{2}/{3}/{2}-{3}.json'.format(maven['repository'], maven['groupid'].replace('.', '/'), maven['artifactid'], maven['version']))

        # Merge overrides into json template
        config = merge(config, document.get('override', {}))

        # Substitute variables into the config
        config = replace(config, document.get('variables', {}))

        return Service(document, config)

def get_marathon_url(url, id):
    return url.rstrip('/') + '/v2/apps/' + id.strip('/') + '?force=true'

def get_marathon_app(url):
    try:
        return get_json(url)['app']
    except urllib2.URLError, e:
        logging.debug(str(e))
        return {}

if __name__ == '__main__':
    parser = optparse.OptionParser(
        usage='lighter.py [options]... service.yml service2.yml',
        description='Marathon deployment tool')

    parser.add_option('-m', '--marathon', dest='marathon', help='Marathon url, e.g. "http://marathon-01:8080/"',
                      default=os.environ.get('MARATHON_URL', ''))

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

    for file in args:
        logging.info("Processing %s", file)
        service = parse_file(file)
        appurl = get_marathon_url(options.marathon, service.config['id'])

        # See if service config has changed
        prevConfig = get_marathon_app(appurl)
        if compare_service_versions(service.config, prevConfig):
            logging.debug("Service already deployed with same config: %s", file)

        # Deploy new service config
        logging.debug("Deploying %s", file)
        request = build_request(appurl, service.config, {}, 'PUT')
        response = urllib2.urlopen(request)

        # Send HipChat notification
        hipchat = HipChat(rget(service.document,'hipchat','url'), rget(service.document,'hipchat','token')).rooms(["2087542"])
        hipchat.notify("Deployed <b>%s</b> in version <b>%s</b>" % (service.config['id'], service.config['container']['docker']['image']))
