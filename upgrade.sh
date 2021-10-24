#!/usr/bin/env bash

set -e
set -u

if [[ $# != 1 ]]; then
    echo "Usage: upgrade.sh <repo-root>"
    exit 1
fi

git fetch --prune origin
git reset --hard origin/master
echo "LAST_COMMIT=$(git log --pretty=format:"%h \"%s\" by %an, %ad" -n 1 | python3 -c "import sys; sys.stdout.write(repr(next(sys.stdin)))")" > pladder/__init__.py
if [[ ! -d ~/.cache/pladder-venv ]]; then
    python3 -m venv --system-site-packages ~/.cache/pladder-venv
fi
source ~/.cache/pladder-venv/bin/activate
echo "Installing pladder..."
pip install --force-reinstall "$1"[systemd]
echo "Pladder installed"
git checkout -- pladder/__init__.py
echo "Restarting pladder-bot..."
systemctl --user daemon-reload
systemctl --user restart pladder-bot.service
echo "Restarted pladder-bot"
