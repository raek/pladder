from contextlib import ExitStack, contextmanager
import os
import random
import sqlite3
from re import search


@contextmanager
def pladder_plugin(bot):
    snusk_db_path = os.path.join(bot.state_dir, "snusk.db")
    with SnuskDb(snusk_db_path) as snusk_db:
        snusk_commands = SnuskCommands(snusk_db)

        bot.register_command("snusk",       snusk_db.snusk,             parseoutput=True)
        bot.register_command("snuska",      snusk_db.directed_snusk,    parseoutput=True, varargs=True)
        bot.register_command("nickförslag", snusk_db.random_noun,       parseoutput=True)
        bot.register_command("prefix",      snusk_db.random_prefix,     parseoutput=True)
        bot.register_command("suffix",      snusk_db.random_suffix,     parseoutput=True)
        bot.register_command("noun",        snusk_db.random_noun,       parseoutput=True)
        bot.register_command("inbetweeny",  snusk_db.random_inbetweeny, parseoutput=True)

        bot.register_command("smak",                snusk_commands.smak,                parseoutput=True)
        bot.register_command("add-snusk",           snusk_commands.add_noun)
        bot.register_command("add-noun",            snusk_commands.add_noun)
        bot.register_command("add-preposition",     snusk_commands.add_inbetweeny,      varargs=True)
        bot.register_command("add-inbetweeny",      snusk_commands.add_inbetweeny,      varargs=True)
        bot.register_command("find-snusk",          snusk_commands.find_noun)
        bot.register_command("find-noun",           snusk_commands.find_noun)
        bot.register_command("upvote-snusk",        snusk_commands.upvote_noun)
        bot.register_command("upvote-noun",         snusk_commands.upvote_noun)
        bot.register_command("downvote-snusk",      snusk_commands.downvote_noun)
        bot.register_command("downvote-noun",       snusk_commands.downvote_noun)
        bot.register_command("upvote-inbetweeny",   snusk_commands.upvote_inbetweeny,   varargs=True)
        bot.register_command("downvote-inbetweeny", snusk_commands.downvote_inbetweeny, varargs=True)

        yield


class SnuskCommands:
    def __init__(self, snusk_db):
        self.snusk_db = snusk_db

    def smak(self):
        return "{}/{}".format(self.snusk_db.random_prefix().upper(), self.snusk_db.random_prefix().upper())

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
        hits = len(nouns) if len(nouns) < 11 else "10+"
        results = [prefix + " " + suffix + " (" + str(score) + ")" for prefix, suffix, score in nouns]
        return "{} found:  ".format(hits) + ",  ".join(results)

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

    def random_prefix(self):
        with self._db:
            c = self._db.cursor()
            c.execute("""
                SELECT prefix
                FROM nouns
                WHERE score > :skip_score
                ORDER BY RANDOM()
                LIMIT 1
            """, {"skip_score": SKIP_SCORE})
            return c.fetchone()[0]

    def random_suffix(self):
        with self._db:
            c = self._db.cursor()
            c.execute("""
                SELECT suffix
                FROM nouns
                WHERE score > :skip_score
                ORDER BY RANDOM()
                LIMIT 1
            """, {"skip_score": SKIP_SCORE})
            return c.fetchone()[0]

    def random_noun(self):
        with self._db:
            c = self._db.cursor()
            c.execute("""
                SELECT prefix, suffix
                FROM nouns
                WHERE score > :skip_score
                ORDER BY RANDOM()
                LIMIT 1
            """, {"skip_score": SKIP_SCORE})
            parts = c.fetchone()
            return random.choice(parts)

    def random_inbetweeny(self):
        with self._db:
            c = self._db.cursor()
            c.execute("""
                SELECT inbetweeny
                FROM inbetweenies
                WHERE score > :skip_score
                ORDER BY RANDOM()
                LIMIT 1
            """, {"skip_score": SKIP_SCORE})
            return c.fetchone()[0]

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
        if search('([a-z])\\1\\1', parts[0].lower() + parts[1].lower()):
            parts[0] += '-'

        if search('([a-z])\\1\\1', parts[3].lower() + parts[4].lower()):
            parts[3] += '-'

        return "{}{} {} {}{}".format(*parts)

    def _random_parts(self):
        return [
            self.random_prefix(),
            self.random_suffix(),
            self.random_inbetweeny(),
            self.random_prefix(),
            self.random_suffix(),
        ]

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
            searchstr = "%" + word + "%"
            c = self._db.cursor()
            c.execute("""
                SELECT prefix, suffix, score
                FROM nouns
                WHERE prefix LIKE ? OR suffix LIKE ?
                LIMIT 11;
            """, (searchstr, searchstr))
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
