from contextlib import ExitStack, contextmanager
import os
import sqlite3
from typing import Iterator, List, NamedTuple, Optional

from pladder.plugin import BotPluginInterface, Plugin
from pladder.script.parser import escape
from pladder.script.interpreter import interpret
from pladder.script.types import CommandBinding, CommandGroup, CommandRegistry, Context, ScriptError, command_binding


class Command(NamedTuple):
    name: str
    params: List[str]
    script: str


class Cell(NamedTuple):
    name: str
    value: str


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
        admin_cmds.register_command("def-cell", self.def_cell)
        admin_cmds.register_command("get-cell", self.get_cell)
        admin_cmds.register_command("set-cell", self.set_cell)
        admin_cmds.register_command("del-cell", self.del_cell)
        admin_cmds.register_command("list-cells", self.list_cells)
        all_cmds.add_command_group("userdefs", self)
        pass

    # CommandGroup methods

    def lookup_command(self, command_name: str) -> Optional[CommandBinding]:
        maybe_command = self.userdef_db.lookup_command(command_name)
        if maybe_command is None:
            return None
        command = maybe_command
        source = f"def-command {escape(command.name)} {escape(' '.join(command.params))} {escape(command.script)}"

        def exec_command(context: Context, *args: str) -> str:
            if len(command.params) != len(args):
                # special case when the command expects 1 argument: just append the arguments together
                if len(command.params) == 1 and len(args) > 1:
                    args = tuple([" ".join(args)])
                else:
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

    # Commands

    def _prettify_command(self, name: str, params: List[str], script: str) -> str:
        result = f"{name}"
        for param in params:
            result += f" {param}"
        result += f" => {script}"
        return result

    def def_command(self, name: str, params: str, script: str) -> str:
        command = self.userdef_db.lookup_command(name)
        if command:
            return f'A command with name "{name}" already exists!'
        if params:
            params_list = params.split(" ")
        else:
            params_list = []
        self.userdef_db.add_command(name, params_list, script)
        return "Command added: " + self._prettify_command(name, params_list, script)

    def set_command(self, name: str, params: str, script: str) -> str:
        command = self.userdef_db.lookup_command(name)
        if command is None:
            return f'A command with name "{name}" doesn\'t exists!'
        if params:
            params_list = params.split(" ")
        else:
            params_list = []
        self.userdef_db.del_command(name)
        self.userdef_db.add_command(name, params_list, script)
        return ("Command updated. Now: " + self._prettify_command(name, params_list, script) +
                " Was: " + self._prettify_command(command.name, command.params, command.script))

    def del_command(self, name: str) -> str:
        command = self.userdef_db.lookup_command(name)
        if command is None:
            return f'A command with name "{name}" doesn\'t exists!'
        self.userdef_db.del_command(name)
        return "Command deleted. Was: " + self._prettify_command(command.name, command.params, command.script)

    # Cells

    def _prettify_cell(self, name: str, value: str) -> str:
        return f"{name} = {value}"

    def def_cell(self, name: str, value: str) -> str:
        cell = self.userdef_db.lookup_cell(name)
        if cell is not None:
            return f'A cell with name "{name} already exists!"'
        self.userdef_db.add_cell(name, value)
        return "Cell added: " + self._prettify_cell(name, value)

    def get_cell(self, name: str) -> str:
        cell = self.userdef_db.lookup_cell(name)
        if cell is None:
            return f'A cell with name "{name}" doesn\'t exists!"'
        return cell.value

    def set_cell(self, name: str, value: str) -> str:
        cell = self.userdef_db.lookup_cell(name)
        if cell is None:
            return f'A cell with name "{name}" doesn\'t exists!"'
        self.userdef_db.del_cell(name)
        self.userdef_db.add_cell(name, value)
        return ("Cell updated. Now: " + self._prettify_cell(name, value) +
                " Was: " + self._prettify_cell(cell.name, cell.value))

    def del_cell(self, name: str) -> str:
        cell = self.userdef_db.lookup_cell(name)
        if cell is None:
            return f'A cell with name "{name}" doesn\'t exists!"'
        self.userdef_db.del_cell(name)
        return "Cell deleted. Was: " + self._prettify_cell(cell.name, cell.value)

    def list_cells(self) -> str:
        cells = self.userdef_db.list_cells()
        return "Cells: " + ", ".join(sorted(cells))


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
            if version < 2:
                c.execute("""
                    CREATE TABLE cells (
                        name TEXT UNIQUE,
                        value TEXT
                    );
                """)
                c.execute("""
                    UPDATE meta
                    SET value = '2'
                    WHERE key = 'version';
                """)

    # Commands

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
                if params_string:
                    params = params_string.split(" ")
                else:
                    params = []
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

    # Cells

    def lookup_cell(self, name: str) -> Optional[Cell]:
        with self._transaction() as c:
            c.execute("""
                SELECT name, value
                FROM cells
                WHERE name = ?;
            """, (name,))
            row = c.fetchone()
            if row:
                return Cell(*row)
            else:
                return None

    def add_cell(self, name: str, value: str) -> None:
        with self._transaction() as c:
            c.execute("""
                INSERT INTO cells(name, value)
                VALUES (?, ?);
            """, (name, value))

    def del_cell(self, name: str) -> None:
        with self._transaction() as c:
            c.execute("DELETE FROM cells WHERE name = ?;", (name,))

    def list_cells(self) -> List[str]:
        with self._transaction() as c:
            c.execute("SELECT name FROM cells;")
            return [row[0] for row in c.fetchall()]
