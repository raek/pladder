import hmac
import json
from pathlib import Path
import subprocess
import threading
import traceback

from flask import Flask, make_response, request  # type: ignore

from .config import read_config


app = Flask(__name__)


@app.route("/github-webhook", methods=["POST"])
def github_webhook():
    config = read_config()
    payload = request.get_data()
    try:
        signature = request.headers["X-Hub-Signature"]
        assert valid_signature(config.secret, payload, signature)
    except Exception:
        return make_response(("Forbidden", 403))
    try:
        event_type = request.headers["X-GitHub-Event"]
        assert request.content_type == "application/json"
        event = json.loads(payload.decode("utf8"))
    except Exception:
        return make_response(("Bad Request", 400))
    print(f"Got event {event_type} for ref {event['ref']} from user {event['sender']['login']}")
    if event_type == "push" and event["ref"] == config.ref:
        def f():
            upgrade(url=event["repository"]["clone_url"],
                    commit=event["after"],
                    message=event["head_commit"]["message"].split("\n")[0],
                    author=event["head_commit"]["author"]["name"],
                    timestamp=event["head_commit"]["timestamp"])
        threading.Thread(target=f).start()
        # Don't wait for the upgrade to finish. The GitHub client has
        # a too short timeout for it to complete in time.
    return "OK"


def valid_signature(secret, payload, signature):
    expected_signature = "sha1=" + hmac.new(secret.encode("utf8"), payload, "sha1").hexdigest()
    return hmac.compare_digest(signature, expected_signature)


VENV_BIN = Path.home() / ".cache" / "pladder-venv" / "bin"


def upgrade(url, commit, message, author, timestamp):
    try:
        version = f"{commit[:7]} \"{message}\" by {author}, {timestamp}"
        write_version("Upgrade in progress...")
        subprocess.run([VENV_BIN / "pip", "uninstall", "-y", "pladder"], check=False)
        subprocess.run([VENV_BIN / "pip", "install", f"pladder[systemd] @ git+{url}@{commit}"], check=True)
        write_version(version)
        subprocess.run([VENV_BIN / "pladder-systemd", "update-unit-files"], check=True)
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "--user", "restart", "pladder-bot"], check=True)
        print(f"Upgraded successfully to: {version}")
    except Exception:
        write_version("Upgrade error!")
        print(traceback.format_exc())


VERSION_FILE = Path.home() / ".config" / "pladder-bot" / "version.txt"


def write_version(s):
    with VERSION_FILE.open(mode="w", encoding="utf-8") as f:
        f.write(s)
