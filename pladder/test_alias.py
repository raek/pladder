from pytest import fixture

from pladder.alias import AliasDb, AliasCommands
from pladder.script import CommandRegistry, new_context


@fixture(scope="function")
def alias_db():
    with AliasDb(":memory:") as db:
        yield db


@fixture(scope="function")
def commands():
    cmds = CommandRegistry()
    builtin = cmds.new_command_group("builtin")
    builtin.register_command("echo", lambda text="": text, varargs=True)
    return cmds


@fixture()
def alias_cmds(commands, alias_db):
    return AliasCommands(alias_db, commands)


@fixture()
def populated_alias_cmds(alias_cmds):
    alias_cmds.alias_db.add_alias("testdb", "datamaskin")
    alias_cmds.add_alias("testalias", "testtest")
    return alias_cmds


@fixture()
def populated_alias_db(populated_alias_cmds):
    return populated_alias_cmds.alias_db


def test_help(alias_cmds):
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


def test_init_binding(alias_db):
    result = alias_db.get_alias("hello")
    assert result == "hello: Hej!"


def test_db_addalias(alias_db):
    result = alias_db.add_alias("testdb", "datamaskin")
    assert result == '"testdb" added. value is: "datamaskin"'


def test_alias_create(alias_cmds):
    result = alias_cmds.add_alias("testalias", "testtest")
    assert result == '"testalias" added. value is: "testtest"'


def test_binding_exists(populated_alias_cmds):
    result = populated_alias_cmds.binding_exists("testalias")
    assert result


def test_exec_alias(commands, populated_alias_cmds):
    context = new_context(commands, command_name="testalias")
    result = populated_alias_cmds.exec_alias(context)
    assert result == "testtest"


def test_db_getalias(populated_alias_db):
    result = populated_alias_db.get_alias("testdb")
    assert result == "testdb: datamaskin"


def test_db_listalias(populated_alias_db):
    result = populated_alias_db.list_alias("%")
    assert result == "hello testalias testdb"


def test_db_randomalias(populated_alias_db):
    result = populated_alias_db.random_alias("%")
    assert result in ["hello", "testdb", "testalias"]


def test_db_delalias(populated_alias_db):
    res1 = populated_alias_db.del_alias("hello")
    res2 = populated_alias_db.get_alias("hello")
    assert res1 == "Alias removed" and res2 in ["Nej", "https://i.imgur.com/6cpffM4.jpeg"]


def test_delalias(populated_alias_cmds):
    result = populated_alias_cmds.del_alias("testalias")
    assert result == "Alias removed"


def test_invalid_delete(alias_cmds):
    result = alias_cmds.del_alias("get-alias")
    assert result == "Det blir inget med det."


def test_invalid_add(alias_cmds):
    result = alias_cmds.add_alias("get-alias", "hehu jag är smart")
    assert result == "Hallå farfar, den finns ju redan."


def test_invalid_add_other_group(alias_cmds):
    result = alias_cmds.add_alias("echo", "hehu jag är smart")
    assert result == "Hallå farfar, den finns ju redan."
