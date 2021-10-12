from contextlib import contextmanager

from pladder.dbus import RetryProxy


@contextmanager
def pladder_plugin(bot):
    connector_cmds = ConnectorCommands(bot.bus)
    cmds = bot.new_command_group("connector")
    cmds.register_command("get-meta", connector_cmds.get_meta, contextual=True)
    cmds.register_command("send", connector_cmds.send, contextual=True, varargs=True)
    cmds.register_command("channels", connector_cmds.channels, contextual=True)
    cmds.register_command("users", connector_cmds.users, contextual=True)
    cmds.register_command("connector-config", connector_cmds.connector_config, contextual=True)
    yield


class ConnectorCommands:
    def __init__(self, bus):
        self.bus = bus

    def get_meta(self, context, key):
        if key in context.metadata:
            return str(context.metadata[key])
        else:
            return f"Error: no such metadata key: {key}"

    def send(self, context, target, user_text):
        if "send_called" in context.metadata:
            return "Only one send per script is allowed."
        context.metadata["send_called"] = True
        target_parts = target.split("/")
        if len(target_parts) != 2:
            return "Invalid target. Syntax: NetworkName/#channel"
        network, channel = target_parts
        if not network:
            network = context.metadata["network"]
        if context.metadata["channel"] == context.metadata["nick"]:
            text = "({network}/{nick}) ".format(**context.metadata)
        else:
            text = "({network}/{channel}/{nick}) ".format(**context.metadata)
        text += user_text
        connector = RetryProxy(self.bus, f"se.raek.PladderConnector.{network}")
        result = connector.SendMessage(channel, text,
                                       on_error=lambda e: e)
        if isinstance(result, Exception):
            return str(result)
        else:
            return f"{result}   {user_text}"

    def channels(self, context, network=None):
        if network is None:
            network = context.metadata["network"]
        connector = RetryProxy(self.bus, f"se.raek.PladderConnector.{network}")
        channels = connector.GetChannels(on_error=lambda e: None)
        if channels is None:
            return f"Not connected to network {network}."
        else:
            if any(map(lambda c: " " in c, channels)):
                channels = ["{" + c + "}" for c in channels]
            return f"{network}: {', '.join(channels)}"

    def users(self, context, network_and_channel=""):
        parts = network_and_channel.split("/")
        if len(parts) != 2:
            return "Invalid argument. Syntax: NetworkName/#channel"
        network, channel = parts
        if not network:
            network = context.metadata["network"]
        connector = RetryProxy(self.bus, f"se.raek.PladderConnector.{network}")
        users = connector.GetChannelUsers(channel, on_error=lambda e: None)
        if users is None:
            return f"Not connected to network {network}."
        else:
            return f"{network}/{channel}: {', '.join(sorted(users))}"

    def connector_config(self, context, network=None):
        if network is None:
            network = context.metadata["network"]
        connector = RetryProxy(self.bus, f"se.raek.PladderConnector.{network}")
        config = connector.GetConfig(on_error=lambda e: None)
        if config is None:
            return f"Not connected to network {network}."
        else:
            parts = []
            for key, value in config.items():
                parts.append(f"{key}={repr(value)}")
            return f"{network}: {', '.join(parts)}"
