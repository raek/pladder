#!/usr/bin/env bash

set -e
set -u

if [[ $# != 1 ]]; then
    echo "Usage: upgrade.sh <repo-root>"
    exit 1
fi

git fetch --prune origin
git merge --ff-only origin/master
pip3 uninstall -y pladder
pip3 install "$1"
systemctl --user daemon-reload
systemctl --user restart pladder-bot.service
