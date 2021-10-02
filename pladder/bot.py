from contextlib import ExitStack
from datetime import datetime, timezone
from importlib import import_module
from inspect import Parameter, signature
import os
import random

from pladder import LAST_COMMIT
from pladder.dbus import PLADDER_BOT_XML, RetryProxy
from pladder.fuse import Fuse, FuseResult
import pladder.irc.color as color
from pladder.plugin import BotPluginInterface, PluginLoadError
from pladder.script import ScriptError, ApplyError, CommandRegistry, new_context, interpret, apply_call


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
        self.fuse = Fuse(state_dir)
        self.commands = CommandRegistry()
        self.register_builtins()
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
            context = new_context(self.commands, metadata)
            fuse_result = self.fuse.run(metadata['datetime'], network, channel)
            if fuse_result == FuseResult.JUST_BLOWN:
                result = {'text': f'{color.LIGHT_YELLOW}*daily fuse blown*{color.LIGHT_YELLOW}',
                          'command': 'error'}
            elif fuse_result == FuseResult.BLOWN:
                result = {'text': '',
                          'command': 'error'}
            else:
                result_text, display_name = interpret(context, text)
                result_text = result_text[:10000]
                result = {'text': result_text,
                          'command': display_name}
        except ApplyError as e:
            result = {'text': "Usage: {}".format(self.command_usage(e.command)),
                      'command': e.command.display_name}
        except ScriptError as e:
            result = {'text': str(e),
                      'command': 'error'}
        except RecursionError:
            result = {'text': "RecursionError: Maximum recursion depth exceeded",
                      'command': 'error'}
        except Exception as e:
            print(str(e))
            result = {'text': "Internal error: " + str(e),
                      'command': 'error'}
        self.last_contexts[(network, channel)] = context
        return result

    def register_builtins(self):
        cmds = self.new_command_group("builtin")
        cmds.register_command("help", self.help)
        cmds.register_command("version", self.version)
        cmds.register_command("send", self.send, contextual=True, varargs=True)
        cmds.register_command("channels", self.channels, contextual=True)
        cmds.register_command("users", self.users, contextual=True)
        cmds.register_command("connector-config", self.connector_config, contextual=True)
        cmds.register_command("comp", self.comp, contextual=True)
        cmds.register_command("give", self.give, varargs=True)
        cmds.register_command("echo", lambda text="": text, varargs=True)
        cmds.register_command("show-args", lambda *args: repr(args))
        cmds.register_command("show-context", self.show_context, contextual=True)
        cmds.register_command("get-meta", self.get_meta, contextual=True)
        cmds.register_command("pick", lambda *args: random.choice(args) if args else "")
        cmds.register_command("wpick", wpick)
        cmds.register_command("concat", lambda *args: " ".join(arg.strip() for arg in args))
        cmds.register_command("eval", self.eval_command, contextual=True)
        cmds.register_command("eval-pick", self.eval_pick, contextual=True)
        cmds.register_command("=", self.eq)
        cmds.register_command("/=", self.ne)
        cmds.register_command("bool", self.bool_command)
        cmds.register_command("if", self.if_command)
        cmds.register_command("trace", self.trace, contextual=True)
        cmds.register_command("trace-last", self.trace_last, contextual=True)
        cmds.register_command("source", self.source)

    def apply(self, context, words):
        if not words:
            return ""
        command_name, arguments = words[0], words[1:]
        command = context.commands.lookup_command(command_name)
        if command is None:
            raise ScriptError(f"Unknown command name: {command_name}")
        command_context = context._replace(command_name=command_name)
        return apply_call(command_context, command, command_name, arguments)

    def comp(self, context, command1, *command2_words):
        command2_result = self.apply(context, list(command2_words))
        return self.apply(context, [command1, command2_result])

    def give(self, target, text):
        return f"{target}: {text}"

    def command_usage(self, command):
        result = command.display_name
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

    def help(self, type=None, name=None):
        if type and not type.startswith("-"):
            name = type
            type = "-command"
        if (not type and not name) or (type not in ["-group", "-command"]):
            return "   ".join([
                "Usage: help (-group|-command) [name]",
                "List groups: help -group",
                "List commands in group: help -group <name>",
                "Show usage of command: help [-command] <name>",
            ])
        elif type == "-group":
            if not name:
                groups = sorted(self.commands.list_groups())
                result = f"Command groups ({len(groups)}): "
                result += ", ".join(groups)
                return result
            else:
                group = self.commands.lookup_group(name)
                if group is None:
                    return f"Unknown group: {name}"
                else:
                    command_names = sorted(command.display_name for command in group.list_commands())
                    result = f"Commands in {name} group ({len(command_names)}): "
                    result += ", ".join(command_names)
                    return result
        elif type == "-command":
            command = self.commands.lookup_command(name)
            if command is None:
                return f"Unknown command: {name}"
            else:
                return f"Usage: {self.command_usage(command)}"
        else:
            raise Exception("Unreachable")

    def version(self):
        return LAST_COMMIT

    def send(self, context, target, user_text):
        if "send_called" in context.metadata:
            return "Only one send per script is allowed."
        context.metadata["send_called"] = True
        target_parts = target.split("/")
        if len(target_parts) != 2:
            return "Invalid target. Syntax: NetworkName/#channel"
        network, channel = target_parts
        if not network:
            network = context.metadata["network"]
        if context.metadata["channel"] == context.metadata["nick"]:
            text = "({network}/{nick}) ".format(**context.metadata)
        else:
            text = "({network}/{channel}/{nick}) ".format(**context.metadata)
        text += user_text
        connector = RetryProxy(self.bus, f"se.raek.PladderConnector.{network}")
        result = connector.SendMessage(channel, text,
                                       on_error=lambda e: e)
        print(repr(result))
        if isinstance(result, Exception):
            return str(result)
        else:
            return f"{result}   {user_text}"

    def channels(self, context, network=None):
        if network is None:
            network = context.metadata["network"]
        connector = RetryProxy(self.bus, f"se.raek.PladderConnector.{network}")
        channels = connector.GetChannels(on_error=lambda e: None)
        if channels is None:
            return f"Not connected to network {network}."
        else:
            if any(map(lambda c: " " in c, channels)):
                channels = ["{" + c + "}" for c in channels]
            return f"{network}: {', '.join(channels)}"

    def users(self, context, network_and_channel=""):
        parts = network_and_channel.split("/")
        if len(parts) != 2:
            return "Invalid argument. Syntax: NetworkName/#channel"
        network, channel = parts
        if not network:
            network = context.metadata["network"]
        connector = RetryProxy(self.bus, f"se.raek.PladderConnector.{network}")
        users = connector.GetChannelUsers(channel, on_error=lambda e: None)
        if users is None:
            return f"Not connected to network {network}."
        else:
            return f"{network}/{channel}: {', '.join(sorted(users))}"

    def connector_config(self, context, network=None):
        if network is None:
            network = context.metadata["network"]
        connector = RetryProxy(self.bus, f"se.raek.PladderConnector.{network}")
        config = connector.GetConfig(on_error=lambda e: None)
        if config is None:
            return f"Not connected to network {network}."
        else:
            parts = []
            for key, value in config.items():
                parts.append(f"{key}={repr(value)}")
            return f"{network}: {', '.join(parts)}"

    def show_context(self, context):
        return repr({
            "commands": "...",
            "metadata": repr(context.metadata),
            "command_name": context.command_name,
        })

    def get_meta(self, context, key):
        if key in context.metadata:
            return str(context.metadata[key])
        else:
            return f"Error: no such metadata key: {key}"

    def eval_command(self, context, script):
        text, _display_name = interpret(context, script)
        return text

    def eval_pick(self, context, *args):
        script = random.choice(args) if args else ""
        text, _display_name = interpret(context, script)
        return text

    def eq(self, value1, value2):
        return self.bool_py_to_pladder(value1 == value2)

    def ne(self, value1, value2):
        return self.bool_py_to_pladder(value2 == value1)

    def bool_command(self, value):
        return self.bool_py_to_pladder(self.bool_pladder_to_py(value))

    def if_command(self, condition, then_value, else_value):
        if self.bool_pladder_to_py(condition):
            return then_value
        else:
            return else_value

    def bool_py_to_pladder(self, b):
        return "true" if b else "false"

    def bool_pladder_to_py(self, string):
        if string == "true":
            return True
        elif string == "false":
            return False
        else:
            raise ScriptError(f'Expected "true" or "false", got "{string}"')

    def trace(self, context, mode, script):
        subcontext = new_context(context.commands, context.metadata)
        try:
            interpret(subcontext, script)
        except Exception:
            pass
        return render_trace(subcontext.trace, mode)

    def trace_last(self, context, mode):
        last_context = self.last_contexts.get((context.metadata["network"], context.metadata["channel"]), None)
        if not last_context.trace:
            return "No last trace stored"
        return render_trace(last_context.trace, mode)

    def source(self, command_name):
        command = self.commands.lookup_command(command_name)
        if command is None:
            return f"Unknown command name: {command_name}"
        return command.source


