import logging, urllib2
import lighter.util as util

class Datadog(object):
    def __init__(self, token):
        self._token = token
        self._url = 'https://app.datadoghq.com'
        self._message_attribs = {
            'aggregation_key': 'Lighter Deployment',
            'source_type_name': 'lighter'
        }

    def notify(self, title, message, tags=[], priority='normal', alert_type='info'):
        if not title or not message:
            logging.warn('Datadog title and message required')
            return
        
        logging.debug("Sending Datadog event: %s", message)
        self._call('/api/v1/events', util.merge(self._message_attribs, {
            'title': title,
            'text': message,
            'tags':tags,
            'priority': priority,
            'alert_type': alert_type
        }))

    def _call(self, endpoint, data):
        if not self._url or not self._token:
            logging.debug('Datadog is not enabled')
            return

        try:
            url = self._url.rstrip('/') + endpoint + '?api_key=' + self._token
            logging.debug('Calling Datadog endpoint %s', endpoint)
            util.jsonRequest(url, data=data, method='POST')
        except urllib2.URLError, e:
            logging.warn(str(e))
            return {}
