import unittest
from mock import patch
from lighter.newrelic import NewRelic


class NewRelicTest(unittest.TestCase):
    @patch('lighter.util.xmlRequest')
    def testNotify(self, mock_xmlRequest):

        newrelic = NewRelic('iamanapitoken')

        newrelic.notify('FH Dev API SearchService', '1.2.3-test')
        newrelic.notify('FH Dev API SearchService', '1.2.4-test', 'just testing')
        newrelic.notify('FH Dev API SearchService', '1.2.5-test', 'just testing', 'changed something')

        self.assertEquals(mock_xmlRequest.call_count, 3)

    @patch('lighter.util.xmlRequest')
    def testNoNewRelicApiKey(self, mock_xmlRequest):

        newrelic = NewRelic('')

        newrelic.notify('FH Dev API SearchService', '1.2.3-test')

        self.assertEquals(mock_xmlRequest.call_count, 0)

    @patch('lighter.util.xmlRequest')
    def testAppNotInNewRelic(self, mock_xmlRequest):

        newrelic = NewRelic('iamanapitoken')

        newrelic.notify(None, '1.2.3-test')
        newrelic.notify('', '1.2.4-test')

        self.assertEquals(mock_xmlRequest.call_count, 0)
