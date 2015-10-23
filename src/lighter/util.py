import os, urlparse, base64, json, urllib2
from copy import copy

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
            else:
                result[key] = bval or aval

    return result

def replace(template, variables):
    result = copy(template)

    if isinstance(result, dict):
        for key, value in result.items():
            result[key] = replace(value, variables)
    elif isinstance(result, list) or isinstance(result, tuple):
        result = [replace(elem, variables) for elem in result]
    else:
        if isinstance(result, str) or isinstance(result, unicode) and '${' in result:
            for varkey, varval in variables.items():
                result = result.replace('${' + varkey + '}', unicode(varval))

    return result

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

def build_request(url, data=None, headers={}, method='GET'):
    parsed_url = urlparse.urlparse(url)
    parts = list(parsed_url[0:6])
    parts[1] = ('@' in parts[1]) and parts[1].split('@')[1] or parts[1]

    body = None
    if data is not None:
        body = json.dumps(data)
        headers['Content-Type'] = 'application/json'

    request = urllib2.Request(urlunparse(parts), body, headers)
    request.get_method = lambda: method

    if parsed_url.username is not None and parsed_url.password is not None:
        # You need the replace to handle encodestring adding a trailing newline
        # (https://docs.python.org/2/library/base64.html#base64.encodestring)
        base64string = base64.encodestring('%s:%s' % (parsed_url.username, parsed_url.password)).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)

    return request

def get_json(url):
    response = urllib2.urlopen(build_request(url)).read()
    return json.loads(response)

def rget(root, *args):
    node = root
    for arg, i in zip(args, range(len(args))):
        node = node.get(arg, i < len(args)-1 and {} or None)
    return node

def rchmod(path, dirmode, filemode=None):
    for root, dirs, files in os.walk(path):  
      for entry in dirs:
        os.chmod(os.path.join(root, entry), dirmode)
      for entry in files:
        os.chmod(os.path.join(root, entry), filemode or dirmode)
