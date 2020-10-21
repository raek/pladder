from collections import namedtuple
from contextlib import ExitStack
from datetime import datetime, timezone
from inspect import Parameter, signature
import os
import re

from pladder import LAST_COMMIT


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


class Command(namedtuple("Command", "name, fn, varargs, regex, contextual")):
    @property
    def display_name(self):
        if self.regex:
            return f"/{self.name.pattern[1:-1]}/"
        else:
            return self.name

    @property
    def usage(self):
        result = self.display_name
        parameters = list(signature(self.fn).parameters.values())
        if self.contextual:
            # pop context argument
            parameters.pop(0)
        for i, parameter in enumerate(parameters):
            if i == len(parameters) - 1 and self.varargs:
                result += f" {{{parameter.name}...}}"
            elif parameter.default != Parameter.empty:
                result += f" [{parameter.name}]"
            else:
                result += f" <{parameter.name}>"
        return result


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
        self.commands = []
        self.register_command("help", self.help)
        self.register_command("version", self.version)

    def RunCommand(self, timestamp, network, channel, nick, text):
        context = {'timestamp': datetime.fromtimestamp(timestamp, tz=timezone.utc),
                   'network': network,
                   'channel': channel,
                   'nick': nick,
                   'text': text}
        return self.interpret(context, text)

    def register_command(self, name, fn, varargs=False, regex=False, contextual=False):
        if regex:
            name = re.compile("^" + name + "$")
        self.commands.append(Command(name, fn, varargs, regex, contextual))

    def interpret(self, context, text):
        words = self.eval(text)
        return self.apply(context, words)

    def eval(self, text):
        return text.split()

    def apply(self, context, words):
        if not words:
            return ""
        command_name = words[0]
        arguments = words[1:]
        command = self.find_command(command_name)
        if command is None:
            return f"Unknown command: {command_name}"
        if command.contextual:
            context['command'] = command_name
            arguments.insert(0, context)
        if command.varargs:
            last_arg_index = self.max_args(command.fn) - 1
            first_args = arguments[:last_arg_index]
            last_args = arguments[last_arg_index:]
            if last_args:
                arguments = first_args + [" ".join(last_args)]
            else:
                arguments = first_args
        if not self.signature_accepts_arguments(command.fn, arguments):
            return f"Usage: {command.usage}"
        return command.fn(*arguments)

    def find_command(self, command_name):
        for command in self.commands:
            if command.regex:
                if command.name.match(command_name):
                    return command
            else:
                if command.name == command_name:
                    return command
        return None

    def max_args(self, fn):
        sig = signature(fn)
        max_args = 0
        for parameter in sig.parameters.values():
            if parameter.kind in [Parameter.POSITIONAL_ONLY,
                                  Parameter.POSITIONAL_OR_KEYWORD]:
                max_args += 1
        return max_args

    def signature_accepts_arguments(self, fn, arguments):
        try:
            sig = signature(fn)
            sig.bind(*arguments)
            return True
        except TypeError:
            return False

    def help(self, command_name=None):
        if not command_name:
            result = "Available commands: "
            result += ", ".join(command.display_name for command in self.commands)
            return result
        else:
            command = self.find_command(command_name)
            if command:
                return f"Usage: {command.usage}"
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
