# Lighter
[![Travis CI](https://img.shields.io/travis/meltwater/lighter/master.svg)](https://travis-ci.org/meltwater/lighter)
[![Coverage Status](https://codecov.io/github/meltwater/lighter/coverage.svg?branch=master)](https://codecov.io/github/meltwater/lighter?branch=master&view=all)

[Lighter](https://en.wikipedia.org/wiki/Lighter_(barge)) solves the problem of automating 
deployments to [Marathon](https://github.com/mesosphere/marathon) and handling of differences
between multiple environments. Given a hierachy of yaml files and environments, Lighter can
expand service config files and deploy them to Marathon. 

For even tighter integration into the development process, Lighter can resolve Marathon config files
from Maven and merge these with environment specific overrides. This enables continuous deployment 
whenever new releases or snapshots appear in the Maven repository. Optional version range constraints 
allows patches/minor versions to be rolled out continuously, while requiring a config change to roll
out major versions.

## Usage
```
usage: lighter COMMAND [OPTIONS]...

Marathon deployment tool

positional arguments:
  {deploy,verify}  Available commands
    deploy         Deploy services to Marathon
    verify         Verify and generate Marathon configuration files

optional arguments:
  -h, --help       show this help message and exit
  -n, --noop       Execute dry-run without modifying Marathon [default: False]
  -v, --verbose    Increase logging verbosity [default: False]
```

### Deploy Command
```
usage: lighter deploy [OPTIONS]... YMLFILE...

Deploy services to Marathon

positional arguments:
  YMLFILE               Service files to expand and deploy

optional arguments:
  -h, --help            show this help message and exit
  -m MARATHON, --marathon MARATHON
                        Marathon url, e.g. "http://marathon-host:8080/"
  -f, --force           Force deployment even if the service is already
                        affected by a running deployment [default: False]
```

## Configuration
Given a directory structure like

```
my-config-repo/
|   globals.yml
└─ production/
|   |   globals.yml
|   └─ services/
|          myservice.yml
|          myservice2.yml
└─ staging/
    |   globals.yml
    └─ services/
           myservice.yml
```

Running `lighter deploy -m http://marathon-host:8080 staging/services/myservice.yml` will

* Merge *myservice.yml* with environment defaults from *my-config-repo/staging/globals.yml* and *my-config-repo/globals.yml*
* Fetch the *json* template for this service and version from the Maven repository
* Expand the *json* template with variables and overrides from the *yml* files
* Post the resulting *json* configuration into Marathon

## Maven
The `maven:` section specifies where to fetch *json* templates from which are 
merged into the configuration. For example

*globals.yml*
```
maven:
  repository: "http://username:password@maven.example.com/nexus/content/groups/public"
```

*myservice.yml*
```
maven:
  groupid: 'com.example'
  artifactid: 'myservice'
  version: '1.0.0'
  classifier: 'marathon'
```

The Maven 'classifier' tag is optional.

### Dynamic Versions
Versions can be dynamically resolved from Maven using a range syntax.

```
maven:
  groupid: 'com.example'
  artifactid: 'myservice'
  resolve: '[1.0.0,2.0.0)'
```

For example

Expression | Resolve To
:----------|:-----------
[1.0.0,2.0.0) | 1.0.0 up to but not including 2.0.0
[1.0.0,1.2.0] | 1.0.0 up to and including 1.2.0
[1.0.0,2.0.0)-featurebranch | 1.0.0 up to and including 1.2.0, only matches *featurebranch* releases
[1.0.0,1.2.0]-SNAPSHOT | 1.0.0 up to and including 1.2.0, only matches *SNAPSHOT* versions
[1.0.0,2.0.0]-featurebranch-SNAPSHOT | 1.0.0 up to and including 1.2.0, only matches *featurebranch-SNAPSHOT* versions
[1.0.0,] | 1.0.0 or greater
(1.0.0,] | Greater than 1.0.0
[,] | Latest release version
[,]-SNAPSHOT | Latest *SNAPSHOT* version

## Freestyle Services
Yaml files may contain a `service:` tag which specifies a Marathon *json* fragment 
to use as the service configuration base for further merging. This allows for
services which aren't based on a *json* template but rather defined exclusively 
in *yaml*.

*myservice.yml*
```
service:
  id: '/myproduct/myservice'
  container:
    docker:
      image: 'meltwater/myservice:latest'
  env:
    DATABASE: 'database:3306'
  cpus: 1.0
  mem: 1200
  instances: 1
```

## Overrides
Yaml files may contain an `override:` section that will be merged directly into the Marathon json. The 
structure contained in the `override:` section must correspond to the [Marathon REST API](https://mesosphere.github.io/marathon/docs/rest-api.html#post-v2-apps). For example 

```
override:
  instances: 4
  cpus: 2.0
  env:
    LOGLEVEL: 'info'
    NEW_RELIC_APP_NAME: 'MyService Staging'
    NEW_RELIC_LICENSE_KEY: '123abc'
```

## Variables
Yaml files may contain an `variables:` section containing key/value pairs that will be substituted into the *json* template. All 
variables in a templates must be resolved or it's considered an error. This can be used to ensure that some parameters are 
guaranteed to be provided to a service. For example
```
variables:
  docker.registry: 'docker.example.com'
  rabbitmq.host: 'rabbitmq-hostname'
```

And used from the *json* template like
```
{
    "id": "/myproduct/myservice",
    "container": {
        "docker": {
            "image": "%{docker.registry}/myservice:1.2.3"
        }
    },
    "env": {
        "rabbitmq.url": "amqp://guest:guest@%{rabbitmq.host}:5672"
    }
}
```

### Predefined Variables

Variable | Contains
:--------|:--------
%{lighter.version} | Maven artifact version or Docker image version
%{lighter.uniqueVersion} | Unique build version resolved from Maven/Docker metadata

## Snapshot Builds
If an image is rebuilt with the same Docker tag, Marathon won't detect a change and hence won't roll out the new
image. To ensure that new snapshot/latest versions are deployed use `%{lighter.uniqueVersion}` and `forcePullImage`
like this

*myservice.yml*
```
override:
  container:
    docker:
      forcePullImage: true
  env:
    SERVICE_BUILD: '%{lighter.uniqueVersion}'
```

### Docker Registry
Lighter calls the Docker Registry API to resolve `%{lighter.uniqueVersion}` when it's used
in a non-Maven based service. This is only enabled if the `%{lighter.uniqueVersion}` variable
is actually referenced from the service config. 

For authenticated reprositories you must supply read-access credentials to be used when calling
the registry API. You can find the base64 encoded credentials in your *~/.docker/config.json* or
*~/.dockercfg* files. Note that Docker Hub is not supported at this time.

*globals.yml*
```
docker:
  registries:
    'registry.example.com':
      auth: 'dXNlcm5hbWU6cGFzc3dvcmQ='
```

## Facts
Yaml files may contain a `facts:` section with information about the service surroundings

*staging/globals.yml*
```
facts:
  environment: 'staging'
```

## Installation
Place a `lighter` script in the root of your configuration repo. Replace the LIGHTER_VERSION with 
a version from the [releases page](https://github.com/meltwater/lighter/releases).

```
#!/bin/sh
set -e

LIGHTER_VERSION="x.y.z"
LIGHTER="`dirname $0`/target/lighter-`uname -s`-`uname -m`-${LIGHTER_VERSION}"

if [ ! -x "$LIGHTER" ]; then
    mkdir -p $(dirname "$LIGHTER")
    curl -sfLo "$LIGHTER" https://github.com/meltwater/lighter/releases/download/${LIGHTER_VERSION}/lighter-`uname -s`-`uname -m`
    chmod +x "$LIGHTER"
fi

# Ligher will write the expanded json files to /tmp/output 
exec "$LIGHTER" -t "`dirname $0`/target" $@
```

Use the script like
```
cd my-config-repo

# Deploy/sync all services (from Jenkins or other CI/CD server)
./lighter deploy -f -m http://marathon-host:8080 $(find staging -name \*.yml -not -name globals.yml)

# Deploy single services
./lighter deploy -m http://marathon-host:8080 staging/myservice.yml staging/myservice2.yml
```

## Integrations
Lighter can push deployment notifications to a number of services.

### HipChat
Yaml files may contain an `hipchat:` section that specifies where to announce deployments. Create a [HipChat V2 token](https://www.hipchat.com/docs/apiv2) that is allowed to post to rooms. 

```
hipchat:
  token: '123abc'
  rooms:
    - '123456'
```

### New Relic
To send [New Relic deployment notifications](https://docs.newrelic.com/docs/apm/new-relic-apm/maintenance/deployment-notifications) supply your [New Relic REST API key](https://docs.newrelic.com/docs/apis/rest-api-v2/requirements/api-keys) (different from the license key given to the agent). 

*globals.yml*
```
newrelic:
  token: '123abc'
```

*myservice.yml*
```
override:
  env:
    NEW_RELIC_LICENSE_KEY: 'abc123'
    NEW_RELIC_APP_NAME: 'MyService'
```

### Datadog
To send [Datadog deployment events](http://docs.datadoghq.com/guides/overview/#events) supply your [Datadog API key](https://app.datadoghq.com/account/settings#api).

*globals.yml*
```
datadog:
  token: '123abc'
```