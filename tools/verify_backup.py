"""Restore a JSON backup into disposable SQLite, never into the working database."""
import argparse
from collections import Counter
from contextlib import closing
from datetime import date
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import db
from services.balance_audit import audit_tables
from tools.backup_postgres import TABLES


def verify_backup(path, today=None):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    tables = payload["tables"]
    if not {"users", "months", "transactions"} <= tables.keys():
        raise ValueError("Backup lacks required financial tables")
    if tables.keys() - TABLES.keys():
        raise ValueError("Backup contains unknown tables")
    original_path, original_url = db.SQLITE_PATH, db.DATABASE_URL
    with tempfile.TemporaryDirectory(prefix="cash-backup-check-") as folder:
        target = Path(folder) / "restored.sqlite"
        try:
            db.SQLITE_PATH, db.DATABASE_URL = target, ""
            db.init_db(attempts=1)
        finally:
            db.SQLITE_PATH, db.DATABASE_URL = original_path, original_url
        restored = {}
        with closing(sqlite3.connect(target)) as conn, conn:
            conn.row_factory = sqlite3.Row
            for table, rows in tables.items():
                allowed = {r["name"] for r in conn.execute(f'PRAGMA table_info("{table}")')}
                for row in rows:
                    if not row or row.keys() - allowed:
                        raise ValueError(f"Invalid columns in {table}")
                    columns = ",".join(f'"{column}"' for column in row)
                    placeholders = ",".join("?" for _ in row)
                    conn.execute(f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders})', tuple(row.values()))
                if rows:
                    columns = ",".join(f'"{column}"' for column in rows[0])
                    actual = [dict(r) for r in conn.execute(f'SELECT {columns} FROM "{table}"')]
                else:
                    actual = [dict(r) for r in conn.execute(f'SELECT * FROM "{table}"')]
                freeze = lambda records: Counter(tuple(sorted(row.items())) for row in records)
                if freeze(actual) != freeze(rows):
                    raise ValueError(f"Restored rows differ in {table}")
                restored[table] = actual
            if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("SQLite integrity check failed")
        return {"restore": "verified in disposable SQLite (not a PostgreSQL disaster-recovery test)",
                "tables": {table: len(rows) for table, rows in restored.items()},
                "missing_tables": sorted(TABLES.keys() - tables.keys()),
                "audit": audit_tables(restored, today)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    parser.add_argument("--date", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    print(json.dumps(verify_backup(args.backup, args.date), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
