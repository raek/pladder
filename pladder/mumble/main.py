import argparse
import json
import logging
import os

from pladder.mumble.client import Config, Client


CONFIG_DEFAULTS = {
}


logger = logging.getLogger("pladder.mumble")


def main():
    use_systemd, use_dbus, config_name = parse_arguments()
    config = read_config(config_name)
    with Client(config) as client:
        if use_systemd:
            from pladder.mumble.systemd import SystemdHook
            client.install_hook(SystemdHook)
        else:
            logging.basicConfig(level=logging.DEBUG)
        if use_dbus:
            from pladder.mumble.dbus import DbusHook
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
    config_path = os.path.join(config_home, "pladder-mumble", config_name + ".json")
    with open(config_path, "rt") as f:
        config_data = json.load(f)
        config = Config(**{**CONFIG_DEFAULTS, **config_data})
        return config
