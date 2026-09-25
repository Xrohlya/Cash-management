import sqlite3
import sys
from pathlib import Path

import psycopg

from config.settings import DATABASE_URL
from database.db import init_db


def table_exists(conn, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def value(row, name, default=None):
    return row[name] if name in row.keys() else default


def migrate(source: Path):
    if not DATABASE_URL:
        raise SystemExit("DATABASE_URL is required")
    if not source.is_file():
        raise SystemExit(f"SQLite database not found: {source}")

    source_uri = f"file:{source.resolve()}?mode=ro"
    sqlite_conn = sqlite3.connect(source_uri, uri=True)
    sqlite_conn.row_factory = sqlite3.Row
    integrity = sqlite_conn.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise SystemExit(f"Source database integrity check failed: {integrity}")

    init_db()
    pg = psycopg.connect(DATABASE_URL)
    counts = {"users": 0, "months": 0, "transactions": 0, "goals": 0}
    try:
        with pg.cursor() as cur:
            for row in sqlite_conn.execute("SELECT * FROM users"):
                cur.execute(
                    """
                    INSERT INTO users(
                        user_id, mandatory_percent, savings, status_chat_id,
                        status_message_id, first_name, username
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(user_id) DO UPDATE SET
                        mandatory_percent=EXCLUDED.mandatory_percent,
                        savings=EXCLUDED.savings,
                        status_chat_id=EXCLUDED.status_chat_id,
                        status_message_id=EXCLUDED.status_message_id,
                        first_name=EXCLUDED.first_name,
                        username=EXCLUDED.username
                    """,
                    (
                        row["user_id"], row["mandatory_percent"], row["savings"],
                        value(row, "status_chat_id"), value(row, "status_message_id"),
                        value(row, "first_name", ""), value(row, "username", ""),
                    ),
                )
                counts["users"] += 1

            for row in sqlite_conn.execute("SELECT * FROM months"):
                cur.execute(
                    """
                    INSERT INTO months(user_id, month, budget, spent, rent, saved)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT(user_id, month) DO UPDATE SET
                        budget=EXCLUDED.budget, spent=EXCLUDED.spent,
                        rent=EXCLUDED.rent, saved=EXCLUDED.saved
                    """,
                    tuple(row),
                )
                counts["months"] += 1

            for row in sqlite_conn.execute(
                "SELECT id, user_id, created_at, kind, amount, description FROM transactions ORDER BY id"
            ):
                cur.execute(
                    """
                    INSERT INTO transactions(id, user_id, created_at, kind, amount, description)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT(id) DO NOTHING
                    """,
                    tuple(row),
                )
                counts["transactions"] += 1

            if table_exists(sqlite_conn, "goals"):
                for row in sqlite_conn.execute("SELECT user_id, target, target_date FROM goals"):
                    cur.execute(
                        """
                        INSERT INTO goals(user_id, target, target_date) VALUES (%s, %s, %s)
                        ON CONFLICT(user_id) DO UPDATE SET
                            target=EXCLUDED.target, target_date=EXCLUDED.target_date
                        """,
                        tuple(row),
                    )
                    counts["goals"] += 1

            cur.execute(
                "SELECT setval(pg_get_serial_sequence('transactions', 'id'), "
                "GREATEST(COALESCE((SELECT MAX(id) FROM transactions), 1), 1), true)"
            )
        pg.commit()
    except Exception:
        pg.rollback()
        raise
    finally:
        sqlite_conn.close()
        pg.close()

    print("Migration completed:", ", ".join(f"{key}={count}" for key, count in counts.items()))


if __name__ == "__main__":
    source_path = Path(sys.argv[1] if len(sys.argv) > 1 else "data/budget.db")
    migrate(source_path)
