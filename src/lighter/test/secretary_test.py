import unittest
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

        checksum1 = util.rget(service1.config, 'labels', 'com.meltwater.lighter.checksum')
        self.assertIsNotNone(checksum1)
        self.assertEqual(checksum1, util.rget(service2.config, 'labels', 'com.meltwater.lighter.checksum'))

        self.assertNotEqual(service1.config['env']['DEPLOY_PUBLIC_KEY'], service2.config['env']['DEPLOY_PUBLIC_KEY'])
        self.assertNotEqual(service1.config['env']['DEPLOY_PRIVATE_KEY'], service2.config['env']['DEPLOY_PRIVATE_KEY'])

    def testServiceWithoutSecrets(self):
        service = lighter.parse_service('src/resources/yaml/staging/myservice-nosecret.yml')
        self.assertFalse('SECRETARY_URL' in service.config['env'])
        self.assertFalse('MASTER_PRIVATE_KEY' in service.config['env'])
        self.assertFalse('DEPLOY_PUBLIC_KEY' in service.config['env'])
        self.assertFalse('DEPLOY_PRIVATE_KEY' in service.config['env'])

    def testServiceWithEmbeddedSecret(self):
        service = lighter.parse_service('src/resources/yaml/staging/myservice-embedded-encrypted-url.yml')
        self.assertTrue('SECRETARY_URL' in service.config['env'])
        self.assertTrue('DEPLOY_PUBLIC_KEY' in service.config['env'])
        self.assertTrue('DEPLOY_PRIVATE_KEY' in service.config['env'])

    def testExtractEnvelopes(self):
        envelopes = secretary.extractEnvelopes("amqp://ENC[NACL,uSr123+/=]:ENC[NACL,pWd123+/=]@rabbit:5672/")
        self.assertEqual(2, len(envelopes))
        self.assertEqual(["ENC[NACL,uSr123+/=]", "ENC[NACL,pWd123+/=]"], envelopes)

        envelopes = secretary.extractEnvelopes("amqp://ENC[NACL,uSr123+/=]:ENC[NACL,pWd123+/=]@rabbit:5672/ENC[KMS,123abc+/=]")
        self.assertEqual(3, len(envelopes))
        self.assertEqual(["ENC[NACL,uSr123+/=]", "ENC[NACL,pWd123+/=]", "ENC[KMS,123abc+/=]"], envelopes)

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

    def testServiceWithEnvvarDots(self):
        try:
            lighter.parse_service('src/resources/yaml/staging/myservice-encrypted-dots.yml')
        except RuntimeError as e:
            self.assertEquals(
                "The env var 'database.uri' is not a valid shell script identifier and not supported by Secretary. " +
                "Only alphanumeric characters and underscores are supported, starting with an alphabetic or underscore character.", e.message)
        else:
            self.fail("Expected exception RuntimeError")

    def testNonStringValue(self):
        try:
            secretary.extractEnvelopes({1: 2})
        except ValueError as e:
            self.assertEquals("Input must be str or unicode, was dict({1: 2})", str(e))
        else:
            self.fail("Expected exception ValueError")
