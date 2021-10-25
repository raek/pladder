import argparse
import importlib.resources
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="cmd", required=True)
    subparsers.add_parser("update-unit-files")
    subparsers.add_parser("remove-unit-files")
    args = parser.parse_args()
    if args.cmd == "update-unit-files":
        remove_unit_files()
        update_unit_files()
    if args.cmd == "remove-unit-files":
        remove_unit_files()


CURRENT_UNITS = [
    "pladder-bot.service",
    "pladder-irc@.service",
    "pladder-mumble@.service",
    "pladder-upgrade.service",
    "pladder-web.service",
]

OBSOLETE_UNITS = [
    "pladder-log.service",
]


def update_unit_files():
    print("Wrote unit files:")
    print()
    for unit_name in CURRENT_UNITS:
        content = importlib.resources.read_binary("pladder.systemd", unit_name)
        unit_path = Path.home() / ".config" / "systemd" / "user" / unit_name
        unit_path.write_bytes(content)
        print(unit_path)
    print()


def remove_unit_files():
    print("Removed unit files and links:")
    print()
    for unit_name in CURRENT_UNITS + OBSOLETE_UNITS:
        unit_path = Path.home() / ".config" / "systemd" / "user" / unit_name
        try:
            unit_path.unlink()
            print(unit_path)
        except FileNotFoundError:
            pass
        # The unlink above is needed even though the glob below ought to cover that case too.
        # See https://bugs.python.org/issue45606 .
        instances = unit_path.parent.glob(unit_path.name.replace("@", "@*"))
        for instance in instances:
            instance.unlink()
            print(instance)
    print()
