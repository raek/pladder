import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dbus", action="store_true",
                        help="Connect to existing pladder-bot service instead of running command directly.")
    parser.add_argument("--state-dir",
                        help="Directory where bot keeps its state")
    parser.add_argument("--command",
                        help="Run this command instead of reading commands from stdin.")
    args = parser.parse_args()
    if args.dbus:
        bot = dbus_bot()
    else:
        state_dir = args.state_dir or default_state_dir()
        bot = direct_bot(state_dir)
    if args.command:
        print(bot.RunCommand(args.command))
    else:
        for line in sys.stdin:
            print(bot.RunCommand(line.strip()))


def dbus_bot():
    from gi.repository import GLib
    from pydbus import SessionBus
    bus = SessionBus()
    return bus.get("se.raek.PladderBot")


def direct_bot(state_dir):
    from pladder.bot import PladderBot
    return PladderBot(state_dir)


def default_state_dir():
    state_home = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.environ["HOME"], ".config"))
    state_dir = os.path.join(state_home, "pladder-bot")
    return state_dir


if __name__ == "__main__":
    main()
