import unittest, yaml
from mock import patch, ANY
import lighter.main as lighter
from lighter.util import get_json

class DeployTest(unittest.TestCase):
    def testParseService(self):
        service = lighter.parse_service('src/resources/yaml/staging/myservice.yml')
        self.assertEqual(service.document['hipchat']['token'], 'abc123')
        self.assertEqual(sorted(service.document['hipchat']['rooms']), ['123','456','789'])
        self.assertEqual(service.environment, 'staging')

        config = service.config
        self.assertEqual(config['id'],'/myproduct/myservice')
        self.assertEqual(config['env']['DATABASE'], 'database:3306')
        self.assertEqual(config['env']['rabbitmq'], 'amqp://myserver:15672')
        self.assertEqual(config['cpus'], 1)
        self.assertEqual(config['instances'], 3)

	def _parseErrorPost(self, url, *args, **kwargs):
		if url.startswith('file:'):
			return get_json(url, *args, **kwargs)
		raise self.fail('Should not POST into Marathon')

	def testParseError(self):
		with patch('lighter.util.get_json', wraps=self._parseErrorPost) as mock_get_json:
			try:
				lighter.deploy('http://localhost:1/', filenames=['src/resources/yaml/staging/myservice.yml', 'src/resources/yaml/staging/myservice-broken.yml'])
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
			lighter.deploy('http://localhost:1/', filenames=['src/resources/yaml/integration/myservice.yml'])
			self.assertTrue(self._resolvePostCalled)
