import unittest
from lighter.test.deploy_test import DeployTest
from lighter.test.hipchat_test import HipChatTest
from lighter.test.maven_test import MavenTest
from lighter.test.util_test import UtilTest
from lighter.test.newrelic_test import NewRelicTest
from lighter.test.datadog_test import DatadogTest
from lighter.test.docker_test import DockerTest
from lighter.test.secretary_test import SecretaryTest

if __name__ == '__main__':
    suite = unittest.TestSuite()

    suite.addTest(unittest.makeSuite(DeployTest))
    suite.addTest(unittest.makeSuite(HipChatTest))
    suite.addTest(unittest.makeSuite(MavenTest))
    suite.addTest(unittest.makeSuite(UtilTest))
    suite.addTest(unittest.makeSuite(NewRelicTest))
    suite.addTest(unittest.makeSuite(DatadogTest))
    suite.addTest(unittest.makeSuite(DockerTest))
    suite.addTest(unittest.makeSuite(SecretaryTest))

    unittest.TextTestRunner(verbosity=2).run(suite)
