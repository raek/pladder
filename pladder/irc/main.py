import argparse
import json
import logging
import os

from pladder.irc.client import AuthConfig, Config, Hooks, run_client


logger = logging.getLogger("pladder.irc")


def main():
    hooks_class = Hooks
    use_systemd, use_dbus, config_name = parse_arguments()
    config = read_config(config_name)
    if use_systemd:
        from pladder.irc.systemd import set_up_systemd
        hooks_class = set_up_systemd(config, hooks_class)
    else:
        logging.basicConfig(level=logging.DEBUG)
    if use_dbus:
        from pladder.irc.dbus import set_up_dbus
        hooks_class = set_up_dbus(config, hooks_class)
    hooks = hooks_class()
    run_client(config, hooks)


def read_config(config_name):
    config_home = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.environ["HOME"], ".config"))
    config_path = os.path.join(config_home, "pladder-irc", config_name + ".json")
    with open(config_path, "rt") as f:
        config_data = json.load(f)
        config = Config(**{**CONFIG_DEFAULTS, **config_data})
        if config.auth:
            config = config._replace(auth=AuthConfig(**config.auth))
        return config


CONFIG_DEFAULTS = {
    "port": 6667,
    "channels": [],
    "auth": None,
    "user_mode": None,
    "trigger_prefix": "~",
    "reply_prefix": "> ",
}


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--systemd", action="store_true")
    parser.add_argument("--dbus", action="store_true")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    return args.systemd, args.dbus, args.config
