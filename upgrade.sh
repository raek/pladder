#!/usr/bin/env bash

set -e
set -u

if [[ $# != 1 ]]; then
    echo "Usage: upgrade.sh <repo-root>"
    exit 1
fi

git fetch --prune origin
git reset --hard origin/master
pip3 uninstall -y pladder
echo "LAST_COMMIT=$(git log --pretty=format:"%h \"%s\" by %an, %ad" -n 1 | python3 -c "import sys; sys.stdout.write(repr(next(sys.stdin)))")" > pladder/__init__.py
pip3 install --user --no-warn-script-location "$1"
git checkout -- pladder/__init__.py
systemctl --user daemon-reload
systemctl --user restart pladder-bot.service
systemctl --user restart pladder-log.service
