import logging

from pydbus import SessionBus  # type: ignore

from pladder.dbus import RetryProxy


logger = logging.getLogger("pladder.irc")


def set_up_dbus(config, hooks_base_class):
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
