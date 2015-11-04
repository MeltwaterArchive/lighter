import unittest
import lighter.maven as maven

class MavenTest(unittest.TestCase):
    def setUp(self):
        self.resolver = maven.ArtifactResolver('file:./src/resources/repository/', 'com.meltwater', 'myservice')

    def select(self, expression, versions):
        return self.resolver.selectVersion(expression, versions)

    def testResolve(self):
        self.assertEquals(self.resolver.resolve('[1.0.0,2.0.0)'), '1.1.0')
        
    def testSelectVersionInclusive(self):
        versions = ['0.1.2', '1.2.0', '1.2.1', '2.0.0-SNAPSHOT', '2.0.0', '2.0.1', '2.0.2-SNAPSHOT']
        self.assertEquals(self.select('[1.0.0,2.0.0]', versions), '2.0.0')
        self.assertEquals(self.select('[1.0.0,2.2.0]', versions), '2.0.1')
        self.assertEquals(self.select('[1.0.0,1.3.0]', versions), '1.2.1')

    def testSelectVersionExclusive(self):
        versions = ['0.1.2', '1.2.0', '1.2.1', '2.0.0-SNAPSHOT', '2.0.0', '2.0.1', '2.0.2-SNAPSHOT']
        self.assertEquals(self.select('[1.0.0,2.0.0)', versions), '1.2.1')
        self.assertEquals(self.select('[0.1.0,2.2.0)', versions), '2.0.1')
        self.assertEquals(self.select('[0.0.0,1.3.0)', versions), '1.2.1')

        try:
            self.assertEquals(self.select('(1.2.0,1.2.0]', versions), '1.2.0')
        except RuntimeError:
            pass
        else:
            self.fail('Expected RuntimeError')

    def testSelectVersionLatest(self):
        versions = ['0.1.2', '1.2.0', '1.2.1', '2.0.0-SNAPSHOT', '2.0.0', '2.0.1', '2.0.2-SNAPSHOT']
        self.assertEquals(self.select('[1.0.0,)', versions), '2.0.1')
        self.assertEquals(self.select('[1.0.0,]', versions), '2.0.1')
        self.assertEquals(self.select('(1.0.0,)', versions), '2.0.1')
        self.assertEquals(self.select('(1.0.0,]', versions), '2.0.1')

        self.assertEquals(self.select('[,1.2.1)', versions), '1.2.0')
        self.assertEquals(self.select('[,1.2.1]', versions), '1.2.1')
        self.assertEquals(self.select('(,1.2.1)', versions), '1.2.0')
        self.assertEquals(self.select('(,1.2.1]', versions), '1.2.1')

    def testGet(self):
        json = self.resolver.get('1.0.0')
        self.assertTrue(bool(json))

        try:
            self.resolver.get('0.0.0')
        except RuntimeError, e:
            pass
        else:
            self.fail("Expected RuntimeError")

    def testClassifier(self):
        resolver = maven.ArtifactResolver('file:./src/resources/repository/', 'com.meltwater', 'myservice-classifier', classifier='marathon')
        json = resolver.get('1.0.0')
        self.assertTrue(bool(json))

    def testUniqueSnapshotClassifier(self):
        resolver = maven.ArtifactResolver('file:./src/resources/repository/', 'com.meltwater', 'myservice-snapshot', classifier='marathon')
        json = resolver.get('1.1.1-SNAPSHOT')
        self.assertTrue(bool(json))
