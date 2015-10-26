import unittest, yaml
from mock import patch, ANY
from lighter.main import deploy
from lighter.util import get_json


class DeployTest(unittest.TestCase):
	def proxy_get_json(self, url, *args, **kwargs):
		if url.startswith('file:'):
			return get_json(url, *args, **kwargs)
		raise self.fail('Should not POST into Marathon')

	def test_notify(self):
		with patch('lighter.util.get_json', wraps=self.proxy_get_json) as mock_get_json:
			try:
				deploy('http://localhost:1/', noop=False, files=['src/resources/yaml/staging/myservice.yml', 'src/resources/yaml/staging/myservice-broken.yml'])
			except yaml.scanner.ScannerError:
				pass
			else:
				self.fail("Expected yaml.ScannerError")
