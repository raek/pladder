#!/usr/bin/env bash

set -e

python3 -m mypy pladder
python3 -m flake8
python3 -m pytest
