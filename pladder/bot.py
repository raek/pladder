import os

from pladder.snusk import SnuskDb


def main():
    from gi.repository import GLib
    from pydbus import SessionBus

    pladder_bot = PladderBot()
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

    def __init__(self):
        state_home = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.environ["HOME"], ".config"))
        snusk_db_path = os.path.join(state_home, "pladder-bot", "snusk_db.json")
        prepositions_db_path = os.path.join(state_home, "pladder-bot", "prepositions_db.json")
        self.snusk_db = SnuskDb(snusk_db_path, prepositions_db_path)

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
        elif command == "add-snusk":
            arguments = argument.split()
            if len(arguments) == 2:
                if self.snusk_db.add_snusk(*arguments):
                    return self.snusk_db.example_snusk(*arguments)
                else:
                    return "Hörrudu! Den där finns ju redan!"
        elif command == "add-preposition":
            arguments = argument.split()
            if len(arguments) == 1:
                if self.snusk_db.add_preposition(arguments[0]):
                    return f'Här borde man ha lagt till en exempelutskrift som är fin... men du får nöja dig med att veta att "{arguments[0]}" lades till i databasen.'
            else:
                return "Men ditt inavlade mähä! En preposition, EN!"

        return ""


if __name__ == "__main__":
    main()
