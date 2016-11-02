import logging
import urllib2
import socket
import time
import re
import lighter.util as util

class Graphite(object):
    def __init__(self, address, url, tags=[]):
        """
        @param  address    hostname:port where the Graphite listens for the plaintext protocol, usually port 2003
        @param  url         URL where Graphite's API is, usually port 80
        """
        self._address = address
        self._url = url
        self._tags = tags + ['source:lighter', 'type:change']

    def notify(self, metricname, title, message, tags=[]):
        if not title or not message:
            logging.warn('Graphite event title and message')
            return

        merged_tags = list(tags) + self._tags
        now = int(time.time())

        logging.debug('Sending Graphite deployment event %s', message)
        self._send(self._address, '%s 1 %s\n' % (metricname, now))

        # For info on Graphite tags and filtering see
        # https://github.com/grafana/grafana/issues/1474#issuecomment-105811191
        self._call('/events/', {
            'what': title,
            'data': message,
            'tags': ' '.join(self._mangle(tag) for tag in merged_tags),
            'when': now
        })

    def _mangle(self, tag):
        return re.sub('[\s,]', '_', tag.strip())

    def _send(self, address, data):
        if not self._address or not self._url:
            logging.debug('Graphite is not enabled')
            return

        ip, port = address.split(':')
        try:
            logging.debug('Sending Graphite metric to %s:%s' % (ip, port))
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect((ip, int(port)))
                sock.send(data)
            finally:
                sock.close()
        except (socket.error, ValueError) as e:
            logging.warn(str(e))

    def _call(self, endpoint, data):
        if not self._address or not self._url:
            logging.debug('Graphite is not enabled')
            return

        try:
            url = self._url.rstrip('/') + endpoint
            logging.debug('Calling Graphite endpoint %s', endpoint)
            util.jsonRequest(url, data=data, method='POST')
        except urllib2.URLError as e:
            logging.warn(str(e))
            return {}
