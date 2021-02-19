#!/usr/bin/env bash

set -e

echo "Mypy (type checking)"
python3 -m mypy -p pladder && echo OK
echo "Flake8"
python3 -m flake8 && echo OK
echo "Pytest"
python3 -m pytest && echo OK
