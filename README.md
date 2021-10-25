# Pladder IRC Bot

This is a personal IRC bot project written by Rasmus and other
contributors.


# Basic Setup

This is a bare minimum setup for when you only want to develop the bot
logic and don't care about running an actual IRC client.

Make sure you have Python 3 installed:

    $ sudo apt install python3

Pladder has some dependencies. The recommended way to install them is
to use a virtual environment. There is a script that sets up
everything in the `.venv` directory inside the repository. Run it like
this:

    $ source setup_and_activate_venv.sh
    (.venv) $

When the venv is active, you have access to the various bot
applications in the shell. Run `deactivate` to exit the venv. In this
readme `(.venv) $` will be used to signal that the command needs to be
run in the virtual environment.

To run a one-off command in the bot, use `pladder-cli` like this:

    (.venv) $ pladder-cli -c 'echo Hello, world!'

The bot will stores its state in `~/.config/pladder-bot/`. If the
directory does not exist, it will be created and initialized the first
time the bot is run.


## Trying out changes

In the venv, the Pladder package is installed in "editable mode". This
means that changes made to the bot code will be seen immediately by
`pladder-cli` the next time it is run.


## Running the automated tests and checks

Before comitting changes, please run the checked-in test suite:

    (.venv) $ ./check.sh

If you are making changes to the dependencies of Pladder, please run
the cheks in fresh virtual environment like this:

    $ ./full_check.sh


# Design Overview

The pladder package installs four console commands:

* a bot service (`pladder-bot`) that contains the features of the bot
(the "business logic", for some value of "business"),
* an IRC client (`pladder-irc`) that keeps a connection to an IRC
  server and reacts to commands from users,
* a Mubmle client (`pladder-mumble`) that keeps a connection to an IRC
  server and reacts to commands from users,
* a command line tool (`pladder-cli`) that provides a simple way to
  run bot commands during development, and

The bot service can serve multiple IRC and Mumble client. In other
words, the bot can be present on multiple IRC networks and Mumble
servers simultaneously.

The bot parts can be run in two main ways:

* temporarily in the shell during development, and
* automatically in the background, managed by systemd.

I recommend testing both, but starting with the first.


# Running manually from the shell

## Trying out commands using the command line interface

The `pladder-cli` command is a convenience tool to run bot commands
from a normal shell:

    (.venv) $ pladder-cli -command snusk

If run without arguments it will read lines from stdin and run them as
commands.


## Trying out the bot service

The bot service communicates with its clients using DBus. A test
instance of the service can be started like this:

    (.venv) $ pladder-bot

To interact with it, run the CLI from another shell:

    (.venv) $ pladder-cli --dbus --command snusk


## Trying out the IRC client

To connect to an IRC network, first create a configuration file for
that network:

    $ mkdir -p ~/.config/pladder-irc/
    $ editor ~/.config/pladder-irc/raeknet.json

Set up the configuration file like this:

    {
        "network": "RaekNet",
        "host": "irc.raek.se",
        "port": 6667,
        "nick": "pladder123",
        "realname": "Pladder IRC Bot",
        "channels": ["#bot"]
    }

There are some optional configuration options. If they are not
specified, then their default values are used:

        "port": 6667,
        "channels": [],
        "auth": null,
        "user_mode": null,
        "trigger_prefix": "~",
        "reply_prefix": "> ",

Then start a client process:

    (.venv) $ pladder-irc --dbus --config raeknet

A `--config foo` argument results in the file
`/.config/pladder-irc/foo.json` being used. If `--dbus` is given, then
the IRC client runs commands using the bot service (which has to be
started separately). If it is not given, then commands are ignored
(useful for testing the pure IRC parts).


### IRC Authentication

Support for Q authentication on QuakeNet is available. Add an "auth" section like this in the IRC config:

    {
        ...
        "auth": {
            "system": "Q",
            "username": "foo",
            "password": "bar"
        }
    }


## Trying out the Mumble client

The mumble client has an extra dependency that cannot be installed by
pip and must be installed through the system package manager. On
Debian-based systems (like Ubuntu) install it like this:

    $ sudo apt install libopus0

To connect to a mumble server, first create a configuration file for
that server. This example will use `examplenet.json` as the config
file name.

    $ mkdir -p ~/.config/pladder-mumble/
    $ editor ~/.config/pladder-mumble/examplenet.json

Set up the configuration file like this:

    {
        "network": "ExampleNet",
        "host": "mumble.example.se",
        "password": "server_password",
        "user": "NAME_OF_YOUR_BOT"
    }

