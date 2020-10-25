from collections import namedtuple
from contextlib import ExitStack
from datetime import datetime, timezone
from inspect import Parameter, signature
import os
import re

from pladder import LAST_COMMIT
from pladder.script import ScriptError, ApplyError, CommandBinding, interpret, lookup_command, apply_call


def main():
    from gi.repository import GLib
    from pydbus import SessionBus

    state_home = os.environ.get(
        "XDG_CONFIG_HOME", os.path.join(os.environ["HOME"], ".config"))
    state_dir = os.path.join(state_home, "pladder-bot")

    with PladderBot(state_dir) as bot:
        load_standard_plugins(bot)
        bus = SessionBus()
        bus.publish("se.raek.PladderBot", bot)
        loop = GLib.MainLoop()
        loop.run()


class PladderBot(ExitStack):
    """
    <node>
      <interface name="se.raek.PladderBot">
        <method name="RunCommand">
          <arg direction="in" name="timestamp" type="u" />
          <arg direction="in" name="network" type="s" />
          <arg direction="in" name="channel" type="s" />
          <arg direction="in" name="nick" type="s" />
          <arg direction="in" name="text" type="s" />
          <arg direction="out" name="return" type="s" />
        </method>
      </interface>
    </node>
    """

    def __init__(self, state_dir):
        super().__init__()
        os.makedirs(state_dir, exist_ok=True)
        self.state_dir = state_dir
        self.bindings = []
        self.register_command("help", self.help)
        self.register_command("version", self.version)

    def RunCommand(self, timestamp, network, channel, nick, text):
        context = {'datetime': datetime.fromtimestamp(timestamp, tz=timezone.utc),
                   'network': network,
                   'channel': channel,
                   'nick': nick,
                   'text': text}
        try:
            return interpret(self.bindings, context, text)
        except ApplyError as e:
            return "Usage: {}".format(self.command_usage(e.command))
        except ScriptError as e:
            return str(e)

    def interpret(self, context, text):
        return interpret(self.bindings, context, text)

    def apply(self, context, words):
        if not words:
            return ""
        command_name, arguments = words[0], words[1:]
        command = lookup_command(self.bindings, command_name)
        return apply_call(context, command, command_name, arguments)

    def register_command(self, name, fn, varargs=False, regex=False, contextual=False):
        if regex:
            name = re.compile("^" + name + "$")
        self.bindings.append(CommandBinding(name, fn, varargs, regex, contextual))

    def command_display_name(self, command):
        if command.regex:
            return f"/{command.command_name.pattern[1:-1]}/"
        else:
            return command.command_name

    def command_usage(self, command):
        result = self.command_display_name(command)
        parameters = list(signature(command.fn).parameters.values())
        if command.contextual:
            # pop context argument
            parameters.pop(0)
        for i, parameter in enumerate(parameters):
            if i == len(parameters) - 1 and command.varargs:
                result += f" {{{parameter.name}...}}"
            elif parameter.default != Parameter.empty:
                result += f" [{parameter.name}]"
            else:
                result += f" <{parameter.name}>"
        return result

    def help(self, command_name=None):
        if not command_name:
            result = "Available commands: "
            result += ", ".join(self.command_display_name(command) for command in self.bindings)
            return result
        else:
            command = lookup_command(self.bindings, command_name)
            if command:
                return "Usage: {}".format(self.command_usage(command))
            else:
                return f"Unknown command: {command_name}"

    def version(self):
        return LAST_COMMIT


def load_standard_plugins(bot):
    from pladder.snusk import SnuskPlugin
    from pladder.misc import MiscPlugin
    bot.enter_context(SnuskPlugin(bot))
    bot.enter_context(MiscPlugin(bot))


if __name__ == "__main__":
    main()
