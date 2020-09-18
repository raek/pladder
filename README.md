# Pladder IRC Bot

This is a personal IRC bot project written by Rasmus and other
contributors.


# Installation

Install Python 3 and dependency libaries:

    sudo apt install python3 pytgon3-pip python3-pydbus
    sudo pip3 install ftfy

Then install this package in "development mode":

    pip3 --user --editable .

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


## Testing commands using the command line interface

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
