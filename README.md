# Pladder IRC Bot

This is a personal IRC bot project written by Rasmus and other
contributors.


# Installation

Install Python 3 and dependency libaries:

    sudo apt install python3 python3-systemd python3-pydbus

Then install this package in "development mode":

    pip3 install --user --editable .

This makes pladder commands available from the PATH. The commands
"point into" this source directory, so source code changes are
effective immediately.


# Overview

The pladder package insatlls three console commands:

* a bot service (`pladder-bot`) that contains the features of the bot
(the "business logic", for some value of "business"),
* an IRC client (`pladder-irc`) that keeps a connection to an IRC
  server and reacts to commands from users, and
* a command line tool (`pladder-cli`) that provides a simple way to
  run bot commands during development.
  
The bot service can serve multiple IRC client. In other words, the bot
can be present on multiple IRC networks simultaneously.

The bot parts can be run in two main ways:

* temporarily in the shell during development, and
* automatically in the background, managed by systemd.

I recommend testing both, but starting with the first.


# Running manually from the shell

## Trying out commands using the command line interface

The `pladder-cli` command is a convenience tool to run bot commands
from a normal shell:

    pladder-cli --command snusk

If run without arguments it will read lines from stdin and run them as
commands.


## Trying out the bot service

The bot service communicates with its clients using DBus. A test
instance of the service can be started like this:

    pladder-bot

To interact with, run the CLI from another shell:

    pladder-cli --dbus --command snusk
    

## Trying out the IRC client

To connect to an IRC network, first create a configuration file for
that network:

    mkdir -p ~/.config/pladder-irc/
    editor ~/.config/pladder-irc/raeknet.json

Set up the configuration file like this:

    {
        "host": "irc.raek.se",
        "port": 6667,
        "nick": "pladder123",
        "realname": "Pladder IRC Bot",
        "channels": ["#bot"]
    }

Then start a client process:

    pladder-irc --dbus --config raeknet

A `--config foo` argument results in the file
`/.config/pladder-irc/foo.json` being used. If `--dbus` is given, then
the IRC client run commands using the bot service (which has to be
started separately). If it is not given, then commands are ignored
(useful for testing the pure IRC parts).


# Running automatically using systemd

Systemd is used to manage long-running background services. Services
can be run at the system level or on user level. Pladder is designed
to be run as a user service (so root is not required for running).

## Installing the bot service

First let systemd know that there is such a thing as pladder-bot:

    systemctl --user link $PWD/pladder-bot.service

This sets up symlinks from the location where user services are
defined (`~/.config/systemd/user/`) to the repo directory. The service
is still not enable nor started. Enable the service to tell systemd
that it should be started automatically on boot:

    systemctl --user enable pladder-bot.service

Since we just added the service after the last boot, we also need to
start it manually the first time:

    systemctl --user start pladder-bot.service

The `--dbus` flag can be given to `pladder-cli` to run commands on the
new background service. To check in on the service you can use this
command (which also display its most recent log lines):

    systemctl --user status pladder-bot.servcie

You can display the full log like this (useful for errors):

    journalctl --user-unit pladder-bot.service -e

If you change the bot code, you can restart the service like this:

    systemctl --user restart pladder-bot.service

When changing settins in the `.service` file themselves, reload them using:

    systemctl --user daemon-reload


## Installing the IRC client

The IRC client service is parameterized (a "template unit"). The idea
is that you start one instance for each IRC network. First install the
template:

    systemctl --user link $PWD/pladder-irc@.service

Assuming you have a configuration file named `foo.json`, enable an
start a service for it like this (the `--now` argument is like running
`start` immediately afterwards):

    systemctl --user enable --now pladder-irc@foo.service

You can watch the log in "follow mode" to see how lines appear:

    journalctl --user-unit pladder-irc@foo.service -f

Note that the bot service and the IRC client can be started and
stopped independently of each other. The DBus connection between them
will reconnect automatically.


# Uninstalling everything

The systemd parts:

    systemctl --user disable --now pladder-bot.service
    systemctl --user disable --now pladder-irc@REPLACEME.service

Use `systemctl --user status` to list all the service if you don't know their names.

The Python parts:

    pip3 uninstall pladder
