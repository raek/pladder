from pladder.alias import AliasDb, AliasCommands
from pladder.bot import PladderBot
from pladder.script import CommandRegistry, new_context


class MockBot():
    new_command_group = PladderBot.new_command_group

    def __init__(self):
        self.commands = CommandRegistry()
        self.commands.register_command("echo", lambda text="": text, varargs=True)


mock_bot = MockBot()
alias_db = AliasDb(":memory:")
alias_cmds = AliasCommands(mock_bot, alias_db)


def test_help():
    functions = [
        "get-alias [name]",
        "del-alias [name]",
        "add-alias [name] [content]",
        "list-alias *[name]*",
        "random-alias *[name]*",
    ]
    expected = ("Functions: " + ",".join(functions) + ". " +
                "Wildcards are % and _. " +
                "Use {} when adding PladderScript to database.")
    result = alias_cmds.help()
    assert result == expected


def test_init_binding():
    result = alias_db.get_alias("hello")
    assert result == "hello: Hej!"


def test_db_addalias():
    result = alias_db.add_alias("testdb", "datamaskin")
    assert result == '"testdb" added. value is: "datamaskin"'


def test_alias_create():
    result = alias_cmds.add_alias("testalias", "testtest")
    assert result == '"testalias" added. value is: "testtest"'


def test_binding_exists():
    result = alias_cmds.binding_exists("testalias")
    assert result


def test_exec_alias():
    context = new_context(mock_bot.commands, command_name="testalias")
    result = alias_cmds.exec_alias(context)
    assert result == "testtest"


def test_db_getalias():
    result = alias_db.get_alias("testdb")
    assert result == "testdb: datamaskin"


def test_db_listalias():
    result = alias_db.list_alias("%")
    assert result == "hello testalias testdb"


def test_db_randomalias():
    result = alias_db.random_alias("%")
    assert result == "hello" or "testdb"


def test_db_delalias():
    res1 = alias_db.del_alias("hello")
    res2 = alias_db.get_alias("hello")
    assert res1 == "Alias removed" and res2 in ["Nej", "https://i.imgur.com/6cpffM4.jpeg"]


def test_delalias():
    result = alias_cmds.del_alias("testalias")
    assert result == "Alias removed"


def test_invalid_delete():
    result = alias_cmds.del_alias("get-alias")
    assert result == "Det blir inget med det."


def test_invalid_add():
    result = alias_cmds.add_alias("get-alias", "hehu jag är smart")
    assert result == "Hallå farfar, den finns ju redan."
