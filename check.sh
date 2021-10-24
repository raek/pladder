#!/usr/bin/env bash

set -e

echo "Flake8: static analysis and style check"
flake8 --extend-exclude .venv && echo OK
echo "Mypy: type checking"
mypy -p pladder && echo OK
echo "Pytest: unit tests"
pytest && echo OK
