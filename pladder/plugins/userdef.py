from contextlib import ExitStack, contextmanager
import os
import sqlite3
from typing import Iterator, List, NamedTuple, Optional

from pladder.plugin import BotPluginInterface, Plugin
from pladder.script.interpreter import interpret
from pladder.script.types import CommandBinding, CommandGroup, CommandRegistry, Context, ScriptError, command_binding


class Command(NamedTuple):
    name: str
    params: List[str]
    script: str


@contextmanager
def pladder_plugin(bot: BotPluginInterface) -> Plugin:
    userdef_db_path = os.path.join(bot.state_dir, "userdef.db")
    with UserdefDb(userdef_db_path) as userdef_db:
        UserdefCommands(userdef_db, bot.commands)
        yield


class UserdefCommands(CommandGroup):
    def __init__(self,
                 userdef_db: "UserdefDb",
                 all_cmds: CommandRegistry) -> None:
        self.userdef_db = userdef_db
        self.all_cmds = all_cmds
        admin_cmds = all_cmds.new_command_group("userdef")
        admin_cmds.register_command("def-command", self.def_command)
        admin_cmds.register_command("set-command", self.set_command)
        admin_cmds.register_command("del-command", self.del_command)
        all_cmds.add_command_group("userdefs", self)
        pass

    # CommandGroup methods

    def lookup_command(self, command_name: str) -> Optional[CommandBinding]:
        maybe_command = self.userdef_db.lookup_command(command_name)
        if maybe_command is None:
            return None
        command = maybe_command
        source = f"def-command {{{command.name}}} {{{command.params}}} {{{command.script}}}"

        def exec_command(context: Context, *args: str) -> str:
            if len(command.params) != len(args):
                raise ScriptError(f"{command.name} takes {len(command.params)} arguments, got {len(args)}")
            new_env = dict(zip(command.params, args))
            subcontext = context._replace(environment=new_env)
            result, _display_name = interpret(subcontext, command.script)
            return result

        return command_binding(command_name, exec_command,
                               contextual=True, source=source)

    def list_commands(self) -> List[str]:
        return self.userdef_db.list_commands()

    # Public methods

    def _prettify(self, name: str, params: List[str], script: str) -> str:
        result = f"{name}"
        for param in params:
            result += f" {param}"
        result += f" => {script}"
        return result

    def def_command(self, name: str, params: str, script: str) -> str:
        command = self.userdef_db.lookup_command(name)
        if command:
            return f'A command with name "{name}" already exists!'
        params_list = params.split(" ")
        self.userdef_db.add_command(name, params_list, script)
        return "Command added: " + self._prettify(name, params_list, script)

    def set_command(self, name: str, params: str, script: str) -> str:
        command = self.userdef_db.lookup_command(name)
        if command is None:
            return f'A command with name "{name}" doesn\'t exists!'
        params_list = params.split(" ")
        self.userdef_db.del_command(name)
        self.userdef_db.add_command(name, params_list, script)
        return ("Command replaced. Now: " + self._prettify(name, params_list, script) +
                " Was: " + self._prettify(command.name, command.params, command.script))

    def del_command(self, name: str) -> str:
        command = self.userdef_db.lookup_command(name)
        if command is None:
            return f'A command with name "{name}" doesn\'t exists!'
        self.userdef_db.del_command(name)
        return "Command deleted. Was: " + self._prettify(command.name, command.params, command.script)


class UserdefDb(ExitStack):
    def __init__(self, db_file_path: str) -> None:
        super().__init__()
        self._db = sqlite3.connect(db_file_path)
        self.callback(self._db.close)
        self._setup()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.dbapi2.Cursor]:
        with self._db:
            yield self._db.cursor()

    def _setup(self) -> None:
        with self._transaction() as c:
            try:
                c.execute("SELECT value FROM meta WHERE key = 'version';")
                version = int(c.fetchone()[0])
            except sqlite3.Error:
                version = 0
            if version < 1:
                c.execute("""
                    CREATE TABLE meta (
                        key TEXT UNIQUE,
                        value TEXT
                    );
                """)
                c.execute("""
                    INSERT INTO meta(key, value)
                    VALUES ('version', '1');
                """)
                c.execute("""
                    CREATE TABLE commands (
                        name TEXT UNIQUE,
                        params TEXT,
                        script TEXT
                    );
                """)

    def lookup_command(self, name: str) -> Optional[Command]:
        with self._transaction() as c:
            c.execute("""
                SELECT name, params, script
                FROM commands
                WHERE name = ?;
            """, (name,))
            row = c.fetchone()
            if row:
                name, params_string, script = row
                params = params_string.split(" ")
                return Command(name, params, script)
            else:
                return None

    def add_command(self, name: str, params: List[str], script: str) -> None:
        for param in params:
            if " " in param or "{" in param or "}" in param:
                raise ScriptError(f'Invalid parameter name: "{param}"')
        params_string = " ".join(params)
        with self._transaction() as c:
            c.execute("""
                INSERT INTO commands(name, params, script)
                VALUES (?, ?, ?);
            """, (name, params_string, script))

    def del_command(self, name: str) -> None:
        with self._transaction() as c:
            c.execute("DELETE FROM commands WHERE name = ?;", (name,))

    def list_commands(self) -> List[str]:
        with self._transaction() as c:
            c.execute("SELECT name FROM commands;")
            return [row[0] for row in c.fetchall()]
