import argparse
import json
import logging
import os

from pladder.irc.client import AuthConfig, Config, Hooks, run_client
from pladder.log import PladderLogProxy


logger = logging.getLogger("pladder.irc")


def main():
    hooks_class = Hooks
    use_systemd, use_dbus, config_name = parse_arguments()
    if use_systemd:
        hooks_class = set_up_systemd(hooks_class)
    else:
        logging.basicConfig(level=logging.DEBUG)
    if use_dbus:
        hooks_class = set_up_dbus(hooks_class)
    hooks = hooks_class()
    config = read_config(config_name)
    run_client(config, hooks)


def read_config(config_name):
    config_home = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.environ["HOME"], ".config"))
    config_path = os.path.join(config_home, "pladder-irc", config_name + ".json")
    with open(config_path, "rt") as f:
        config_data = json.load(f)
        config = Config(**{**CONFIG_DEFAULTS, **config_data})
        if config.auth:
            config = config._replace(auth=AuthConfig(**config.auth))
        return config


CONFIG_DEFAULTS = {
    "port": 6667,
    "channels": [],
    "auth": None,
    "user_mode": None,
    "trigger_prefix": "~",
    "reply_prefix": "> ",
}


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--systemd", action="store_true")
    parser.add_argument("--dbus", action="store_true")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    return args.systemd, args.dbus, args.config


def set_up_systemd(hooks_base_class):
    from systemd.journal import JournalHandler
    from systemd.daemon import notify

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(JournalHandler(SYSLOG_IDENTIFIER="pladder-irc"))

    class SystemdHooks(hooks_base_class):
        def on_ready(self):
            notify("READY=1")

        def on_ping(self):
            notify("WATCHDOG=1")

        def on_status(self, status):
            notify("STATUS=" + status)

    return SystemdHooks


def set_up_dbus(hooks_base_class):
    from gi.repository import GLib
    from pydbus import SessionBus

    class DbusHooks(hooks_base_class):
        def __init__(self):
            super().__init__()
            self._bus = SessionBus()
            self._bot = None
            self._log = PladderLogProxy(self._bus)

        def on_trigger(self, timestamp, network, channel, sender, text):
            retry = True
            while True:
                try:
                    if self._bot is None:
                        self._bot = self._bus.get("se.raek.PladderBot")
                    return self._bot.RunCommand(timestamp, network, channel, sender.nick, text)
                except GLib.Error as e:
                    if "org.freedesktop.DBus.Error.ServiceUnknown" in str(e):
                        if retry:
                            retry = False
                            self._bot = None
                            continue
                        else:
                            self._bot = None
                            return "Internal error: could not reach pladder-bot. Please check the log: \"journalctl --user-unit pladder-bot -e\""
                    else:
                        logger.error(str(e))
                        return "Internal error: " + str(e)

        def on_privmsg(self, timestamp, network, channel, sender, text):
            self._log.AddLine(timestamp, network, channel, sender.nick, text)

        def on_send_privmsg(self, timestamp, network, channel, nick, text):
            self._log.AddLine(timestamp, network, channel, nick, text)

    return DbusHooks
