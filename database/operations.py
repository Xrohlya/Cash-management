from services.categories import normalize_expense_category
from datetime import datetime
from database.db import get_connection
from database.periods import ensure_month, financial_period_start, get_month, month_key, rebuild_month_from_transactions


def _claim_request(conn, user_id: int, request_id: str | None) -> bool:
    if not request_id:
        return True
    cursor = conn.execute(
        "INSERT OR IGNORE INTO operation_requests(user_id, request_id, created_at) VALUES (?, ?, ?)",
        (user_id, request_id[:100], datetime.now().isoformat(timespec="seconds")),
    )
    return cursor.rowcount == 1


def add_income(user_id: int, gross: float, percent: float, description="Доход", request_id=None):
    ensure_month(user_id)
    fee = 0.0
    net = round(gross, 2)
    key = month_key(user_id)
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        if not _claim_request(conn, user_id, request_id):
            return fee, net, False
        conn.execute(
            "INSERT INTO transactions(user_id, created_at, kind, amount, description) VALUES (?, ?, 'income', ?, ?)",
            (user_id, now, gross, description),
        )
        conn.execute("UPDATE months SET budget=budget+? WHERE user_id=? AND month=?", (net, user_id, key))
    return fee, net, True


def _add_budget_reduction(user_id, kind, column, amount, description, request_id=None, created_at=None):
    key = month_key(user_id, created_at)
    ensure_month(user_id, key)
    timestamp = (created_at or datetime.now()).isoformat(timespec="seconds")
    with get_connection() as conn:
        if not _claim_request(conn, user_id, request_id):
            return True
        cursor = conn.execute(
            f"UPDATE months SET {column}={column}+? "
            "WHERE user_id=? AND month=? AND (budget-spent-rent-saved)>=?",
            (amount, user_id, key, amount),
        )
        if cursor.rowcount != 1:
            if request_id:
                conn.execute(
                    "DELETE FROM operation_requests WHERE user_id=? AND request_id=?",
                    (user_id, request_id[:100]),
                )
            return False
        conn.execute(
            "INSERT INTO transactions(user_id, created_at, kind, amount, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, timestamp, kind, amount, description),
        )
        if kind == "save":
            conn.execute("UPDATE users SET savings=savings+? WHERE user_id=?", (amount, user_id))
    return True


def add_expense(user_id: int, amount: float, description: str, request_id=None, created_at=None):
    return _add_budget_reduction(
        user_id,
        "expense",
        "spent",
        amount,
        normalize_expense_category(description),
        request_id,
        created_at,
    )


def add_recurring_charge(user_id: int, amount: float, description: str, request_id=None):
    return _add_budget_reduction(
        user_id, "recurring", "spent", amount, description, request_id
    )


def add_rent(user_id: int, amount: float, description="Квартира", request_id=None):
    return _add_budget_reduction(user_id, "rent", "rent", amount, description, request_id)


def add_to_savings(user_id: int, amount: float, description="Накопления", request_id=None):
    return _add_budget_reduction(user_id, "save", "saved", amount, description, request_id)


def add_bulk_expenses(user_id: int, items: list[tuple[float, str]], request_id=None) -> bool:
    key = month_key(user_id)
    ensure_month(user_id, key)
    total = round(sum(amount for amount, _ in items), 2)
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        if not _claim_request(conn, user_id, request_id):
            return True
        cursor = conn.execute(
            "UPDATE months SET spent=spent+? WHERE user_id=? AND month=? "
            "AND (budget-spent-rent-saved)>=?",
            (total, user_id, key, total),
        )
        if cursor.rowcount != 1:
            if request_id:
                conn.execute(
                    "DELETE FROM operation_requests WHERE user_id=? AND request_id=?",
                    (user_id, request_id[:100]),
                )
            return False
        for amount, description in items:
            conn.execute(
                "INSERT INTO transactions(user_id, created_at, kind, amount, description) VALUES (?, ?, 'expense', ?, ?)",
                (user_id, now, amount, normalize_expense_category(description)),
            )
    return True


def update_expense(user_id: int, transaction_id: int, amount: float, description: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT created_at,amount,kind FROM transactions WHERE id=? AND user_id=?",
            (transaction_id, user_id),
        ).fetchone()
    if not row or row["kind"] != "expense":
        raise ValueError("Можно изменять только обычные расходы")
    created_at = datetime.fromisoformat(row["created_at"])
    key = month_key(user_id, created_at)
    month = get_month(user_id, key)
    increase = round(amount - float(row["amount"]), 2)
    available = float(month["budget"]) - float(month["spent"]) - float(month["rent"]) - float(month["saved"])
    if increase > available:
        raise ValueError("Недостаточно средств для увеличения расхода")
    with get_connection() as conn:
        conn.execute(
            "UPDATE transactions SET amount=?,description=? WHERE id=? AND user_id=? AND kind='expense'",
            (round(amount, 2), normalize_expense_category(description), transaction_id, user_id),
        )
    rebuild_month_from_transactions(user_id, financial_period_start(user_id, created_at))
