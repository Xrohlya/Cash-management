from datetime import datetime
from database.db import get_connection

def list_extra_accounts(user_id: int):
    from database.repository import ensure_user
    ensure_user(user_id)
    with get_connection() as conn:
        return conn.execute(
            "SELECT id,name,balance FROM extra_accounts "
            "WHERE user_id=? AND active=1 ORDER BY id",
            (user_id,),
        ).fetchall()


def create_extra_account(user_id: int, name: str):
    from database.repository import ensure_user
    ensure_user(user_id)
    clean_name = " ".join(name.split())[:80]
    if not clean_name:
        raise ValueError("Введите название счёта")
    with get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) count FROM extra_accounts WHERE user_id=? AND active=1",
            (user_id,),
        ).fetchone()["count"]
        if int(count) >= 3:
            raise ValueError("Можно создать не больше трёх дополнительных счетов")
        if conn.execute(
            "SELECT 1 FROM extra_accounts WHERE user_id=? AND active=1 AND lower(name)=lower(?)",
            (user_id, clean_name),
        ).fetchone():
            raise ValueError("Счёт с таким названием уже существует")
        conn.execute(
            "INSERT INTO extra_accounts(user_id,name,balance) VALUES (?, ?, 0)",
            (user_id, clean_name),
        )


def delete_extra_account(user_id: int, account_id: int):
    with get_connection() as conn:
        account = conn.execute(
            "SELECT balance FROM extra_accounts WHERE id=? AND user_id=? AND active=1",
            (account_id, user_id),
        ).fetchone()
        if not account:
            raise ValueError("Счёт не найден")
        if abs(float(account["balance"])) > 0.005:
            raise ValueError("Сначала верните остаток на основной счёт")
        conn.execute(
            "UPDATE extra_accounts SET active=0 WHERE id=? AND user_id=?",
            (account_id, user_id),
        )


def transfer_extra_account(user_id: int, account_id: int, amount: float, direction: str, request_id=None):
    from database.repository import ensure_month, month_key, _claim_request
    if direction not in {"to_account", "to_main"}:
        raise ValueError("Некорректное направление перевода")
    amount = round(float(amount), 2)
    if amount <= 0:
        raise ValueError("Сумма должна быть больше нуля")
    ensure_month(user_id)
    key = month_key(user_id)
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        account = conn.execute(
            "SELECT name,balance FROM extra_accounts WHERE id=? AND user_id=? AND active=1",
            (account_id, user_id),
        ).fetchone()
        if not account:
            raise ValueError("Счёт не найден")
        if not _claim_request(conn, user_id, request_id):
            return
        if direction == "to_account":
            cursor = conn.execute(
                "UPDATE months SET spent=spent+? WHERE user_id=? AND month=? "
                "AND (budget-spent-rent-saved)>=?",
                (amount, user_id, key, amount),
            )
            if cursor.rowcount != 1:
                if request_id:
                    conn.execute(
                        "DELETE FROM operation_requests WHERE user_id=? AND request_id=?",
                        (user_id, request_id[:100]),
                    )
                raise ValueError("Недостаточно денег на основном счёте")
            conn.execute(
                "UPDATE extra_accounts SET balance=balance+? WHERE id=? AND user_id=?",
                (amount, account_id, user_id),
            )
            global_kind, account_kind = "account_transfer", "in"
            description = f"На счёт «{account['name']}»"
        else:
            cursor = conn.execute(
                "UPDATE extra_accounts SET balance=balance-? "
                "WHERE id=? AND user_id=? AND balance>=?",
                (amount, account_id, user_id, amount),
            )
            if cursor.rowcount != 1:
                if request_id:
                    conn.execute(
                        "DELETE FROM operation_requests WHERE user_id=? AND request_id=?",
                        (user_id, request_id[:100]),
                    )
                raise ValueError("Недостаточно денег на дополнительном счёте")
            conn.execute(
                "UPDATE months SET spent=spent-? WHERE user_id=? AND month=?",
                (amount, user_id, key),
            )
            global_kind, account_kind = "account_return", "out"
            description = f"Со счёта «{account['name']}»"
        conn.execute(
            "INSERT INTO transactions(user_id,created_at,kind,amount,description) VALUES (?, ?, ?, ?, ?)",
            (user_id, now, global_kind, amount, description),
        )
        conn.execute(
            "INSERT INTO account_transactions(account_id,user_id,created_at,kind,amount) VALUES (?, ?, ?, ?, ?)",
            (account_id, user_id, now, account_kind, amount),
        )

