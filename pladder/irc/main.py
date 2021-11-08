import argparse
import json
import logging
import os
import sys

from pladder.irc.client import AuthConfig, Config, Client
from pladder.irc.message import FdDetached


CONFIG_DEFAULTS = {
    "port": 6667,
    "channels": [],
    "auth": None,
    "user_mode": None,
    "trigger_prefix": "~",
    "reply_prefix": "> ",
}


logger = logging.getLogger("pladder.irc")


def main():
    args = parse_arguments()
    config = read_config(args.config)
    if args.trigger_reload:
        from pladder.irc.dbus import send_reload_trigger
        logging.basicConfig(level=logging.DEBUG)
        ok = send_reload_trigger(config)
        return 0 if ok else 1
    try:
        with Client(config, inherited_fd=args.fd) as client:
            if args.systemd:
                from pladder.irc.systemd import SystemdHook
                client.install_hook(SystemdHook)
            else:
                logging.basicConfig(level=logging.DEBUG)
            if args.dbus:
                from pladder.irc.dbus import DbusHook
                client.install_hook(DbusHook)
            client.run()
    except FdDetached as e:
        fd = e.args[0]
        restart(args, fd)


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--systemd", action="store_true")
    parser.add_argument("--dbus", action="store_true")
    parser.add_argument("--config", required=True)
    parser.add_argument("--trigger-reload", action="store_true",
                        help="Don't run a client, but signal an existing client to reload its code.")
    parser.add_argument("--fd", type=int)
    args = parser.parse_args()
    return args


def read_config(config_name):
    config_home = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.environ["HOME"], ".config"))
    config_path = os.path.join(config_home, "pladder-irc", config_name + ".json")
    with open(config_path, "rt") as f:
        config_data = json.load(f)
        config = Config(**{**CONFIG_DEFAULTS, **config_data})
        if config.auth:
            config = config._replace(auth=AuthConfig(**config.auth))
        return config


def restart(args, fd):
    os.set_inheritable(fd, True)
    exe = sys.argv[0]
    argv = [exe]
    if args.systemd:
        argv += ["--systemd"]
    if args.dbus:
        argv += ["--dbus"]
    argv += ["--config", args.config]
    argv += ["--fd", str(fd)]
    os.execv(exe, argv)
