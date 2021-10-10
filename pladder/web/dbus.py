import logging

from pladder.dbus import PLADDER_CONNECTOR_XML, PLADDER_WEB_API_XML


logger = logging.getLogger("pladder.web")


NETWORK = "Web"
DUMMY_CHANNEL = "api"


class PladderConnector:
    # Note: methods of this class are called in the separate GLib main
    # loop thread.

    dbus = PLADDER_CONNECTOR_XML

    def __init__(self, db, bus):
        self.db = db
        bus.publish(f"se.raek.PladderConnector.{NETWORK}", self)

    def GetConfig(self):
        return {
            "network": NETWORK,
            "dummy_channel": DUMMY_CHANNEL,
        }

    def SendMessage(self, channel, text):
        return "Sending is not supported"

    def GetChannels(self):
        return [DUMMY_CHANNEL]

    def GetChannelUsers(self, channel):
        if channel == DUMMY_CHANNEL:
            return self.db.list_tokens()
        else:
            return []


class PladderWebApi:

    dbus = PLADDER_WEB_API_XML

    def __init__(self, db, bus):
        self.db = db
        bus.publish("se.raek.PladderWebApi", self)

    def CreateToken(self, token_name, creator_network, creator_user):
        secret = self.db.create_token(token_name, creator_network, creator_user)
        if secret is not None:
            return True, secret
        else:
            return False, ""

    def GetToken(self, token_name):
        token = self.db.get_token(token_name)
        if token:
            return True, token.used, token.use_count, token.created, token.creator_network, token.creator_user
        else:
            return False, 0, 0, 0, "", ""

    def ListTokens(self):
        return self.db.list_tokens()

    def DeleteToken(self, token_name):
        return self.db.delete_token(token_name)
