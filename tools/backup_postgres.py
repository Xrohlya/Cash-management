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
    "users": "user_id, mandatory_percent, financial_day, savings, status_chat_id, status_message_id, first_name, username",
    "months": "user_id, month, budget, spent, rent, saved",
    "transactions": "id, user_id, created_at, kind, amount, description",
    "goals": "user_id, target, target_date",
    "operation_requests": "user_id, request_id, created_at",
}


def require_sslmode(url: str) -> str:
    parts = urlsplit(url.strip())
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.setdefault("sslmode", "require")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def main():
    if not DATABASE_URL:
        raise SystemExit("В .env нет DATABASE_URL.")

    data = {}
    with psycopg.connect(require_sslmode(DATABASE_URL), row_factory=dict_row, connect_timeout=20) as conn:
        with conn.cursor() as cur:
            for table, columns in TABLES.items():
                cur.execute(f"SELECT {columns} FROM {table} ORDER BY 1")
                data[table] = [dict(row) for row in cur.fetchall()]

    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    path = backup_dir / f"postgres_backup_{datetime.now():%Y%m%d_%H%M%S}.json"
    payload = {"created_at": datetime.now().isoformat(timespec="seconds"), "tables": data}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Backup создан: {path}")
    print(", ".join(f"{table}={len(rows)}" for table, rows in data.items()))


if __name__ == "__main__":
    main()
