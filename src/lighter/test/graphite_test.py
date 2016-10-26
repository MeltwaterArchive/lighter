import unittest
from mock import patch
from lighter.graphite import Graphite

class GraphiteTest(unittest.TestCase):
    @patch('lighter.util.jsonRequest')
    def testNotify(self, mock_jsonRequest):
        graphite = Graphite('localhost:2003', 'http://localhost:80/', 'lighter.deployments')

        graphite.notify('Deployed myservice', 'Deployed myservice to production environment')
        graphite.notify('Deployed myservice', 'Deployed myservice to production environment', ['subsystem:something'])

        self.assertEquals(mock_jsonRequest.call_count, 2)

    @patch('lighter.util.jsonRequest')
    def testNoGraphiteUrl(self, mock_jsonRequest):
        graphite = Graphite('', '', '')

        graphite.notify('Deployed myservice', 'Deployed myservice to production environment')

        self.assertEquals(mock_jsonRequest.call_count, 0)
