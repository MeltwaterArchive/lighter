#!/bin/bash
# Copied from https://github.com/pyca/cryptography/blob/master/.travis/install.sh
set -e -x

if [[ "$(uname -s)" == 'Darwin' ]]; then
    brew update || brew update

    if [[ "${OPENSSL}" != "0.9.8" ]]; then
        brew outdated openssl || brew upgrade openssl
    fi

    brew outdated libffi || brew upgrade libffi
    [[ -f "/usr/local/opt/libffi/lib/libffi.6.dylib" ]] || brew unlink pkg-config && brew install pkg-config libffi

    # install pyenv
    git clone https://github.com/yyuu/pyenv.git ~/.pyenv
    PYENV_ROOT="$HOME/.pyenv"
    PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)"

    curl -O https://bootstrap.pypa.io/get-pip.py
    python get-pip.py --user
    rm -f get-pip.py

    pyenv rehash
    python -m pip install --user virtualenv

    python -m virtualenv ~/.venv
    source ~/.venv/bin/activate
fi

pip install -r requirements.txt
