import sys, re, urllib2, logging
import lighter.util as util

class VersionRange(object):
    SPLIT = re.compile('[^\d\w_]+')

    def __init__(self, expression):
        result = re.match('([\(\[])\s*((?:\d+\.)*\d+)?\s*,\s*((?:\d+\.)*\d+)?\s*([\)\]])', expression)
        if not result:
            raise ArgumentError('%s is not a valid version range' % expression)

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

class ArtifactResolver(object):
    def __init__(self, url, groupid, artifactid, classifier=None):
        self._url = url
        self._groupid = groupid
        self._artifactid = artifactid
        self._classifier = classifier

    def get(self, version):
        try:
            return self._get(version)
        except RuntimeError, e:
            # Try to resolve unique/timestamped snapshot versions
            if version.endswith('-SNAPSHOT'):
                logging.debug('Trying to resolve %s to a unique timestamp-buildnumber version', version)
                url = '{0}/{1}/{2}/{3}/maven-metadata.xml'.format(self._url, self._groupid.replace('.', '/'), self._artifactid, version)
                document = util.get_xml(url)
                snapshot = document.getElementsByTagName('snapshot')[0]
                timestamp = util.xml_text(snapshot.getElementsByTagName('timestamp'))
                buildNumber = util.xml_text(snapshot.getElementsByTagName('buildNumber'))
                uniqueversion = version.replace('-SNAPSHOT', '-%s-%s' % (timestamp, buildNumber))
                logging.debug('Resolved %s to unique version %s', version, uniqueversion)
                return self._get(version, uniqueversion)
            
            raise e, None, sys.exc_info()[2]

    def _get(self, version, uniqueversion=None):
        url = '{0}/{1}/{2}/{3}/{2}-{4}'.format(self._url, self._groupid.replace('.', '/'), self._artifactid, version, uniqueversion or version)
        if self._classifier is not None:
            url += '-' + self._classifier
        url += '.json'

        try:
            return util.get_json(url)
        except urllib2.HTTPError, e:
            raise RuntimeError("Failed to retrieve %s HTTP %d (%s)" % (url, e.code, e)), None, sys.exc_info()[2]
        except urllib2.URLError, e:
            raise RuntimeError("Failed to retrieve %s (%s)" % (url, e)), None, sys.exc_info()[2]

    def resolve(self, expression):
        document = util.get_xml('{0}/{1}/{2}/maven-metadata.xml'.format(self._url, self._groupid.replace('.', '/'), self._artifactid))
        versions = [util.xml_text(version.childNodes) for version in document.getElementsByTagName('version')]
        logging.debug('%s:%s candidate versions %s', self._groupid, self._artifactid, versions)
        return self.selectVersion(expression, versions)

    def selectVersion(self, expression, versions):
        matcher = VersionRange(expression)
        matches = [version for version in versions if matcher.accepts(version)]
        matches.sort(VersionRange.compareVersions)
        logging.debug('%s:%s matched %s to versions %s', self._groupid, self._artifactid, expression, matches)

        if not matches:
            raise RuntimeError('Failed to find a version that matches %s', expression)
        return matches[-1]
