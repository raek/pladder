#!/usr/bin/env bash

set -e

echo "Setting up a clean virtual environment..."
rm -rf .venv
source setup_and_activate_venv.sh
echo "Virtual environment set up."
echo
echo "Running checks..."
./check.sh
echo "Checks done."
