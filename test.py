#!/usr/bin/env python
import unittest, lighter

class TestStringMethods(unittest.TestCase):
    def test_parse_file(self):
        json_file = lighter.parse_file('test/myservice.yml')
        self.assertEqual(json_file['id'],'/myproduct/myservice')
        self.assertEqual(json_file['env']['DATABASE'], 'database:3306')
        self.assertEqual(json_file['cpus'], 1)

    def test_merge_dicts(self):
        x = {'a': 1, 'b': 2}
        y = {'b': 3, 'c': 4}
        x_y = {'a': 1, 'b': 3, 'c': 4}
        self.assertEqual(lighter.merge_dicts(x, y),x_y)
        y_x = {'a': 1, 'b': 2, 'c': 4}
        self.assertEqual(lighter.merge_dicts(y, x),y_x)

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
