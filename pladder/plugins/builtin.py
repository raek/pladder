from contextlib import contextmanager
from inspect import Parameter, signature
import os
import random

import pladder.irc.color as color
from pladder.script.parser import escape
from pladder.script.interpreter import apply_call, interpret
from pladder.script.types import ScriptError, new_context


def _pairs(iterable):
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


@contextmanager
def pladder_plugin(bot):
    last_contexts = bot.last_contexts
    try:
        with open(os.path.join(bot.state_dir, "version.txt"), encoding="utf-8") as f:
            version = f.read().strip()
    except Exception:
        version = "(unknown)"

    cmds = bot.new_command_group("builtin")
    # Strings
    cmds.register_command("echo", lambda text="": text, varargs=True)
    cmds.register_command("concat", lambda *args: " ".join(arg.strip() for arg in args))
    cmds.register_command("escape", lambda text="": escape(text), varargs=True)
    # Booleans
    cmds.register_command("=", eq)
    cmds.register_command("/=", ne)
    cmds.register_command("bool", bool_command)
    cmds.register_command("if", if_command)
    # Integers
    cmds.register_command("format-int", format_int)
    cmds.register_command("random-range", random_range)
    # Arguments
    cmds.register_command("first", first)
    cmds.register_command("last", last)
    cmds.register_command("nth", nth)
    cmds.register_command("pick", lambda *args: random.choice(args) if args else "")
    cmds.register_command("wpick", wpick)
    # Intertwined with interpreter
    cmds.register_command("eval", eval_command, contextual=True)
    cmds.register_command("eval-pick", eval_pick, contextual=True)
    cmds.register_command("comp", comp, contextual=True)
    cmds.register_command("repeat", repeat, contextual=True)
    cmds.register_command("let", let, contextual=True)
    # Documentation
    cmds.register_command("version", lambda: version)
    cmds.register_command("help", help, contextual=True)
    cmds.register_command("source", source, contextual=True)
    # Debuggning
    cmds.register_command("show-args", lambda *args: repr(args))
    cmds.register_command("show-context", show_context, contextual=True)
    cmds.register_command("trace", trace, contextual=True)
    cmds.register_command("trace-last", lambda context, mode: trace_last(context, mode, last_contexts), contextual=True)
    yield


def eq(value1, value2):
    return _bool_py_to_pladder(value1 == value2)


def ne(value1, value2):
    return _bool_py_to_pladder(value2 == value1)


def bool_command(value):
    return _bool_py_to_pladder(_bool_pladder_to_py(value))


def if_command(condition, then_value, else_value):
    if _bool_pladder_to_py(condition):
        return then_value
    else:
        return else_value


def _bool_py_to_pladder(b):
    return "true" if b else "false"


def _bool_pladder_to_py(string):
    if string == "true":
        return True
    elif string == "false":
        return False
    else:
        raise ScriptError(f'Expected "true" or "false", got "{string}"')


def format_int(format_string: str, value: str) -> str:
    return format(int(value), format_string)


def random_range(start: str, exl_end: str, step: str = "1") -> str:
    return str(random.randrange(int(start), int(exl_end), int(step)))


def first(*args):
    if not args:
        raise ScriptError("first: no arguments given")
    return args[0]


def last(*args):
    if not args:
        raise ScriptError("last: no arguments given")
    return args[-1]


def nth(index, *args):
    index = int(index)
    if index < 0 or index >= len(args):
        raise ScriptError("nth: index out of range")
    return args[index]


def wpick(*args):
    weights = []
    values = []
    for weight, value in _pairs(args):
        weights.append(int(weight))
        values.append(value)
    return random.choices(values, weights, k=1)[0]


def eval_command(context, script):
    text, _display_name = interpret(context, script)
    return text


def eval_pick(context, *args):
    script = random.choice(args) if args else ""
    text, _display_name = interpret(context, script)
    return text


def comp(context, command1, *command2_words):
    command2_result = _apply(context, list(command2_words))
    return _apply(context, [command1, command2_result])


def _apply(context, words):
    if not words:
        return ""
    command_name, arguments = words[0], words[1:]
    command = context.commands.lookup_command(command_name)
    if command is None:
        raise ScriptError(f"Unknown command name: {command_name}")
    command_context = context._replace(command_name=command_name)
    return apply_call(command_context, command, command_name, arguments)


def repeat(context, count, script):
    texts = [interpret(context, script)[0] for _ in range(int(count))]
    return "   ".join(texts)


def let(context, *args):
    if len(args) % 2 != 1:
        raise ScriptError("Let accepts an odd number of arguments (name-value pairs and a body)")
    new_env = dict(context.environment)
    for variable, value in _pairs(args[:-1]):
        new_env[variable] = value
    subcontext = context._replace(environment=new_env)
    result, _display_name = interpret(subcontext, args[-1])
    return result


def help(context, type=None, name=None):
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
            groups = sorted(context.commands.list_groups())
            result = f"Command groups ({len(groups)}): "
            result += ", ".join(groups)
            return result
        else:
            group = context.commands.lookup_group(name)
            if group is None:
                return f"Unknown group: {name}"
            else:
                command_names = sorted(group.list_commands())
                result = f"Commands in {name} group ({len(command_names)}): "
                result += ", ".join(command_names)
                return result
    elif type == "-command":
        if name is None:
            command_names = sorted(context.commands.list_commands())
            result = f"Commands ({len(command_names)}): "
            result += ", ".join(command_names)
            return result
        else:
            command = context.commands.lookup_command(name)
            if command is None:
                return f"Unknown command: {name}"
            else:
                return f"Usage: {command_usage(command)}"
    else:
        raise Exception("Unreachable")


def command_usage(command):
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


def source(context, command_name):
    command = context.commands.lookup_command(command_name)
    if command is None:
        return f"Unknown command name: {command_name}"
    return command.source


def show_context(context):
    return repr({
        "commands": "...",
        "metadata": repr(context.metadata),
        "command_name": context.command_name,
    })


def trace(context, mode, script):
    subcontext = new_context(context.commands, metadata=context.metadata)
    try:
        interpret(subcontext, script)
    except Exception:
        pass
    return render_trace(subcontext.trace, mode)


def trace_last(context, mode, last_contexts):
    last_context = last_contexts.get((context.metadata["network"], context.metadata["channel"]), None)
    if not last_context.trace:
        return "No last trace stored"
    return render_trace(last_context.trace, mode)


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
