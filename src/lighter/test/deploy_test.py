import unittest, yaml
from mock import patch, ANY
import lighter.main as lighter
from lighter.util import jsonRequest

class DeployTest(unittest.TestCase):
    def testParseService(self):
        service = lighter.parse_service('src/resources/yaml/staging/myservice.yml')
        self.assertEquals(service.document['hipchat']['token'], 'abc123')
        self.assertEquals(sorted(service.document['hipchat']['rooms']), ['123','456','456','789'])
        self.assertEquals(service.environment, 'staging')

        self.assertEquals(service.config['id'], '/myproduct/myservice')
        self.assertEquals(service.config['env']['DATABASE'], 'database:3306')
        self.assertEquals(service.config['env']['rabbitmq'], 'amqp://myserver:15672')
        self.assertEquals(service.config['cpus'], 1)
        self.assertEquals(service.config['instances'], 3)
        self.assertEquals(service.config['env']['SERVICE_VERSION'], '1.0.0')
        self.assertEquals(service.config['env']['SERVICE_BUILD'], '1.0.0')

    def testParseClassifier(self):
        service = lighter.parse_service('src/resources/yaml/staging/myservice-classifier.yml')
        self.assertEquals(service.config['env']['isclassifier'], 'marathon')
        self.assertEquals(service.config['env']['SERVICE_VERSION'], '1.0.0')
        self.assertEquals(service.config['env']['SERVICE_BUILD'], '1.0.0-marathon')

    def testParseSnapshot(self):
        service = lighter.parse_service('src/resources/yaml/staging/myservice-snapshot.yml')
        self.assertEquals(service.config['env']['SERVICE_VERSION'], '1.1.1-SNAPSHOT')
        self.assertEquals(service.config['env']['SERVICE_BUILD'], '1.1.1-20151105011659-4')

    def testParseUniqueSnapshot(self):
        service = lighter.parse_service('src/resources/yaml/staging/myservice-unique-snapshot.yml')
        self.assertEquals(service.config['env']['SERVICE_VERSION'], '1.1.1-SNAPSHOT')
        self.assertEquals(service.config['env']['SERVICE_BUILD'], '1.1.1-20151102.035053-8-marathon')

    def _parseErrorPost(self, url, *args, **kwargs):
        if url.startswith('file:'):
            return jsonRequest(url, *args, **kwargs)
        raise self.fail('Should not POST into Marathon')

    def testParseError(self):
        with patch('lighter.util.jsonRequest', wraps=self._parseErrorPost) as mock_jsonRequest:
            try:
                lighter.deploy('http://localhost:1/', filenames=['src/resources/yaml/staging/myservice.yml', 'src/resources/yaml/staging/myservice-broken.yml'])
            except yaml.scanner.ScannerError:
                pass
            else:
                self.fail("Expected yaml.ScannerError")

    def _resolvePost(self, url, data=None, *args, **kwargs):
        if url.startswith('file:'):
            return jsonRequest(url, data, *args, **kwargs)
        if '/v2/apps' in url and data:
            self.assertEquals(data['container']['docker']['image'], 'meltwater/myservice:1.0.0')
            self._resolvePostCalled = True
        return {'app': {}}

    def testResolve(self):
        with patch('lighter.util.jsonRequest', wraps=self._resolvePost) as mock_jsonRequest:
            lighter.deploy('http://localhost:1/', filenames=['src/resources/yaml/integration/myservice.yml'])
            self.assertTrue(self._resolvePostCalled)

    def testParseNoMavenService(self):
        service = lighter.parse_service('src/resources/yaml/staging/myservice-nomaven.yml')
        self.assertEquals(service.document['hipchat']['token'], 'abc123')
        self.assertEquals(service.config['id'], '/myproduct/myservice-nomaven')
        self.assertEquals(service.config['instances'], 1)
        self.assertEquals(service.config['env']['DATABASE'], 'database:3306')
        self.assertEquals(service.config['container']['docker']['image'], 'meltwater/myservice:latest')
