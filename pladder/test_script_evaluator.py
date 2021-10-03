import re

import pytest

from pladder.script import \
    EvalError, ApplyError, CommandRegistry, PythonCommandGroup, \
    command_binding, new_context, interpret


def make_registry(*bindings):
    return CommandRegistry({"group": PythonCommandGroup(bindings)})


def test_eval_simple():
    script = "upper foo"
    commands = make_registry(command_binding("upper", lambda s: s.upper()))
    result, command = interpret(new_context(commands), script)
    assert result == "FOO"
    assert command == "upper"


def test_eval_missing_command():
    script = "foo"
    commands = CommandRegistry([])
    with pytest.raises(EvalError):
        interpret(new_context(commands), script)


def test_eval_nested():
    script = "upper [reverse foo]"
    commands = make_registry(
        command_binding("upper", lambda s: s.upper()),
        command_binding("reverse", lambda s: s[::-1]),
    )
    result, command = interpret(new_context(commands), script)
    assert result == "OOF"
    assert command == "upper"


def test_eval_multple_args():
    script = "cat3 one two three"
    commands = make_registry(command_binding("cat3", lambda x, y, z: x + y + z))
    result, command = interpret(new_context(commands), script)
    assert result == "onetwothree"
    assert command == "cat3"


def test_eval_too_few_args():
    script = "cat3 one two"
    commands = make_registry(command_binding("cat3", lambda x, y, z: x + y + z))
    with pytest.raises(ApplyError):
        interpret(new_context(commands), script)


def test_eval_too_many_args():
    script = "cat3 one two three four"
    commands = make_registry(command_binding("cat3", lambda x, y, z: x + y + z))
    with pytest.raises(ApplyError):
        interpret(new_context(commands), script)


def test_eval_optional_arg_unfilled():
    script = "maybe"
    commands = make_registry(command_binding("maybe", lambda x="bar": x))
    result, command = interpret(new_context(commands), script)
    assert result == "bar"
    assert command == "maybe"


def test_eval_optional_arg_filled():
    script = "maybe foo"
    commands = make_registry(command_binding("maybe", lambda x="bar": x))
    result, command = interpret(new_context(commands), script)
    assert result == "foo"
    assert command == "maybe"


def test_eval_text_varargs():
    script = "echo one two three"
    commands = make_registry(command_binding("echo", lambda text: text, varargs=True))
    result, command = interpret(new_context(commands), script)
    assert result == "one two three"
    assert command == "echo"


def test_eval_text_varargs_with_extra_whitespace():
    script = "echo   one   two   three   "
    commands = make_registry(command_binding("echo", lambda text: text, varargs=True))
    result, command = interpret(new_context(commands), script)
    assert result == "one two three"
    assert command == "echo"


def test_eval_text_varargs_with_no_args():
    script = "echo"
    commands = make_registry(command_binding("echo", lambda text: text, varargs=True))
    with pytest.raises(ApplyError):
        interpret(new_context(commands), script)


def test_eval_text_varargs_with_no_args_and_default():
    script = "echo"
    commands = make_registry(command_binding("echo", lambda text="": text, varargs=True))
    result, command = interpret(new_context(commands), script)
    assert result == ""
    assert command == "echo"


def test_eval_python_varargs():
    script = "list one two three"
    commands = make_registry(command_binding("list", lambda *words: ",".join(words)))
    result, command = interpret(new_context(commands), script)
    assert result == "one,two,three"
    assert command == "list"


def test_eval_python_varargs_with_no_args():
    script = "list"
    commands = make_registry(command_binding("list", lambda *words: ",".join(words)))
    result, command = interpret(new_context(commands), script)
    assert result == ""
    assert command == "list"


def test_eval_contextual_means_extra_arg():
    script = "ctxaware foo"
    commands = make_registry(command_binding("ctxaware", lambda _context, arg: arg, contextual=True))
    result, command = interpret(new_context(commands), script)
    assert result == "foo"
    assert command == "ctxaware"


def test_eval_contextual_propagates_metadata():
    script = "ctxaware"
    metadata = {"a": "foo"}
    commands = make_registry(command_binding("ctxaware", lambda context: context.metadata["a"], contextual=True))
    result, command = interpret(new_context(commands, metadata), script)
    assert result == "foo"
    assert command == "ctxaware"


def test_eval_contextual_adds_command_name():
    script = "ctxaware"
    commands = make_registry(command_binding("ctxaware", lambda context: context.command_name, contextual=True))
    result, command = interpret(new_context(commands), script)
    assert result == "ctxaware"
    assert command == "ctxaware"


def test_eval_regex_command():
    script = "grooooovy"
    commands = make_registry(command_binding(re.compile("^groo+vy$"), lambda: "foo"))
    result, command = interpret(new_context(commands), script)
    assert result == "foo"
    assert command == "/groo+vy/"


def test_eval_contextual_regex_command():
    script = "grooooovy"
    commands = make_registry(command_binding(re.compile("^groo+vy$"),
                                             lambda context: context.command_name, contextual=True))
    result, command = interpret(new_context(commands), script)
    assert result == "grooooovy"
    assert command == "/groo+vy/"
