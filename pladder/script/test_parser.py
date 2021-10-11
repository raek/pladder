import pytest

from .parser import parse
from .types import ParseError, Call, Word, Literal, Variable


def call(*words):
    return Call(list(words))


def word(*fragments):
    return Word(list(fragments))


def literal(string):
    return Literal(string)


def variable(name):
    return Variable(name)


def test_parse_no_args():
    text = "cmd"
    invocation = parse(text)
    assert invocation == call(word(literal("cmd")))


def test_parse_args():
    text = "cmd arg1 arg2 arg3"
    invocation = parse(text)
    assert invocation == call(word(literal("cmd")),
                              word(literal("arg1")),
                              word(literal("arg2")),
                              word(literal("arg3")))


def test_leading_whitespace():
    text = "   cmd"
    invocation = parse(text)
    assert invocation == call(word(literal("cmd")))


def test_trailing_whitespace():
    text = "cmd   "
    invocation = parse(text)
    assert invocation == call(word(literal("cmd")))


def test_call():
    text = "cmd1 [cmd2 a] b"
    invocation = parse(text)
    assert invocation == call(word(literal("cmd1")),
                              word(call(word(literal("cmd2")),
                                        word(literal("a")))),
                              word(literal("b")))


def test_call_in_word():
    text = "cmd1 aa[cmd2]bb cc"
    invocation = parse(text)
    assert invocation == call(word(literal("cmd1")),
                              word(literal("aa"),
                                   call(word(literal("cmd2"))),
                                   literal("bb")),
                              word(literal("cc")))


def test_nested_calls():
    text = "cmd1 [cmd2 [cmd3 a] b] c"
    invocation = parse(text)
    assert invocation == call(word(literal("cmd1")),
                              word(call(word(literal("cmd2")),
                                        word(call(word(literal("cmd3")),
                                                  word(literal("a")))),
                                        word(literal("b")))),
                              word(literal("c")))


def test_missing_closing_bracket():
    text = "cmd1 [cmd2"
    with pytest.raises(ParseError, match="Missing closing bracket"):
        parse(text)


def test_excessive_closing_bracket():
    text = "cmd1]"
    with pytest.raises(ParseError, match="Excessive closing bracket"):
        parse(text)


def test_quote():
    text = "cmd1 {cmd2 a} b"
    invocation = parse(text)
    assert invocation == call(word(literal("cmd1")),
                              word(literal("cmd2 a")),
                              word(literal("b")))


def test_quote_in_word():
    text = "cmd1 aa{cmd2}bb cc"
    invocation = parse(text)
    assert invocation == call(word(literal("cmd1")),
                              word(literal("aa"),
                                   literal("cmd2"),
                                   literal("bb")),
                              word(literal("cc")))


def test_nested_quotes():
    text = "cmd1 {cmd2 {cmd3 a} b} c"
    invocation = parse(text)
    assert invocation == call(word(literal("cmd1")),
                              word(literal("cmd2 {cmd3 a} b")),
                              word(literal("c")))


def test_missing_closing_brace():
    text = "cmd1 {cmd2"
    with pytest.raises(ParseError, match="Missing closing brace"):
        parse(text)


def test_excessive_closing_brace():
    text = "cmd1}"
    with pytest.raises(ParseError, match="Excessive closing brace"):
        parse(text)


def test_variable():
    text = "cmd $var"
    invocation = parse(text)
    assert invocation == call(word(literal("cmd")),
                              word(variable("var")))


def test_variable_after_literal():
    text = "cmd aa$var"
    invocation = parse(text)
    assert invocation == call(word(literal("cmd")),
                              word(literal("aa"),
                                   variable("var")))


def test_variable_between_calls():
    text = "cmd [aa]$var[bb]"
    invocation = parse(text)
    assert invocation == call(word(literal("cmd")),
                              word(call(word(literal("aa"))),
                                   variable("var"),
                                   call(word(literal("bb")))))


def test_variable_between_quotes():
    text = "cmd {aa}$var{bb}"
    invocation = parse(text)
    assert invocation == call(word(literal("cmd")),
                              word(literal("aa"),
                                   variable("var"),
                                   literal("bb")))


def test_adjacient_variables():
    text = "cmd $foo$bar"
    invocation = parse(text)
    assert invocation == call(word(literal("cmd")),
                              word(variable("foo"),
                                   variable("bar")))
