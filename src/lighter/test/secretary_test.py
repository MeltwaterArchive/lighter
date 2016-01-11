import unittest
import json
import lighter.main as lighter
import lighter.secretary as secretary
import lighter.util as util

class SecretaryTest(unittest.TestCase):
    def testAddMasterKey(self):
        service = lighter.parse_service('src/resources/yaml/staging/myservice.yml')
        self.assertEquals(service.config['env']['MASTER_PUBLIC_KEY'], 'pq01FdTbzF7q29HiX8f01oDfQyHgVFw03vEZes7OtnQ=')

    def testAddDeployKey(self):
        service = lighter.parse_service('src/resources/yaml/staging/myservice.yml')
        self.assertIsNotNone(service.config['env']['DEPLOY_PUBLIC_KEY'])
        self.assertIsNotNone(service.config['env']['DEPLOY_PRIVATE_KEY'])

    def testRedeployWithoutChange(self):
        service1 = lighter.parse_service('src/resources/yaml/staging/myservice-servicekey.yml')
        service2 = lighter.parse_service('src/resources/yaml/staging/myservice-servicekey.yml')
        self.assertNotEqual(service1.config, service2.config)

        self.assertTrue(lighter.compare_service_versions(service1.config, service2.config))
        self.assertTrue(lighter.compare_service_versions(service1.config, json.loads(util.toJson(service2.config))))

        self.assertNotEqual(service1.config['env']['DEPLOY_PUBLIC_KEY'], service2.config['env']['DEPLOY_PUBLIC_KEY'])
        self.assertNotEqual(service1.config['env']['DEPLOY_PRIVATE_KEY'], service2.config['env']['DEPLOY_PRIVATE_KEY'])

    def testServiceWithoutSecrets(self):
        service = lighter.parse_service('src/resources/yaml/staging/myservice-nosecret.yml')
        self.assertFalse('SECRETARY_URL' in service.config['env'])
        self.assertFalse('MASTER_PRIVATE_KEY' in service.config['env'])
        self.assertFalse('DEPLOY_PUBLIC_KEY' in service.config['env'])
        self.assertFalse('DEPLOY_PRIVATE_KEY' in service.config['env'])

    def testExtractEnvelopes(self):
        envelopes = secretary.extractEnvelopes("amqp://ENC[NACL,uSr123+/=]:ENC[NACL,pWd123+/=]@rabbit:5672/")
        self.assertEqual(2, len(envelopes))
        self.assertEqual(["ENC[NACL,uSr123+/=]", "ENC[NACL,pWd123+/=]"], envelopes)

        envelopes = secretary.extractEnvelopes("amqp://ENC[NACL,]:ENC[NACL,pWd123+/=]@rabbit:5672/")
        self.assertEqual(1, len(envelopes))
        self.assertEqual(["ENC[NACL,pWd123+/=]"], envelopes)

        envelopes = secretary.extractEnvelopes("amqp://ENC[NACL,:ENC[NACL,pWd123+/=]@rabbit:5672/")
        self.assertEqual(1, len(envelopes))
        self.assertEqual(["ENC[NACL,pWd123+/=]"], envelopes)

        envelopes = secretary.extractEnvelopes("amqp://NC[NACL,]:ENC[NACL,pWd123+/=]@rabbit:5672/")
        self.assertEqual(1, len(envelopes))
        self.assertEqual(["ENC[NACL,pWd123+/=]"], envelopes)

        envelopes = secretary.extractEnvelopes("amqp://ENC[NACL,abc:ENC[NACL,pWd123+/=]@rabbit:5672/")
        self.assertEqual(1, len(envelopes))
        self.assertEqual(["ENC[NACL,pWd123+/=]"], envelopes)
