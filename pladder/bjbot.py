from contextlib import contextmanager
from functools import partial
import os


@contextmanager
def pladder_plugin(bot):
    datorbas = importera(os.path.join(bot.state_dir, "bunny.txt"))
    def jb(trigger):
        return datorbas.get(trigger, "Trigger not found.")
    bot.register_command("jb", jb)
    yield

    
def importera(path):
    db = {}
    if os.path.exists(path):
        with open(path, "rt", encoding="latin1") as fp:
            for line in fp:
                line = line.strip()
                delim_index = line.find("¤")
                db[line[0:delim_index]] = line[delim_index + 1:]
    return db
