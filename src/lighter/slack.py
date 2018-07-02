import logging
import urllib2
import lighter.util as util
import json

class Slack(object):
    def __init__(self, token, url=None, channels=[]):
        self._token = token
        self._url = url or 'https://slack.com/api'
        self._channels = util.unique(channels or [])
        self._message_attribs = {
            "color": "good",
            "title": "Marathon Deployment Triggered",
            "footer": "Marathon API",
            "footer_icon": "https://raw.githubusercontent.com/mesosphere/marathon-ui/master/src/img/marathon-favicon.ico",
        }

    def notify(self, payload):
        logging.debug("Sending Slack message: %s", json.dumps(payload))
        headers = {
            'Content-type': 'application/json; charset=UTF-8',
            'Authorization': 'Bearer ' + str(self._token or '')
        }
        for channel in self._channels:
            payload_object = {
                "channel": channel,
                "attachments": [
                    util.merge(payload, self._message_attribs)
                ]
            }
            self._call('/chat.postMessage', payload_object, headers)

    def _call(self, endpoint, data, headers):
        if not self._url or not self._token:
            logging.debug('Slack is not enabled')
            return

        try:
            url = self._url.rstrip('/') + endpoint
            logging.debug('Calling Slack endpoint %s', endpoint)
            util.jsonRequest(url, data=data, method='POST', headers=headers)
        except urllib2.URLError as e:
            logging.warn(str(e))
            return {}
