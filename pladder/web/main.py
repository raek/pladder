import argparse
import json
import os
import sys
from typing import NamedTuple

import gunicorn.app.wsgiapp  # type: ignore


class Config(NamedTuple):
    bind_host: str
    bind_port: int


CONFIG_DEFAULTS = {
    "bind_host": "localhost",
}


def main():
    parse_arguments()
    config = read_config()
    run_gunicorn(config)


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.parse_args()


def read_config():
    config_home = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.environ["HOME"], ".config"))
    config_path = os.path.join(config_home, "pladder-web", "config.json")
    with open(config_path, "rt") as f:
        config_data = json.load(f)
        config = Config(**{**CONFIG_DEFAULTS, **config_data})
        return config


def run_gunicorn(config):
    print(sys.argv)
    sys.argv = [
        sys.argv[0].replace("pladder-web", "gunicorn"),
        "--access-logfile", "-",
        "-b", f"{config.bind_host}:{config.bind_port}",
        "pladder.web.api:app",
    ]
    gunicorn.app.wsgiapp.run()
