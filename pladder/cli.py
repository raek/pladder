import argparse
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dbus", action="store_true",
                        help="Connect to existing pladder-bot service instead of running command directly.")
    parser.add_argument("--command",
                        help="Run this command instead of reading commands from stdin.")
    args = parser.parse_args()
    if args.dbus:
        bot = dbus_bot()
    else:
        bot = direct_bot()
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


def direct_bot():
    from pladder.bot import PladderBot
    return PladderBot()


if __name__ == "__main__":
    main()
