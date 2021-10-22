import hmac
import json
import os
import subprocess

from flask import Flask, make_response, request  # type: ignore


app = Flask(__name__)


@app.route("/github-webhook", methods=["POST"])
def github_webhook():
    secret, repo_dir = read_config()
    payload = request.get_data()
    try:
        signature = request.headers["X-Hub-Signature"]
        assert valid_signature(secret, payload, signature)
    except Exception:
        return make_response(("Forbidden", 403))
    try:
        event_type = request.headers["X-GitHub-Event"]
        assert request.content_type == "application/json"
        event = json.loads(payload.decode("utf8"))
    except Exception:
        return make_response(("Bad Request", 400))
    print("Got event {} from user {}".format(event_type, event["sender"]["login"]))
    if event_type == "push":
        script = os.path.join(repo_dir, "upgrade.sh")
        subprocess.Popen([script, repo_dir], cwd=repo_dir)
        # Don't wait for subprocess to finish. The GitHub client has
        # a too short timeout for it to complete in time.
    return "OK"


def read_config():
    config_home = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.environ["HOME"], ".config"))
    config_path = os.path.join(config_home, "pladder-upgrade", "config.json")
    with open(config_path, "rt") as f:
        config = json.load(f)
    return config["secret"], config["repo_dir"]


def valid_signature(secret, payload, signature):
    expected_signature = "sha1=" + hmac.new(secret.encode("utf8"), payload, "sha1").hexdigest()
    return hmac.compare_digest(signature, expected_signature)
