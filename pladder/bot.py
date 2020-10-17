from collections import namedtuple
import inspect
import os
import re

from pladder.snusk import SnuskDb, SKIP_SCORE
from pladder.misc import MiscCmds


def main():
    from gi.repository import GLib
    from pydbus import SessionBus

    state_home = os.environ.get(
        "XDG_CONFIG_HOME", os.path.join(os.environ["HOME"], ".config"))
    state_dir = os.path.join(state_home, "pladder-bot")

    pladder_bot = PladderBot(state_dir)
    bus = SessionBus()
    bus.publish("se.raek.PladderBot", pladder_bot)
    loop = GLib.MainLoop()
    loop.run()


class Command(namedtuple("Command", "name, fn, raw, regex")):
    @property
    def display_name(self):
        if self.regex:
            return f"/{self.name.pattern[1:-1]}/"
        else:
            return self.name

    @property
    def usage(self):
        result = self.display_name
        parameters = list(inspect.signature(self.fn).parameters.values())
        if self.regex:
            parameters.pop(0)
        for i, parameter in enumerate(parameters):
            if i == len(parameters) - 1 and self.raw:
                result += f" {{{parameter.name}...}}"
            elif parameter.default != inspect.Parameter.empty:
                result += f" [{parameter.name}]"
            else:
                result += f" <{parameter.name}>"
        return result


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
        self.misc_cmds = MiscCmds()
        self.commands = []
        self.register_commands()

    def register_commands(self):
        self.register_command("help", self.help)
        self.register_command("snusk", self.snusk_db.snusk)
        self.register_command("snuska", self.snusk_db.directed_snusk, raw=True)
        self.register_command("smak", self.snusk_db.taste)
        self.register_command("nickförslag", self.snusk_db.nick)
        self.register_command("add-snusk", self.add_noun)
        self.register_command("add-noun", self.add_noun)
        self.register_command("add-preposition", self.add_inbetweeny)
        self.register_command("add-inbetweeny", self.add_inbetweeny, raw=True)
        self.register_command("find-noun", self.find_noun)
        self.register_command("upvote-noun", self.upvote_noun)
        self.register_command("downvote-noun", self.downvote_noun)
        self.register_command("upvote-inbetweeny", self.upvote_inbetweeny, raw=True)
        self.register_command("downvote-inbetweeny", self.downvote_inbetweeny, raw=True)
        self.register_command("kloo+fify", self.kloofify, raw=True, regex=True)
        self.register_command("comp", self.comp, raw=True)

    def register_command(self, name, fn, raw=False, regex=False):
        if regex:
            name = re.compile("^" + name + "$")
        self.commands.append(Command(name, fn, raw, regex))

    def RunCommand(self, text):
        parts = text.strip().split(maxsplit=1)
        if len(parts) == 1:
            command_name, argument_text = text, ""
        else:
            command_name, argument_text = parts
        command = self.find_command(command_name)
        if command is None:
            return f"Unknown command: {command_name}"
        if command.raw:
            arguments = [argument_text]
        else:
            arguments = argument_text.split()
        if command.regex:
            arguments.insert(0, command_name)
        sig = inspect.signature(command.fn)
        try:
            sig.bind(*arguments)
        except TypeError:
            return f"Usage: {command.usage}"
        return command.fn(*arguments)

    def find_command(self, command_name):
        for command in self.commands:
            if command.regex:
                if command.name.match(command_name):
                    return command
            else:
                if command.name == command_name:
                    return command
        return None

    # Bot commands

    def help(self, command_name=None):
        if not command_name:
            result = "Available commands: "
            result += ", ".join(command.display_name for command in self.commands)
            return result
        else:
            command = self.find_command(command_name)
            if command:
                return f"Usage: {command.usage}"
            else:
                return f"Unknown command: {command_name}"

    def add_noun(self, prefix, suffix):
        if self.snusk_db.add_noun(prefix, suffix):
            return self.snusk_db.example_snusk(prefix, suffix)
        else:
            return "Hörrudu! Den där finns ju redan!"

    def add_inbetweeny(self, inbetweeny):
        if self.snusk_db.add_inbetweeny(inbetweeny):
            return self.snusk_db.example_snusk_with_inbetweeny(inbetweeny)
        else:
            return "Hörrudu! Den där finns ju redan!"

    def find_noun(self, word):
        nouns = self.snusk_db.find_noun(word)
        return "{} found:   ".format(len(nouns)) + ",   ".join(prefix + " " + suffix for prefix, suffix in nouns)

    def upvote_noun(self, prefix, suffix):
        score = self.snusk_db.add_noun_score(prefix, suffix, 1)
        if score is None:
            return "Noun not found"
        else:
            description = "out" if score <= SKIP_SCORE else "in"
            return "New score is {} ({})".format(score, description)

    def downvote_noun(self, prefix, suffix):
        score = self.snusk_db.add_noun_score(prefix, suffix, -1)
        if score is None:
            return "Noun not found"
        else:
            description = "out" if score <= SKIP_SCORE else "in"
            return "New score is {} ({})".format(score, description)

    def upvote_inbetweeny(self, inbetweeny):
        score = self.snusk_db.add_inbetweeny_score(inbetweeny, 1)
        if score is None:
            return "Inbetweeny not found"
        else:
            description = "out" if score <= SKIP_SCORE else "in"
            return "New score is {} ({})".format(score, description)

    def downvote_inbetweeny(self, inbetweeny):
        score = self.snusk_db.add_inbetweeny_score(inbetweeny, -1)
        if score is None:
            return "Inbetweeny not found"
        else:
            description = "out" if score <= SKIP_SCORE else "in"
            return "New score is {} ({})".format(score, description)

    def kloofify(self, command, text):
        for _ in range(command.count("o")-1):
            text = self.misc_cmds.kloofify(text)
        return text

    def comp(self, text):
        subparts = text.split(maxsplit=1)
        return self.run_command(subparts[0] + " " + self.run_command(subparts[1]))


if __name__ == "__main__":
    main()
