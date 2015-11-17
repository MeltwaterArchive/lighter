import os, urlparse, base64, json, urllib2, logging, itertools, types, re
import urllib
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

def replace(template, variables):
    result = copy(template)

    if isinstance(result, dict):
        for key, value in result.items():
            result[key] = replace(value, variables)
    elif isinstance(result, (list, tuple)):
        result = [replace(elem, variables) for elem in result]
    else:
        if isinstance(result, (str, unicode)):
            remainingvars = copy(variables)
            while True:
                varnames = re.findall(r"%\{([\w\.]+)\}", result)
                if not varnames:
                    break
                for varname in varnames:
                    if varname not in remainingvars:
                        raise KeyError('Variable %%{%s} not found' % varname)
                    result = result.replace('%{' + varname + '}', unicode(remainingvars[varname]))
                    del remainingvars[varname]

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
    if data is not None:
        if contentType == 'application/json':
            body = json.dumps(data)
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

def jsonRequest(url, data=None, headers={}, method='GET', contentType='application/json'):
    logging.debug('%sing url %s', method, url)
    response = urllib2.urlopen(buildRequest(url, data, headers, method, contentType))
    content = response.read()
    if response.info().gettype() == 'application/json' or response.info().gettype() == 'text/plain':
        return json.loads(content)

    logging.debug('Content-Type %s is not json %s', response.info().gettype(), content)
    return {}

def xmlRequest(url, data=None, headers={}, method='GET', contentType='application/json'):
    logging.debug('%sing url %s', method, url)
    response = urllib2.urlopen(buildRequest(url, data, headers, method, contentType)).read()
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
        node = node.get(arg, default)
    return node
