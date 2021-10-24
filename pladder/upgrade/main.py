import argparse
import sys

import gunicorn.app.wsgiapp  # type: ignore

from .config import read_config


def main():
    parse_arguments()
    config = read_config()
    run_gunicorn(config)


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.parse_args()


def run_gunicorn(config):
    print(sys.argv)
    sys.argv = [
        sys.argv[0].replace("pladder-upgrade", "gunicorn"),
        "--access-logfile", "-",
        "-b", f"{config.bind_host}:{config.bind_port}",
        "pladder.upgrade.api:app",
    ]
    gunicorn.app.wsgiapp.run()
