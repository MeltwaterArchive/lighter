# ![Lighter](docs/logo.png)
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
  {deploy,verify}       Available commands
    deploy              Deploy services to Marathon
    verify              Verify and generate Marathon configuration files

optional arguments:
  -h, --help            show this help message and exit
  -n, --noop            Execute dry-run without modifying Marathon [default:
                        False]
  -v, --verbose         Increase logging verbosity [default: False]
  -t TARGETDIR, --targetdir TARGETDIR
                        Directory to output rendered config files
  -p PROFILES, --profile PROFILES
                        Extra profile file(s) to be merged with service
                        definitions.
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
                        Marathon URL like "http://marathon-host:8080/".
                        Overrides default Marathon URL's provided in config
                        files
  -f, --force           Force deployment even if the service is already
                        affected by a running deployment [default: False]
  --canary-group CANARYGROUP
                        Unique name for this group of canaries [default: None]
  --canary-cleanup      Destroy canaries that are no longer present [default:
                        False]
```

## Configuration
Given a directory structure like

```
config-repo/
|   globals.yml
|   myprofile.yml 
└─ production/
|   |   globals.yml
|   |   myfrontend.yml
|   └─ mysubsystem/
|          globals.yml
|          myservice-api.yml
|          myservice-database.yml
└─ staging/
    |   globals.yml
    |   myfrontend.yml
```

Running `lighter deploy -p myprofile1.yml -p myprofile2.yml staging/myfrontend.yml` will

* Merge *myfrontend.yml* with environment defaults from *config-repo/staging/globals.yml*, *config-repo/globals.yml*, *myprofile1.yml* and *myprofile2.yml*
* Fetch the *json* template for this service and version from the Maven repository
* Expand the *json* template with variables and overrides from the *yml* files
* Post the resulting *json* configuration into Marathon

## Marathon
Yaml files may contain a `marathon:` section with a default URL to reach Marathon at. The `-m/--marathon`
parameter will override this setting when given on the command-line.

*globals.yml*
```
marathon:
  url: 'http://marathon-host:8080/'
```

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
  version: '[1.0.0,2.0.0)'
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

### Deep Merge
An YAML and JSON file upwards-recursive deep merge is performed when parsing service definitions. Precedence is defined by the directory structure

* myservice.yml has the highest precedence
* globals.yml files are merged with decreasing precedency upwards in the directory structure
* myservice-1.0.0-marathon.json if fetched from Maven has the lowest precedence

Lists, dicts and scalar values are deep merged 

 * Dicts are deep merged, the result containing the union of all keys
 * Lists are appended together
 * Scalar values coalesce to the not-null value with highest precedence

The default behaviour is to append lists together, however specific list items can be overriden and deep merged using a dict with integer keys. For example

*myservice-1.0.0-marathon.json*
```
{
    "container": {
        "docker": {
            "portMappings": [
                {"containerPort": 8080, "servicePort": 1234},
                {"containerPort": 8081, "servicePort": 1235}
            ]
        }
    }
}
```

*myservice-override-serviceport.yml*
```
override:
  container:
    docker:
      portMappings:
        # Override service ports 1234,1235 with port 4000,4001
        0: 
          servicePort: 4000
        1: 
          servicePort: 4001
```

#### Non-string Environment Variables
Booleans, integers and floats in the `env` section are converted to strings before being posted
to Marathon. Non-scalar environment variables like dicts and lists are deep merged and automatically
serialized to json strings.

*myservice.yml*
```
override:
  env:
    intvar: 123
    boolvar: TRUE
    dictvar:
      mykey:
       - 1
       - 'abc'
```

Would result in a rendered json like
```
{
  "env": {
    "intvar": "123",
    "boolvar": "true",
    "dictvar": "{\"mykey\": [1, \"abc\"]}"
  }
}
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

Lighter also allows specifying environment variables as values in the configuration yaml files.

With the following configuration:
*myservice.yml*
```
service:
  id: '/myproduct/myservice'
  container:
    docker:
      image: 'meltwater/myservice:%{env.VERSION}'
  env:
    DATABASE: 'database:3306'
  cpus: 1.0
  mem: 1200
  instances: 1
```

And Running `VERSION=1.1.1 lighter deploy myservice.yml`, lighter will deploy the docker image ``meltwater/myservice:1.1.1`` to marathon.


To avoid interpolating some string like ``%{id}`` when you really want it, use ``%%{id}``

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

