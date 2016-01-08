import sys, re, urllib2, logging
import lighter.util as util

class VersionRange(object):
    SPLIT = re.compile('[^\d\w_]+')

    def __init__(self, expression):
        result = re.match('([\(\[])\s*((?:\d+\.)*\d+)?\s*,\s*((?:\d+\.)*\d+)?\s*([\)\]])', expression)
        if not result:
            raise ValueError('%s is not a valid version range' % expression)

        self._lbound, lversion, rversion, self._rbound = result.groups()
        self._lversion = VersionRange.parseVersion(lversion)
        self._rversion = VersionRange.parseVersion(rversion)
        self._suffix = VersionRange.suffix(expression)

    def accepts(self, version):
        parsed = self.parseVersion(version)
        return (self._lversion is None or self._lbound == '[' and self._lversion <= parsed or self._lbound == '(' and self._lversion < parsed) and \
               (self._rversion is None or self._rbound == ']' and parsed <= self._rversion or self._rbound == ')' and parsed < self._rversion) and \
               VersionRange.suffix(version) == self._suffix

    @staticmethod
    def suffix(version):
        parts = version.split('-', 1)
        return len(parts) == 2 and parts[1] or ''

    @staticmethod
    def issnapshot(version):
        return version.endswith('-SNAPSHOT')

    @staticmethod
    def parseVersion(version):
        if version:
            return tuple(int(digit) for digit in VersionRange.SPLIT.split(version.split('-')[0]) if digit.isdigit())
        return None

    @staticmethod
    def compareVersions(a, b):
        av = VersionRange.parseVersion(a)
        bv = VersionRange.parseVersion(b)
        result = cmp(av, bv)
        
        # Snapshots are less than a release with the same version number
        if result == 0:
            if VersionRange.issnapshot(a) and not VersionRange.issnapshot(b):
                result = -1
            elif not VersionRange.issnapshot(a) and VersionRange.issnapshot(b):
                result = 1

        return result

class Artifact(object):
    def __init__(self, version, uniqueVersion, classifier, body):
        self.version = version
        self.uniqueVersion = (uniqueVersion or version) + (classifier and ('-' + classifier) or '')
        self.body = body

class ArtifactVariables(object):
    def __init__(self, wrappedResolver, artifact):
        self._wrappedResolver = wrappedResolver
        self._artifact = artifact

    def clone(self):
        return ArtifactVariables(self._wrappedResolver.clone(), self._artifact)

    def pop(self, name):
        if name == 'lighter.version':
            return self._artifact.version
        if name == 'lighter.uniqueVersion':
            return self._artifact.uniqueVersion
        return self._wrappedResolver.pop(name)

class ArtifactResolver(object):
    def __init__(self, url, groupid, artifactid, classifier=None):
        self._url = url
        self._groupid = groupid
        self._artifactid = artifactid
        self._classifier = classifier

    def get(self, version):
        return self.fetch(version).body

    def fetch(self, version):
        trailer = '-SNAPSHOT'
        if not version.endswith(trailer):
            return self._fetch(version)

        # Try to resolve unique/timestamped snapshot versions from maven-metadata.xml
        logging.debug('Trying to resolve %s to a unique timestamp-buildnumber version', version)
        url = '{0}/{1}/{2}/{3}/maven-metadata.xml'.format(self._url, self._groupid.replace('.', '/'), self._artifactid, version)
        metadata = {}

        try:
            metadata = util.xmlRequest(url)
        except urllib2.URLError, e:
            logging.debug('Failed to fetch %s', url)

        # Find a matching snapshot version (Gradle doesn't create <snapshotVersions> but Maven does)
        timestamp = util.rget(metadata, 'versioning', 'snapshot', 'timestamp')
        buildNumber = util.rget(metadata, 'versioning', 'snapshot', 'buildNumber')
        snapshot = '-'.join(filter(bool, [version[0:len(version)-len(trailer)], timestamp, buildNumber])) if (timestamp is not None or buildNumber is not None) else None
        return self._fetch(version, snapshot, metadata)

    def _fetch(self, version, uniqueVersion=None, metadata={}):
        url = '{0}/{1}/{2}/{3}/{2}-{4}'.format(self._url, self._groupid.replace('.', '/'), self._artifactid, version, uniqueVersion or version)
        if self._classifier is not None:
            url += '-' + self._classifier
        url += '.json'

        # Extract unique version number from metadata
        if not uniqueVersion:
            timestamp = util.rget(metadata,'versioning','snapshot','timestamp') or util.rget(metadata,'versioning','lastUpdated')
            buildNumber = util.rget(metadata,'versioning','snapshot','buildNumber')
            if timestamp or buildNumber:
                uniqueVersion = '-'.join(filter(bool, [version.replace('-SNAPSHOT',''), timestamp, buildNumber]))

        try:
            return Artifact(version, uniqueVersion, self._classifier, util.jsonRequest(url))
        except urllib2.HTTPError, e:
            raise RuntimeError("Failed to retrieve %s HTTP %d (%s)" % (url, e.code, e)), None, sys.exc_info()[2]
        except urllib2.URLError, e:
            raise RuntimeError("Failed to retrieve %s (%s)" % (url, e)), None, sys.exc_info()[2]

    def resolve(self, expression):
        metadata = util.xmlRequest('{0}/{1}/{2}/maven-metadata.xml'.format(self._url, self._groupid.replace('.', '/'), self._artifactid))
        versions = util.toList(util.rget(metadata,'versioning','versions','version'))
        logging.debug('%s:%s candidate versions %s', self._groupid, self._artifactid, versions)
        return self.selectVersion(expression, versions)

    def selectVersion(self, expression, versions):
        matcher = VersionRange(expression)
        matches = [version for version in versions if matcher.accepts(version)]
        matches.sort(VersionRange.compareVersions)
        logging.debug('%s:%s matched %s to versions %s', self._groupid, self._artifactid, expression, matches)

        if not matches:
            raise RuntimeError('Failed to find a version that matches %s' % expression)
        return matches[-1]
