from contextlib import ExitStack
import os
import sqlite3
import random
from pladder.plugin import Plugin


class DBError(Exception):
    pass


class AliasPlugin(Plugin):
    def __init__(self, bot):
        super().__init__()
        alias_db_path = os.path.join(bot.state_dir, "alias.db")
        self.alias_db = self.enter_context(AliasDb(alias_db_path))
        self.bot = bot
        bot.register_command("alias", self.help)
        bot.register_command("add-alias", self.add_alias, varargs=True)
        bot.register_command("get-alias", self.alias_db.get_alias, varargs=True)
        bot.register_command("del-alias", self.del_alias, varargs=True)
        bot.register_command("list-alias", self.alias_db.list_alias, varargs=True)
        bot.register_command("random-alias", self.alias_db.random_alias, varargs=True)
        self.register_db_bindings()


    def help(self):
        return "Functions: get-alias [name], del-alias [name], add-alias [name] [content], list-alias *[name]*, random-alias *[name]*. Wildcards are % and _. Use {} when adding PladderScript to database."
    
    def binding_exists(self, name):
        for binding in self.bot.bindings:
            if name == binding.command_name:
                return True
        return False
    
    def exec_alias(self, context):
        name = context.get("command")
        data = self.alias_db.get_alias(name)
        _, data = data.split(": ", 1)
        return data
    
    def register_db_bindings(self):
        names = self.alias_db.list_alias("_").split(" ")
        for name in names:
            self.register_binding(name)
    
    def register_binding(self, name):
        self.bot.register_command(name, self.exec_alias, contextual=True, parseoutput=True)
    
    def remove_binding(self, name):
        for binding in self.bot.bindings:
            if name == binding.command_name:
                if self.bot.bindings.remove(binding):
                    return True
        return False
    
    def add_alias(self, args):
        try:
            name, data = args.split(" ", 1)
        except:
            return "Det lär ju inte bara vara ett ord ditt mähulkande våp! ~add-alias hest {[prefix] gillar hest!}"
        if self.binding_exists(name):
            return "Hallå farfar, den finns ju redan."
        if result := self.alias_db.add_alias(name, data):
            self.register_binding(name)
        return result
    
    def del_alias(self, args):
        if self.binding_exists(args):
            try: 
                result = self.alias_db.del_alias(args)
            except:
                return "Det blir inget med det."
            else:
                self.remove_binding(args)
            return result
        else:
            return "Nej"







class AliasDb(ExitStack):
    def __init__(self, db_file_path):
        super().__init__()
        self._db = sqlite3.connect(db_file_path)
        self.callback(self._db.close)
        c = self._db.cursor()
        if self._check_db_exists(c) == False:
            self._initdb(c)

    def _check_db_exists(self, c):
        try:
            c.execute("SELECT value FROM config WHERE id=1")
            return True
        except:
            return False

    def _initdb(self, c):
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

    def _alias_exists(self, name):
        c = self._db.cursor()
        c.execute("SELECT * FROM alias WHERE name=?", [name])
        if c.fetchone():
            return True
        else:
            return False
    
    def _insert_alias(self, name, data):
        c = self._db.cursor()
        c.execute("BEGIN TRANSACTION")
        try:
            c.execute("INSERT INTO alias (name, data) VALUES (?, ?)", (name, data))
        except:
            self._db.rollback()
            raise DBError("You cannot insert ye value :(")
        else:
            self._db.commit()
            return f"\"{name}\" added"

    def add_alias(self, name, data):
        if self._alias_exists(name):
            raise DBError("Om du ser det här har Krille fuckat upp")
        return self._insert_alias(name, data)
    
    def get_alias(self, args):
        if self._alias_exists(args):
            c = self._db.cursor()
            try:
                c.execute("SELECT name, data FROM alias WHERE name=?", [args])
            except:
                return "eror :("
            else:
                row = c.fetchone()
                return f"{row[0]}: {row[1]}"
        else:
            return "Nej"
    
    def del_alias(self, args):
        if self._alias_exists(args):
            c = self._db.cursor()
            c.execute("BEGIN TRANSACTION")
            try:
                c.execute("DELETE FROM alias WHERE name=?", [args])
            except:
                self._db.rollback()
                raise DBError("You cannot delete ye flask")
            else:
                self._db.commit()
                return "Alias removed"
        else:
            raise DBError("poop")
    
    def list_alias(self, args):
        c = self._db.cursor()
        searchstr = "%"+args+"%"
        try:
            c.execute("SELECT name FROM alias WHERE name LIKE ?", [searchstr])
        except:
            return "eror :("
        else:
            result = ""
            if (match := c.fetchall()):
                for line in match:
                    result += " " + line[0]
            result = result.strip()
            return result
    
    def random_alias(self, args):
        list = self.list_alias(args)
        return random.choice(list.split())


