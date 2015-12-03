import unittest, logging
from lighter.test.deploy_test import *
from lighter.test.hipchat_test import *
from lighter.test.maven_test import *
from lighter.test.util_test import *
from lighter.test.newrelic_test import *
from lighter.test.datadog_test import *
from lighter.test.docker_test import *

#logging.getLogger().setLevel(logging.DEBUG)

if __name__ == '__main__':
    unittest.main(verbosity=2)