There are some optional configuration options. If they are not
specified, then their default values are used:

        "port": 64738,
        "application": "Pladder Bot",
        "trigger_prefix": "~",
        "reply_prefix": "> ",
        "certfile": "/path/to/certfile.pem",

The `certfile` option defaults to
`~/.config/pladder-mumble/<config-name>.pem`.

After writing a config file, create a certificate file for the Mumble
client to use. The certificate contains the user name (same as in the
config). Generate a certificate like this:

    cd ~/.config/pladder-mumble/
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 -keyout examplenet.pem -out examplenet.pem -subj "/CN=NAME_OF_YOUR_BOT"

Then start a mumble client process:

    pladder-mumble --dbus --config examplenet

A `--config foo` argument results in the file
`/.config/pladder-mumble/foo.json` being used. If `--dbus` is given,
then the Mumble client runs commands using the bot service (which has
to be started separately). If it is not given, then commands are
ignored (useful for testing the pure Mumble parts).


# Running automatically using systemd

Systemd is used to manage long-running background services. Services
can be run at the system level or on user level. Pladder is designed
to be run as a user service (so root is not required for running).

When run from systemd, a different virtual environment is used than
for the one used in testing. It resides in `~/.cache/pladder-venv`. In
addition, the services need some package than cannot be installed by
pip, and needs to be installed through the system package manager. On
Debian-based systems (such as Ubuntu) they are installed like this:

    $ sudo apt install python3-gi libsystemd-dev

Then create the virtual environment for the services (run the commands
from the repo root):

    $ python3 -m venv --system-site-packages ~/.cache/pladder-venv
    $ source ~/.cache/pladder-venv/bin/activate
    (pladder-venv) $ pip install .[systemd]

Installing the `pladder` package does unfortunately not put the
systemd unit files into `~/.config/systemd/user` where they need to
be. There is a tool that does this. Run it like this:

    (pladder-venv) $ pladder-systemd update-unit-files
    $ systemctl --user daemon-reload

This does not enable the units, but merely makes systemd know about
them. If you change the `.service` files, you need to reinstall the
`pladder` package and rerun the above two commands.


## Installing the bot service

After writing the unit files, it is time to enable the service. This
means that systemd that it will be started automatically by systemd on
boot:

    $ systemctl --user enable pladder-bot.service

Since we just enable the service and have not rebooted yet, we also
need to start it manually this first time:

    $ systemctl --user start pladder-bot.service

The `--dbus` flag can be given to `pladder-cli` to run commands on the
new background service:

    (.venv) $ pladder-cli -c 'echo hello'

To check in on the service you can use this command (which also
displays its most recent log lines):

    $ systemctl --user status pladder-bot.service

You can display the full log like this (useful for errors):

    $ journalctl --user-unit pladder-bot.service -e

If you change the bot code, you can restart the service like this:

    $ systemctl --user restart pladder-bot.service


## Installing the IRC client

The IRC client service is parameterized (a "template unit"). The idea
is that you start one instance for each IRC network. First install the
template:

    $ systemctl --user link ./pladder-irc@.service

Assuming you have a configuration file named `foo.json`, enable and
start a service for it like this (the `--now` argument is like running
`start` immediately afterwards):

    $ systemctl --user enable --now pladder-irc@foo.service

You can watch the log in "follow mode" to see how lines appear:

    $ journalctl --user-unit pladder-irc@foo.service -f

Note that the bot service and the IRC client can be started and
stopped independently of each other. The DBus connection between them
will reconnect automatically.


## Installing the Mumble client

Follow the instructions above for IRC, but replace `pladder-irc` with
`pladder-mumlbe`.


# Uninstalling everything

If you haven't set up any systemd services or used the Mumble client,
then there is nothing to uninstall. You can delete the `.venv`
directory in the repository to free up space if you want.

If you have set up systemd services, then uninstall them like this:

    $ systemctl --user disable --now pladder-bot.service
    $ systemctl --user disable --now pladder-irc@REPLACEME.service
    $ systemctl --user disable --now pladder-mubmle@REPLACEME.service

Use `systemctl --user status` to list all the services if you don't know their names.

Then use the `pladder-systemd` tool to remove the unit files:

    $ source ~/.cache/pladder-venv/bin/activate
    (pladder-venv) $ pladder-systemd remove-unit-files

Then remove the virtual environment used by the services:

    $ rm -rf ~/.cache/pladder-venv

Lastly, you can uninstall the system packages needed by the Mumble
client and the services (but be sure to check that this doesn't
uninstall any packages you need):

    $ sudo apt remove libopus0 python3-gi libsystemd-dev
