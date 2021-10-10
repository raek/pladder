from collections import namedtuple
from contextlib import ExitStack
import logging
import os

from pydbus import SessionBus  # type: ignore

from pladder.dbus import RetryProxy, dbus_loop
from .dbus import PladderConnector, PladderWebApi
from .tokens import TokenDb
from .types import Token


class Hub(ExitStack):
    def __init__(self):
        super().__init__()
        state_home = os.environ.get(
            "XDG_CONFIG_HOME", os.path.join(os.environ["HOME"], ".config"))
        state_dir = os.path.join(state_home, "pladder-web")
        os.makedirs(state_dir, exist_ok=True)
        db_file_path = os.path.join(state_dir, "tokens.db")
        self.db = self.enter_context(TokenDb(db_file_path))
        bus = SessionBus()
        self.dbus_connector = PladderConnector(self.db, bus)
        self.dbus_web_api = PladderWebApi(self.db, bus)
        self.bot = RetryProxy(bus, "se.raek.PladderBot")
        self.enter_context(dbus_loop())
