from contextlib import ExitStack
import logging

from pydbus import SessionBus  # type: ignore

from pladder.dbus import PLADDER_CONNECTOR_XML, RetryProxy, dbus_loop
from pladder.mumble.client import Hook


logger = logging.getLogger("pladder.mumble")


class DbusHook(Hook, ExitStack):
    def __init__(self, config, client):
        super().__init__()
        self.config = config
        bus = SessionBus()
        self.bot = RetryProxy(bus, "se.raek.PladderBot")
        self.connector = PladderConnector(bus, config, client)
        self.enter_context(dbus_loop())

    def on_trigger(self, timestamp, channel, sender, text):
        return self.bot.RunCommand(timestamp, self.config.network, channel, sender, text,
                                   on_error=self._handle_bot_error)

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


class PladderConnector:
    # Note: methods of this class are called in the separate GLib main
    # loop thread.

    dbus = PLADDER_CONNECTOR_XML

    def __init__(self, bus, config, client):
        self.client = client
        self.config = config
        bus.publish(f"se.raek.PladderConnector.{config.network}", self)

    def GetConfig(self):
        return {
            "network": self.config.network,
            "host": self.config.host,
            "port": str(self.config.port),
            "user": str(self.config.user),
            "application": str(self.config.application),
        }

    def SendMessage(self, channel, text):
        if channel not in self.client.get_channels():
            return f"No such channel: {channel}"
        else:
            self.client.send_message(channel, text)
            return "Message sent."

    def GetChannels(self):
        return self.client.get_channels()

    def GetChannelUsers(self, channel):
        return self.client.get_channel_users(channel)
