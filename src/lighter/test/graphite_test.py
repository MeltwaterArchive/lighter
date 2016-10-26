import unittest
from mock import patch, Mock
import lighter.main as lighter
from lighter.graphite import Graphite

class GraphiteTest(unittest.TestCase):
    @patch('lighter.util.jsonRequest')
    def testNotify(self, mock_jsonRequest):
        graphite = Graphite('localhost:2003', 'http://localhost:80/')

        graphite.notify(
            'lighter.myservice.deployments',
            'Deployed myservice', 'Deployed myservice to production environment')
        graphite.notify(
            'lighter.myservice.deployments',
            'Deployed myservice', 'Deployed myservice to production environment', ['subsystem:something'])

        self.assertEquals(mock_jsonRequest.call_count, 2)

    @patch('lighter.util.jsonRequest')
    def testNoGraphiteUrl(self, mock_jsonRequest):
        graphite = Graphite('', '')

        graphite.notify(
            'lighter.myservice.deployments',
            'Deployed myservice', 'Deployed myservice to production environment')

        self.assertEquals(mock_jsonRequest.call_count, 0)

    @patch('lighter.util.jsonRequest')
    @patch('lighter.graphite.socket.socket')
    @patch('lighter.graphite.time.time', return_value=1477507464.895971)
    def testDeployNotify(self, mock_time, mock_socket, mock_jsonRequest):
        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        service = lighter.parse_service('src/resources/yaml/integration/graphite-config-tags.yml')
        lighter.notify('http://localhost:8080/', service)

        mock_jsonRequest.assert_called_with(
            'http://localhost:80/events/', method='POST', data={
                'what': 'Deployed /myproduct/myservice to the default environment',
                'data': 'Lighter deployed /myproduct/myservice with image meltwater/myservice:latest to default (localhost:8080)',
                'tags': ['environment:default', 'service:/myproduct/myservice', 'somekey:someval',
                         'anotherkey:anotherval', 'justakey', 'source:lighter', 'type:change'],
                'when': 1477507464})

        self.assertEquals(1, mock_sock.connect.call_count)
        mock_sock.connect.assert_called_with(('localhost', 2003))

        self.assertEquals(1, mock_sock.send.call_count)
        mock_sock.send.assert_called_with("ci.lighter.default.myproduct.myservice.deployments 1 1477507464\n")
