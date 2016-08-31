import logging
import urllib2
import time
import lighter.util as util

class Datadog(object):
    def __init__(self, token, tags=[]):
        self._token = token
        self._url = 'https://app.datadoghq.com'
        self._tags = tags + ['source:lighter', 'type:change']

    def notify(self, title, message, aggregation_key, tags=[], priority='normal', alert_type='success'):
        if not title or not message or not aggregation_key:
            logging.warn('Datadog title, message and aggregation_key required')
            return

        merged_tags = list(tags) + self._tags
        now = int(time.time())

        logging.debug("Sending Datadog deployment metric: %s", message)
        self._call('/api/v1/series', {'series': [{
            'metric': 'lighter.deployments',
            'points': [[now, 1]],
            'tags': merged_tags
        }]})

        logging.debug("Sending Datadog event: %s", message)
        self._call('/api/v1/events', {
            'title': title,
            'text': message,
            'aggregation_key': 'lighter_' + aggregation_key,
            'tags': merged_tags,
            'priority': priority,
            'alert_type': alert_type,
            'date_happened': now
        })

    def _call(self, endpoint, data):
        if not self._url or not self._token:
            logging.debug('Datadog is not enabled')
            return

        try:
            url = self._url.rstrip('/') + endpoint + '?api_key=' + self._token
            logging.debug('Calling Datadog endpoint %s', endpoint)
            util.jsonRequest(url, data=data, method='POST')
        except urllib2.URLError as e:
            logging.warn(str(e))
            return {}
