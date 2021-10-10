from base64 import b32encode
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
import secrets
import sqlite3

from .types import Token


SECRET_BYTE_COUNT = 10


class TokenDb(ExitStack):
    def __init__(self, db_file_path):
        super().__init__()
        self._db = sqlite3.connect(db_file_path, check_same_thread=False)
        self.callback(self._db.close)
        self._setup()

    @contextmanager
    def _transaction(self):
        with self._db:
            yield self._db.cursor()

    def _setup(self):
        with self._transaction() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    name TEXT UNIQUE,
                    secret TEXT UNIQUE,
                    used INTEGER,
                    use_count INTEGER,
                    created INTEGER,
                    creator_network TEXT,
                    creator_user TEXT
                );
            """)

    def _generate_secret(self):
        secret_bytes = secrets.token_bytes(SECRET_BYTE_COUNT)
        return b32encode(secret_bytes).decode("ascii")

    def create_token(self, token_name, creator_network, creator_user):
        secret = self._generate_secret()
        now = int(datetime.now(timezone.utc).timestamp())
        with self._transaction() as c:
            c.execute("SELECT name FROM tokens WHERE name = ?;", (token_name,))
            row = c.fetchone()
            if row:
                return None
            c.execute("""
                INSERT INTO tokens (name, secret, used, use_count, created, creator_network, creator_user)
                VALUES (?, ?, ?, 0, ?, ?, ?);
            """, (token_name, secret, now, now, creator_network, creator_user))
            return secret

    def get_token(self, token_name):
        with self._transaction() as c:
            c.execute("""
                SELECT name, used, use_count, created, creator_network, creator_user
                FROM tokens
                WHERE name = ?
            """, (token_name,))
            row = c.fetchone()
            if row:
                return Token(*row)
            else:
                return None

    def list_tokens(self):
        with self._transaction() as c:
            c.execute("SELECT name FROM tokens;")
            return [row[0] for row in c.fetchall()]

    def delete_token(self, token_name):
        with self._transaction() as c:
            c.execute("SELECT name FROM tokens WHERE name = ?;", (token_name,))
            row = c.fetchone()
            if not row:
                return False
            c.execute("DELETE FROM tokens WHERE name = ?;", (token_name,))
            return True

    def check_token(self, secret):
        with self._transaction() as c:
            c.execute("SELECT name, use_count FROM tokens WHERE secret = :secret;",
                      {"secret": secret})
            row = c.fetchone()
            if not row:
                return None
            name, use_count = row
            now = int(datetime.now(timezone.utc).timestamp())
            c.execute("""
                UPDATE tokens
                SET used = :now, use_count = :use_count
                WHERE secret = :secret;
            """, {"now": now, "use_count": use_count, "secret": secret})
            return name
