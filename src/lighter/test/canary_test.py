import unittest
from mock import patch
import lighter.main as lighter
from lighter.util import jsonRequest

class CanaryTest(unittest.TestCase):
    def testCanary(self):
        service = lighter.parse_service('src/resources/yaml/integration/myservice-canary1.yml')
        canary1 = lighter.parse_service('src/resources/yaml/integration/myservice-canary1.yml', canaryGroup='generic')
        canary2 = lighter.parse_service('src/resources/yaml/integration/myservice-canary2.yml', canaryGroup='generic')

        self.assertEquals('/myproduct/myservice', service.config['id'])
        self.assertEquals('/myproduct/myservice-canary-generic-1dc8007f327f5053cb4e4a36ee305ad8', canary1.config['id'])
        self.assertEquals('/myproduct/myservice-canary-generic-41649b19575adeaf59faf5c16389b747', canary2.config['id'])

        self.assertEquals(3, service.config['instances'])
        self.assertEquals(1, canary1.config['instances'])

        self.assertEquals(service.config['container']['docker']['portMappings'][0]['servicePort'], 1234)
        self.assertEquals(canary1.config['container']['docker']['portMappings'][0]['servicePort'], 0)
        self.assertEquals(canary2.config['ports'][0], 0)

        self.assertEquals(canary1.config['container']['docker']['parameters'][1]['key'], 'label')
        self.assertEquals(canary1.config['container']['docker']['parameters'][1]['value'], 'com.meltwater.lighter.canary.group=generic')

        self.assertEquals(canary2.config['container']['docker']['parameters'][1]['key'], 'label')
        self.assertEquals(canary2.config['container']['docker']['parameters'][1]['value'], 'com.meltwater.lighter.canary.group=generic')

        self.assertEquals(canary1.config['labels']['com.meltwater.lighter.canary.group'], 'generic')
        self.assertEquals(canary1.config['labels']['com.meltwater.proxymatic.port.0.servicePort'], '1234')
        self.assertEquals(canary2.config['labels']['com.meltwater.proxymatic.port.0.servicePort'], '1234')

    def testCanaryGroupMangling(self):
        canary = lighter.parse_service('src/resources/yaml/integration/myservice-canary1.yml', canaryGroup='gene -ric')
        self.assertEquals('/myproduct/myservice-canary-gene_-ric-3773b8983ccd7b8767ef805719841a05', canary.config['id'])

        canary = lighter.parse_service('src/resources/yaml/integration/myservice-canary2.yml', canaryGroup='gene+%&ric')
        self.assertEquals('/myproduct/myservice-canary-gene_ric-9e6be44a14c1e2e44f3fbe4a88116b2c', canary.config['id'])

    def testCanaryCleanup(self):
        marathonurl = 'http://localhost:1'
        canaryGroup = 'generic'
        self._deleted = False

        canary1 = lighter.parse_service('src/resources/yaml/integration/myservice-canary1.yml', canaryGroup=canaryGroup)
        canary2 = lighter.parse_service('src/resources/yaml/integration/myservice-canary2.yml', canaryGroup=canaryGroup)
        canary3 = lighter.parse_service('src/resources/yaml/integration/myservice-canary3.yml', canaryGroup=canaryGroup)

        def wrapper(url, method='GET', data=None, *args, **kwargs):
            if url.startswith('file:') and method == 'GET':
                return jsonRequest(url, data, *args, **kwargs)
            if url == '%s/v2/apps?label=com.meltwater.lighter.canary.group%%3D%%3Dgeneric' % marathonurl and method == 'GET':
                return {'apps': [canary2.config, canary3.config]}
            if url == '%s/v2/apps%s' % (marathonurl, canary3.config['id']) and method == 'DELETE':
                self._deleted = True
                return {}
            raise RuntimeError("Unexpected HTTP %s call to %s" % (method, url))

        with patch('lighter.util.jsonRequest', wraps=wrapper):
            lighter.cleanup_canaries(marathonurl, canaryGroup, [canary1, canary2])
            self.assertTrue(self._deleted)
