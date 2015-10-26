import unittest, yaml
from mock import patch, ANY
from lighter.main import deploy
from lighter.util import get_json

class DeployTest(unittest.TestCase):
	def _parseErrorPost(self, url, *args, **kwargs):
		if url.startswith('file:'):
			return get_json(url, *args, **kwargs)
		raise self.fail('Should not POST into Marathon')

	def testParseError(self):
		with patch('lighter.util.get_json', wraps=self._parseErrorPost) as mock_get_json:
			try:
				deploy('http://localhost:1/', noop=False, files=['src/resources/yaml/staging/myservice.yml', 'src/resources/yaml/staging/myservice-broken.yml'])
			except yaml.scanner.ScannerError:
				pass
			else:
				self.fail("Expected yaml.ScannerError")

	def _resolvePost(self, url, data=None, *args, **kwargs):
		if url.startswith('file:'):
			return get_json(url, data, *args, **kwargs)
		if data is not None:
			self.assertEquals(data['container']['docker']['image'], 'meltwater/myservice:1.0.0')
			self._resolvePostCalled = True
		return {'app': {}}

	def testResolve(self):
		with patch('lighter.util.get_json', wraps=self._resolvePost) as mock_get_json:
			deploy('http://localhost:1/', noop=False, files=['src/resources/yaml/integration/myservice.yml'])
			self.assertTrue(self._resolvePostCalled)
