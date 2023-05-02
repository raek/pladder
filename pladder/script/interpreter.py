from inspect import signature, Parameter
from typing import Any, Callable, List

from .parser import parse
from .types import ApplyError, Call, CommandBinding, Context, EvalError, Literal, Result, TraceEntry


def interpret(context: Context, script: str) -> Result:
    call = parse(script)
    return eval_call(context, call)


def eval_call(context: Context, call: Call) -> Result:
    evaled_words = []
    for word in call.words:
        evaled_fragments = []
        for fragment in word.fragments:
            if isinstance(fragment, Literal):
                evaled_fragment = fragment.string
            elif isinstance(fragment, Call):
                evaled_fragment = eval_call(context, fragment)
            else:
                try:
                    evaled_fragment = context.environment[fragment.name]
                except KeyError:
                    raise EvalError(f"Unbound variable: {fragment.name}")
            evaled_fragments.append(evaled_fragment)
        evaled_word = "".join(evaled_fragments)
        evaled_words.append(evaled_word)
    if not evaled_words:
        return ""
    command_name, arguments = evaled_words[0], evaled_words[1:]
    command = context.commands.lookup_command(command_name)
    if command is None:
        raise EvalError(f"Unknown command name: {command_name}")
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
    return result


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
