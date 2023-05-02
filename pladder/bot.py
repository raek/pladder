from contextlib import ExitStack
from datetime import datetime, timezone
from importlib import import_module
import os
import traceback

from pladder.dbus import PLADDER_BOT_XML
from pladder.plugin import BotPluginInterface, PluginLoadError
from pladder.plugins.builtin import command_usage
from pladder.script.interpreter import interpret
from pladder.script.types import ScriptError, ApplyError, CommandRegistry, new_context


def main():
    from gi.repository import GLib  # type: ignore
    from pydbus import SessionBus  # type: ignore

    state_home = os.environ.get(
        "XDG_CONFIG_HOME", os.path.join(os.environ["HOME"], ".config"))
    state_dir = os.path.join(state_home, "pladder-bot")

    bus = SessionBus()
    with PladderBot(state_dir, bus) as bot:
        load_standard_plugins(bot)
        bus.publish("se.raek.PladderBot", bot)
        loop = GLib.MainLoop()
        loop.run()


class PladderBot(ExitStack, BotPluginInterface):
    dbus = PLADDER_BOT_XML

    def __init__(self, state_dir, bus):
        super().__init__()
        os.makedirs(state_dir, exist_ok=True)
        self.state_dir = state_dir
        self.bus = bus
        self.commands = CommandRegistry()
        self.last_contexts = {}

    def new_command_group(self, name):
        return self.commands.new_command_group(name)

    def RunCommand(self, timestamp, network, channel, nick, text):
        metadata = {'datetime': datetime.fromtimestamp(timestamp, tz=timezone.utc),
                    'network': network,
                    'channel': channel,
                    'nick': nick,
                    'text': text}
        try:
            context = new_context(self.commands, metadata=metadata)
            result_text = interpret(context, text)
            result_text = result_text[:10000]
            result = {'text': result_text,
                      'command': ''}
        except ApplyError as e:
            result = {'text': "Usage: {}".format(command_usage(e.command)),
                      'command': ''}
        except ScriptError as e:
            result = {'text': f"Error: {e}",
                      'command': ''}
        except RecursionError:
            result = {'text': "RecursionError: Maximum recursion depth exceeded",
                      'command': ''}
        except Exception as e:
            print(traceback.format_exc())
            result = {'text': "Internal error: " + repr(e),
                      'command': ''}
        self.last_contexts[(network, channel)] = context
        return result


def load_standard_plugins(bot):
    plugins = [
        "builtin",
        "connector",
        "web",
        "snusk",
        "misc",
        "bjbot",
        "ttd",
        "alias",
        "bjukkify",
        "pladdble",
        "name",
        "bah",
        "azure",
        "userdef",
        "rest",
    ]
    for module_name in plugins:
        try:
            plugin_module = import_module(f"pladder.plugins.{module_name}")
            plugin_ctxmgr = getattr(plugin_module, "pladder_plugin")
            bot.enter_context(plugin_ctxmgr(bot))
            print(f"Loaded {module_name}")
        except PluginLoadError as e:
            print(f"Skipped {module_name}: {e}")
        except Exception:
            print(f"Could not load '{module_name}'. Fatal error")
            raise
    print("")


if __name__ == "__main__":
    main()
