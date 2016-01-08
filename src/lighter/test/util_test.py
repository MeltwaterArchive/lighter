import os, unittest
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
        self.assertEquals(util.replace(x, util.FixedVariables({'var':'1', 'var2':2, 'var3': '3'})), m)

    def testReplaceEscape(self):
        x = {'a':'abc%%{var}def', 'b':'abc%{var}def'}
        m = {'a':'abc%{var}def', 'b':'abc1def'}
        self.assertEquals(util.replace(x, util.FixedVariables({'var':'1'})), m)

    def testReplaceEnv(self):
        x = {'a':'%{env.ES_PORT}'}
        m = {'a':'9300'}
        os.environ['ES_PORT'] = '9300'
        self.assertEquals(util.replace(x, util.EnvironmentVariables(util.FixedVariables({}))), m)

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
                'lastUpdated': '20151102035120'
            }
        }

        self.assertEquals(actual, expected)

    def testGetMarathonUrl(self):
        self.assertEqual(lighter.get_marathon_url('myurl', 'myid'), 'myurl/v2/apps/myid')
        self.assertEqual(lighter.get_marathon_url('myurl/', '/myid/'), 'myurl/v2/apps/myid')
        self.assertEqual(lighter.get_marathon_url('myurl/', '/myid/', True), 'myurl/v2/apps/myid?force=true')

    def testBuildRequest(self):
        url = "https://user:pass@maven.example.com/path/to/my/repo"
        req = util.buildRequest(url)
        self.assertTrue(req.get_header('Authorization').startswith('Basic '))

        req = util.buildRequest(url, data={'a':'b'})
        self.assertTrue(req.get_header('Authorization').startswith('Basic '))
        self.assertEqual('application/json', req.get_header('Content-type'))
        self.assertEqual('{"a": "b"}', req.get_data())

        req = util.buildRequest(url, data={'a':'b'}, contentType='application/x-www-form-urlencoded')
        self.assertEqual('application/x-www-form-urlencoded', req.get_header('Content-type'))
        self.assertEqual('a=b', req.get_data())

    def testRGet(self):
        self.assertEqual('c', util.rget({'a': [{'b': 'c'}]}, 'a', 0, 'b'))
        self.assertEqual(None, util.rget({'a': [{'b': 'c'}]}, 'a', 0, 'd'))
        self.assertEqual(None, util.rget({'a': [{'b': 'c'}]}, 'a', 1, 'b'))
        self.assertEqual(None, util.rget({'a': [{'b': 'c'}]}, 'a', -1, 'b'))
