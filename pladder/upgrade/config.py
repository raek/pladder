import json
import os
from typing import NamedTuple


class Config(NamedTuple):
    bind_host: str
    bind_port: int
    secret: str
    repo_dir: str


CONFIG_DEFAULTS = {
    "bind_host": "localhost",
}


def read_config():
    config_home = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.environ["HOME"], ".config"))
    config_path = os.path.join(config_home, "pladder-upgrade", "config.json")
    with open(config_path, "rt") as f:
        config_data = json.load(f)
        config = Config(**{**CONFIG_DEFAULTS, **config_data})
        return config