def render_trace(trace, mode):
    color_pairs = [
        (color.LIGHT_RED, color.DARK_RED),
        (color.LIGHT_GREEN, color.DARK_GREEN),
        (color.LIGHT_BLUE, color.DARK_BLUE),
        (color.LIGHT_YELLOW, color.DARK_YELLOW),
        (color.LIGHT_MAGENTA, color.DARK_MAGENTA),
        (color.LIGHT_CYAN, color.DARK_CYAN),
    ]
    if mode == "-brief":
        return brief_trace(trace, color_pairs)
    elif mode == "-results":
        return results_trace(trace, color_pairs)
    elif mode == "-full":
        return full_trace(trace, color_pairs)
    else:
        return "Mode must be one of: -brief, -results, -full"


def brief_trace(trace, color_pairs):
    print(color_pairs)
    if color_pairs:
        (light, dark), *color_pairs = color_pairs
    else:
        light = color.RESET
        dark = color.RESET
    parts = []
    for entry in trace:
        if entry.subtrace:
            sub = brief_trace(entry.subtrace, color_pairs)
            part = f"{light}{entry.command_name}{dark}({sub}{dark})"
        else:
            part = f"{light}{entry.command_name}"
        parts.append(part)
    return f"{dark}, ".join(parts) + color.RESET


