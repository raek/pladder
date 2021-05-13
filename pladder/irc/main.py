import argparse
import json
import logging
import os

from pladder.irc.client import AuthConfig, Config, Client


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
    use_systemd, use_dbus, config_name = parse_arguments()
    config = read_config(config_name)
    with Client(config) as client:
        if use_systemd:
            from pladder.irc.systemd import SystemdHook
            client.install_hook(SystemdHook)
        else:
            logging.basicConfig(level=logging.DEBUG)
        if use_dbus:
            from pladder.irc.dbus import DbusHook
            client.install_hook(DbusHook)
        client.run()


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--systemd", action="store_true")
    parser.add_argument("--dbus", action="store_true")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    return args.systemd, args.dbus, args.config


def read_config(config_name):
    config_home = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.environ["HOME"], ".config"))
    config_path = os.path.join(config_home, "pladder-irc", config_name + ".json")
    with open(config_path, "rt") as f:
        config_data = json.load(f)
        config = Config(**{**CONFIG_DEFAULTS, **config_data})
        if config.auth:
            config = config._replace(auth=AuthConfig(**config.auth))
        return config
