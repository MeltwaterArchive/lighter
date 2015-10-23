import logging, urllib2
from lighter.util import merge_dicts, build_request

class HipChat(object):
    def __init__(self, url, token):
        self._url = url
        self._token = token
        self_rooms = []
        self._sender = 'Lighter'
        self._message_attribs = {
            'from': 'Lighter',
            'color': 'green',
            'notify': True,
            'message_format': 'html'
        }

    def rooms(self, ids):
        self._rooms = ids
        return self

    def notify(self, message):
        for room in self._rooms:
            self._call('/v2/room/%s/notification' % room, merge_dicts({'message': message}, self._message_attribs))

    def _call(self, endpoint, data):
        try:
            url = self._url.rstrip('/') + '/' + endpoint + '?auth_token=' + self._token
            response = urllib2.urlopen(build_request(url, data, {}, 'POST'))
            content = response.read()
        except urllib2.URLError, e:
            logging.warn(str(e))
            return {}
