import os
from _pytest.monkeypatch import MonkeyPatch
from pladder.alias import AliasDb, AliasPlugin
from pladder.bot import PladderBot


context = {'datetime': "",
'network': "pytestnet",
'channel': "pytest",
'nick': "pytest",
'command': "testalias",
'text': "testalias"}


class mockbot():
    def __init__(self):
        self.state_dir = ":memory:"
        self.bindings = []
    register_command = PladderBot.register_command


class aliasplugin():
    def __init__(self):
        self.monkeypatch = MonkeyPatch()
        self.db = AliasDb(":memory:")
        self.monkeypatch.setattr(AliasPlugin, "enter_context", self.mockdb)
        self.monkeypatch.setattr(os.path, "join", self.mockdbpath)
        self.aliasplugin = AliasPlugin(mockbot())

    def mockdb(self, _):
        return self.db
    def mockdbpath(self, *_):
        return ":memory:"

aliasplugin = aliasplugin().aliasplugin
db = aliasplugin.alias_db

def test_help():
    result = aliasplugin.help()
    assert result == "Functions: get-alias [name], del-alias [name], add-alias [name] [content], list-alias *[name]*, random-alias *[name]*. Wildcards are % and _. Use {} when adding PladderScript to database."

def test_init_binding():
    result = db.get_alias("hello")
    assert result == "hello: Hej!"

def test_db_addalias():
    result = db.add_alias("testdb", "datamaskin")
    assert result == '"testdb" added'

def test_alias_create():
    result = aliasplugin.add_alias("testalias testtest")
    assert result == '"testalias" added'

def test_binding_exists():
    result = aliasplugin.binding_exists("testalias")
    assert result

def test_exec_alias():
    result = aliasplugin.exec_alias(context)
    assert result == "testtest"

def test_db_getalias():
    result = db.get_alias("testdb")
    assert result == "testdb: datamaskin"

def test_db_listalias():
    result = db.list_alias("%")
    assert result == "hello testalias testdb"

def test_db_randomalias():
    result = db.random_alias("%")
    assert result == "hello" or "testdb"

def test_db_delalias():
    res1 = db.del_alias("hello")
    res2 = db.get_alias("hello")
    assert res1 == "Alias removed" and res2 == "Nej"

def test_delalias():
    result = aliasplugin.del_alias("testalias")
    assert result == "Alias removed"

def test_invalid_delete():
    result = aliasplugin.del_alias("get-alias")
    assert result == "Det blir inget med det."

def test_invalid_add():
    result = aliasplugin.add_alias("get-alias hehu jag är smart")
    assert result == "Hallå farfar, den finns ju redan."