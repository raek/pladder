from collections import namedtuple
from contextlib import ExitStack
from inspect import Parameter, signature
import os
import re


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


class Command(namedtuple("Command", "name, fn, raw, regex")):
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
        if self.regex:
            parameters.pop(0)
        for i, parameter in enumerate(parameters):
            if i == len(parameters) - 1 and self.raw:
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
          <arg direction="in" name="text" type="s" />
          <arg direction="out" name="return" type="s" />
        </method>
      </interface>
    </node>
    """

    def __init__(self, state_dir):
        super().__init__()
        self.state_dir = state_dir
        self.commands = []
        self.register_command("help", self.help)

    def register_command(self, name, fn, raw=False, regex=False):
        if regex:
            name = re.compile("^" + name + "$")
        self.commands.append(Command(name, fn, raw, regex))

    def RunCommand(self, text):
        parts = text.strip().split(maxsplit=1)
        if len(parts) == 1:
            command_name, argument_text = text, ""
        else:
            command_name, argument_text = parts
        command = self.find_command(command_name)
        if command is None:
            return f"Unknown command: {command_name}"
        if command.raw:
            max_args = self.max_args(command.fn)
            if command.regex:
                max_args -= 1
            arguments = argument_text.split(maxsplit=(max_args - 1))
        else:
            arguments = argument_text.split()
        if command.regex:
            arguments.insert(0, command_name)
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


def load_standard_plugins(bot):
    from pladder.snusk import SnuskPlugin
    from pladder.misc import MiscPlugin
    bot.enter_context(SnuskPlugin(bot))
    bot.enter_context(MiscPlugin(bot))


if __name__ == "__main__":
    main()
