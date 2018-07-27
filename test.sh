#!/usr/bin/env bash
echo "Running pycodestyle" && pycodestyle ./garbagedog --ignore=E501,E701,W605 && echo "Running mypy" && mypy --ignore-missing-imports --no-warn-no-return ./garbagedog && echo "pycodestyle/mypy passed!" \
    && echo "Running Python tests" && pytest -v && echo "Python tests passed!"
