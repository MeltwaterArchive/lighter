import urlparse, base64, json, urllib2

def merge_two_dicts(a, b):
    result = {}

    for key in set(a.keys() + b.keys()):
        aval = a.get(key)
        bval = b.get(key)
        if isinstance(aval, dict) or isinstance(bval, dict):
            result[key] = merge_two_dicts(aval or {}, bval or {})
        else:
            result[key] = bval or aval

    return result

def merge_dicts(*dicts):
    result = {}
    for dts in dicts:
        result = merge_two_dicts(result, dts)

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
