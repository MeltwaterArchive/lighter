# Lighter
Lighter solves the problem of automating deployments to [Marathon](https://github.com/mesosphere/marathon) and 
handling of differences between multiple environments.

## Environment Variables

 * **MARATHON_URL** - Marathon url, e.g. "http://marathon-host:8080/"

## Usage

```
Usage: docker run --rm -v "`pwd`:/site" meltwater/lighter:latest [options]... production/service.yml production/service2.yml

Marathon deployment tool

Options:
  -h, --help            show this help message and exit
  -m MARATHON, --marathon=MARATHON
                        Marathon url, e.g. "http://marathon-host:8080/"
  -n, --noop            Execute dry-run without modifying Marathon
  -v, --verbose         Increase logging verbosity
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

Running `lighter -m http://marathon-host:8080 staging/services/myservice.yml` will

* Merge *myservice.yml* with environment defaults from *my-config-repo/staging/globals.yml* and *my-config-repo/globals.yml*
* Fetch the *json* template for this service and version from the Maven repository
* Expand the *json* template with variables and overrides from the *yml* files
* Post the resulting *json* configuration into Marathon

### Maven
The `maven:` section specifies where to fetch *json* templates from. For example

*globals.yml*
```
maven:
  repository: "http://username:password@maven.example.com/nexus/content/groups/public"
```

*myservice.yml*
```
maven:
  groupid: "com.example"
  artifactid: "myservice"
  version: "1.0.0"
```

#### Dynamic Versions
Versions can be dynamically resolved from Maven using a range syntax.

```
maven:
  groupid: "com.example"
  artifactid: "myservice"
  resolve: "[1.0.0,2.0.0)"
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

### Facts
Yaml files may contain a `facts:` section with information about the service surroundings

```
facts:
  environment: "staging"
```

### Variables
Yaml files may contain an `variables:` section containing key/value pairs that will be substituted into the *json* template. All 
variables in a templates must be resolved or it's considered an error. This can be used to ensure that some parameters are 
guaranteed to be provided to a service. For example
```
variables:
  docker.registry: "docker.example.com"
  rabbitmq.host: "rabbitmq-hostname"
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

### Overrides
Yaml files may contain an `overrides:` section that will be merged directly into the Marathon json. The 
structure contained in the `override:` section must correspond to the [Marathon REST API](https://mesosphere.github.io/marathon/docs/rest-api.html#post-v2-apps). For example 

```
overrides:
  instances: 4
  cpus: 2.0
  env:
    LOGLEVEL: "info"
    NEW_RELIC_APP_NAME: "MyService Staging"
    NEW_RELIC_LICENSE_KEY: "123abc"
```

### HipChat
Yaml files may contain an `hipchat:` section that specifies where to announce deployments. Create a [HipChat V2 token](https://www.hipchat.com/docs/apiv2) that is allowed to post to rooms. For example

```
hipchat:
  token: "123abc"
  rooms:
    - "123456"
```

## Deployment
Place a `lighter` script in the root of your configuration repo.

```
#!/bin/sh
set -e

# Must mount this directory into the container so that all globals.yml are found
OLDCWD="`pwd`"
cd "`dirname $0`"
NEWCWD="`pwd`"

if [ "$OLDCWD" != "$NEWCWD" ]; then
  LIGHTER_DOCKER_OPTS="$LIGHTER_DOCKER_OPTS -v ${NEWCWD}:${NEWCWD} -v ${OLDCWD}:${OLDCWD} --workdir ${OLDCWD}"
else
  LIGHTER_DOCKER_OPTS="$LIGHTER_DOCKER_OPTS -v ${NEWCWD}:${NEWCWD} --workdir ${NEWCWD}"
fi

# Ligher will write the expanded json files to ./output 
exec docker run --rm --net=host -v "${NEWCWD}/output:/tmp/lighter" $LIGHTER_DOCKER_OPTS meltwater/lighter:latest $@
```

Execute the script for example like

```
cd my-config-repo

# Deploy/sync all services (for example from Jenkins or other CI/CD server)
./lighter -m http://marathon-host:8080 $(find staging -name \*.yml -not -name globals.yml)

# Deploy single services
./lighter -m http://marathon-host:8080 staging/myservice.yml staging/myservice2.yml
```
