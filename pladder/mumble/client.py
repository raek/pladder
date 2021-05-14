from contextlib import AbstractContextManager, ExitStack
from collections import namedtuple
import logging
from threading import Event


logger = logging.getLogger("pladder.mumble")


Config = namedtuple("Config", [
    "network",
])


class Hook(AbstractContextManager):
    def on_ready(self):
        pass

    def on_status(self, s):
        pass


class Client(ExitStack):
    def __init__(self, config):
        super().__init__()
        self._config = config
        self._hooks = []

    # Public API

    def install_hook(self, hook_ctor):
        hook = self.enter_context(hook_ctor(self._config, self))
        self._hooks.append(hook)

    def run(self):
        for hook in self._hooks:
            hook.on_ready()
        self._update_status("Running...")
        forever = Event()
        forever.wait()

    # Internal helper methods

    def _update_status(self, s):
        logger.info(s)
        for hook in self._hooks:
            hook.on_status(s)
