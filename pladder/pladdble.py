from contextlib import contextmanager
import json
import os


try:
    import pymumble_py3 as mumble
except Exception:
    mumble = None


@contextmanager
def pladder_plugin(bot):
    pladdble = Pladdble(bot.state_dir)
    bot.register_command('mömb', pladdble.connected_users)
    bot.register_command('mömb-users', pladdble.list_users)
    bot.register_command('mömb-info', pladdble.get_info)
    yield


class PladdbleError(Exception):
    pass


class Pladdble:
    ''' Pladdble is class that helps pladder to interface with a mumble server. '''

    def __init__(self, config_dir):
        config_defaults = {
            'certfile': os.path.join(config_dir, 'pladdble.pem'),
            'port': 64738,
            'reconnect': True,
        }
        if not mumble:
            raise PladdbleError("'pymumble' or its dependencies are not installed correctly")

        try:
            config_path = os.path.join(config_dir, 'pladdble.json')
            with open(config_path, 'rt') as f:
                config = json.load(f)
                config = {**config_defaults, **config}
                self.connect(**config)
        except FileNotFoundError:
            raise PladdbleError("Could not open Pladdble config file.")
        except json.JSONDecodeError:
            raise PladdbleError('Could not parse Pladdble config file.')

    def connect(self, host, user, password, certfile, port, reconnect):

        self.user_name = user
        self.host = host
        self.port = port

        self.mumble = mumble.Mumble(self.host, self.user_name, port=self.port, password=password, certfile=certfile, reconnect=reconnect)
        
        self.mumble.set_application_string('StrutOS')
        
        # Set callbacks
        self.mumble.callbacks.set_callback(mumble.constants.PYMUMBLE_CLBK_CONNECTED, self.connected)
        self.mumble.callbacks.set_callback(mumble.constants.PYMUMBLE_CLBK_DISCONNECTED, self.disconnected)
        
        self.mumble.start()


    # Callback functions

    def connected(self):
        print ('Pladdble connected sucessfully')

    def disconnected(self):
        print ('Pladdble disconnected from server')

    def connected_users(self) -> str:
        if self.mumble.connected:
            return f'Antalet anslutna nötter är: {self.mumble.users.count() - 1}' #Exclude the bot itself
        else:
            return f'Icke ansluten till servern'

    def list_users(self) -> str:
        users = []
        for id in self.mumble.users:
            users.append(self.mumble.users[id]['name'])
        
        users.remove(self.user_name) # Remove the bot itself from the list
        return ", ".join(users)

    def get_info(self) -> str:
        info_string = [f'Bot name: {self.user_name}', f'Server address: {self.host}', f'Port: {self.port}']
        return '   '.join(info_string)


if __name__ == "__main__":
    m = PladdblePlugin()
