import unittest
from mock import patch, ANY
from lighter.datadog import Datadog
import lighter.util

class DatadogTest(unittest.TestCase):
    @patch('lighter.util.jsonRequest')
    def testNotify(self, mock_jsonRequest):
        datadog = Datadog('abc').notify(title='test title', message='test message', id='/jenkins/test', tags=['environment:test'], priority='normal', alert_type='info')
        self.assertEquals(mock_jsonRequest.call_count, 1)
        mock_jsonRequest.assert_any_call('https://app.datadoghq.com/api/v1/events?api_key=abc', data=ANY, method='POST')
    
    @patch('lighter.util.jsonRequest')
    def testNoApiKey(self, mock_jsonRequest):
        datadog = Datadog('').notify(title='test title', message='test message', id='/jenkins/test', tags=['environment:test'], priority='normal', alert_type='info')
        self.assertEquals(mock_jsonRequest.call_count, 0)
        
    @patch('lighter.util.jsonRequest')
    def testNoTitle(self, mock_jsonRequest):
        datadog = Datadog('abc').notify(title='', message='test message', id='/jenkins/test', tags=['environment:test'], priority='normal', alert_type='info')
        self.assertEquals(mock_jsonRequest.call_count, 0)
    
    @patch('lighter.util.jsonRequest')
    def testNoMessage(self, mock_jsonRequest):
        datadog = Datadog('abc').notify(title='test title', message='', id='/jenkins/test', tags=['environment:test'], priority='normal', alert_type='info')
        self.assertEquals(mock_jsonRequest.call_count, 0)
    
    @patch('lighter.util.jsonRequest')
    def testNoID(self, mock_jsonRequest):
        datadog = Datadog('abc').notify(title='test title', message='test message', id='', tags=['environment:test'], priority='normal', alert_type='info')
        self.assertEquals(mock_jsonRequest.call_count, 0)
