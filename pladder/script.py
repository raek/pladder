from collections import namedtuple
from inspect import signature, Parameter


class ScriptError(Exception):
    pass


class ParseError(ScriptError):
    pass


Call = namedtuple("Call", "words")
Word = namedtuple("Word", "fragments")
Literal = namedtuple("Literal", "string")


def interpret(bindings, context, text):
    call = parse(text)
    return eval_call(bindings, context, call)


def parse(text):
    return _Parser(text).parse()


class _Parser:
    def __init__(self, text):
        self.text = text
        self.end_pos = len(text)
        self.pos = 0

    def at_end(self):
        return self.pos == self.end_pos

    def del_previous_char(self):
        self.pos -= 1
        self.end_pos -= 1
        self.text = self.text[0:self.pos:] + self.text[self.pos+1::]

    def pop(self):
        c = self.text[self.pos]
        self.pos += 1
        return c

    def try_pop(self, c):
        if self.at_end():
            return False
        else:
            if self.text[self.pos] == c:
                self.pos += 1
                return True
            else:
                return False

    def try_peek(self, c):
        if self.at_end():
            return False
        else:
            return self.text[self.pos] == c

    def parse(self):
        call = self.parse_call()
        if self.at_end():
            return call
        else:
            raise ParseError("Excessive closing bracket")

    def parse_call(self):
        words = []
        while True:
            self.parse_whitespace()
            if self.at_end() or self.try_peek("]"):
                break
            word = self.parse_word()
            words.append(word)
        return Call(words)

    def parse_whitespace(self):
        while True:
            if not self.try_pop(" "):
                break

    def parse_word(self):
        fragments = []
        fragment_start = self.pos
        while True:
            if self.at_end() or self.try_peek("]") or self.try_peek(" "):
                fragment_end = self.pos
                if fragment_start != fragment_end:
                    fragment = Literal(self.text[fragment_start:fragment_end])
                    fragments.append(fragment)
                break
            elif self.try_pop("{"):
                self.del_previous_char()
                while not self.try_pop("}"):
                    if self.at_end():
                        raise ParseError("Missing closing stabby-bracket")
                    self.pop()
                self.del_previous_char()
            elif self.try_pop("["):
                fragment_end = self.pos - 1
                if fragment_start != fragment_end:
                    fragment = Literal(self.text[fragment_start:fragment_end])
                    fragments.append(fragment)
                call = self.parse_call()
                if self.at_end():
                    raise ParseError("Missing closing bracket")
                else:
                    assert self.pop() == "]"  # Should always be true
                fragments.append(call)
                fragment_start = self.pos
            else:
                self.pop()
        return Word(fragments)


class EvalError(ScriptError):
    pass


class ApplyError(ScriptError):
    def __init__(self, msg, command, command_name, arguments):
        super().__init__(msg)
        self.command = command
        self.command_name = command_name
        self.arguments = arguments


CommandBinding = namedtuple("CommandBinding", "command_name, fn, varargs, regex, contextual, parseoutput, display_name")


def command_binding(command_name, fn, varargs=False, regex=False, contextual=False, parseoutput=False, display_name=False):
    if not display_name:
        if regex:
            display_name = f"/{command_name.pattern[1:-1]}/"
        else:
            display_name = command_name
    return CommandBinding(command_name, fn, varargs, regex, contextual, parseoutput, display_name)


def eval_call(bindings, context, call):
    assert isinstance(call, Call)
    evaled_words = []
    for word in call.words:
        evaled_fragments = []
        for fragment in word.fragments:
            if isinstance(fragment, Literal):
                evaled_fragment = fragment.string
            elif isinstance(fragment, Call):
                evaled_fragment, _display_name = eval_call(bindings, context, fragment)
            evaled_fragments.append(evaled_fragment)
        evaled_word = "".join(evaled_fragments)
        evaled_words.append(evaled_word)
    if not evaled_words:
        return ""
    command_name, arguments = evaled_words[0], evaled_words[1:]
    command = lookup_command(bindings, command_name)
    result = apply_call(context, command, command_name, arguments)
    if command.parseoutput and result.find("[")>=0:
        result, _display_name = interpret(bindings, context, "echo " + result)
    print("command: ", command)
    return result, command.display_name


def lookup_command(bindings, command_name):
    for command in bindings:
        if command.regex:
            if command.command_name.match(command_name):
                return command
        else:
            if command.command_name == command_name:
                return command
    raise EvalError(f"Unkown command name: {command_name}")


def apply_call(context, command, command_name, arguments):
    if command.contextual:
        context = dict(context)
        context['command'] = command_name
        arguments = [context] + arguments
    if command.varargs:
        last_arg_index = _max_positional_arguments(command.fn) - 1
        first_args = arguments[:last_arg_index]
        last_args = arguments[last_arg_index:]
        if last_args:
            arguments = first_args + [" ".join(last_args)]
        else:
            arguments = first_args
    if not _signature_accepts_arguments(command.fn, arguments):
        raise ApplyError("Argument count does not match what command accepts",
                         command, command_name, arguments)
    result = command.fn(*arguments)
    assert isinstance(result, str), "Commands must return strings"
    return result


def _max_positional_arguments(fn):
    sig = signature(fn)
    max_args = 0
    for parameter in sig.parameters.values():
        if parameter.kind in [Parameter.POSITIONAL_ONLY,
                              Parameter.POSITIONAL_OR_KEYWORD]:
            max_args += 1
    return max_args


def _signature_accepts_arguments(fn, arguments):
    try:
        sig = signature(fn)
        sig.bind(*arguments)
        return True
    except TypeError:
        return False
