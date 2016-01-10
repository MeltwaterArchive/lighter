#!/bin/sh
# Copied from https://github.com/pyca/cryptography/blob/master/.travis/run.sh
set -e -x

if [[ "$(uname -s)" == "Darwin" ]]; then
    # initialize our pyenv
    PYENV_ROOT=${PYENV_ROOT:-"$HOME/.pyenv"}
    PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)"

    if [[ "${OPENSSL}" != "0.9.8" ]]; then
        # set our flags to use homebrew openssl
        export ARCHFLAGS="-arch x86_64"
        # if the build is static we need different LDFLAGS
        if [[ "${CRYPTOGRAPHY_OSX_NO_LINK_FLAGS}" == "1" ]]; then
            export LDFLAGS="/usr/local/opt/openssl/lib/libssl.a /usr/local/opt/openssl/lib/libcrypto.a"
        else
            export LDFLAGS="-L/usr/local/opt/openssl/lib"
        fi
        export CFLAGS="-I/usr/local/opt/openssl/include"
        # The Travis OS X jobs are run for two versions
        # of OpenSSL, but we only need to run the
        # CommonCrypto backend tests once. Exclude
        # CommonCrypto when we test against brew OpenSSL
        export TOX_FLAGS="--backend=openssl"
    fi

    export DYLD_FALLBACK_LIBRARY_PATH=/opt/local/lib

    source ~/.venv/bin/activate
fi
