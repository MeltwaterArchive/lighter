#!/bin/bash
set -e -x
. ./common.sh

# if "test" is provided as an argument, skip building the binary
if [ "$1" != "test" ]; then
    # Build the standalone binary
    pyinstaller --onefile "--name=lighter-$(uname -s)-$(uname -m)" "--additional-hooks-dir=`dirname $0`/src/hooks" src/lighter/main.py
fi
