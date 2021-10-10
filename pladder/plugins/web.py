from contextlib import contextmanager
from datetime import datetime, timezone

from pladder.dbus import RetryProxy


@contextmanager
def pladder_plugin(bot):
    web_api = RetryProxy(bot.bus, "se.raek.PladderWebApi")
    web_commands = WebCommands(web_api)
    cmds = bot.new_command_group("web")
    cmds.register_command("create-token", web_commands.create_token, contextual=True)
    cmds.register_command("show-token", web_commands.show_token)
    cmds.register_command("list-tokens", web_commands.list_tokens)
    cmds.register_command("delete-token", web_commands.delete_token)
    yield


def _format_time(ts):
    utc_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    local_dt = utc_dt.astimezone(tz=None)
    return local_dt.strftime("%Y-%m-%d %H:%M:%S")


class WebCommands:
    def __init__(self, web_api):
        self.web_api = web_api

    def create_token(self, context, token_name):
        network = context.metadata["network"]
        user = context.metadata["nick"]
        ok, secret = self.web_api.CreateToken(token_name, network, user)
        if ok:
            return (f'New token named "{token_name}" created with secret "{secret}". ' +
                    "The string will not be displayed again and does not contain any zero or one digits.")
        else:
            return f'Token name "{token_name}" is already in use.'

    def show_token(self, token_name):
        ok, used, use_count, created, network, user = self.web_api.GetToken(token_name)
        if ok:
            used = _format_time(used)
            created = _format_time(created)
            return f'Token "{token_name}", used {use_count} times, last used {used}, created by {user} ({network}) at {created}'
        else:
            return f'Token "{token_name}" was not found.'

    def list_tokens(self):
        return "Active tokens: " + ", ".join((self.web_api.ListTokens()))

    def delete_token(self, token_name):
        ok = self.web_api.DeleteToken(token_name)
        if ok:
            return f'Token "{token_name}" was deleted.'
        else:
            return f'Token "{token_name}" was not found.'
