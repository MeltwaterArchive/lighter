import unittest, yaml, nacl, json
from mock import patch, ANY
from nacl.public import Box, PrivateKey
import lighter.main as lighter
import lighter.secretary as secretary
import lighter.util as util

def decryptEnvelope(publicKey, privateKey, envelope):
    box = Box(privateKey, publicKey)
    encrypted = nacl.encoding.Base64Encoder.decode(envelope[9:][0:-1])
    plaintext = box.decrypt(encrypted)
    return plaintext

class SecretaryTest(unittest.TestCase):
    def testAddMasterConfigKeys(self):
        service = lighter.parse_service('src/resources/yaml/staging/myservice.yml')
        self.assertEquals(service.config['env']['MASTER_PUBLIC_KEY'], 'pq01FdTbzF7q29HiX8f01oDfQyHgVFw03vEZes7OtnQ=')
        self.assertEquals(service.config['env']['CONFIG_PUBLIC_KEY'], 'othVuDgGaaglOD0e7tMRyFR2lfn9hS8yxlxousfBeSY=')

    def testAddDeployKey(self):
        service = lighter.parse_service('src/resources/yaml/staging/myservice.yml')
        self.assertIsNotNone(service.config['env']['DEPLOY_PUBLIC_KEY'])
        self.assertIsNotNone(service.config['env']['DEPLOY_PRIVATE_KEY'])

    def testDeployKeyEncryption(self):
        service = lighter.parse_service('src/resources/yaml/staging/myservice.yml')
        configPublicKey = secretary.decodePublicKey(service.config['env']['CONFIG_PUBLIC_KEY'])
        masterPrivateKey = secretary.decodePrivateKey("src/resources/yaml/staging/keys/master-private-key.pem")

        deployPublicKey = secretary.decodePublicKey(service.config['env']['DEPLOY_PUBLIC_KEY'])
        deployPrivateKey = secretary.decodePrivateKey(service.config['env']['DEPLOY_PRIVATE_KEY'])

        actual = service.config['env']['DATABASE_PASSWORD']
        actual = decryptEnvelope(configPublicKey, deployPrivateKey, actual)
        actual = decryptEnvelope(configPublicKey, masterPrivateKey, actual)
        self.assertEquals("secret", actual)

    def testServiceKeyEncryption(self):
        service = lighter.parse_service('src/resources/yaml/staging/myservice-servicekey.yml')
        configPublicKey = secretary.decodePublicKey(service.config['env']['CONFIG_PUBLIC_KEY'])
        masterPrivateKey = secretary.decodePrivateKey("src/resources/yaml/staging/keys/master-private-key.pem")
        servicePrivateKey = secretary.decodePrivateKey("src/resources/yaml/staging/keys/myservice-private-key.pem")

        deployPublicKey = secretary.decodePublicKey(service.config['env']['DEPLOY_PUBLIC_KEY'])
        deployPrivateKey = secretary.decodePrivateKey(service.config['env']['DEPLOY_PRIVATE_KEY'])

        actual = service.config['env']['DATABASE_PASSWORD']
        actual = decryptEnvelope(configPublicKey, deployPrivateKey, actual)
        actual = decryptEnvelope(configPublicKey, servicePrivateKey, actual)
        actual = decryptEnvelope(configPublicKey, masterPrivateKey, actual)
        self.assertEquals("secret", actual)

    def testRedeployWithoutChange(self):
        service1 = lighter.parse_service('src/resources/yaml/staging/myservice-servicekey.yml')
        service2 = lighter.parse_service('src/resources/yaml/staging/myservice-servicekey.yml')
        self.assertNotEqual(service1.config, service2.config)

        self.assertTrue(lighter.compare_service_versions(service1.config, service2.config))
        self.assertTrue(lighter.compare_service_versions(service1.config, json.loads(util.toJson(service2.config))))

    def testRedeployWithChange(self):
        service1 = lighter.parse_service('src/resources/yaml/staging/myservice-servicekey.yml')
        service2 = lighter.parse_service('src/resources/yaml/staging/myservice-servicekey.yml')
        self.assertTrue(lighter.compare_service_versions(service1.config, service2.config))

        configPrivateKey = secretary.decodePrivateKey("src/resources/yaml/staging/keys/config-private-key.pem")
        masterPublicKey = secretary.decodePublicKey(service1.config['env']['MASTER_PUBLIC_KEY'])
        secret = secretary.encryptEnvelope(masterPublicKey, configPrivateKey, 'secret')
        secret2 = secretary.encryptEnvelope(masterPublicKey, configPrivateKey, 'secret2')

        # Create new service/deploy keys
        serviceKey1, serviceKey2 = PrivateKey.generate().public_key, PrivateKey.generate().public_key
        deployKey1, deployKey2 = PrivateKey.generate().public_key, PrivateKey.generate().public_key

        # Encrypt the secret using serviceKey
        service1.config['env']['DATABASE_PASSWORD'] = secretary.encryptEnvelope(serviceKey1, configPrivateKey, secret)
        service2.config['env']['DATABASE_PASSWORD'] = secretary.encryptEnvelope(serviceKey2, configPrivateKey, secret)
        self.assertNotEqual(service1.config['env']['DATABASE_PASSWORD'], service2.config['env']['DATABASE_PASSWORD'])
        self.assertTrue(lighter.compare_service_versions(service1.config, service2.config))
        self.assertTrue(lighter.compare_service_versions(service1.config, json.loads(util.toJson(service2.config))))

        # Encrypt the secret using deployKey
        service1.config['env']['DATABASE_PASSWORD'] = secretary.encryptEnvelope(deployKey1, configPrivateKey, service1.config['env']['DATABASE_PASSWORD'])
        service2.config['env']['DATABASE_PASSWORD'] = secretary.encryptEnvelope(deployKey2, configPrivateKey, service2.config['env']['DATABASE_PASSWORD'])
        self.assertNotEqual(service1.config['env']['DATABASE_PASSWORD'], service2.config['env']['DATABASE_PASSWORD'])
        self.assertTrue(lighter.compare_service_versions(service1.config, service2.config))
        self.assertTrue(lighter.compare_service_versions(service1.config, json.loads(util.toJson(service2.config))))

        # Modify the secret and encrypt using serviceKey and deployKey
        service2.config['env']['DATABASE_PASSWORD'] = \
            secretary.encryptEnvelope(deployKey2, configPrivateKey, 
            secretary.encryptEnvelope(serviceKey2, configPrivateKey, secret2))
        self.assertNotEqual(service1.config['env']['DATABASE_PASSWORD'], service2.config['env']['DATABASE_PASSWORD'])

        # Verify that it's now differing
        self.assertFalse(lighter.compare_service_versions(service1.config, service2.config))
        self.assertFalse(lighter.compare_service_versions(service1.config, json.loads(util.toJson(service2.config))))
