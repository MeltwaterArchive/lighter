import unittest
from mock import patch, ANY
from lighter.hipchat import HipChat
import lighter.util

class HipChatTest(unittest.TestCase):
	@patch('lighter.util.get_json')
	def testNotify(self, mock_get_json):
		hipchat = HipChat(token='abc', rooms=['123','123','456']).notify("Test message")
		mock_get_json.assert_any_call('https://api.hipchat.com/v2/room/123/notification?auth_token=abc', data=ANY, method='POST')
		mock_get_json.assert_any_call('https://api.hipchat.com/v2/room/456/notification?auth_token=abc', data=ANY, method='POST')
		self.assertEquals(mock_get_json.call_count, 2)