## Secrets Management
Lighter has support for [Secretary](https://github.com/meltwater/secretary) which can
securely distribute secrets to containers.

*someenv/globals.yml *
```
secretary:
  url: 'https://secretary-daemon-loadbalancer:5070'
  master:
    publickey: 'someenv/keys/master-public-key.pem'
```

*someenv/myservice.yml*
```
override:
  env:
    DATABASE_PASSWORD: "ENC[NACL,NVnSkhxA010D2yOWKRFog0jpUvHQzmkmKKHmqAbHAnz8oGbPEFkDfyKHQHGO7w==]"
```

## Canary Deployments
Lighter together with [Proxymatic](http://github.com/meltwater/proxymatic) supports [canary deployments](http://martinfowler.com/bliki/CanaryRelease.html) using
the `--canary-group` parameter. This parameter makes Lighter rewrite the app id and servicePort to avoid conflicts and automatically add 
the metadata labels that Proxymatic use for canaries. The `--canary-cleanup` parameter destroys canary instances when they are removed 
from configuration. 

### Canaries From Files
This example use a `*-canary-*` filename convention to separate canaries from normal services. In this workflow 
you would copy the regular service file `myservice.yml`, and make any tentative changes in this new 
`myservice-canary-somechange.yml`. When the canary has served its purpose you'd `git mv` back or `git rm` the 
canary file.


```
# Deploy regular services
lighter deploy -f -m "http://marathon-host:8080/" $(find . -name \*.yml -not -name globals.yml -not -name \*-canary-\*)

# Deploy and prune canaries
lighter deploy -f -m "http://marathon-host:8080/" --canary-group=generic --canary-cleanup $(find . -name \*-canary-\*.yml)
```

### Canaries From Pull Requests
This usage would run `lighter -t /some/output/dir verify ...` on a PR and again on its base revision. Then `diff -r` the 
rendered json files to figure out what services were modifed in the PR. The modified services would be deployed as canaries
with `lighter deploy --canary-group=mybranchname --canary-cleanup ...` whenever the PR branch is changed. When the PR is closed
or merged the canaries would be destroyed using `lighter deploy --canary-group=mybranchname --canary-cleanup`

### Canary Metrics
Lighter adds a [Docker label](https://docs.docker.com/engine/userguide/labels-custom-metadata/) `com.meltwater.lighter.canary.group`
which can be used to separate out container metrics from the canaries. 

## Installation
Place a `lighter` script in the root of your configuration repo. Replace the LIGHTER_VERSION with
a version from the [releases page](https://github.com/meltwater/lighter/releases).

```
#!/bin/bash
set -e

LIGHTER_VERSION="x.y.z"

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LIGHTER="$BASEDIR/target/lighter-`uname -s`-`uname -m`-${LIGHTER_VERSION}"

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
./lighter deploy $(find staging -name \*.yml -not -name globals.yml)

# Deploy single services
./lighter deploy staging/myservice.yml staging/myservice2.yml
```

## Integrations
Lighter can push deployment notifications to a number of services.

### HipChat
Yaml files may contain an `hipchat:` section that specifies where to announce deployments. Create a [HipChat V2 token](https://www.hipchat.com/docs/apiv2) that is allowed to post to rooms. The numeric room ID can be found in the room preferences in the HipChat web interface.

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
To send [Datadog deployment events](http://docs.datadoghq.com/guides/overview/#events) supply 
your [Datadog API key](https://app.datadoghq.com/account/settings#api). Lighter will add Marathon 
appid and canary group as Docker container labels in order for Datadog to tag collected metrics,
[see: collect_labels_as_tags](https://github.com/DataDog/dd-agent/blob/master/conf.d/docker_daemon.yaml.example).


*globals.yml*
```
datadog:
  token: '123abc'
  tags:
    - subsystem:example
```

*Datadog Puppet Config*
```
datadog::docker:
  docker_daemon:
    instances:
      - url: "unix://var/run/docker.sock"
        new_tag_names: true
        collect_labels_as_tags: ["com.meltwater.lighter.appid", "com.meltwater.lighter.canary.group"]
```

### Graphite
To send [Graphite deployment events](http://docs.grafana.org/reference/annotations/) supply your Graphite plaintext and HTTP endpoints.

*globals.yml*
```
graphite:
  address: 'graphite-host:2003'
  url: 'http://graphite-host:80/'
  prefix: 'lighter'
  tags:
    - subsystem:example
```

## Contributors

* **[Giuliano Manno](https://github.com/xyden)**

  * Lighter logo
