import json
import argparse
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import psycopg
from psycopg.rows import dict_row

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import DATABASE_URL


TABLES = {
    "telegram_sync": "*",
    "period_openings": "*",
    "wallet_entries": "*",
    "pet_selection": "*",
    "pet_layout": "*",
    "pet_album": "*",
    "pet_minigame": "*",
    "pet_appearance": "*",
    "pet_item_upgrades": "*",
    "pet_daily_budget": "*",
    "pet_world": "*",
    "pet_rewards": "*",
    "pet_inventory": "*",
    "users": "*",
    "months": "user_id, month, budget, spent, rent, saved",
    "transactions": "id, user_id, created_at, kind, amount, description, income_source_id",
    "goals": "user_id, target, target_date",
    "operation_requests": "user_id, request_id, created_at",
    "recurring_payments": "id, user_id, title, amount, kind, day_of_month, active, last_run, last_notified",
    "income_sources": "id, user_id, name, withholding_percent, active",
    "extra_accounts": "id, user_id, name, balance, active",
    "account_transactions": "id, account_id, user_id, created_at, kind, amount",
    "expected_income": "*",
    "category_limits": "*",
    "operation_undo": "*",
}


def require_sslmode(url: str) -> str:
    parts = urlsplit(url.strip())
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.setdefault("sslmode", "require")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def main():
    parser = argparse.ArgumentParser(description="Create and verify a read-only PostgreSQL backup")
    parser.add_argument("--output-dir", type=Path, default=Path("backups"))
    args = parser.parse_args()
    if not DATABASE_URL:
        raise SystemExit("В .env нет DATABASE_URL.")

    data = {}
    with psycopg.connect(require_sslmode(DATABASE_URL), row_factory=dict_row, connect_timeout=20,
                         options="-c statement_timeout=60000 -c idle_in_transaction_session_timeout=60000") as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            cur.execute("SET TRANSACTION READ ONLY")
            for table, columns in TABLES.items():
                cur.execute("SELECT to_regclass(%s) present", (table,))
                if cur.fetchone()["present"] is None:
                    continue
                cur.execute(f"SELECT {columns} FROM {table} ORDER BY 1")
                data[table] = [dict(row) for row in cur.fetchall()]

    backup_dir = args.output_dir
    backup_dir.mkdir(parents=True, exist_ok=True)
    path = backup_dir / f"postgres_backup_{datetime.now():%Y%m%d_%H%M%S}.json"
    payload = {"created_at": datetime.now().isoformat(timespec="seconds"), "tables": data}
    from tools.verify_backup import verify_backup
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=backup_dir,
                                         prefix=".pending-backup-", delete=False) as stream:
            temporary_path = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        verification = verify_backup(temporary_path)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    backups = sorted(backup_dir.glob("postgres_backup_*.json"), reverse=True)
    for old_backup in backups[30:]:
        old_backup.unlink()
    print(f"Backup создан: {path}")
    print("Проверено восстановление строк в отдельной SQLite-базе; рабочая база не изменялась.")
    print(f"Сверка: {verification['audit']['checked']} проверок, расхождений: {len(verification['audit']['findings'])}.")
    print(", ".join(f"{table}={len(rows)}" for table, rows in data.items()))


if __name__ == "__main__":
    main()
