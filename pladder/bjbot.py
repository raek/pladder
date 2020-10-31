import os
from pladder.plugin import Plugin

class BjBotPlugin(Plugin):
    def __init__(self, bot):
        super().__init__()
        self._datorbas = dict()
        self.importera(self._datorbas, os.path.join(bot.statedir, "bunny.txt"))
        if not bot is None:
            bot.register_command("jb", self.jb)

    def importera(self, db, path):
        if os.path.exists(path):
            with open(path) as fp:
                for line in fp:
                    delim_index = line.find("¤")
                    db[line[0:delim_index]] = line[delim_index + 1:]

    def jb(self, trigger):
        if trigger in self._datorbas.keys():
            return self._datorbas[trigger]
        else:
            return "Trigger not found."


if __name__ == "__main__":
    import sys

    bot = BjBotPlugin(None)
    print(bot.jb(sys.argv[1]))
