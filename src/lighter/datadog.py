import logging, urllib2
import lighter.util as util

class Datadog(object):
    def __init__(self, api_key, url=None):
        self._api_key = api_key
        self._url = url or 'https://app.datadoghq.com'
        self._message_attribs = {
            'aggregation_key': 'Lighter Deployment',
            'source_type_name': 'lighter'
        }

    def notify(self, title, message, tags=[], priority='normal', alert_type='info'):
        if self._api_key is None or self._api_key is '':
            logging.debug('No Datadog api key configured')
            return
        
        if title is None or title is '':
            logging.debug('Datadog title required')
            return
        
        if message is None or message is '':
            logging.debug('Datadog message required')
            return

        logging.debug("Sending Datadog event: %s", message)
        self._call('/api/v1/events', util.merge(self._message_attribs, {
            'title': title,
            'message': message,
            'tags':tags,
            'priority': priority,
            'alert_type': alert_type
        }))

    def _call(self, endpoint, data):
        if self._url is None or self._api_key is None:
            logging.debug('Datadog is not enabled')
            return

        try:
            url = self._url.rstrip('/') + endpoint + '?api_key=' + self._api_key
            logging.debug('Calling Datadog endpoint %s', endpoint)
            util.jsonRequest(url, data=data, method='POST')
        except urllib2.URLError, e:
            logging.warn(str(e))
            return {}
