from contextlib import contextmanager

from pladder.script.types import ScriptError

import requests  # type: ignore


@contextmanager
def pladder_plugin(bot):
    cmds = bot.new_command_group("rest")
    cmds.register_command("rest-post-simple", rest_post_simple)
    cmds.register_command("rest-post", rest_post)
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


def rest_post(url, message, *header_pairs):
    """
    Do a POST to a REST API, sending plain text with optional headers and returning the result
    Example usage:
    rest-post https://example.com/api {Hello together!} x-api-key secret
    """
    headers = {}
    if len(header_pairs) % 2 != 0:
        raise ScriptError("Headers must be provided in pairs (key, value)")

    if header_pairs:
        it = iter(header_pairs)
        headers = dict(zip(it, it))
        for key, value in headers.items():
            headers[key] = value.encode("utf-8")

    headers.setdefault("Content-Type", "text/plain; charset=utf-8")
    r = requests.post(url, headers=headers, data=message.encode("utf-8"), allow_redirects=False)
    if not r.ok:
        raise ScriptError(f"Unexpected error code: {r.status_code} - {r.reason}")
    else:
        return r.text
