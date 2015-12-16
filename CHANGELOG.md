# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]

- Corrected [Secretary](https://github.com/meltwater/secretary) link to use the [meltwater/secretary](https://github.com/meltwater/secretary) repo
- Clarified directory structure
- Add warnings when 'token' is the env var name
- Your contribution here.

## [0.6.3] - 2015.12.15
#### Fixed
- Fix detection of encrypted multiline strings

## [0.6.2] - 2015.12.15
#### Changed
- Avoid adding public keys if no secrets present

## [0.6.1] - 2015.12.15
#### Changed
- Made installation example safe for whitespace in filenames

#### Fixed
- Fix problem with config being null when [secretary](https://github.com/meltwater/secretary) wasn't configured

## [0.6.0] - 2015.12.1
#### Added
- Added [Secretary](https://github.com/meltwater/secretary) support

#### Changed
- Removed deployment time encryption

#### Fixed
- Fix secrets check + improve tests

## [0.5.0] - 2015.12.11
#### Added
- Added support for setting a default [Marathon](https://mesosphere.github.io/marathon/) URL for an environment

#### Changed
- Converted to Makefile based build
- Improve checks on unencrypted secrets
- Improve error message on missing variables

#### Fixed
- Improve error message when parsing broken yaml files

## [0.4.2] - 2015.12.07
#### Added
- Added [codecov.io](https://codecov.io/) support for unit test coverage

#### Fixed
- Fixed directory creation race condition
- Improve readme

## [0.4.1] - 2015.12.03
#### Changed
- Parallelize services yaml files processing

## [0.4.0] - 2015.12.03
#### Added
- Unique version resolution from [docker registries](https://docs.docker.com/registry/)

## [0.3.1] - 2015.11.23
#### Changed
- Improve formatting of [Datadog](https://www.datadoghq.com/) deployment notifications.

## [0.3.0] - 2015.11.19
#### Added
- Add [Datadog](https://www.datadoghq.com/) deployment notifications

## [0.2.2] - 2015.11.19
#### Fixed
- Fixed CA cert packaging problem with [pyinstaller](http://www.pyinstaller.org/).

#### Changed
- Render output files in script example.

## [0.2.0] - 2015.11.19
#### Added
- Added parameter where to write rendered json files to.

#### Changed
- Replace docker based lighter script with shell script that download released versions

## [0.1.2] - 2015.11.17
#### Added
- Initial Release
