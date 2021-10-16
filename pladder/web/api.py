import atexit
from contextlib import ExitStack
from datetime import datetime, timezone

from flask import Flask, make_response, request

from pladder.web.hub import Hub


app = Flask(__name__)

global_context = ExitStack().__enter__()
atexit.register(global_context.__exit__, None, None, None)
hub = global_context.enter_context(Hub())


@app.route("/run-command", methods=["POST"])
def hello():
    now = int(datetime.now(timezone.utc).timestamp())
    if not request.data:
        return make_response(("Bad Request", 400))
    if request.headers.get("Content-Type", None) != "text/plain; charset=utf-8":
        return make_response(("Bad Request", 400))
    secret = request.headers.get("X-Pladder-Token", None)
    if secret is None:
        return make_response(("Forbidden", 403))
    token_name = hub.db.check_token(secret)
    if token_name is None:
        return make_response(("Forbidden", 403))
    script = request.data.decode("utf-8")
    print(f"Request by {token_name}: {script}")
    result = hub.bot.RunCommand(now, "Web", "api", token_name, script)
    print(f"Response: {result['text']}")
    return result["text"]
