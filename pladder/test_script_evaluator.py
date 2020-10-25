import re

import pytest

from pladder.script import EvalError, ApplyError, command_binding, interpret


EMPTY_CONTEXT = {}


def test_eval_simple():
    script = "upper foo"
    bindings = [command_binding("upper", lambda s: s.upper())]
    result = interpret(bindings, EMPTY_CONTEXT, script)
    assert result == "FOO"


def test_eval_missing_command():
    script = "foo"
    bindings = []
    with pytest.raises(EvalError):
        interpret(bindings, EMPTY_CONTEXT, script)


def test_eval_nested():
    script = "upper [reverse foo]"
    bindings = [
        command_binding("upper", lambda s: s.upper()),
        command_binding("reverse", lambda s: s[::-1]),
    ]
    result = interpret(bindings, EMPTY_CONTEXT, script)
    assert result == "OOF"


def test_eval_multple_args():
    script = "cat3 one two three"
    bindings = [command_binding("cat3", lambda x, y, z: x + y + z)]
    result = interpret(bindings, EMPTY_CONTEXT, script)
    assert result == "onetwothree"


def test_eval_too_few_args():
    script = "cat3 one two"
    bindings = [command_binding("cat3", lambda x, y, z: x + y + z)]
    with pytest.raises(ApplyError):
        interpret(bindings, EMPTY_CONTEXT, script)


def test_eval_too_many_args():
    script = "cat3 one two three four"
    bindings = [command_binding("cat3", lambda x, y, z: x + y + z)]
    with pytest.raises(ApplyError):
        interpret(bindings, EMPTY_CONTEXT, script)


def test_eval_optional_arg_unfilled():
    script = "maybe"
    bindings = [command_binding("maybe", lambda x="bar": x)]
    result = interpret(bindings, EMPTY_CONTEXT, script)
    assert result == "bar"


def test_eval_optional_arg_unfilled():
    script = "maybe foo"
    bindings = [command_binding("maybe", lambda x="bar": x)]
    result = interpret(bindings, EMPTY_CONTEXT, script)
    assert result == "foo"


def test_eval_text_varargs():
    script = "echo one two three"
    bindings = [command_binding("echo", lambda text: text, varargs=True)]
    result = interpret(bindings, EMPTY_CONTEXT, script)
    assert result == "one two three"


def test_eval_text_varargs_with_extra_whitespace():
    script = "echo   one   two   three   "
    bindings = [command_binding("echo", lambda text: text, varargs=True)]
    result = interpret(bindings, EMPTY_CONTEXT, script)
    assert result == "one two three"


def test_eval_text_varargs_with_no_args():
    script = "echo"
    bindings = [command_binding("echo", lambda text: text, varargs=True)]
    with pytest.raises(ApplyError):
        interpret(bindings, EMPTY_CONTEXT, script)


def test_eval_text_varargs_with_no_args_and_default():
    script = "echo"
    bindings = [command_binding("echo", lambda text="": text, varargs=True)]
    result = interpret(bindings, EMPTY_CONTEXT, script)
    assert result == ""


def test_eval_python_varargs():
    script = "list one two three"
    bindings = [command_binding("list", lambda *words: ",".join(words))]
    result = interpret(bindings, EMPTY_CONTEXT, script)
    assert result == "one,two,three"


def test_eval_python_varargs_with_no_args():
    script = "list"
    bindings = [command_binding("list", lambda *words: ",".join(words))]
    result = interpret(bindings, EMPTY_CONTEXT, script)
    assert result == ""


def test_eval_contextual_means_extra_arg():
    script = "ctxaware foo"
    bindings = [command_binding("ctxaware", lambda _context, arg: arg, contextual=True)]
    result = interpret(bindings, EMPTY_CONTEXT, script)
    assert result == "foo"


def test_eval_contextual_propagates_context():
    script = "ctxaware"
    context = {"a": "foo"}
    bindings = [command_binding("ctxaware", lambda context: context["a"], contextual=True)]
    result = interpret(bindings, context, script)
    assert result == "foo"


def test_eval_contextual_adds_command_name():
    script = "ctxaware"
    bindings = [command_binding("ctxaware", lambda context: context["command"], contextual=True)]
    result = interpret(bindings, EMPTY_CONTEXT, script)
    assert result == "ctxaware"


def test_eval_regex_command():
    script = "grooooovy"
    bindings = [command_binding(re.compile("^groo+vy$"), lambda: "foo", regex=True)]
    result = interpret(bindings, EMPTY_CONTEXT, script)
    assert result == "foo"


def test_eval_contextual_regex_command():
    script = "grooooovy"
    bindings = [command_binding(re.compile("^groo+vy$"), lambda context: context["command"], regex=True, contextual=True)]
    result = interpret(bindings, EMPTY_CONTEXT, script)
    assert result == "grooooovy"
