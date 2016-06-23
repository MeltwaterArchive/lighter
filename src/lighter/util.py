import os
import sys
import logging
import re
import urllib
import urllib2
import urlparse
import base64
import json
import hashlib
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

def merge(aval, bval, path=''):
    aval = copy(aval)

    if isinstance(aval, (list, tuple)) and isinstance(bval, (dict)):
        # Override and deep merge specific list items
        aval = toList(aval)
        for key, value in bval.items():
            if int(key) < 0 or int(key) >= len(aval):
                raise IndexError("The given list override index %s[%d] doesn't exist" % (path.lstrip('.'), int(key)))
            aval[int(key)] = merge(aval[int(key)], value, '%s[%d]' % (path, int(key)))
    elif isinstance(aval, dict) and isinstance(bval, dict):
        # Deep merge dicts
        for key in set(aval.keys() + bval.keys()):
            asubval = aval.get(key)
            bsubval = bval.get(key)
            aval[key] = merge(asubval, bsubval, '%s.%s' % (path, key))
    elif isinstance(aval, (list, tuple)) and isinstance(bval, (list, tuple)):
        # Append lists
        aval = toList(aval) + toList(bval)
    elif bval is not None:
        # Scalar values
        aval = bval

    return aval

class FixedVariables(object):
    def __init__(self, variables):
        self._variables = variables

    def clone(self):
        return FixedVariables(copy(self._variables))

    def pop(self, name):
        if name not in self._variables:
            raise KeyError('Variable %%{%s} not found' % name)
        return self._variables.pop(name)

class EnvironmentVariables(object):
    def __init__(self, wrappedResolver):
        self._wrappedResolver = wrappedResolver

    def clone(self):
        return EnvironmentVariables(self._wrappedResolver.clone())

    def pop(self, name):
        if name.startswith('env.'):
            return os.environ[name[4:]]
        return self._wrappedResolver.pop(name)

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

def replace(template, variables, raiseError=True, escapeVar=True):
    result = copy(template)

    if isinstance(result, dict):
        for key, value in result.items():
            result[key] = replace(value, variables, raiseError, escapeVar)
    elif isinstance(result, (list, tuple)):
        result = [replace(elem, variables, raiseError, escapeVar) for elem in result]
    else:
        if isinstance(result, (str, unicode)):
            remaining = variables.clone()
            replacements = 1

            while replacements > 0:
                replacements = 0
                names = re.findall(r"(?<!%)%\{(\s*[\w\.]+\s*)\}", result)

                if not names:
                    break
                for name in set([name.strip() for name in names]):
                    try:
                        value = unicode(remaining.pop(name))
                        result = re.sub('%{\s*' + re.escape(name) + '\s*}', value, result)
                        replacements += 1
                    except KeyError as e:
                        if raiseError:
                            raise KeyError(e.message), None, sys.exc_info()[2]

            # Replace double %%{foo} with %{foo}
            if escapeVar:
                result = re.sub(r"%%\{(\s*[\w\.]+\s*)\}", "%{\\1}", result)

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
    contenttype = response.info().gettype()
    if contenttype == 'application/json' or contenttype == 'text/plain' or 'docker.distribution.manifest' in contenttype:
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
        if i + 1 >= len(args):
            default = None
        if isinstance(node, (list, tuple)):
            node = node[arg] if (arg >= 0 and arg < len(node)) else default
        else:
            node = node.get(arg, default)
    return node
