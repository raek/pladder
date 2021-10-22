from contextlib import contextmanager

from pladder.script.types import ScriptError

import requests  # type: ignore


@contextmanager
def pladder_plugin(bot):
    cmds = bot.new_command_group("rest")
    cmds.register_command("rest-post-simple", rest_post_simple)
    yield


def rest_post_simple(url, message):
    """
    Do a POST to a simple REST API, sending plain text and returning the result
    """
    headers = {"Content-Type": "text/plain; charset=utf-8"}
    r = requests.post(url, headers=headers, data=message.encode("utf-8"))
    if r.status_code != 200:
        raise ScriptError("Unexpected error code: %d" % r.status_code)
    else:
        return r.text
