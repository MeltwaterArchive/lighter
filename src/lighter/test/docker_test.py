import unittest
import urllib2
import logging
from mock import patch
import lighter.main as lighter
from lighter.util import jsonRequest

class DockerTest(unittest.TestCase):
    def _wrapRequest(self, knownurl, response):
        def request(url, data=None, *args, **kwargs):
            if url.startswith('file:'):
                return jsonRequest(url, data, *args, **kwargs)

            if url == knownurl:
                self._dockerRegistryCalled = True
                return response

            logging.debug(url)
            raise urllib2.URLError("Unknown URL %s" % url)
        return request

    def setUp(self):
        self._dockerRegistryCalled = False

    def testPrivateV2(self):
        url = 'http://registrywithport.example.com:5000/v2/myservice/manifests/1.2.3'
        data = {"schemaVersion": 1,
                "history": [
                    {
                        "v1Compatibility": "{\"id\":\"30e6fc5eecc6e76733cf7881ee965335aae73d7c1bc7ca9817ecccbf925a4647\",\"parent\":\"b90ac02561d777b67829f428d73e78dca2adb3cf5bbd4e1ad152a330e88281b7\",\"created\":\"2015-11-23T12:56:12.819222551Z\",\"container\":\"a6cb5f2df76e9755f987bb5638eb7a56e11a221ee7083657c5e5c6167be01a5c\",\"container_config\":{\"Hostname\":\"afbbf75ae75d\",\"Domainname\":\"\",\"User\":\"\",\"AttachStdin\":false,\"AttachStdout\":false,\"AttachStderr\":false,\"Tty\":false,\"OpenStdin\":false,\"StdinOnce\":false,\"Env\":[\"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\"],\"Cmd\":[\"/bin/sh\",\"-c\",\"#(nop) ENTRYPOINT \\u0026{[\\\"/lighter\\\"]}\"],\"Image\":\"b90ac02561d777b67829f428d73e78dca2adb3cf5bbd4e1ad152a330e88281b7\",\"Volumes\":{\"/site\":{}},\"WorkingDir\":\"/site\",\"Entrypoint\":[\"/lighter\"],\"OnBuild\":[],\"Labels\":null},\"docker_version\":\"1.8.3-rc4\",\"config\":{\"Hostname\":\"afbbf75ae75d\",\"Domainname\":\"\",\"User\":\"\",\"AttachStdin\":false,\"AttachStdout\":false,\"AttachStderr\":false,\"Tty\":false,\"OpenStdin\":false,\"StdinOnce\":false,\"Env\":[\"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\"],\"Cmd\":null,\"Image\":\"b90ac02561d777b67829f428d73e78dca2adb3cf5bbd4e1ad152a330e88281b7\",\"Volumes\":{\"/site\":{}},\"WorkingDir\":\"/site\",\"Entrypoint\":[\"/lighter\"],\"OnBuild\":[],\"Labels\":null},\"architecture\":\"amd64\",\"os\":\"linux\"}"},  # noqa
                    {
                        "v1Compatibility": "{\"id\":\"b90ac02561d777b67829f428d73e78dca2adb3cf5bbd4e1ad152a330e88281b7\",\"parent\":\"277d2a07471445a484d24d352e57ac42ff7e8a31e1da06a0fccd578bba26ff17\",\"created\":\"2015-11-23T12:56:12.232870097Z\",\"container\":\"4200b3984c2ea437937b6fb0e43cfe2f61507217cdbda050f5b53ecc4f63b026\",\"container_config\":{\"Hostname\":\"afbbf75ae75d\",\"Domainname\":\"\",\"User\":\"\",\"AttachStdin\":false,\"AttachStdout\":false,\"AttachStderr\":false,\"Tty\":false,\"OpenStdin\":false,\"StdinOnce\":false,\"Env\":[\"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\"],\"Cmd\":[\"/bin/sh\",\"-c\",\"#(nop) WORKDIR /site\"],\"Image\":\"277d2a07471445a484d24d352e57ac42ff7e8a31e1da06a0fccd578bba26ff17\",\"Volumes\":{\"/site\":{}},\"WorkingDir\":\"/site\",\"Entrypoint\":null,\"OnBuild\":[],\"Labels\":null},\"docker_version\":\"1.8.3-rc4\",\"config\":{\"Hostname\":\"afbbf75ae75d\",\"Domainname\":\"\",\"User\":\"\",\"AttachStdin\":false,\"AttachStdout\":false,\"AttachStderr\":false,\"Tty\":false,\"OpenStdin\":false,\"StdinOnce\":false,\"Env\":[\"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\"],\"Cmd\":null,\"Image\":\"277d2a07471445a484d24d352e57ac42ff7e8a31e1da06a0fccd578bba26ff17\",\"Volumes\":{\"/site\":{}},\"WorkingDir\":\"/site\",\"Entrypoint\":null,\"OnBuild\":[],\"Labels\":null},\"architecture\":\"amd64\",\"os\":\"linux\"}"},  # noqa
                ]}

        with patch('lighter.util.jsonRequest', wraps=self._wrapRequest(url, data)):
            service = lighter.parse_service('src/resources/yaml/staging/myservice-docker-private.yml')
            self.assertEquals(service.config['env']['SERVICE_VERSION'], '1.2.3')
            self.assertEquals(service.config['env']['SERVICE_BUILD'], '30e6fc5eecc6e76733cf7881ee965335aae73d7c1bc7ca9817ecccbf925a4647')
            self.assertTrue(self._dockerRegistryCalled)

    def testPrivateV1Repo(self):
        url = 'https://registry.example.com/v1/repositories/myrepo/myservice/tags/latest'
        data = "30e6fc5eecc6e76733cf7881ee965335aae73d7c1bc7ca9817ecccbf925a4647"

        with patch('lighter.util.jsonRequest', wraps=self._wrapRequest(url, data)):
            service = lighter.parse_service('src/resources/yaml/staging/myservice-docker-private-repo.yml')
            self.assertEquals(service.config['env']['SERVICE_VERSION'], 'latest')
            self.assertEquals(service.config['env']['SERVICE_BUILD'], '30e6fc5eecc6e76733cf7881ee965335aae73d7c1bc7ca9817ecccbf925a4647')
            self.assertTrue(self._dockerRegistryCalled)

    def testPrivateV1(self):
        url = 'http://registrywithport.example.com:5000/v1/repositories/library/myservice/tags/1.2.3'
        data = "30e6fc5eecc6e76733cf7881ee965335aae73d7c1bc7ca9817ecccbf925a4647"

        with patch('lighter.util.jsonRequest', wraps=self._wrapRequest(url, data)):
            service = lighter.parse_service('src/resources/yaml/staging/myservice-docker-private.yml')
            self.assertEquals(service.config['env']['SERVICE_VERSION'], '1.2.3')
            self.assertEquals(service.config['env']['SERVICE_BUILD'], '30e6fc5eecc6e76733cf7881ee965335aae73d7c1bc7ca9817ecccbf925a4647')
            self.assertTrue(self._dockerRegistryCalled)

    def testPrivateV1Auth(self):
        url = 'http://username:password@authregistrywithport:5000/v1/repositories/library/myservice/tags/1.2.3'
        data = "30e6fc5eecc6e76733cf7881ee965335aae73d7c1bc7ca9817ecccbf925a4647"

        with patch('lighter.util.jsonRequest', wraps=self._wrapRequest(url, data)):
            service = lighter.parse_service('src/resources/yaml/staging/myservice-docker-private-auth.yml')
            self.assertEquals(service.config['env']['SERVICE_VERSION'], '1.2.3')
            self.assertEquals(service.config['env']['SERVICE_BUILD'], '30e6fc5eecc6e76733cf7881ee965335aae73d7c1bc7ca9817ecccbf925a4647')
            self.assertTrue(self._dockerRegistryCalled)
