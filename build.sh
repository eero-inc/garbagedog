#!/bin/bash

mkdir -p ./dist
VERSION=`python setup.py  --version`

OS=$OSTYPE
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="osx"
fi

ARTIFACT=./dist/garbagedog-${OS}-${VERSION}.pex
env PEX_VERBOSE=1 pex . -r requirements.txt -o ${ARTIFACT} -c garbagedog
echo Built to ${ARTIFACT}
