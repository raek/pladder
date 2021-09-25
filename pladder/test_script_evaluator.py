import re

import pytest

from pladder.script import EvalError, ApplyError, CommandRegistry, command_binding, new_context, interpret


def test_eval_simple():
    script = "upper foo"
    bindings = CommandRegistry([command_binding("upper", lambda s: s.upper())])
    result, command = interpret(new_context(bindings), script)
    assert result == "FOO"
    assert command == "upper"


def test_eval_missing_command():
    script = "foo"
    bindings = CommandRegistry([])
    with pytest.raises(EvalError):
        interpret(new_context(bindings), script)


def test_eval_nested():
    script = "upper [reverse foo]"
    bindings = CommandRegistry([
        command_binding("upper", lambda s: s.upper()),
        command_binding("reverse", lambda s: s[::-1]),
    ])
    result, command = interpret(new_context(bindings), script)
    assert result == "OOF"
    assert command == "upper"


def test_eval_multple_args():
    script = "cat3 one two three"
    bindings = CommandRegistry([command_binding("cat3", lambda x, y, z: x + y + z)])
    result, command = interpret(new_context(bindings), script)
    assert result == "onetwothree"
    assert command == "cat3"


def test_eval_too_few_args():
    script = "cat3 one two"
    bindings = CommandRegistry([command_binding("cat3", lambda x, y, z: x + y + z)])
    with pytest.raises(ApplyError):
        interpret(new_context(bindings), script)


def test_eval_too_many_args():
    script = "cat3 one two three four"
    bindings = CommandRegistry([command_binding("cat3", lambda x, y, z: x + y + z)])
    with pytest.raises(ApplyError):
        interpret(new_context(bindings), script)


def test_eval_optional_arg_unfilled():
    script = "maybe"
    bindings = CommandRegistry([command_binding("maybe", lambda x="bar": x)])
    result, command = interpret(new_context(bindings), script)
    assert result == "bar"
    assert command == "maybe"


def test_eval_optional_arg_filled():
    script = "maybe foo"
    bindings = CommandRegistry([command_binding("maybe", lambda x="bar": x)])
    result, command = interpret(new_context(bindings), script)
    assert result == "foo"
    assert command == "maybe"


def test_eval_text_varargs():
    script = "echo one two three"
    bindings = CommandRegistry([command_binding("echo", lambda text: text, varargs=True)])
    result, command = interpret(new_context(bindings), script)
    assert result == "one two three"
    assert command == "echo"


def test_eval_text_varargs_with_extra_whitespace():
    script = "echo   one   two   three   "
    bindings = CommandRegistry([command_binding("echo", lambda text: text, varargs=True)])
    result, command = interpret(new_context(bindings), script)
    assert result == "one two three"
    assert command == "echo"


def test_eval_text_varargs_with_no_args():
    script = "echo"
    bindings = CommandRegistry([command_binding("echo", lambda text: text, varargs=True)])
    with pytest.raises(ApplyError):
        interpret(new_context(bindings), script)


def test_eval_text_varargs_with_no_args_and_default():
    script = "echo"
    bindings = CommandRegistry([command_binding("echo", lambda text="": text, varargs=True)])
    result, command = interpret(new_context(bindings), script)
    assert result == ""
    assert command == "echo"


def test_eval_python_varargs():
    script = "list one two three"
    bindings = CommandRegistry([command_binding("list", lambda *words: ",".join(words))])
    result, command = interpret(new_context(bindings), script)
    assert result == "one,two,three"
    assert command == "list"


def test_eval_python_varargs_with_no_args():
    script = "list"
    bindings = CommandRegistry([command_binding("list", lambda *words: ",".join(words))])
    result, command = interpret(new_context(bindings), script)
    assert result == ""
    assert command == "list"


def test_eval_contextual_means_extra_arg():
    script = "ctxaware foo"
    bindings = CommandRegistry([command_binding("ctxaware", lambda _context, arg: arg, contextual=True)])
    result, command = interpret(new_context(bindings), script)
    assert result == "foo"
    assert command == "ctxaware"


def test_eval_contextual_propagates_metadata():
    script = "ctxaware"
    metadata = {"a": "foo"}
    bindings = CommandRegistry([command_binding("ctxaware", lambda context: context.metadata["a"], contextual=True)])
    result, command = interpret(new_context(bindings, metadata), script)
    assert result == "foo"
    assert command == "ctxaware"


def test_eval_contextual_adds_command_name():
    script = "ctxaware"
    bindings = CommandRegistry([command_binding("ctxaware", lambda context: context.command_name, contextual=True)])
    result, command = interpret(new_context(bindings), script)
    assert result == "ctxaware"
    assert command == "ctxaware"


def test_eval_regex_command():
    script = "grooooovy"
    bindings = CommandRegistry([command_binding(re.compile("^groo+vy$"), lambda: "foo")])
    result, command = interpret(new_context(bindings), script)
    assert result == "foo"
    assert command == "/groo+vy/"


def test_eval_contextual_regex_command():
    script = "grooooovy"
    bindings = CommandRegistry([
        command_binding(re.compile("^groo+vy$"), lambda context: context.command_name, contextual=True)
    ])
    result, command = interpret(new_context(bindings), script)
    assert result == "grooooovy"
    assert command == "/groo+vy/"
