import unittest
from mock import patch, ANY
from lighter.hipchat import HipChat
import lighter.util

class HipChatTest(unittest.TestCase):
	def setUp(self):
		self.hipchat = HipChat(token='abc')

	@patch('lighter.util.get_json')
	def test_notify(self, mock_get_json):
		self.hipchat.rooms(['123456']).notify("Test message")
		mock_get_json.assert_called_with('https://api.hipchat.com/v2/room/123456/notification?auth_token=abc', data=ANY, method='POST')
