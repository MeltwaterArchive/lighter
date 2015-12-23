import os, sys, logging, itertools, types, re
import urllib, urllib2, urlparse, base64, json, hashlib
import xml.dom.minidom as minidom
from copy import copy

def hashable(a):
    return not isinstance(a, (dict, list, tuple))

def unique(a):
    result = list(set(value for value in a if hashable(value)))
    result.extend([value for value in a if not hashable(value)])
    return result

def toList(a):
    if isinstance(a, (list, tuple)):
        return a
    return [a] if (a is not None) else []

def merge(*args):
    args = list(args)
    result = copy(args.pop(0))

    while args:
        b = args.pop(0)

        for key in set(result.keys() + b.keys()):
            aval = result.get(key)
            bval = b.get(key)
            if isinstance(aval, dict) or isinstance(bval, dict):
                result[key] = merge(aval or {}, bval or {})
            elif isinstance(aval, (list, tuple)) or isinstance(bval, (list, tuple)):
                result[key] = toList(aval) + toList(bval)
            else:
                result[key] = bval if (bval is not None) else aval

    return result

class FixedVariables(object):
    def __init__(self, variables):
        self._variables = variables

    def clone(self):
        return FixedVariables(copy(self._variables))

    def pop(self, name):
        if name not in self._variables:
            raise KeyError('Variable %%{%s} not found' % name)
        return self._variables.pop(name)

class Value(object):
    """
    Allows to override the test when service.config is compared
    against the previous version to see if it needs redeployment.
    """
    def __init__(self, value):
        self._value = value

    def __str__(self):
        return str(self._value)

    def __repr__(self):
        return repr(self._value)

    def __cmp__(self, other):
        return cmp(self._value, str(other))

    def __getitem__(self, a):
        return self._value[a]

    def __getslice__(self, a, b):
        return self._value[a:b]

    def same(self, other):
        return self == other

    def hashstr(self):
        return str(self)

class ValueEncoder(json.JSONEncoder):
    def default(self, value):
        if isinstance(value, Value):
            return str(value)
        return value

class HashEncoder(json.JSONEncoder):
    def default(self, value):
        if isinstance(value, Value):
            return value.hashstr()
        return value

def checksum(value):
    jsonvalue = json.dumps(value, cls=HashEncoder)
    return hashlib.md5(jsonvalue).hexdigest()

def toJson(value, *args, **kwargs):
    return json.dumps(value, cls=ValueEncoder, *args, **kwargs)

def replace(template, variables):
    result = copy(template)

    if isinstance(result, dict):
        for key, value in result.items():
            result[key] = replace(value, variables)
    elif isinstance(result, (list, tuple)):
        result = [replace(elem, variables) for elem in result]
    else:
        if isinstance(result, (str, unicode)):
            remaining = variables.clone()
            while True:
                names = re.findall(r"(?<!%)%\{([\w\.]+)\}", result)
                if not names:
                    break
                for name in names:
                    value = unicode(remaining.pop(name))
                    result = result.replace('%{' + name + '}', value)
            while True:
                names = re.findall(r"%%\{([\w\.]+)\}", result)
                if not names:
                    break
                for name in names:
                    value = unicode(remaining.pop(name))
                    result = result.replace('%%{' + name + '}', '%{' + name + '}')

    return result

def find(collection, condition, default=None):
    for item in toList(collection):
        if condition(item):
            return item
    return default

def urlunparse(data):
    """
    Modified from urlparse.urlunparse to support file://./path/to urls
    """
    scheme, netloc, url, params, query, fragment = data
    if params:
        url = "%s;%s" % (url, params)
    if netloc:
        url = '//' + (netloc or '') + url
    if scheme:
        url = scheme + ':' + url
    if query:
        url = url + '?' + query
    if fragment:
        url = url + '#' + fragment
    return url

def buildRequest(url, data=None, headers={}, method='GET', contentType='application/json'):
    parsed_url = urlparse.urlparse(url)
    parts = list(parsed_url[0:6])
    parts[1] = ('@' in parts[1]) and parts[1].split('@')[1] or parts[1]

    body = None
    headers = copy(headers)

    if data is not None:
        if contentType == 'application/json':
            body = toJson(data)
            headers['Content-Type'] = 'application/json'
        elif contentType == 'application/x-www-form-urlencoded':
            body = urllib.urlencode(data)
            headers['Content-Type'] = 'application/x-www-form-urlencoded'

    request = urllib2.Request(urlunparse(parts), body, headers)
    request.get_method = lambda: method

    if parsed_url.username is not None and parsed_url.password is not None:
        # You need the replace to handle encodestring adding a trailing newline
        # (https://docs.python.org/2/library/base64.html#base64.encodestring)
        base64string = base64.encodestring('%s:%s' % (parsed_url.username, parsed_url.password)).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)

    return request

def openRequest(request, timeout=None):
    cafile = os.path.join(sys._MEIPASS, 'requests', 'cacert.pem') if getattr(sys, 'frozen', None) else None
    return urllib2.urlopen(request, cafile=cafile, timeout=timeout)

def jsonRequest(url, data=None, headers={}, method='GET', contentType='application/json', timeout=None):
    logging.debug('%sing url %s', method, url)
    response = openRequest(buildRequest(url, data, headers, method, contentType), timeout=timeout)
    content = response.read()
    if response.info().gettype() == 'application/json' or response.info().gettype() == 'text/plain':
        return json.loads(content)

    logging.debug('Content-Type %s is not json %s', response.info().gettype(), content)
    return {}

def xmlRequest(url, data=None, headers={}, method='GET', contentType='application/json', timeout=None):
    logging.debug('%sing url %s', method, url)
    response = openRequest(buildRequest(url, data, headers, method, contentType), timeout=timeout).read()
    return xmlTransform(minidom.parseString(response).documentElement)

def xmlText(nodelist):
    result = ''
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            result += node.data
        else:
            result += xmlText(node.childNodes)
    return result

def xmlTransform(node):
    result = {}

    for child in node.childNodes:
        if child.nodeType != node.TEXT_NODE:
            value = xmlTransform(child)
            item = result.get(child.tagName)
            if item is None:
                item = value
            elif isinstance(item, list):
                item.append(value)
            else:
                item = [item, value]
            result[child.tagName] = item

    return result or xmlText(node.childNodes)

def rget(root, *args):
    node = root
    default = {}
    for arg, i in zip(args, range(len(args))):
        if i+1 >= len(args):
            default = None
        if isinstance(node, (list, tuple)):
            node = node[arg] if (arg >= 0 and arg < len(node)) else default
        else:
            node = node.get(arg, default)
    return node
