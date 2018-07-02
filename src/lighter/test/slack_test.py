import unittest
from mock import patch, ANY
from lighter.slack import Slack

class SlackTest(unittest.TestCase):
    @patch('lighter.util.jsonRequest')
    def testNotify(self, mock_jsonRequest):
        Slack(token='abc', channels=['123', '123', '456']).notify("Test message")
        mock_jsonRequest.assert_any_call('https://slack.com/api/chat.postMessage', data=ANY, method='POST', headers={
            'Content-type': 'application/json; charset=UTF-8', 'Authorization': 'Bearer abc'
        })
        mock_jsonRequest.assert_any_call('https://slack.com/api/chat.postMessage', data=ANY, method='POST', headers={
            'Content-type': 'application/json; charset=UTF-8', 'Authorization': 'Bearer abc'
        })
        self.assertEquals(mock_jsonRequest.call_count, 2)
