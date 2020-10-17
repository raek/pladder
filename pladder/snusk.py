from contextlib import ExitStack
import os
import random
import sqlite3

from pladder.plugin import Plugin


class SnuskPlugin(Plugin):
    def __init__(self, bot):
        super().__init__()
        snusk_db_path = os.path.join(bot.state_dir, "snusk.db")
        self.snusk_db = self.enter_context(SnuskDb(snusk_db_path))
        bot.register_command("snusk", self.snusk_db.snusk)
        bot.register_command("snuska", self.snusk_db.directed_snusk, raw=True)
        bot.register_command("smak", self.snusk_db.taste)
        bot.register_command("nickförslag", self.snusk_db.nick)
        bot.register_command("add-snusk", self.add_noun)
        bot.register_command("add-noun", self.add_noun)
        bot.register_command("add-preposition", self.add_inbetweeny)
        bot.register_command("add-inbetweeny", self.add_inbetweeny, raw=True)
        bot.register_command("find-noun", self.find_noun)
        bot.register_command("upvote-noun", self.upvote_noun)
        bot.register_command("downvote-noun", self.downvote_noun)
        bot.register_command("upvote-inbetweeny", self.upvote_inbetweeny, raw=True)
        bot.register_command("downvote-inbetweeny", self.downvote_inbetweeny, raw=True)

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


# Words with scores lower than or equal to this will not be included in random picks
SKIP_SCORE = -3


class SnuskDb(ExitStack):
    def __init__(self, db_file_path):
        super().__init__()
        self._db = sqlite3.connect(db_file_path)
        self.callback(self._db.close)
        self._setup()

    def _setup(self):
        with self._db:
            c = self._db.cursor()

            # Nouns
            c.execute("""
                CREATE TABLE IF NOT EXISTS nouns (
                    prefix TEXT,
                    suffix TEXT,
                    score  INTEGER DEFAULT 0,
                    UNIQUE(prefix, suffix)
                );
            """)
            c.execute("PRAGMA table_info(nouns);")
            if len(c.fetchall()) < 3:
                c.execute("ALTER TABLE nouns ADD COLUMN score INTEGER DEFAULT 0;")
            c.execute("SELECT COUNT(*) = 0 FROM nouns;")
            if c.fetchone()[0]:
                c.execute("INSERT INTO nouns (prefix, suffix) VALUES ('frukt', 'frukten');")

            # Inbetweenies
            c.execute("""
                CREATE TABLE IF NOT EXISTS inbetweenies (
                    inbetweeny TEXT UNIQUE,
                    score      INTEGER DEFAULT 0
                );
            """)
            c.execute("PRAGMA table_info(inbetweenies);")
            if len(c.fetchall()) < 2:
                c.execute("ALTER TABLE inbetweenies ADD COLUMN score INTEGER DEFAULT 0;")
            c.execute("SELECT COUNT(*) = 0 FROM inbetweenies;")
            if c.fetchone()[0]:
                c.execute("INSERT INTO inbetweenies (inbetweeny) VALUES ('i');")

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

    def nick(self):
        parts = self._random_parts()
        return parts[random.choice([0, 1])]

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
                WITH
                random_noun AS (
                    SELECT rowid
                    FROM nouns
                    WHERE score > :skip_score
                    ORDER BY RANDOM()
                    LIMIT 1
                ),
                random_inbetweeny AS (
                    SELECT rowid
                    FROM inbetweenies
                    WHERE score > :skip_score
                    ORDER BY RANDOM()
                    LIMIT 1
                )
                SELECT a.prefix, b.suffix, c.inbetweeny, d.prefix, e.suffix
                FROM nouns a, nouns b, inbetweenies c, nouns d, nouns e
                WHERE a.rowid IN random_noun
                AND b.rowid IN random_noun
                AND c.rowid IN random_inbetweeny
                AND d.rowid IN random_noun
                AND e.rowid IN random_noun;
            """, {"skip_score": SKIP_SCORE})
            return list(c.fetchone())

    def add_noun(self, prefix, suffix):
        with self._db:
            c = self._db.cursor()
            try:
                c.execute("INSERT INTO nouns (prefix, suffix) VALUES (?, ?);", (prefix, suffix))
                return True
            except sqlite3.IntegrityError:
                return False

    def add_inbetweeny(self, inbetweeny):
        with self._db:
            c = self._db.cursor()
            try:
                c.execute("INSERT INTO inbetweenies (inbetweeny) VALUES (?);", (inbetweeny,))
                return True
            except sqlite3.IntegrityError:
                return False

    def find_noun(self, word):
        with self._db:
            c = self._db.cursor()
            c.execute("""
                SELECT prefix, suffix
                FROM nouns
                WHERE ? IN (prefix, suffix);
            """, (word,))
            return c.fetchall()

    def add_noun_score(self, prefix, suffix, delta):
        with self._db:
            c = self._db.cursor()
            c.execute("""
                UPDATE nouns
                SET score = score + ?
                WHERE prefix = ? AND suffix = ?;
            """, (delta, prefix, suffix))
            c.execute("""
                SELECT score
                FROM nouns
                WHERE prefix = ? AND suffix = ?;
            """, (prefix, suffix))
            row = c.fetchone()
            return None if row is None else row[0]

    def add_inbetweeny_score(self, inbetweeny, delta):
        with self._db:
            c = self._db.cursor()
            c.execute("""
                UPDATE inbetweenies
                SET score = score + ?
                WHERE inbetweeny = ?;
            """, (delta, inbetweeny))
            c.execute("""
                SELECT score
                FROM inbetweenies
                WHERE inbetweeny = ?;
            """, (inbetweeny,))
            row = c.fetchone()
            return None if row is None else row[0]


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
