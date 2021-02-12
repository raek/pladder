from contextlib import contextmanager
from random import randrange
import os


@contextmanager
def pladder_plugin(bot):
    fnamn_db = importera(os.path.join(bot.state_dir, "fnamn.txt"))
    enamn_db = importera(os.path.join(bot.state_dir, "enamn.txt"))

    def _random_entry(db):
        return db[randrange(0, len(db), 1)]

    def fnamn():
        return _random_entry(fnamn_db)

    def enamn():
        return _random_entry(enamn_db)

    bot.register_command("förnamn", fnamn)
    bot.register_command("efternamn", enamn)
    yield


def importera(path):
    db = []
    if os.path.exists(path):
        with open(path, "rt", encoding="latin1") as fp:
            for line in fp:
                line = line.strip()
                db.append(line)
    else:
        db.append("foo")
    return db
