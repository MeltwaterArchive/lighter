#!/usr/bin/env python
import os, sys, optparse, logging
from pprint import pprint
import yaml, urllib2, json

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

def merge(a, b):
    result = {}

    for key in set(a.keys() + b.keys()):
        aval = a.get(key)
        bval = b.get(key)
        if isinstance(aval, dict) or isinstance(bval, dict):
            result[key] = merge(aval or {}, bval or {})
        else:
            result[key] = bval or aval

    return result

def parse_file(file):
    with open(file, 'r') as stream:
        doc = yaml.load(stream)
        repository = doc['maven']['repository']
        url = '{0}/{1}/{2}/{3}/{2}-{3}.json'.format(repository, doc['maven']['groupid'].replace('.', '/'), doc['maven']['artifactid'], doc['maven']['version'])
        response = urllib2.urlopen(url).read()
        json_response = json.loads(response)
        merged_content = merge(json_response, doc['override'])
        return merged_content


def get_marathon_url(url, id):
    return url.rstrip('/') + '/v2/apps/' + id.strip('/')

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
        file_content = parse_file(file)
        serialized_json = json.dumps(file_content)
        pprint(serialized_json)
        request = urllib2.Request(get_marathon_url(options.marathon, file_content['id']), serialized_json, {'Content-Type': 'application/json'})
        request.get_method = lambda: 'PUT'
        response = urllib2.urlopen(request)
        pprint(response.read())

