import logging
import traceback
import urllib2
import lighter.util as util


class NewRelic(object):
    """
    For ref see https://docs.newrelic.com/docs/apm/new-relic-apm/maintenance/deployment-notifications
    """

    def __init__(self, token):
        self._url = 'https://api.newrelic.com/deployments.xml'
        self._token = token

    def notify(self, app_name, version, description=None, changelog=None):
        if not self._token:
            logging.debug('No New Relic api key configured for %s', app_name)
            return

        if not app_name:
            logging.debug('No New Relic app name configured, app is most likely not on NewRelic')
            return

        logging.debug("Sending deployment notification to New Relic: %s %s %s %s", app_name, version, description,
                      changelog)

        try:
            headers = {
                'x-api-key': self._token
            }

            data = {
                'deployment[app_name]': app_name,
                'deployment[revision]': version,
                'deployment[description]': description,
                'deployment[changelog]': changelog,
                'deployment[user]': 'Lighter'
            }

            return util.xmlRequest(self._url, method='POST', data=data, headers=headers, contentType='application/x-www-form-urlencoded')

        except urllib2.URLError, e:
            logging.warn(str(e))
            print traceback.format_exc()
            return {}

