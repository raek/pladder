import re
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Pattern, Tuple, Union
from inspect import getsource, signature, Parameter


class ScriptError(Exception):
    pass


class ParseError(ScriptError):
    pass


class Call(NamedTuple):
    # Actually this should be List[Word], but mypy does not support recursive types.
    words: List[Any]


class Literal(NamedTuple):
    string: str


class Variable(NamedTuple):
    name: str


Fragment = Union[Call, Literal, Variable]


class Word(NamedTuple):
    fragments: List[Fragment]


NamePattern = Union[str, Pattern[str]]


class CommandBinding(NamedTuple):
    name_matches: Callable[[str], bool]
    display_name: str
    fn: Callable[..., str]
    varargs: bool
    contextual: bool
    source: str


def command_binding(name_pattern: NamePattern,
                    fn: Callable[..., str],
                    varargs: bool = False,
                    contextual: bool = False,
                    source: Optional[str] = None) -> CommandBinding:
    if isinstance(name_pattern, str):
        name: str = name_pattern
        display_name = name

        def name_matches(name: str) -> bool:
            return name == name_pattern

    elif isinstance(name_pattern, re.Pattern):
        pattern: Pattern[str] = name_pattern
        display_name = "/{}/".format(pattern.pattern[1:-1])

        def name_matches(name: str) -> bool:
            return pattern.match(name) is not None

    else:
        raise TypeError(name_pattern)

    if source is None:
        source_str = "Python: " + getsource(fn).replace("\n", "")
    else:
        source_str = source

    return CommandBinding(name_matches, display_name, fn, varargs, contextual, source_str)


class CommandRegistry:
    def __init__(self, initial: List[CommandBinding] = []) -> None:
        self._commands: List[CommandBinding] = list(initial)

    def register_command(self, name: str, fn: Callable[..., str],
                         varargs: bool = False,
                         contextual: bool = False,
                         source: Optional[str] = None) -> None:
        self._commands.append(command_binding(name, fn, varargs, contextual, source))

    def lookup_command(self, command_name: str) -> CommandBinding:
        for command in self._commands:
            if command.name_matches(command_name):
                return command
        raise EvalError(f"Unknown command name: {command_name}")

    def list_commands(self) -> List[CommandBinding]:
        return list(self._commands)

    def remove_command(self, command_name: str) -> None:
        binding = self.lookup_command(command_name)
        self._commands.remove(binding)


Metadata = Dict[Any, str]
Result = Tuple[str, str]
Char = str


class TraceEntry(NamedTuple):
    command: CommandBinding
    command_name: str
    arguments: List[str]
    # Actually this should be List[TraceEntry], but mypy does not support recursive types.
    subtrace: List[Any]
    result: Union[None, str, Exception]


class Context(NamedTuple):
    commands: CommandRegistry
    metadata: Metadata
    command_name: str
    trace: List[TraceEntry]


def new_context(commands: CommandRegistry, metadata: Metadata = {}, command_name: str = "<TOP>") -> Context:
    return Context(commands, metadata, command_name, [])


def interpret(context: Context, script: str) -> Result:
    call = parse(script)
    return eval_call(context, call)


def parse(text: str) -> Call:
    return _Parser(text).parse()


