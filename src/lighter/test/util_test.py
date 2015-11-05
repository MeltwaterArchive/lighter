import unittest
import lighter.main as lighter
import lighter.util as util

class UtilTest(unittest.TestCase):
    def testMerge(self):
        x = {'a': 1, 'b': 2}
        y = {'b': 3, 'c': 4}
        z = {'c': 5, 'd': 6}
        
        m = {'a': 1, 'b': 3, 'c': 5, 'd': 6}
        self.assertEqual(util.merge(x, y, z),m)
        m = {'a': 1, 'b': 2, 'c': 4, 'd': 6}
        self.assertEqual(util.merge(z, y, x),m)

    def testMergeLists(self):
        x = {'a': [1, 2]}
        y = {'a': [2, 3]}
        m = {'a': [1, 2, 2, 3]}
        self.assertEquals(util.merge(x, y), m)

    def testReplace(self):
        x = {'a':'abc%{var}def', 'b':['%{var} %{var2} %{var3}'], 'c': {'d': '%{var2} %{var3}'}}
        m = {'a':'abc1def', 'b':['1 2 3'], 'c': {'d': '2 3'}}
        self.assertEquals(util.replace(x, {'var':'1', 'var2':2, 'var3': '3'}), m)

    def testCompare(self):
        x = {'a': 1, 'b': 2}
        y = {'b': 3, 'c': 4}
        self.assertFalse(lighter.compare_service_versions(x, y))
        self.assertFalse(lighter.compare_service_versions(y, x))
        self.assertTrue(lighter.compare_service_versions(x, x))

        x = {'a': [1], 'b': 2}
        y = {'a': [2], 'b': 2}
        self.assertFalse(lighter.compare_service_versions(x, y))
        self.assertTrue(lighter.compare_service_versions(x, x))

        x = {'a': [1], 'b': 2}
        y = {'a': [2,1], 'b': 2}
        self.assertFalse(lighter.compare_service_versions(x, y))
        self.assertFalse(lighter.compare_service_versions(y, x))
        self.assertTrue(lighter.compare_service_versions(x, x))

        x = {'a': {'c':2}, 'b': 2}
        y = {'a': {'c':1}, 'b': 2}
        self.assertFalse(lighter.compare_service_versions(x, y))
        self.assertFalse(lighter.compare_service_versions(y, x))
        self.assertTrue(lighter.compare_service_versions(x, x))

        x = {'a': {'c':2, 'd':4}, 'b': 2}
        y = {'a': {'c':1}, 'b':2}
        self.assertFalse(lighter.compare_service_versions(x, y))
        self.assertFalse(lighter.compare_service_versions(y, x))
        self.assertTrue(lighter.compare_service_versions(x, x))

        x = {'foo': [0, 456]}
        y = {'foo': [789, 456]}
        self.assertFalse(lighter.compare_service_versions(x, y))

        x = {'ports': [0, 456]}
        y = {'ports': [789, 456]}
        self.assertTrue(lighter.compare_service_versions(x, y))

        x = {'ports': [0, 456]}
        y = {'ports': [123, 456]}
        self.assertTrue(lighter.compare_service_versions(x, y))

    def testGetXml(self):
        url = 'file:./src/resources/repository/com/meltwater/myservice-snapshot/1.1.1-SNAPSHOT/maven-metadata.xml'
        actual = util.xmlRequest(url)
        expected = {
            'versioning': {
                'snapshot': {
                    'timestamp': '20151102.035053',
                    'buildNumber': '8'
                },
                'lastUpdated': '20151102035120',
                'snapshotVersions': {
                    'snapshotVersion': {
                        'classifier': 'marathon', 'extension': 'json', 'value': '1.1.1-20151102.035053-8', 'updated': '20151102035120'
                    }
                }
            }
        }

        self.assertEquals(actual, expected)

    def test_get_marathon_url(self):
        self.assertEqual(lighter.get_marathon_url('myurl', 'myid'), 'myurl/v2/apps/myid')
        self.assertEqual(lighter.get_marathon_url('myurl/', '/myid/'), 'myurl/v2/apps/myid')
        self.assertEqual(lighter.get_marathon_url('myurl/', '/myid/', True), 'myurl/v2/apps/myid?force=true')

    def test_buildRequest(self):
        url = "https://user:pass@maven.example.com/path/to/my/repo"
        req = util.buildRequest(url)
        self.assertTrue(req.get_header('Authorization').startswith('Basic '))
