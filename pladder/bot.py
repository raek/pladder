from collections import defaultdict, namedtuple
from contextlib import ExitStack
from datetime import datetime, timezone
from importlib import import_module
from inspect import Parameter, signature
import logging
import os
import random
import re

from pladder import LAST_COMMIT
from pladder.log import PladderLogProxy
from pladder.script import ScriptError, ApplyError, CommandBinding, interpret, lookup_command, apply_call


def main():
    from gi.repository import GLib
    from pydbus import SessionBus

    state_home = os.environ.get(
        "XDG_CONFIG_HOME", os.path.join(os.environ["HOME"], ".config"))
    state_dir = os.path.join(state_home, "pladder-bot")

    bus = SessionBus()
    with PladderBot(state_dir, bus) as bot:
        load_standard_plugins(bot)
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

    def __init__(self, state_dir, bus):
        super().__init__()
        os.makedirs(state_dir, exist_ok=True)
        self.state_dir = state_dir
        self.bus = bus
        self.log = PladderLogProxy(bus)
        self.bindings = []
        self.register_command("help", self.help)
        self.register_command("version", self.version)
        self.register_command("lastlog", self.lastlog, contextual=True)
        self.register_command("comp", self.comp, contextual=True)
        self.register_command("give", self.give, varargs=True)
        self.register_command("echo", lambda text="": text, varargs=True)
        self.register_command("show-args", lambda *args: repr(args))
        self.register_command("show-context", lambda context: repr(context), contextual=True)
        self.register_command("pick", lambda *args: random.choice(args) if args else "")
        self.register_command("concat", lambda *args: " ".join(arg.strip() for arg in args))
        self.register_command("eval", self.eval_command, contextual=True)
        self.register_command("=", self.eq)
        self.register_command("/=", self.ne)
        self.register_command("bool", self.bool_command)
        self.register_command("if", self.if_command, contextual=True)

    def comp(self, context, command1, *command2_words):
        command2_result = self.apply(context, list(command2_words))
        return self.apply(context, [command1, command2_result])

    def give(self, target, text):
        return f"{target}: {text}"

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

    def apply(self, context, words):
        if not words:
            return ""
        command_name, arguments = words[0], words[1:]
        command = lookup_command(self.bindings, command_name)
        return apply_call(context, command, command_name, arguments)

    def register_command(self, name, fn, varargs=False, regex=False, contextual=False, parseoutput=False):
        if regex:
            name = re.compile("^" + name + "$")
        self.bindings.append(CommandBinding(name, fn, varargs, regex, contextual, parseoutput))

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

    def lastlog(self, context, needle, skip=0):
        try:
            skip = int(skip)
            assert(skip >= 0)
        except (ValueError, AssertionError):
            return "'skip' needs to be a non-negative number!"

        def format_log_line(date, nick, text):
            return '[{} {}: {}]'.format(date.strftime('%H:%M'), nick, text)

        # Add one to skip to ignore the line where the command was issued
        lines = self.log.SearchLines(context['network'], context['channel'], needle, 3, skip + 1)
        lines_by_day = defaultdict(list)
        for timestamp, nick, text in lines:
            date = datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(tz=None)
            line = format_log_line(date, nick, text)
            lines_by_day[(date.year, date.month, date.day)].append(line)
        formatted = ['{}-{}-{}: {}'.format(*day, ', '.join(lines))
                     for (day, lines) in lines_by_day.items()]
        result = '; '.join(formatted)
        if result:
            return result
        else:
            return "Found no matches for '{}'".format(needle)

    def eval_command(self, context, *args):
        script = " ".join(arg.strip() for arg in args)
        return interpret(self.bindings, context, script)

    def eq(self, value1, value2):
        return self.bool_py_to_pladder(value1 == value2)

    def ne(self, value1, value2):
        return self.bool_py_to_pladder(value2 == value1)

    def bool_command(self, value):
        return self.bool_py_to_pladder(self.bool_pladder_to_py(value))

    def if_command(self, context, condition, then_script, else_script):
        if self.bool_pladder_to_py(condition):
            return interpret(self.bindings, context, then_script)
        else:
            return interpret(self.bindings, context, else_script)

    def bool_py_to_pladder(self, b):
        return "true" if b else "false"

    def bool_pladder_to_py(self, string):
        if string == "true":
            return True
        elif string == "false":
            return False
        else:
            raise ScriptError(f'Expected "true" or "false", got "{string}"')


def load_standard_plugins(bot):
    plugins = [
        "pladder.snusk",
        "pladder.misc",
        "pladder.bjbot",
        "pladder.ttd",
        "pladder.alias",
        "pladder.bjukkify",
        "pladder.pladdble",
    ]
    for module_name in plugins:
        try:
            plugin_module = import_module(module_name)
            plugin_ctxmgr = getattr(plugin_module, "pladder_plugin")
            bot.enter_context(plugin_ctxmgr(bot))
            print(f"Loaded '{module_name}'.")
        except Exception as e:
            print(f"Could not load '{module_name}'. Skipping. Error: {e}")


if __name__ == "__main__":
    main()