class _Parser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.end_pos = len(text)
        self.pos = 0

    def at_end(self) -> bool:
        return self.pos == self.end_pos

    def pop(self) -> Char:
        c = self.text[self.pos]
        self.pos += 1
        return c

    def try_pop(self, c: Char) -> bool:
        if self.at_end():
            return False
        else:
            if self.text[self.pos] == c:
                self.pos += 1
                return True
            else:
                return False

    def try_peek(self, c: Char) -> bool:
        if self.at_end():
            return False
        else:
            return self.text[self.pos] == c

    def parse(self) -> Call:
        call = self.parse_call()
        if self.at_end():
            return call
        else:
            raise ParseError("Excessive closing bracket")

    def parse_call(self) -> Call:
        words = []
        while True:
            self.parse_whitespace()
            if self.at_end() or self.try_peek("]"):
                break
            word = self.parse_word()
            words.append(word)
        return Call(words)

    def parse_whitespace(self) -> None:
        while True:
            if not self.try_pop(" "):
                break

    def parse_word(self) -> Word:
        fragments: List[Fragment] = []
        fragment_start = self.pos
        fragment_type: Callable[[str], Fragment] = Literal
        while True:
            if self.at_end() or self.try_peek("]") or self.try_peek(" "):
                fragment_end = self.pos
                if fragment_start != fragment_end:
                    fragment = fragment_type(self.text[fragment_start:fragment_end])
                    fragments.append(fragment)
                break
            elif self.try_pop("["):
                fragment_end = self.pos - 1
                if fragment_start != fragment_end:
                    fragment = fragment_type(self.text[fragment_start:fragment_end])
                    fragments.append(fragment)
                call = self.parse_call()
                if self.at_end():
                    raise ParseError("Missing closing bracket")
                else:
                    assert self.pop() == "]"  # Should always be true
                fragments.append(call)
                fragment_start = self.pos
                fragment_type = Literal
            elif self.try_pop("{"):
                fragment_end = self.pos - 1
                if fragment_start != fragment_end:
                    fragment = Literal(self.text[fragment_start:fragment_end])
                    fragments.append(fragment)
                fragment_start = self.pos
                level = 1
                while not self.at_end():
                    c = self.pop()
                    if c == "{":
                        level += 1
                    elif c == "}":
                        level -= 1
                        if level == 0:
                            break
                if level != 0:
                    raise ParseError("Missing closing brace")
                fragment_end = self.pos - 1
                fragment = Literal(self.text[fragment_start:fragment_end])
                fragments.append(fragment)
                fragment_start = self.pos
                fragment_type = Literal
            elif self.try_pop("}"):
                raise ParseError("Excessive closing brace")
            elif self.try_pop("$"):
                fragment_end = self.pos - 1
                if fragment_start != fragment_end:
                    fragment = fragment_type(self.text[fragment_start:fragment_end])
                    fragments.append(fragment)
                fragment_start = self.pos
                fragment_type = Variable
            else:
                self.pop()
        return Word(fragments)


class EvalError(ScriptError):
    pass


class ApplyError(ScriptError):
    def __init__(self, msg: str, command: CommandBinding, command_name: str, arguments: List[Any]):
        super().__init__(msg)
        self.command = command
        self.command_name = command_name
        self.arguments = arguments


def eval_call(context: Context, call: Call) -> Result:
    evaled_words = []
    for word in call.words:
        evaled_fragments = []
        for fragment in word.fragments:
            if isinstance(fragment, Literal):
                evaled_fragment = fragment.string
            elif isinstance(fragment, Call):
                evaled_fragment, _display_name = eval_call(context, fragment)
            else:
                raise ScriptError(f"Unsupported fragment: {fragment}")
            evaled_fragments.append(evaled_fragment)
        evaled_word = "".join(evaled_fragments)
        evaled_words.append(evaled_word)
    if not evaled_words:
        return "", ""
    command_name, arguments = evaled_words[0], evaled_words[1:]
    command = context.commands.lookup_command(command_name)
    subtrace: List[TraceEntry] = []
    command_context = context._replace(command_name=command_name, trace=subtrace)
    try:
        result = apply_call(command_context, command, command_name, arguments)
        trace_entry = TraceEntry(command, command_name, arguments, subtrace, result)
        context.trace.append(trace_entry)
    except Exception as e:
        trace_entry = TraceEntry(command, command_name, arguments, subtrace, e)
        context.trace.append(trace_entry)
        raise
    return result, command.display_name


def apply_call(context: Context, command: CommandBinding, command_name: str, arguments: List[str]) -> str:
    fn_arguments: List[Any] = list(arguments)
    if command.contextual:
        fn_arguments.insert(0, context)
    if command.varargs:
        last_arg_index = _max_positional_arguments(command.fn) - 1
        first_args = fn_arguments[:last_arg_index]
        last_args = fn_arguments[last_arg_index:]
        if last_args:
            fn_arguments = first_args + [" ".join(last_args)]
        else:
            fn_arguments = first_args
    if not _signature_accepts_arguments(command.fn, fn_arguments):
        raise ApplyError("Argument count does not match what command accepts",
                         command, command_name, fn_arguments)
    result = command.fn(*fn_arguments)
    assert isinstance(result, str), f"Commands must return strings, got {type(result).__name__}"
    return result


def _max_positional_arguments(fn: Callable[..., Any]) -> int:
    sig = signature(fn)
    max_args = 0
    for parameter in sig.parameters.values():
        if parameter.kind in [Parameter.POSITIONAL_ONLY,
                              Parameter.POSITIONAL_OR_KEYWORD]:
            max_args += 1
    return max_args


def _signature_accepts_arguments(fn: Callable[..., Any], arguments: List[Any]) -> bool:
    try:
        sig = signature(fn)
        sig.bind(*arguments)
        return True
    except TypeError:
        return False
