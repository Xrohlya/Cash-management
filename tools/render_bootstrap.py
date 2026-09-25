import base64
import json
import os

from database.db import get_connection


def migrate_from_environment() -> dict[str, int] | None:
    encoded = os.getenv("RENDER_MIGRATION_SNAPSHOT", "").strip()
    if not encoded:
        return None

    payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
    counts = {name: len(payload.get(name, [])) for name in ("users", "months", "transactions", "goals")}

    with get_connection() as conn:
        for row in payload.get("users", []):
            conn.execute(
                """
                INSERT INTO users(
                    user_id, mandatory_percent, savings, status_chat_id,
                    status_message_id, first_name, username
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
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
                    row.get("status_chat_id"), row.get("status_message_id"),
                    row.get("first_name", ""), row.get("username", ""),
                ),
            )

        for row in payload.get("months", []):
            conn.execute(
                """
                INSERT INTO months(user_id, month, budget, spent, rent, saved)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, month) DO UPDATE SET
                    budget=EXCLUDED.budget, spent=EXCLUDED.spent,
                    rent=EXCLUDED.rent, saved=EXCLUDED.saved
                """,
                (row["user_id"], row["month"], row["budget"], row["spent"], row["rent"], row["saved"]),
            )

        for row in payload.get("transactions", []):
            conn.execute(
                """
                INSERT INTO transactions(id, user_id, created_at, kind, amount, description)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (
                    row["id"], row["user_id"], row["created_at"],
                    row["kind"], row["amount"], row["description"],
                ),
            )

        for row in payload.get("goals", []):
            conn.execute(
                """
                INSERT INTO goals(user_id, target, target_date) VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    target=EXCLUDED.target, target_date=EXCLUDED.target_date
                """,
                (row["user_id"], row["target"], row["target_date"]),
            )

        conn.execute(
            "SELECT setval(pg_get_serial_sequence('transactions', 'id'), "
            "GREATEST(COALESCE((SELECT MAX(id) FROM transactions), 1), 1), true)"
        )

    print("Render migration completed:", counts)
    return counts
