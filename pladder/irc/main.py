import argparse
import json
import logging
import os

from pladder.dbus import RetryProxy
from pladder.irc.client import AuthConfig, Config, Hooks, run_client


logger = logging.getLogger("pladder.irc")


def main():
    hooks_class = Hooks
    use_systemd, use_dbus, config_name = parse_arguments()
    config = read_config(config_name)
    if use_systemd:
        hooks_class = set_up_systemd(config, hooks_class)
    else:
        logging.basicConfig(level=logging.DEBUG)
    if use_dbus:
        hooks_class = set_up_dbus(config, hooks_class)
    hooks = hooks_class()
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


def set_up_systemd(config, hooks_base_class):
    from systemd.journal import JournalHandler  # type: ignore
    from systemd.daemon import notify  # type: ignore

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(JournalHandler(SYSLOG_IDENTIFIER="pladder-irc"))

    class SystemdHooks(hooks_base_class):
        def on_ready(self):
            super().on_ready()
            notify("READY=1")

        def on_message_received(self):
            super().on_message_received()
            notify("WATCHDOG=1")

        def on_privmsg(self, timestamp, channel, sender, text):
            super().on_privmsg(timestamp, channel, sender, text)
            notify("WATCHDOG=1")

        def on_status(self, status):
            super().on_status(status)
            notify("STATUS=" + status)

    return SystemdHooks


def set_up_dbus(config, hooks_base_class):
    from pydbus import SessionBus  # type: ignore

    class DbusHooks(hooks_base_class):
        def __init__(self):
            super().__init__()
            bus = SessionBus()
            self._bot = RetryProxy(bus, "se.raek.PladderBot")
            self._log = RetryProxy(bus, "se.raek.PladderLog")

        def on_trigger(self, timestamp, channel, sender, text):
            super().on_trigger(timestamp, channel, sender, text)
            return self._bot.RunCommand(timestamp, config.network, channel, sender.nick, text,
                                        on_error=self._handle_bot_error)

        def on_privmsg(self, timestamp, channel, sender, text):
            super().on_privmsg(timestamp, channel, sender, text)
            self._log.AddLine(timestamp, config.network, channel, sender.nick, text,
                              on_error=self._handle_log_error)

        def on_send_privmsg(self, timestamp, channel, nick, text):
            super().on_send_privmsg(timestamp, channel, nick, text)
            self._log.AddLine(timestamp, config.network, channel, nick, text,
                              on_error=self._handle_log_error)

        def _handle_bot_error(self, e):
            if "org.freedesktop.DBus.Error.ServiceUnknown" in str(e):
                return {
                    "text": "Internal error: could not reach pladder-bot. " +
                            "Please check the log: \"journalctl --user-unit pladder-bot.service -e\"",
                    "command": "error",
                }
            else:
                logger.error(str(e))
                return {
                    "text": "Internal error: " + str(e),
                    "command": "error",
                }

        def _handle_log_error(self, e):
            return None

    return DbusHooks
