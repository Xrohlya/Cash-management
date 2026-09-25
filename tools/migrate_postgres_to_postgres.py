import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import psycopg
from psycopg.rows import dict_row

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import DATABASE_URL


TABLES = {
    "users": (
        "user_id, mandatory_percent, financial_day, savings, status_chat_id, status_message_id, first_name, username",
        "user_id",
        """
        mandatory_percent=EXCLUDED.mandatory_percent,
        financial_day=EXCLUDED.financial_day,
        savings=EXCLUDED.savings,
        status_chat_id=EXCLUDED.status_chat_id,
        status_message_id=EXCLUDED.status_message_id,
        first_name=EXCLUDED.first_name,
        username=EXCLUDED.username
        """,
    ),
    "months": (
        "user_id, month, budget, spent, rent, saved",
        "user_id, month",
        """
        budget=EXCLUDED.budget,
        spent=EXCLUDED.spent,
        rent=EXCLUDED.rent,
        saved=EXCLUDED.saved
        """,
    ),
    "transactions": (
        "id, user_id, created_at, kind, amount, description",
        "id",
        """
        user_id=EXCLUDED.user_id,
        created_at=EXCLUDED.created_at,
        kind=EXCLUDED.kind,
        amount=EXCLUDED.amount,
        description=EXCLUDED.description
        """,
    ),
    "goals": (
        "user_id, target, target_date",
        "user_id",
        "target=EXCLUDED.target, target_date=EXCLUDED.target_date",
    ),
    "operation_requests": (
        "user_id, request_id, created_at",
        "user_id, request_id",
        "created_at=EXCLUDED.created_at",
    ),
}


def require_sslmode(url: str) -> str:
    parts = urlsplit(url.strip())
    if not parts.scheme.startswith("postgres"):
        raise SystemExit("Aiven DATABASE_URL должен начинаться с postgresql:// или postgres://")
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.setdefault("sslmode", "require")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def connect(url: str):
    return psycopg.connect(require_sslmode(url), row_factory=dict_row, connect_timeout=20)


def create_schema(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
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
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS months (
                user_id BIGINT NOT NULL,
                month TEXT NOT NULL,
                budget DOUBLE PRECISION NOT NULL DEFAULT 0,
                spent DOUBLE PRECISION NOT NULL DEFAULT 0,
                rent DOUBLE PRECISION NOT NULL DEFAULT 0,
                saved DOUBLE PRECISION NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, month)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                created_at TEXT NOT NULL,
                kind TEXT NOT NULL,
                amount DOUBLE PRECISION NOT NULL,
                description TEXT NOT NULL DEFAULT ''
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS goals (
                user_id BIGINT PRIMARY KEY,
                target DOUBLE PRECISION NOT NULL,
                target_date TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS operation_requests (
                user_id BIGINT NOT NULL,
                request_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (user_id, request_id)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_transactions_user_created "
            "ON transactions(user_id, created_at DESC)"
        )
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name TEXT NOT NULL DEFAULT ''")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS username TEXT NOT NULL DEFAULT ''")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS financial_day INTEGER NOT NULL DEFAULT 20")
    conn.commit()


def read_rows(conn):
    data = {}
    with conn.cursor() as cur:
        for table, (columns, _conflict, _updates) in TABLES.items():
            cur.execute(f"SELECT {columns} FROM {table} ORDER BY 1")
            data[table] = [dict(row) for row in cur.fetchall()]
    return data


def backup_to_file(data):
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    path = backup_dir / f"postgres_backup_{datetime.now():%Y%m%d_%H%M%S}.json"
    payload = {"created_at": datetime.now().isoformat(timespec="seconds"), "tables": data}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def insert_rows(conn, data):
    counts = {}
    with conn.cursor() as cur:
        for table, rows in data.items():
            columns, conflict, updates = TABLES[table]
            names = [name.strip() for name in columns.split(",")]
            placeholders = ", ".join(["%s"] * len(names))
            sql = (
                f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) "
                f"ON CONFLICT ({conflict}) DO UPDATE SET {updates}"
            )
            for row in rows:
                cur.execute(sql, tuple(row[name] for name in names))
            counts[table] = len(rows)
        cur.execute(
            "SELECT setval(pg_get_serial_sequence('transactions', 'id'), "
            "GREATEST(COALESCE((SELECT MAX(id) FROM transactions), 1), 1), true)"
        )
    conn.commit()
    return counts


def count_rows(conn):
    with conn.cursor() as cur:
        return {
            table: cur.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"]
            for table in TABLES
        }


def migrate(target_url: str):
    if not DATABASE_URL:
        raise SystemExit("В .env нет текущего DATABASE_URL Render.")
    if not target_url:
        raise SystemExit("Передайте Aiven DATABASE_URL первым аргументом.")
    if target_url.strip() == DATABASE_URL.strip():
        raise SystemExit("Aiven DATABASE_URL совпадает с текущим Render DATABASE_URL.")

    with connect(DATABASE_URL) as source:
        data = read_rows(source)

    backup_path = backup_to_file(data)

    with connect(target_url) as target:
        create_schema(target)
        before = count_rows(target)
        counts = insert_rows(target, data)
        after = count_rows(target)

    print(f"Локальный backup создан: {backup_path}")
    print("Перенесено:", ", ".join(f"{table}={count}" for table, count in counts.items()))
    print("Было в Aiven:", ", ".join(f"{table}={count}" for table, count in before.items()))
    print("Стало в Aiven:", ", ".join(f"{table}={count}" for table, count in after.items()))


if __name__ == "__main__":
    migrate(sys.argv[1] if len(sys.argv) > 1 else "")
