
from pladder.plugin import Plugin
import json
import os
try:
    import pymumble_py3 as mumble
    mumble_available = True
except (ImportError, Exception):
    mumble_available = False

class PladdblePlugin(Plugin):
    ''' Pladdble is class that helps pladder to interface with a mumble server. '''

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        bot.register_command('mömb', self.connected_users)
        bot.register_command('mömb-users', self.list_users)

        if not mumble_available:
            raise ImportError

        try:
            state_home = os.environ.get(
        "XDG_CONFIG_HOME", os.path.join(os.environ["HOME"], ".config"))
            self.config_dir_path = os.path.join(state_home, "pladder-pladdble")
            config_path = os.path.join(self.config_dir_path, 'config.json')

            with open(config_path, 'rt') as f:
                config = json.load(f)
                self.connect(**config)
        except FileNotFoundError:
            print ("Could not open Pladdble config file.")
            raise ImportError
        except json.JSONDecodeError:
            print ('Could not parse Pladdble config file.')
            raise ImportError

    def connect(self, host, user, password, port=64738, certfile=None, reconnect=True):

        certfile = os.path.join(self.config_dir_path, certfile)

        self.user_name = user
        self.mumble = mumble.Mumble(host, self.user_name, password=password, certfile=certfile, reconnect=reconnect)
        
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


if __name__ == "__main__":
    m = PladdblePlugin()