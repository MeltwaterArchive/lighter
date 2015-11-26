import os, re, nacl, logging, base64
from nacl.public import PublicKey, PrivateKey, Box
from copy import deepcopy
import lighter.util as util

# Regexp to parse simple PEM files
_PEM_RE = re.compile(u"-----BEGIN (.+?)-----\r?\n(.+?)\r?\n-----END \\1-----")

class KeyEncoder(object):
    """
    Base64 NaCL encoder that can also load keys from PEM files
    """
    @staticmethod
    def encode(data):
        return nacl.encoding.Base64Encoder.encode(data)

    @staticmethod
    def decode(data):
        if os.path.exists(data):
            with open(data, "rb") as f:
                contents = f.read()
                matches = _PEM_RE.match(contents)
                if not matches.group(2):
                    raise ValueError("Failed to parse PEM file %s (is absolute path %s readable?)" % (data, path))
                data = matches.group(2)
        
        try:
            return nacl.encoding.Base64Encoder.decode(data)
        except TypeError, e:
            logging.error("Failed to decode key %s (%s)", data, e)

class KeyValue(util.Value):
    """
    Compares deployment keys to be the same if their length is
    """
    def same(self, other):
        return len(self._value) == len(str(other))

class SecretValue(util.Value):
    """
    Only compares nonces since the innermost nonce is random for each encrypted 
    secret and is reused on all the upper levels.
    """
    def same(self, other):
        return isEnvelope(other) and getNonce(self) == getNonce(other)

def isEnvelope(value):
    return str(value).startswith('ENC[NACL,') and str(value).endswith(']')

def getNonce(message):
    return base64.b64decode(str(message)[9:-1])[0:Box.NONCE_SIZE]

def encryptEnvelope(publicKey, privateKey, message):
    """
    Encrypts a secret and returns a ENC[NACL,...] envelope
    """
    if isEnvelope(message):
        # Reuse the same nonce for higher level boxes to allow comparison. This is safe
        # as long as each {privateKey, publicKey} differ, which is always the case here. 
        # Innermost box is master-public-key, then service-public-key and deploy-public-key.
        # See the "Security model" section of http://nacl.cr.yp.to/box.html
        nonce = getNonce(message)
    else:
        nonce = nacl.utils.random(Box.NONCE_SIZE)

    box = Box(privateKey, publicKey)
    encrypted = box.encrypt(str(message), nonce)
    encoded = KeyEncoder.encode(encrypted)
    return SecretValue('ENC[NACL,%s]' % encoded)

def encryptEnvironment(publicKey, privateKey, result):
    """
    Encrypts all secrets in the 'env' element an extra time with the deploy/service keys
    """
    for key, value in list(result['env'].items()):
        if isEnvelope(value):
            envelope = encryptEnvelope(publicKey, privateKey, str(value))
            result['env'][key] = SecretValue(envelope)

def decodePublicKey(key):
    return PublicKey(str(key), encoder=KeyEncoder)

def decodePrivateKey(key):
    return PrivateKey(str(key), encoder=KeyEncoder)

def encodeKey(key):
    return key.encode(encoder=KeyEncoder)

def apply(document, config):
    """
    Generates a deploy key, injects config/master keys and performs the extra deployment time encryption of secrets.
    """
    result = deepcopy(config)
    url = util.rget(document, 'secretary', 'url')
    if not url:
        return

    masterKey = decodePublicKey(util.rget(document, 'secretary', 'master', 'publickey'))
    configPublicKey = decodePublicKey(util.rget(document, 'secretary', 'config', 'publickey'))
    configPrivateKey = decodePrivateKey(util.rget(document, 'secretary', 'config', 'privatekey'))

    result['env'] = result.get('env', {})
    result['env']['SECRETARY_URL'] = url
    result['env']['MASTER_PUBLIC_KEY'] = encodeKey(masterKey)
    result['env']['CONFIG_PUBLIC_KEY'] = encodeKey(configPublicKey)

    # Check for the optional service key
    encodedServiceKey = result['env'].get('SERVICE_PUBLIC_KEY')
    if encodedServiceKey:
        serviceKey = decodePublicKey(encodedServiceKey)
        encryptEnvironment(serviceKey, configPrivateKey, result)

    # Autogenerate a deploy key
    deployKey = PrivateKey.generate()
    result['env']['DEPLOY_PRIVATE_KEY'] = KeyValue(encodeKey(deployKey))
    result['env']['DEPLOY_PUBLIC_KEY'] = KeyValue(encodeKey(deployKey.public_key))
    encryptEnvironment(deployKey.public_key, configPrivateKey, result)

    return result
