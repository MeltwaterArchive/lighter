import sys, re, urllib2, logging, base64, json, md5
import lighter.util as util

class ImageVariables(object):
    def __init__(self, wrappedResolver, document, image):
        m = re.search('^(?:([\w\-]+[\.:].[\w\.\-:]+)/)?(?:([\w\.\-]+)/)?([\w\.\-/]+)(?::([\w\.\-/]+))?$', image)
        if not m:
            raise ValueError("Failed to parse Docker image coordinates '%s'" % image)

        self._wrappedResolver = wrappedResolver
        self._document = document
        self._image = image

        self._registry = m.group(1) if m.group(1) else 'registry-1.docker.io'
        self._organization = m.group(2)
        self._repository = m.group(3)
        self._tag = m.group(4) if m.group(4) else 'latest'
        self._auth = util.rget(document, 'docker', 'registries', self._registry, 'auth')

        logging.debug("Parsed image '%s' as %s" % (self._image, (self._registry, self._organization, self._repository, self._tag)))

    def clone(self):
        return ImageVariables(self._wrappedResolver.clone(), self._document, self._image)

    @staticmethod
    def create(wrappedResolver, document, image):
        if image:
            return ImageVariables(wrappedResolver, document, image)
        return wrappedResolver

    def pop(self, name):
        if name == 'lighter.version':
            return self._tag
        
        if name == 'lighter.uniqueVersion':
            return \
                self._tryRegistryV2('https://%s/v2/%s/manifests/%s') or \
                self._tryRegistryV1('https://%s/v1/repositories/%s/tags/%s') or \
                self._tryRegistryV2('http://%s/v2/%s/manifests/%s') or \
                self._tryRegistryV1('http://%s/v1/repositories/%s/tags/%s') or \
                self._fail('https://%s/v2/%s/manifests/%s')

        return self._wrappedResolver.pop(name)

    def _tryRegistryV1(self, url):
        """
        Resolves an image id using the Docker Registry V1 API
        """
        try:
            expandedurl = self._expandurl(url, defaultrepo=True)
            response = util.jsonRequest(expandedurl, timeout=1)
        except urllib2.HTTPError, e:
            if e.code != 404:
                obfuscatedurl = self._expandurl(url, defaultrepo=True, obfuscateauth=True)
                raise RuntimeError("Failed to call %s (%s)" % (obfuscatedurl, e)), None, sys.exc_info()[2]
            return None
        except urllib2.URLError, e:
            return None

        # Docker Registry v1 returns image id as a string
        if isinstance(response, (str, unicode)):
            return unicode(response)

        return None

    def _tryRegistryV2(self, url):
        """
        Resolves an image id using the Docker Registry V2 API
        """
        try:
            expandedurl = self._expandurl(url)
            response = util.jsonRequest(expandedurl, timeout=1)
        except urllib2.HTTPError, e:
            if e.code != 404:
                obfuscatedurl = self._expandurl(url, obfuscateauth=True)
                raise RuntimeError("Failed to call %s (%s)" % (obfuscatedurl, e)), None, sys.exc_info()[2]
            return None
        except urllib2.URLError, e:
            return None

        # Extract the first compatibility image id if present
        layerblob = util.rget(response, 'history', 0, 'v1Compatibility')
        if layerblob:
            layerinfo = json.loads(layerblob)
            return layerinfo.get('id')

        return None

    def _fail(self, url):
        raise ValueError("Failed to resolve image version '%s' using URL like %s" % (self._image, self._expandurl(url, obfuscateauth=True)))

    def _expandurl(self, url, defaultrepo=False, obfuscateauth=False):
        registry = self._registry
        if self._auth:
            credentials = base64.b64decode(self._auth)
            if obfuscateauth:
                username, password = credentials.split(':')
                credentials = username + ':<hidden>' 
            registry = '%s@%s' % (credentials, registry)

        repository = self._repository 
        if self._organization or defaultrepo:
            repository = '%s/%s' % (self._organization or 'library', repository)

        return url % (registry, repository, self._tag)
