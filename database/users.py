import logging
from config.settings import DEFAULT_MANDATORY_PERCENT
from database.db import get_connection


def ensure_user(user_id: int, first_name: str = "", username: str = ""):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users(user_id, mandatory_percent) VALUES (?, ?)",
            (user_id, DEFAULT_MANDATORY_PERCENT),
        )
        if first_name or username:
            conn.execute(
                "UPDATE users SET first_name=?, username=? WHERE user_id=?",
                (first_name[:255], username[:255], user_id),
            )


def get_user_profile(user_id: int):
    ensure_user(user_id)
    with get_connection() as conn:
        return conn.execute(
            "SELECT first_name,username FROM users WHERE user_id=?", (user_id,)
        ).fetchone()


def list_user_summaries():
    from database.snapshot import get_status_snapshot

    with get_connection() as conn:
        users = conn.execute(
            "SELECT user_id,first_name,username FROM users ORDER BY user_id"
        ).fetchall()
    summaries = []
    for user in users:
        try:
            balance = get_status_snapshot(int(user["user_id"]))["remaining"]
        except Exception:
            logging.exception("Could not load startup balance for user %s", user["user_id"])
            balance = None
        summaries.append({
            "user_id": int(user["user_id"]),
            "first_name": user["first_name"] or "",
            "username": user["username"] or "",
            "balance": balance,
        })
    return summaries


def get_savings(user_id: int) -> float:
    ensure_user(user_id)
    with get_connection() as conn:
        row = conn.execute("SELECT savings FROM users WHERE user_id=?", (user_id,)).fetchone()
        return float(row["savings"])


def set_target_balance(user_id: int, amount: float):
    if amount < 0 or amount > 1_000_000_000:
        raise ValueError("Желаемый остаток должен быть от 0 до 1 000 000 000.")
    ensure_user(user_id)
    with get_connection() as conn:
        conn.execute("UPDATE users SET target_balance=? WHERE user_id=?", (round(amount, 2), user_id))


def get_status_message(user_id: int):
    ensure_user(user_id)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT status_chat_id, status_message_id FROM users WHERE user_id=?",
            (user_id,),
        ).fetchone()
        if not row or row["status_chat_id"] is None or row["status_message_id"] is None:
            return None
        return int(row["status_chat_id"]), int(row["status_message_id"])


def set_status_message(user_id: int, chat_id: int, message_id: int):
    ensure_user(user_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET status_chat_id=?, status_message_id=? WHERE user_id=?",
            (chat_id, message_id, user_id),
        )


def clear_status_message(user_id: int):
    ensure_user(user_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET status_chat_id=NULL, status_message_id=NULL WHERE user_id=?",
            (user_id,),
        )


def reset_user_data(user_id: int):
    with get_connection() as conn:
        for table in ("pet_inventory", "pet_rewards", "pet_world"):
            conn.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM expected_income WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM category_limits WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM operation_undo WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM account_transactions WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM extra_accounts WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM income_sources WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM recurring_payments WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM goals WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM operation_requests WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM transactions WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM months WHERE user_id=?", (user_id,))
        conn.execute(
            "UPDATE users SET mandatory_percent=0,target_balance=0,savings=0,status_chat_id=NULL,status_message_id=NULL WHERE user_id=?",
            (user_id,),
        )
