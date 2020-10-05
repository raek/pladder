import os

from pladder.snusk import SnuskDb


def main():
    from gi.repository import GLib
    from pydbus import SessionBus

    state_home = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.environ["HOME"], ".config"))
    state_dir = os.path.join(state_home, "pladder-bot")

    pladder_bot = PladderBot(state_dir)
    bus = SessionBus()
    bus.publish("se.raek.PladderBot", pladder_bot)
    loop = GLib.MainLoop()
    loop.run()


class PladderBot:
    """
    <node>
      <interface name="se.raek.PladderBot">
        <method name="RunCommand">
          <arg direction="in" name="text" type="s" />
          <arg direction="out" name="return" type="s" />
        </method>
      </interface>
    </node>
    """

    def __init__(self, state_dir):
        snusk_db_path = os.path.join(state_dir, "snusk.db")
        self.snusk_db = SnuskDb(snusk_db_path)

    def RunCommand(self, text):
        parts = text.strip().split(maxsplit=1)
        if len(parts) == 1:
            command, argument = text, ""
        else:
            command, argument = parts
        if command == "snusk" and not argument:
            return self.snusk_db.snusk()
        elif command == "snuska" and argument:
            return self.snusk_db.directed_snusk(argument)
        elif command in ["add-snusk", "add-noun"]:
            arguments = argument.split()
            if len(arguments) == 2:
                if self.snusk_db.add_noun(*arguments):
                    return self.snusk_db.example_snusk(*arguments)
                else:
                    return "Hörrudu! Den där finns ju redan!"
        elif command == "add-preposition":
            arguments = argument.split()
            if len(arguments) == 1:
                if self.snusk_db.add_inbetweeny(arguments[0]):
                    return self.snusk_db.example_snusk_with_prep(arguments[0])
                else:
                    return "Hörrudu! Den där finns ju redan!"
            else:
                return "Men ditt inavlade mähä! En preposition, EN!"
        elif command == "add-inbetweeny":
            if self.snusk_db.add_inbetweeny(argument):
                return self.snusk_db.example_snusk_with_inbetweeny(argument)
            else:
                return "Hörrudu! Den där finns ju redan!"
        return ""


if __name__ == "__main__":
    main()
