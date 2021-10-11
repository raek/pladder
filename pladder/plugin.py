from typing import Generator

from pladder.script.types import CommandGroup, CommandRegistry


class BotPluginInterface:
    def __init__(self):
        self.state_dir: str
        self.commands: CommandRegistry

    def new_command_group(self, name: str) -> CommandGroup:
        raise NotImplementedError()


Plugin = Generator[None, None, None]


class PluginError(Exception):
    pass


class PluginLoadError(PluginError):
    """The plugin could not load due to error in environment (missing dependencies, config files, etc)"""
    pass
