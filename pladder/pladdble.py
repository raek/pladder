from contextlib import contextmanager

from pladder.dbus import RetryProxy


NETWORK = 'VirsuNet'


@contextmanager
def pladder_plugin(bot):
    pladdble = Pladdble(bot, NETWORK)
    cmds = bot.new_command_group("pladdble")
    cmds.register_command('mömb', pladdble.connected_users)
    cmds.register_command('mömb-users', pladdble.list_users)
    cmds.register_command('mömb-info', pladdble.get_info)
    yield


class Pladdble:
    ''' Pladdble is class that helps pladder to interface with a mumble server. '''

    def __init__(self, bot, network):
        self.connector = RetryProxy(bot.bus, f'se.raek.PladderConnector.{network}')

    def connected_users(self) -> str:
        users = self.connector.GetChannelUsers('Root', on_error=lambda e: e)
        if users is None:
            return 'Icke ansluten till servern'
        return f'Antalet anslutna nötter är: {len(users) - 1}'  # Exclude the bot itself

    def list_users(self) -> str:
        config = self.connector.GetConfig(on_error=lambda e: None)
        if self is None:
            return 'Icke ansluten till servern'
        self_nick = config['user']
        users = self.connector.GetChannelUsers('Root', on_error=lambda e: None)
        if users is None:
            return 'Icke ansluten till servern'
        users.remove(self_nick)  # Remove the bot itself from the list
        return ", ".join(users)

    def get_info(self) -> str:
        config = self.connector.GetConfig(on_error=lambda e: None)
        if self is None:
            return 'Icke ansluten till servern'
        info_string = [
            f'Bot name: {config["user"]}',
            f'Server address: {config["host"]}',
            f'Port: {config["port"]}',
            f'Network: {config["network"]}',
        ]
        return '   '.join(info_string)
