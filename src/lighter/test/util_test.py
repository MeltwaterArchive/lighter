import os
import unittest
import lighter.main as lighter
import lighter.util as util

class UtilTest(unittest.TestCase):
    def testMerge(self):
        x = {'a': 1, 'b': 2}
        y = {'b': 3, 'c': 4}
        z = {'c': 5, 'd': 6}

        m = {'a': 1, 'b': 3, 'c': 5, 'd': 6}
        self.assertEqual(m, util.merge(util.merge(x, y), z))

        m = {'a': 1, 'b': 2, 'c': 4, 'd': 6}
        self.assertEqual(m, util.merge(util.merge(z, y), x))

    def testMergeLists(self):
        x = {'a': [1, 2]}
        y = {'a': [2, 3]}
        m = {'a': [1, 2, 2, 3]}
        self.assertEquals(m, util.merge(x, y))

    def testMergeListOverride(self):
        x = {'a': [1, 2]}
        y = {'a': {1: 3}}
        m = {'a': [1, 3]}
        self.assertEquals(m, util.merge(x, y))

    def testMergeListNonexisting(self):
        x = {'a': {'b': [1, 2]}}
        y = {'a': {'b': {1: 3, 4: 4}}}
        try:
            util.merge(x, y)
            self.fail("Expected exception ValueError")
        except IndexError as e:
            self.assertEquals("The given list override index a.b[4] doesn't exist", e.message)

    def testMergeListOverrideDeep(self):
        x = {'a': [1, {'a': 2, 'b': 3}]}
        y = {'a': {1: {'a': 4}}}
        m = {'a': [1, {'a': 4, 'b': 3}]}
        self.assertEquals(m, util.merge(x, y))

    def testReplace(self):
        x = {'a': 'abc%{var}def %{var}', 'b': ['%{var} %{ var2 } %{var3}'], 'c': {'d': '%{var2} %{var3}'}}
        m = {'a': 'abc1def 1', 'b': ['1 2 3'], 'c': {'d': '2 3'}}
        self.assertEquals(m, util.replace(x, util.FixedVariables({'var': '1', 'var2': 2, 'var3': '3'})))

    def testReplacePreserveType(self):
        x = {'a': 'abc%{var}def', 'b': '%{var}'}
        m = {'a': 'abc1def', 'b': 1}
        self.assertEquals(m, util.replace(x, util.FixedVariables({'var': 1})))

    def testReplaceEscape(self):
        x = {'a': 'abc%%{var}def %%{var}def', 'b': 'abc%{var}def %{var}'}
        m = {'a': 'abc%{var}def %{var}def', 'b': 'abc1def 1'}
        self.assertEquals(m, util.replace(x, util.FixedVariables({'var': '1'})))

    def testReplaceEnv(self):
        x = {'a': '%{env.ES_PORT}'}
        m = {'a': '9300'}
        os.environ['ES_PORT'] = '9300'
        self.assertEquals(util.replace(x, util.EnvironmentVariables(util.FixedVariables({}))), m)

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
        self.assertEqual(lighter.get_marathon_appurl('myurl', 'myid'), 'myurl/v2/apps/myid')
        self.assertEqual(lighter.get_marathon_appurl('myurl/', '/myid/'), 'myurl/v2/apps/myid')
        self.assertEqual(lighter.get_marathon_appurl('myurl/', '/myid/', True), 'myurl/v2/apps/myid?force=true')

    def testBuildRequest(self):
        url = "https://user:pass@maven.example.com/path/to/my/repo"
        req = util.buildRequest(url)
        self.assertTrue(req.get_header('Authorization').startswith('Basic '))

        req = util.buildRequest(url, data={'a': 'b'})
        self.assertTrue(req.get_header('Authorization').startswith('Basic '))
        self.assertEqual('application/json', req.get_header('Content-type'))
        self.assertEqual('{"a": "b"}', req.get_data())

        req = util.buildRequest(url, data={'a': 'b'}, contentType='application/x-www-form-urlencoded')
        self.assertEqual('application/x-www-form-urlencoded', req.get_header('Content-type'))
        self.assertEqual('a=b', req.get_data())

    def testRGet(self):
        self.assertEqual('c', util.rget({'a': [{'b': 'c'}]}, 'a', 0, 'b'))
        self.assertEqual(None, util.rget({'a': [{'b': 'c'}]}, 'a', 0, 'd'))
        self.assertEqual(None, util.rget({'a': [{'b': 'c'}]}, 'a', 1, 'b'))
        self.assertEqual(None, util.rget({'a': [{'b': 'c'}]}, 'a', -1, 'b'))

    def testMangle(self):
        self.assertEqual('ab_c_', util.mangle('$!ab{c%'))
