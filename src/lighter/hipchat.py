import logging, urllib2
import lighter.util as util

class HipChat(object):
    def __init__(self, token, url=None, rooms=[]):
        self._token = token
        self._url = url or 'https://api.hipchat.com'
        self._rooms = util.unique(rooms or [])
        self._sender = 'Lighter'
        self._message_attribs = {
            'color': 'green',
            'notify': True,
            'message_format': 'html'
        }

    def notify(self, message):
        logging.debug("Sending HipChat message: %s", message)
        for room in self._rooms:
            self._call('/v2/room/%s/notification' % room, util.merge({'message': message}, self._message_attribs))

    def _call(self, endpoint, data):
        if self._url is None or self._token is None:
            logging.debug('HipChat is not enabled')
            return

        try:
            url = self._url.rstrip('/') + endpoint + '?auth_token=' + self._token
            logging.debug('Calling HipChat endpoint %s', endpoint)
            util.get_json(url, data=data, method='POST')
        except urllib2.URLError, e:
            logging.warn(str(e))
            return {}