def results_trace(trace, color_pairs):
    if color_pairs:
        (light, dark), *color_pairs = color_pairs
    else:
        light = color.RESET
        dark = color.RESET
    parts = []
    for entry in trace:
        command = escape(entry.command_name)
        result = escape(entry.result)
        if entry.subtrace:
            sub = results_trace(entry.subtrace, color_pairs)
            part = f"{light}{command} {dark}=> ( {sub} {dark}) => {light}{result}"
        else:
            part = f"{light}{command} {dark}=> {light}{result}"
        parts.append(part)
    return f"{dark}, ".join(parts) + color.RESET


def full_trace(trace, color_pairs):
    if color_pairs:
        (light, dark), *color_pairs = color_pairs
    else:
        light = color.RESET
        dark = color.RESET
    parts = []
    for entry in trace:
        words = [entry.command_name] + entry.arguments
        call = " ".join(map(escape, words))
        result = escape(entry.result)
        if entry.subtrace:
            sub = full_trace(entry.subtrace, color_pairs)
            part = f"{light}[{call}] {dark}=> ( {sub} {dark}) => {light}{result}"
        else:
            part = f"{light}[{call}] {dark}=> {light}{result}"
        parts.append(part)
    return f"{dark}, ".join(parts) + color.RESET


def escape(word):
    if word == "" or " " in word or "{" in word:
        return "{" + word + "}"
    else:
        return word


def wpick(*args):
    weights = []
    values = []
    for weight, value in pairs(args):
        weights.append(int(weight))
        values.append(value)
    return random.choices(values, weights, k=1)[0]


def pairs(iterable):
    it = iter(iterable)
    while True:
        try:
            x = next(it)
        except StopIteration:
            return
        try:
            y = next(it)
        except StopIteration:
            raise ValueError("Got an odd number of elements")
        yield x, y


def load_standard_plugins(bot):
    plugins = [
        "pladder.snusk",
        "pladder.misc",
        "pladder.bjbot",
        "pladder.ttd",
        "pladder.alias",
        "pladder.bjukkify",
        "pladder.pladdble",
        "pladder.name",
        "pladder.bah",
        "pladder.azure",
    ]
    for module_name in plugins:
        try:
            plugin_module = import_module(module_name)
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
