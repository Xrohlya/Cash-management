import re
import sqlite3

from config.settings import DATABASE_URL, DB_POOL_MAX, SQLITE_PATH


_PG_POOL = None


class _PGConnection:
    CONFLICT_KEYS = {
        "users": "user_id",
        "months": "user_id, month",
        "operation_requests": "user_id, request_id",
        "goals": "user_id",
    }

    def __init__(self, conn, release=None):
        self._conn = conn
        self._release = release

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self._conn.rollback()
        else:
            self._conn.commit()
        if self._release:
            self._release(self._conn)
        else:
            self._conn.close()

    def execute(self, sql, params=()):
        from psycopg.rows import dict_row

        match = re.search(r"INSERT OR IGNORE INTO\s+(\w+)", sql, flags=re.I)
        if match:
            table = match.group(1).lower()
            sql = re.sub(r"INSERT OR IGNORE", "INSERT", sql, count=1, flags=re.I)
            keys = self.CONFLICT_KEYS.get(table)
            if keys:
                sql += f" ON CONFLICT ({keys}) DO NOTHING"
        sql = sql.replace("?", "%s")
        cur = self._conn.cursor(row_factory=dict_row)
        cur.execute(sql, params)
        return cur


class _SQLiteConnection:
    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self._conn.rollback()
        else:
            self._conn.commit()
        self._conn.close()

    def execute(self, sql, params=()):
        return self._conn.execute(sql, params)

    def executescript(self, sql):
        return self._conn.executescript(sql)


def get_connection():
    if DATABASE_URL:
        global _PG_POOL
        if _PG_POOL is None:
            from psycopg_pool import ConnectionPool

            _PG_POOL = ConnectionPool(
                conninfo=DATABASE_URL,
                min_size=1,
                max_size=max(2, DB_POOL_MAX),
                open=True,
            )
        return _PGConnection(_PG_POOL.getconn(), release=_PG_POOL.putconn)

    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return _SQLiteConnection(conn)


def _create_schema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            mandatory_percent DOUBLE PRECISION NOT NULL DEFAULT 6.0,
            financial_day INTEGER NOT NULL DEFAULT 20,
            savings DOUBLE PRECISION NOT NULL DEFAULT 0,
            status_chat_id BIGINT,
            status_message_id BIGINT,
            first_name TEXT NOT NULL DEFAULT '',
            username TEXT NOT NULL DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS months (
            user_id BIGINT NOT NULL,
            month TEXT NOT NULL,
            budget DOUBLE PRECISION NOT NULL DEFAULT 0,
            spent DOUBLE PRECISION NOT NULL DEFAULT 0,
            rent DOUBLE PRECISION NOT NULL DEFAULT 0,
            saved DOUBLE PRECISION NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, month)
        )
    """)
    id_type = "BIGSERIAL" if DATABASE_URL else "INTEGER"
    id_suffix = "" if DATABASE_URL else " AUTOINCREMENT"
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS transactions (
            id {id_type} PRIMARY KEY{id_suffix},
            user_id BIGINT NOT NULL,
            created_at TEXT NOT NULL,
            kind TEXT NOT NULL,
            amount DOUBLE PRECISION NOT NULL,
            description TEXT NOT NULL DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            user_id BIGINT PRIMARY KEY,
            target DOUBLE PRECISION NOT NULL,
            target_date TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS operation_requests (
            user_id BIGINT NOT NULL,
            request_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (user_id, request_id)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_transactions_user_created "
        "ON transactions(user_id, created_at DESC)"
    )


def init_db():
    with get_connection() as conn:
        if not DATABASE_URL:
            conn.execute("PRAGMA journal_mode=WAL")
        _create_schema(conn)
        if DATABASE_URL:
            conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name TEXT NOT NULL DEFAULT ''")
            conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS username TEXT NOT NULL DEFAULT ''")
            conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS financial_day INTEGER NOT NULL DEFAULT 20")
            return

        month_columns = {row["name"] for row in conn.execute("PRAGMA table_info(months)")}
        if "rent" not in month_columns:
            conn.execute("ALTER TABLE months ADD COLUMN rent REAL NOT NULL DEFAULT 0")
        if "saved" not in month_columns:
            conn.execute("ALTER TABLE months ADD COLUMN saved REAL NOT NULL DEFAULT 0")

        user_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
        migrations = {
            "status_chat_id": "ALTER TABLE users ADD COLUMN status_chat_id INTEGER",
            "status_message_id": "ALTER TABLE users ADD COLUMN status_message_id INTEGER",
            "first_name": "ALTER TABLE users ADD COLUMN first_name TEXT NOT NULL DEFAULT ''",
            "username": "ALTER TABLE users ADD COLUMN username TEXT NOT NULL DEFAULT ''",
            "financial_day": "ALTER TABLE users ADD COLUMN financial_day INTEGER NOT NULL DEFAULT 20",
        }
        for column, statement in migrations.items():
            if column not in user_columns:
                conn.execute(statement)
