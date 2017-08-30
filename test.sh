#!/usr/bin/env bash
echo "Running PEP8" && pep8 ./garbagedog --ignore=E501,E701 && echo "Running mypy" && mypy --ignore-missing-imports ./garbagedog && echo "Good to go!"
