#!/usr/bin/env bash
echo "Running PEP8" && pep8 ./garbagedog --ignore=E501,E701 && echo "Running mypy" && mypy --ignore-missing-imports --no-warn-no-return ./garbagedog && echo "PEP8/mypy passed!" \
    && echo "Running Python tests" && pytest -v && echo "Python tests passed!"
