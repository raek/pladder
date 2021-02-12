from datetime import datetime, timezone
import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dbus", action="store_true",
                        help="Connect to existing pladder-bot service instead of running command directly.")
    parser.add_argument("--state-dir",
                        help="Directory where bot keeps its state")
    parser.add_argument("-c", "--command",
                        help="Run this command instead of reading commands from stdin.")
    args = parser.parse_args()
    if args.dbus:
        from pydbus import SessionBus
        bus = SessionBus()
        bot = bus.get("se.raek.PladderBot")
        run_commands(bot, args.command)
    else:
        from pladder.bot import PladderBot, load_standard_plugins
        state_dir = args.state_dir or default_state_dir()
        with PladderBot(state_dir, None) as bot:
            load_standard_plugins(bot)
            run_commands(bot, args.command)


def run_commands(bot, command):
    if command is not None:
        print(run_command(bot, command))
    else:
        for line in sys.stdin:
            print(run_command(bot, line.strip()))


def run_command(bot, command):
    network = 'cli'
    reply_to = 'cli'
    sender = 'user'
    timestamp = datetime.now(timezone.utc).timestamp()
    reply = bot.RunCommand(timestamp, network, reply_to, sender, command)
    if reply:
        reply = reply['text']
    return reply


def default_state_dir():
    state_home = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.environ["HOME"], ".config"))
    state_dir = os.path.join(state_home, "pladder-bot")
    return state_dir


if __name__ == "__main__":
    main()
