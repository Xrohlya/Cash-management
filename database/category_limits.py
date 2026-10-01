from database.db import get_connection
from database.users import ensure_user
from services.categories import normalize_expense_category


def list_category_limits(user_id):
    with get_connection() as conn:
        return [dict(row) for row in conn.execute("SELECT category,amount FROM category_limits WHERE user_id=? ORDER BY category", (user_id,)).fetchall()]


def save_category_limit(user_id, category, amount):
    ensure_user(user_id)
    category = normalize_expense_category(category)
    if not 0 < amount <= 1_000_000_000:
        raise ValueError("Лимит должен быть больше нуля")
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO category_limits(user_id,category,amount) VALUES (?,?,?) "
            "ON CONFLICT (user_id,category) DO UPDATE SET amount=excluded.amount",
            (user_id, category, round(amount, 2)),
        )


def delete_category_limit(user_id, category):
    with get_connection() as conn:
        conn.execute("DELETE FROM category_limits WHERE user_id=? AND category=?", (user_id, normalize_expense_category(category)))
