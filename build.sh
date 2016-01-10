#!/bin/sh
set -e -x
. ./common.sh

# Build the standalone binary
pyinstaller --onefile "--name=lighter-$(uname -s)-$(uname -m)" "--additional-hooks-dir=`dirname $0`/src/hooks" src/lighter/main.py
