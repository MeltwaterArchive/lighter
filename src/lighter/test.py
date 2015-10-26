#!/usr/bin/env python
import unittest
import lighter.main as lighter
from lighter.util import *

class TestStringMethods(unittest.TestCase):
    def test_parse_file(self):
        service = lighter.parse_file('src/resources/yaml/staging/myservice.yml')
        self.assertEqual(service.document['hipchat']['token'], 'abc123')
        self.assertEqual(service.document['hipchat']['rooms'][0], '123456')
        self.assertEqual(service.environment, 'staging')

        config = service.config
        self.assertEqual(config['id'],'/myproduct/myservice')
        self.assertEqual(config['env']['DATABASE'], 'database:3306')
        self.assertEqual(config['env']['rabbitmq'], 'amqp://myserver:15672')
        self.assertEqual(config['cpus'], 1)
        self.assertEqual(config['instances'], 3)

    def test_merge(self):
        x = {'a': 1, 'b': 2}
        y = {'b': 3, 'c': 4}
        z = {'c': 5, 'd': 6}
        
        m = {'a': 1, 'b': 3, 'c': 5, 'd': 6}
        self.assertEqual(merge(x, y, z),m)
        m = {'a': 1, 'b': 2, 'c': 4, 'd': 6}
        self.assertEqual(merge(z, y, x),m)

    def test_replace(self):
        x = {'a':'abc%{var}def', 'b':[u'%{var} %{var2} %{var3}'], 'c': {'d': '%{var2} %{var3}'}}
        m = {'a':'abc1def', 'b':[u'1 2 3'], 'c': {'d': '2 3'}}
        self.assertEquals(replace(x, {'var':'1', 'var2':2, 'var3': u'3'}), m)

    def test_compare_service_versions(self):
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

    def test_get_marathon_url(self):
        self.assertEqual(lighter.get_marathon_url('myurl', 'myid'), 'myurl/v2/apps/myid?force=true')
        self.assertEqual(lighter.get_marathon_url('myurl/', '/myid/'), 'myurl/v2/apps/myid?force=true')

    def test_build_request(self):
        url = "https://user:pass@maven.example.com/path/to/my/repo"
        req = lighter.build_request(url)
        self.assertTrue(req.get_header('Authorization').startswith('Basic '))

if __name__ == '__main__':
    unittest.main()
