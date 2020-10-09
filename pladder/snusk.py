from contextlib import ExitStack
import random
import sqlite3


class SnuskDb(ExitStack):
    def __init__(self, db_file_path):
        super().__init__()
        self._db = sqlite3.connect(db_file_path)
        self.callback(self._db.close)
        self._setup()

    def _setup(self):
        with self._db:
            c = self._db.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS nouns (
                    prefix TEXT,
                    suffix TEXT,
                    UNIQUE(prefix, suffix)
                );
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS inbetweenies (
                    inbetweeny TEXT UNIQUE
                );
            """)
            c.execute("SELECT COUNT(*) = 0 FROM nouns;")
            if c.fetchone()[0]:
                c.execute("INSERT INTO nouns VALUES ('frukt', 'frukten');")
            c.execute("SELECT COUNT(*) = 0 FROM inbetweenies;")
            if c.fetchone()[0]:
                c.execute("INSERT INTO inbetweenies VALUES ('i');")

    def snusk(self):
        return self._format_parts(self._random_parts())

    def directed_snusk(self, target):
        parts = self._random_parts()
        i = random.choice([0, 1, 3, 4])
        if i in [0, 3]:
            part = target
        else:
            part = target + "ern"
        parts[i] = part
        return self._format_parts(parts)

    def taste(self):
        parts = self._random_parts()
        return "{}/{}".format(parts[0].upper(), parts[3].upper())

    def example_snusk(self, a, b):
        parts = self._random_parts()
        if random.choice([False, True]):
            parts[0] = a
            parts[4] = b
        else:
            parts[1] = b
            parts[3] = a
        return self._format_parts(parts)

    def example_snusk_with_inbetweeny(self, inbetweeny):
        parts = self._random_parts()
        parts[2] = inbetweeny
        return self._format_parts(parts)

    def _format_parts(self, parts):
        return "{}{} {} {}{}".format(*parts)

    def _random_parts(self):
        with self._db:
            c = self._db.cursor()
            c.execute("""
                SELECT
                    a.prefix, b.suffix, c.inbetweeny, d.prefix, e.suffix
                FROM
                    nouns a, nouns b, inbetweenies c, nouns d, nouns e
                WHERE
                        a.rowid IN (SELECT rowid FROM nouns        ORDER BY RANDOM() LIMIT 1)
                    AND b.rowid IN (SELECT rowid FROM nouns        ORDER BY RANDOM() LIMIT 1)
                    AND c.rowid IN (SELECT rowid FROM inbetweenies ORDER BY RANDOM() LIMIT 1)
                    AND d.rowid IN (SELECT rowid FROM nouns        ORDER BY RANDOM() LIMIT 1)
                    AND e.rowid IN (SELECT rowid FROM nouns        ORDER BY RANDOM() LIMIT 1);
            """)
            return list(c.fetchone())

    def add_noun(self, prefix, suffix):
        with self._db:
            c = self._db.cursor()
            try:
                c.execute("INSERT INTO nouns VALUES (?, ?);", (prefix, suffix))
                return True
            except sqlite3.IntegrityError:
                return False

    def add_inbetweeny(self, inbetweeny):
        with self._db:
            c = self._db.cursor()
            try:
                c.execute("INSERT INTO inbetweenies VALUES (?);", (inbetweeny,))
                return True
            except sqlite3.IntegrityError:
                return False


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("db_file_path")
    parser.add_argument("--import-noun-json")
    parser.add_argument("--import-inbetweeny-json")
    args = parser.parse_args()

    with SnuskDb(args.db_file_path) as db:
        if args.import_noun_json:
            with open(args.import_noun_json, "rt") as f:
                nouns = json.load(f)
            for prefix, suffix in nouns:
                db.add_noun(prefix, suffix)
        if args.import_inbetweeny_json:
            with open(args.import_inbetweeny_json, "rt") as f:
                inbetweenies = json.load(f)
            for inbetweeny in inbetweenies:
                db.add_inbetweeny(inbetweeny)
        print(db.snusk())
        print(db.directed_snusk("raek"))
        print(db.example_snusk("don", "donet"))
