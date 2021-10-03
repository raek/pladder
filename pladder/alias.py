from contextlib import ExitStack, contextmanager
import os
import sqlite3
import random
from typing import List, Optional, Tuple

from pladder.plugin import BotPluginInterface, Plugin
from pladder.script import EvalError, CommandRegistry, Context, interpret


@contextmanager
def pladder_plugin(bot: BotPluginInterface) -> Plugin:
    alias_db_path = os.path.join(bot.state_dir, "alias.db")
    with AliasDb(alias_db_path) as alias_db:
        AliasCommands(alias_db, bot.commands)
        yield


def errorstr() -> str:
    if random.random() > 0.95:
        return "https://i.imgur.com/6cpffM4.jpeg"
    else:
        return "Nej"


class DBError(Exception):
    pass


class AliasCommands:
    def __init__(self,
                 alias_db: "AliasDb",
                 all_cmds: CommandRegistry) -> None:
        self.alias_db = alias_db
        self.all_cmds = all_cmds
        admin_cmds = all_cmds.new_command_group("alias")
        admin_cmds.register_command("alias", self.help)
        admin_cmds.register_command("add-alias", self.add_alias, varargs=True)
        admin_cmds.register_command("get-alias", self.get_alias)
        admin_cmds.register_command("del-alias", self.del_alias)
        admin_cmds.register_command("list-alias", self.list_alias)
        admin_cmds.register_command("random-alias", self.random_alias)
        self.user_cmds = all_cmds.new_command_group("aliases")
        self.register_db_bindings()

    def help(self) -> str:
        functions = [
            "get-alias [name]",
            "del-alias [name]",
            "add-alias [name] [content]",
            "list-alias *[name]*",
            "random-alias *[name]*",
        ]
        return ("Functions: " + ",".join(functions) + ". " +
                "Wildcards are % and _. " +
                "Use {} when adding PladderScript to database.")

    def binding_exists(self, name: str) -> bool:
        return self.all_cmds.lookup_command(name) is not None

    def exec_alias(self, context: Context) -> str:
        row = self.alias_db.get_alias(context.command_name)
        if not row:
            return errorstr()
        _, template = row
        script = "echo " + template
        result, _ = interpret(context, script)
        return result

    def register_db_bindings(self) -> None:
        names = self.alias_db.list_alias("")
        for name in names:
            row = self.alias_db.get_alias(name)
            if not row:
                raise DBError("Om du ser det här så har räk fuckat upp")
            _, data = row
            self.register_binding(name, data)

    def register_binding(self, name: str, data: str) -> None:
        source = f"Alias {name}: {data}"
        self.user_cmds.register_command(name, self.exec_alias, contextual=True, source=source)

    def remove_binding(self, name: str) -> bool:
        try:
            self.user_cmds.remove_command(name)
            return True
        except EvalError:
            return False

    def add_alias(self, name: str, data: str) -> str:
        if self.binding_exists(name):
            return "Hallå farfar, den finns ju redan."
        self.alias_db.add_alias(name, data)
        self.register_binding(name, data)
        return f"\"{name}\" added. value is: \"{data}\""

    def get_alias(self, name: str) -> str:
        row = self.alias_db.get_alias(name)
        if row:
            return f"{row[0]}: {row[1]}"
        else:
            return errorstr()

    def del_alias(self, name: str) -> str:
        if self.binding_exists(name):
            try:
                self.alias_db.del_alias(name)
            except Exception:
                return "Det blir inget med det."
            else:
                self.remove_binding(name)
            return "Alias removed"
        else:
            return errorstr()

    def list_alias(self, name_pattern: str) -> str:
        list = self.alias_db.list_alias(name_pattern)
        if list:
            return f"{len(list)} Found: " + " ".join(list)
        return "0 Found"

    def random_alias(self, name_pattern: str) -> str:
        name = self.alias_db.random_alias(name_pattern)
        if name is None:
            return ":)"
        else:
            return name


class AliasDb(ExitStack):
    def __init__(self, db_file_path: str) -> None:
        super().__init__()
        self._db = sqlite3.connect(db_file_path)
        self.callback(self._db.close)
        c = self._db.cursor()
        if not self._check_db_exists(c):
            self._initdb(c)

    def _check_db_exists(self, c: sqlite3.dbapi2.Cursor) -> bool:
        try:
            c.execute("SELECT value FROM config WHERE id=1")
            return True
        except Exception:
            return False

    def _initdb(self, c: sqlite3.dbapi2.Cursor) -> None:
        c.executescript("""
                BEGIN TRANSACTION;
                CREATE TABLE config (
                    id INTEGER PRIMARY KEY,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT
                );
                INSERT INTO config(id, key, value) VALUES
                ('1', 'version', '1');

                CREATE TABLE alias (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    data TEXT
                );
                INSERT INTO alias(name, data) VALUES
                ('hello', 'Hej!');
            """)

        self._db.commit()

    def _alias_exists(self, name: str) -> bool:
        c = self._db.cursor()
        c.execute("SELECT * FROM alias WHERE name=?", [name])
        if c.fetchone():
            return True
        else:
            return False

    def _insert_alias(self, name: str, data: str) -> None:
        c = self._db.cursor()
        c.execute("BEGIN TRANSACTION")
        try:
            c.execute("INSERT INTO alias (name, data) VALUES (?, ?)", (name, data))
        except Exception:
            self._db.rollback()
            raise DBError("You cannot insert ye value :(")
        else:
            self._db.commit()

    def add_alias(self, name: str, data: str) -> None:
        if self._alias_exists(name):
            raise DBError("Om du ser det här har kodaren som inte vill bli highlightad fuckat upp")
        self._insert_alias(name, data)

    def get_alias(self, name: str) -> Optional[Tuple[str, str]]:
        if self._alias_exists(name):
            c = self._db.cursor()
            try:
                c.execute("SELECT name, data FROM alias WHERE name=?", [name])
            except Exception:
                raise DBError("eror :(")
            else:
                row = c.fetchone()
                return row[0], row[1]
        else:
            return None

    def del_alias(self, name: str) -> None:
        if self._alias_exists(name):
            c = self._db.cursor()
            c.execute("BEGIN TRANSACTION")
            try:
                c.execute("DELETE FROM alias WHERE name=?", [name])
            except Exception:
                self._db.rollback()
                raise DBError("You cannot delete ye flask")
            else:
                self._db.commit()
        else:
            raise DBError("poop")

    def list_alias(self, name_pattern: str) -> List[str]:
        c = self._db.cursor()
        searchstr = "%"+name_pattern+"%"
        try:
            c.execute("SELECT name FROM alias WHERE name LIKE ?", [searchstr])
        except Exception:
            raise DBError("eror :(")
        else:
            return [row[0] for row in c.fetchall()]

    def random_alias(self, name_pattern: str) -> Optional[str]:
        list = self.list_alias(name_pattern)
        if list:
            return random.choice(list)
        else:
            return None
