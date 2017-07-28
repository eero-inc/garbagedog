#!/bin/bash

mkdir -p ./dist
VERSION=`python setup.py  --version`
ARTIFACT=./dist/garbagedog-$OSTYPE-$VERSION.pex
env PEX_VERBOSE=1 pex . -r requirements.txt -o $ARTIFACT -c garbagedog
echo Built to $ARTIFACT
