# Lighter
Lighter solves the problem of automating deployments to [Marathon](https://github.com/mesosphere/marathon) and 
handling of differences between multiple environments.

## Environment Variables

 * **MARATHON_URL** - Marathon url, e.g. "http://marathon-01:8080/"

## Usage

```
Usage: docker run --rm -v "`pwd`:/site" meltwater/lighter:latest [options]... production/service.yml production/service2.yml

Marathon deployment tool

Options:
  -h, --help            show this help message and exit
  -m MARATHON, --marathon=MARATHON
                        Marathon url, e.g. "http://marathon-01:8080/"
  -n, --noop            Execute dry-run without modifying Marathon
  -v, --verbose         Increase logging verbosity
```

## Configuration

Given a directory structure like
```
marathon-site/
|   globals.yml
└─production/
|   |   globals.yml
|   └─ services/
|          myservice.yml
|          myservice2.yml
└─staging/
    |   globals.yml
    └─ services/
            myservice.yml
```

Running `lighter -m http://marathon-host:8080 staging/services/myservice.yml` will

* Merge *myservice.yml* with environment defaults from *marathon-site/staging/globals.yml* and *marathon-site/globals.yml*
* Fetch the *json* template for this service and version from the Maven repository
* Expand the *json* template with variables and overrides from the *yml* files
* Post the resulting *json* configuration into Marathon

### Maven
The `maven:` section specifies where to fetch *json* templates from. For example

*globals.yml*
```
maven:
  repository: "http://username:password@maven.example.com/nexus/content/groups/public
```

*myservice.yml*
```
maven:
  groupid: com.example
  artifactid: myservice
  version: 1.0.0
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
  mem: 4000
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
