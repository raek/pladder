from contextlib import ExitStack
import logging
import threading

from pydbus import SessionBus  # type: ignore
from pydbus.generic import signal  # type: ignore

from pladder.dbus import PLADDER_CONNECTOR_XML, RetryProxy, dbus_loop
from pladder.irc.client import Hook


RELOAD_TIMEOUT_SECONDS = 5*60


logger = logging.getLogger("pladder.irc")


class DbusHook(Hook, ExitStack):
    def __init__(self, config, client):
        super().__init__()
        self.config = config
        bus = SessionBus()
        self.bot = RetryProxy(bus, "se.raek.PladderBot")
        self.connector = PladderConnector(bus, config, client)
        self.enter_context(dbus_loop())
        self.connector.ReloadComplete()

    def on_trigger(self, timestamp, channel, sender, text):
        return self.bot.RunCommand(timestamp, self.config.network, channel, sender.nick, text,
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
            "nick": self.config.nick,
            "realname": self.config.realname,
            "trigger_prefix": self.config.trigger_prefix,
            "reply_prefix": self.config.reply_prefix,
        }

    def SendMessage(self, channel, text):
        if not channel.startswith("#"):
            return f"Invalid channel name: {channel}"
        elif channel not in self.client.get_channels():
            return f"Not joined to channel: {channel}"
        else:
            self.client.send_message(channel, text)
            return "Message sent."

    def GetChannels(self):
        return self.client.get_channels()

    def GetChannelUsers(self, channel):
        return self.client.get_channel_users(channel)

    def TriggerReload(self):
        self.client.trigger_detach()
        return True

    ReloadComplete = signal()


def send_reload_trigger(config):
    logger.info(f"Sending reload trigger to connector for {config.network}...")
    reload_complete = threading.Event()
    bus = SessionBus()
    try:
        client = bus.get(f"se.raek.PladderConnector.{config.network}")
    except Exception:
        logger.error("Coult not reach connector!")
        return False
    with dbus_loop():
        client.ReloadComplete.connect(reload_complete.set)
        if not client.TriggerReload():
            logger.error("Reload not supported!")
            return False
        logger.info("Reload triggered successfully.")
        logger.info("Wating for connector to complete reload...")
        if not reload_complete.wait(timeout=RELOAD_TIMEOUT_SECONDS):
            logger.error("Reload did not complete in {RELOAD_TIMEOUT_SECONDS} seconds!")
            return False
        logger.info("Reload completed.")
        return True
