import logging

from pydbus import SessionBus  # type: ignore

from pladder.dbus import RetryProxy
from pladder.irc.client import Hook


logger = logging.getLogger("pladder.irc")


class DbusHook(Hook):
    def __init__(self, config):
        self.config = config
        bus = SessionBus()
        self.bot = RetryProxy(bus, "se.raek.PladderBot")
        self.log = RetryProxy(bus, "se.raek.PladderLog")

    def on_trigger(self, timestamp, channel, sender, text):
        return self.bot.RunCommand(timestamp, self.config.network, channel, sender.nick, text,
                                   on_error=self._handle_bot_error)

    def on_privmsg(self, timestamp, channel, sender, text):
        self.log.AddLine(timestamp, self.config.network, channel, sender.nick, text,
                         on_error=self._handle_log_error)

    def on_send_privmsg(self, timestamp, channel, nick, text):
        self.log.AddLine(timestamp, self.config.network, channel, nick, text,
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
