from concurrent.futures import ThreadPoolExecutor
import logging

from gi.repository import GLib  # type: ignore
from pydbus import SessionBus  # type: ignore

from pladder.dbus import PLADDER_CONNECTOR_XML
from pladder.irc.client import Hook


logger = logging.getLogger("pladder.mumble")


class DbusHook(Hook):
    def __init__(self, config, client):
        super().__init__()
        self.config = config
        bus = SessionBus()
        self.connector = PladderConnector(bus, config, client)
        self.running = False
        self.exe = None
        self.loop = None
        self.loop_future = None

    def __enter__(self):
        assert not self.running
        self.exe = ThreadPoolExecutor(max_workers=1).__enter__()
        self.loop = GLib.MainLoop()
        self.loop_future = self.exe.submit(self.loop.run)
        self.running = True
        logger.info("Dbus thread started")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        assert self.running
        # Signal loop to stop
        self.loop.quit()
        self.loop = None
        # Wait for loop task to finish
        self.loop_future.result()
        self.loop_future = None
        # Wait for executor to shut down
        self.exe.__exit__(None, None, None)
        self.exe = None
        # Everything is torn down
        self.running = False
        logger.info("Dbus thread stopped")
        return None


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
