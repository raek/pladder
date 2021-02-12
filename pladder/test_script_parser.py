import pytest

from pladder.script import ParseError, Call, Word, Literal, parse


def call(*words):
    return Call(list(words))


def word(*fragments):
    return Word(list(fragments))


def literal(string):
    return Literal(string)


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
        invocation = parse(text)


def test_excessive_closing_bracket():
    text = "cmd1]"
    with pytest.raises(ParseError, match="Excessive closing bracket"):
        invocation = parse(text)


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
        invocation = parse(text)


def test_excessive_closing_brace():
    text = "cmd1}"
    with pytest.raises(ParseError, match="Excessive closing brace"):
        invocation = parse(text)
