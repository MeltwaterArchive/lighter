#!/bin/sh
set -e -x
. ./common.sh

# Build the standalone binary
pyinstaller --hidden-import=cffi --hidden-import=packaging --hidden-import=packaging.version --hidden-import=packaging.specifiers --onefile "--name=lighter-$(uname -s)-$(uname -m)" "--additional-hooks-dir=`dirname $0`/src/hooks" src/lighter/main.py
