import re, logging
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
        return (self._lbound == '[' and self._lversion <= parsed or self._lbound == '(' and self._lversion < parsed) and \
               (self._rbound == ']' and parsed <= self._rversion or self._rbound == ')' and parsed < self._rversion) and \
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
        return tuple(int(digit) for digit in VersionRange.SPLIT.split(version.split('-')[0]) if digit.isdigit())

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
    def __init__(self, url, groupid, artifactid):
        self._url = url
        self._groupid = groupid
        self._artifactid = artifactid

    def get(self, version):
        return util.get_json('{0}/{1}/{2}/{3}/{2}-{3}.json'.format(self._url, self._groupid.replace('.', '/'), self._artifactid, version))

    def resolve(self, expression):
        def getText(nodelist):
            rc = []
            for node in nodelist:
                if node.nodeType == node.TEXT_NODE:
                    rc.append(node.data)
            return ''.join(rc)

        document = util.get_xml('{0}/{1}/{2}/maven-metadata.xml'.format(self._url, self._groupid.replace('.', '/'), self._artifactid))
        versions = [getText(version.childNodes) for version in document.getElementsByTagName('version')]
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
