import unittest
from mock import patch, ANY
from lighter.hipchat import HipChat

class HipChatTest(unittest.TestCase):
    @patch('lighter.util.jsonRequest')
    def testNotify(self, mock_jsonRequest):
        HipChat(token='abc', rooms=['123', '123', '456']).notify("Test message")
        mock_jsonRequest.assert_any_call('https://api.hipchat.com/v2/room/123/notification?auth_token=abc', data=ANY, method='POST')
        mock_jsonRequest.assert_any_call('https://api.hipchat.com/v2/room/456/notification?auth_token=abc', data=ANY, method='POST')
        self.assertEquals(mock_jsonRequest.call_count, 2)
