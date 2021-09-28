from collections import namedtuple, defaultdict
from contextlib import ExitStack
import json
import os
import random
import sqlite3


Config = namedtuple("Config", "networks, logdir")


def main():
    from gi.repository import GLib  # type: ignore
    from pydbus import SessionBus  # type: ignore

    config_home = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.environ["HOME"], ".config"))
    config = read_config(config_home)

    log = PladderLog(config)
    bus = SessionBus()
    bus.publish("se.raek.PladderLog", log)
    loop = GLib.MainLoop()
    loop.run()


def read_config(config_home):
    config_path = os.path.join(config_home, "pladder-log", "config.json")
    with open(config_path, "rt") as f:
        config_data = json.load(f)
        defaults = {
            'networks': [],
            'logdir': os.path.join(config_home, "pladder-log", "logs"),
        }
        return Config(**{**defaults, **config_data})


class PladderLog(ExitStack):
    """
    <node>
      <interface name="se.raek.PladderLog">
        <method name="AddLine">
          <arg direction="in" name="timestamp" type="u" />
          <arg direction="in" name="network" type="s" />
          <arg direction="in" name="channel" type="s" />
          <arg direction="in" name="nick" type="s" />
          <arg direction="in" name="text" type="s" />
        </method>
        <method name="GetLines">
          <arg direction="in" name="network" type="s" />
          <arg direction="in" name="channel" type="s" />
          <arg direction="in" name="line_count" type="u" />
          <arg direction="out" name="return" type="a(iuss)" />
        </method>
        <method name="SearchLines">
          <arg direction="in" name="network" type="s" />
          <arg direction="in" name="channel" type="s" />
          <arg direction="in" name="substring" type="s" />
          <arg direction="in" name="max_count" type="u" />
          <arg direction="in" name="index" type="d" />
          <arg direction="out" name="return" type="a(iuss)" />
        </method>
        <method name="Mimic">
          <arg direction="in" name="network" type="s" />
          <arg direction="in" name="channel" type="s" />
          <arg direction="in" name="nick" type="s" />
          <arg direction="out" name="return" type="s" />
        </method>
      </interface>
    </node>
    """

    def __init__(self, config):
        super().__init__()
        os.makedirs(config.logdir, exist_ok=True)
        self.logdbs = {network: self.enter_context(LogDb(os.path.join(config.logdir, network + '.db')))
                       for network in config.networks}

    def AddLine(self, timestamp, network, channel, nick, text):
        if network in self.logdbs:
            self.logdbs[network].add_line(timestamp, channel, nick, text)

    def GetLines(self, network, channel, line_count):
        if network in self.logdbs:
            return self.logdbs[network].get_lines(channel, line_count)
        else:
            return []

    def SearchLines(self, network, channel, substring, max_count, index):
        if network in self.logdbs:
            return self.logdbs[network].search_lines(channel, '%{}%'.format(substring), max_count, index)
        else:
            return []

    def Mimic(self, network, channel, nick):
        if network in self.logdbs:
            return self.logdbs[network].mimic(channel, nick)
        else:
            return ''


class LogDb(ExitStack):
    def __init__(self, db_file_path):
        super().__init__()
        self._db = sqlite3.connect(db_file_path)
        self.callback(self._db.close)
        self._setup()

    def _setup(self):
        with self._db:
            c = self._db.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS lines (
                    timestamp DATETIME,
                    channel   TEXT,
                    nick      TEXT,
                    text      TEXT
                );
            """)

    def get_lines(self, channel, line_count):
        return self.search_lines(channel, '%', line_count, 0)

    def search_lines(self, channel, substring, max_count, index):
        with self._db:
            c = self._db.cursor()
            if index < 0:
                c.execute("""
                    SELECT COUNT(*)
                    FROM lines
                    WHERE channel = :channel AND (text LIKE :substring OR nick LIKE :substring)
                """, {"channel": channel,
                      "substring": substring}),
                (row_count,) = c.fetchone()
                index = row_count + index
            c.execute("""
                SELECT row_number - 1, timestamp, nick, text FROM (
                    SELECT ROW_NUMBER() OVER(ORDER BY timestamp ASC) AS row_number,
                           timestamp, nick, text
                    FROM lines
                    WHERE channel = :channel AND (text LIKE :substring OR nick LIKE :substring)
                )
                WHERE row_number > :index
                LIMIT :max_count
            """, {"channel": channel,
                  "substring": substring,
                  "max_count": max_count,
                  "index": index})
            return list(c.fetchall())

    def add_line(self, timestamp, channel, nick, text):
        with self._db:
            c = self._db.cursor()
            c.execute("INSERT INTO lines (timestamp, channel, nick, text) VALUES (?, ?, ?, ?);",
                      (timestamp, channel, nick, text))

    def mimic(self, channel, nick):
        stats = self._generate_mimic_stats(channel, nick)
        return self._generate_mimic_line(stats)

    def _generate_mimic_stats(self, channel, nick):
        with self._db:
            c = self._db.cursor()
            c.execute("""
                SELECT text
                FROM lines
                WHERE channel = :channel AND nick = :nick
            """, {'channel': channel,
                  'nick': nick})
            stats = defaultdict(lambda: defaultdict(int))
            for (line,) in c.fetchall():
                prev = ''
                for word in line.split():
                    stats[prev][word] += 1
                    prev = word
                if prev != '':
                    stats[prev][''] += 1
            return stats

    def _generate_mimic_line(self, stats):
        words = []
        prev = ''
        while True:
            if not stats[prev]:
                break
            word = random.choices(list(stats[prev].keys()), weights=stats[prev].values())[0]
            if word == '':
                break
            words.append(word)
            prev = word
        return ' '.join(words)


if __name__ == '__main__':
    main()
