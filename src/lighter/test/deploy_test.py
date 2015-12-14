import unittest, yaml
from mock import patch, ANY
import lighter.main as lighter
from lighter.util import jsonRequest

class DeployTest(unittest.TestCase):
    def setUp(self):
        self._called = False

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

        # Check that zero are translated correctly
        self.assertEquals(service.config['upgradeStrategy']['minimumHealthCapacity'], 0.0)
        self.assertEquals(service.config['upgradeStrategy']['maximumOverCapacity'], 0.0)

    def testParseClassifier(self):
        service = lighter.parse_service('src/resources/yaml/staging/myservice-classifier.yml')
        self.assertEquals(service.config['env']['isclassifier'], 'marathon')
        self.assertEquals(service.config['env']['SERVICE_VERSION'], '1.0.0')
        self.assertEquals(service.config['env']['SERVICE_BUILD'], '1.0.0-marathon')

    def testParseRecursiveVariable(self):
        service = lighter.parse_service('src/resources/yaml/staging/myservice.yml')
        self.assertEquals(service.config['env']['BVAR'], '123')
        self.assertEquals(service.config['env']['CVAR'], '123')

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
            with self.assertRaises(RuntimeError):
                lighter.deploy('http://localhost:1/', filenames=['src/resources/yaml/staging/myservice.yml', 'src/resources/yaml/staging/myservice-broken.yml'])
            
    def _createJsonRequestWrapper(self, marathonurl='http://localhost:1'):
        appurl = '%s/v2/apps/myproduct/myservice' % marathonurl

        def wrapper(url, method='GET', data=None, *args, **kwargs):
            if url.startswith('file:'):
                return jsonRequest(url, data, *args, **kwargs)
            if url == appurl and method == 'PUT' and data:
                self.assertEquals(data['container']['docker']['image'], 'meltwater/myservice:1.0.0')
                self._called = True
                return {}
            if url == appurl and method == 'GET':
                return {'app': {}}
            return None
        return wrapper

    def testResolveMavenJson(self):
        with patch('lighter.util.jsonRequest', wraps=self._createJsonRequestWrapper()) as mock_jsonRequest:
            lighter.deploy('http://localhost:1/', filenames=['src/resources/yaml/integration/myservice.yml'])
            self.assertTrue(self._called)

    def testDefaultMarathonUrl(self):
        with patch('lighter.util.jsonRequest', wraps=self._createJsonRequestWrapper('http://defaultmarathon:2')) as mock_jsonRequest:
            lighter.deploy(marathonurl=None, filenames=['src/resources/yaml/integration/myservice.yml'])
            self.assertTrue(self._called)

    def testNoMarathonUrlDefined(self):
        with patch('lighter.util.jsonRequest', wraps=self._createJsonRequestWrapper()) as mock_jsonRequest:
            with self.assertRaises(RuntimeError) as cm:
                lighter.deploy(marathonurl=None, filenames=['src/resources/yaml/staging/myservice.yml'])
            self.assertEqual("No Marathon URL defined for service src/resources/yaml/staging/myservice.yml", cm.exception.message)
    
    def testUnresolvedVariable(self):
        service_yaml = 'src/resources/yaml/integration/myservice-unresolved-variable.yml'
        try:
            lighter.parse_service(service_yaml)
        except RuntimeError, e:
            self.assertEquals(e.message, 'Failed to parse %s with the following message: Variable %%{bvar} not found' % service_yaml)
        else:
            self.fail('Expected ValueError')

    def testParseNoMavenService(self):
        service = lighter.parse_service('src/resources/yaml/staging/myservice-nomaven.yml')
        self.assertEquals(service.document['hipchat']['token'], 'abc123')
        self.assertEquals(service.config['id'], '/myproduct/myservice-nomaven')
        self.assertEquals(service.config['instances'], 1)
        self.assertEquals(service.config['env']['DATABASE'], 'database:3306')
        self.assertEquals(service.config['container']['docker']['image'], 'meltwater/myservice:latest')

    def testPasswordCheckFail(self):
        with self.assertRaises(RuntimeError):
            lighter.parse_service('src/resources/yaml/staging/myservice-password.yml', verifySecrets=True)
           
    def testPasswordCheckSucceed(self):
        lighter.parse_service('src/resources/yaml/staging/myservice-encrypted-password.yml', verifySecrets=True)
    
    @patch('logging.warn')
    def testPasswordCheckWarning(self, mock_warn):
        lighter.parse_service('src/resources/yaml/staging/myservice-password.yml', verifySecrets=False)
        self.assertEqual(mock_warn.call_count, 1)
        mock_warn.assert_called_with('Found unencrypted secret in src/resources/yaml/staging/myservice-password.yml: DATABASE_PASSWORD')