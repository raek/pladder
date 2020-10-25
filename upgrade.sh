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
echo "LAST_COMMIT='$(git log --pretty=format:"%h \"%s\" by %an, %ad" -n 1)'" > pladder/__init__.py
pip3 install --user --no-warn-script-location "$1"
git checkout -- pladder/__init__.py
systemctl --user daemon-reload
systemctl --user restart pladder-bot.service
