from inspect import getsource
import re
from typing import Any, Callable, Dict, List, Mapping, NamedTuple, Optional, Pattern, Tuple, Union


class ScriptError(Exception):
    pass


class ParseError(ScriptError):
    pass


class EvalError(ScriptError):
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


class CommandGroup:
    def lookup_command(self, command_name: str) -> Optional[CommandBinding]:
        raise NotImplementedError()

    def list_commands(self) -> List[str]:
        raise NotImplementedError()


class PythonCommandGroup(CommandGroup):
    def __init__(self, initial: List[CommandBinding] = []) -> None:
        self._commands: List[CommandBinding] = list(initial)

    def register_command(self, command_name: str, fn: Callable[..., str],
                         varargs: bool = False,
                         contextual: bool = False,
                         source: Optional[str] = None) -> None:
        self._commands.append(command_binding(command_name, fn, varargs, contextual, source))

    def lookup_command(self, command_name: str) -> Optional[CommandBinding]:
        for command in self._commands:
            if command.name_matches(command_name):
                return command
        return None

    def list_commands(self) -> List[str]:
        return [command.display_name for command in self._commands]

    def remove_command(self, command_name: str) -> None:
        binding = self.lookup_command(command_name)
        if binding is None:
            raise ScriptError(f"Unknown command name: {command_name}")
        else:
            self._commands.remove(binding)


class CommandRegistry:
    def __init__(self, initial: Mapping[str, CommandGroup] = {}) -> None:
        self._groups: Dict[str, CommandGroup] = dict(initial)

    def add_command_group(self, group_name: str, group: CommandGroup) -> None:
        if group_name in self._groups:
            raise ScriptError(f"Group {group_name} already registered")
        self._groups[group_name] = group

    def new_command_group(self, group_name: str) -> PythonCommandGroup:
        group = PythonCommandGroup()
        self.add_command_group(group_name, group)
        return group

    def lookup_command(self, command_name: str) -> Optional[CommandBinding]:
        for group in self._groups.values():
            command = group.lookup_command(command_name)
            if command is not None:
                return command
        return None

    def lookup_group(self, group_name: str) -> Optional[CommandGroup]:
        for candidate_group_name, candidate_group in self._groups.items():
            if candidate_group_name == group_name:
                return candidate_group
        return None

    def list_commands(self) -> List[str]:
        return [command_name
                for group in self._groups.values()
                for command_name in group.list_commands()]

    def list_groups(self) -> List[str]:
        return list(self._groups.keys())


Environment = Dict[str, str]
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
    environment: Environment
    metadata: Metadata
    command_name: str
    trace: List[TraceEntry]


def new_context(commands: CommandRegistry, /,
                environment: Environment = {},
                metadata: Metadata = {},
                command_name: str = "<TOP>") -> Context:
    return Context(commands, environment, metadata, command_name, [])


class ApplyError(ScriptError):
    def __init__(self, msg: str, command: CommandBinding, command_name: str, arguments: List[Any]):
        super().__init__(msg)
        self.command = command
        self.command_name = command_name
        self.arguments = arguments
