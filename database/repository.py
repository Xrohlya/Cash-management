from datetime import date, datetime, timedelta

from config.settings import DEFAULT_MANDATORY_PERCENT
from database.db import get_connection


FINANCIAL_DAY = 20

CATEGORY_ALIASES = {
    "еда": "Еда",
    "продукты": "Еда",
    "продукты питания": "Еда",
    "кафе": "Кафе",
    "кофейня": "Кафе",
    "сигареты": "Сигареты",
    "сигарета": "Сигареты",
    "сиги": "Сигареты",
    "бензин": "Бензин",
    "топливо": "Бензин",
    "заправка": "Бензин",
    "такси": "Такси",
    "магазин": "Магазин",
}


def normalize_expense_category(description: str) -> str:
    value = " ".join((description or "").strip().split())
    if not value:
        return "Расход"
    key = value.casefold()
    if key in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[key]
    keyword_categories = {
        "Еда": ("пятероч", "перекрест", "магнит", "лента", "ашан", "вкусвилл", "дикси", "продукт"),
        "Кафе": ("кафе", "ресторан", "бар", "столов", "кофейн", "доставка еды"),
        "Бензин": ("бензин", "топливо", "заправ", "азс", "газпромнефть", "лукойл", "роснефть"),
        "Такси": ("такси", "яндекс го", "uber", "ситимобил"),
        "Сигареты": ("сигарет", "табак", "вейп", "vape"),
    }
    for category, keywords in keyword_categories.items():
        if any(keyword in key for keyword in keywords):
            return category
    return value[:1].upper() + value[1:]


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


def get_percent(user_id: int) -> float:
    ensure_user(user_id)
    with get_connection() as conn:
        row = conn.execute("SELECT mandatory_percent FROM users WHERE user_id=?", (user_id,)).fetchone()
        return float(row["mandatory_percent"])


def set_percent(user_id: int, percent: float):
    ensure_user(user_id)
    with get_connection() as conn:
        conn.execute("UPDATE users SET mandatory_percent=? WHERE user_id=?", (percent, user_id))


def get_savings(user_id: int) -> float:
    ensure_user(user_id)
    with get_connection() as conn:
        row = conn.execute("SELECT savings FROM users WHERE user_id=?", (user_id,)).fetchone()
        return float(row["savings"])


def financial_period_start(dt=None) -> date:
    dt = dt or datetime.now()
    if dt.day >= FINANCIAL_DAY:
        return date(dt.year, dt.month, FINANCIAL_DAY)
    if dt.month == 1:
        return date(dt.year - 1, 12, FINANCIAL_DAY)
    return date(dt.year, dt.month - 1, FINANCIAL_DAY)


def financial_period_end(dt=None) -> date:
    start = financial_period_start(dt)
    if start.month == 12:
        return date(start.year + 1, 1, FINANCIAL_DAY)
    return date(start.year, start.month + 1, FINANCIAL_DAY)


def month_key(dt=None):
    return financial_period_start(dt).isoformat()


def ensure_month(user_id: int, key=None):
    key = key or month_key()
    ensure_user(user_id)
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO months(user_id, month) VALUES (?, ?)", (user_id, key))


def get_month(user_id: int, key=None):
    key = key or month_key()
    ensure_month(user_id, key)
    with get_connection() as conn:
        return conn.execute("SELECT * FROM months WHERE user_id=? AND month=?", (user_id, key)).fetchone()


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
    fee = round(gross * percent / 100, 2)
    net = round(gross - fee, 2)
    key = month_key()
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        if not _claim_request(conn, user_id, request_id):
            return fee, net, False
        conn.execute(
            "INSERT INTO transactions(user_id, created_at, kind, amount, description) VALUES (?, ?, 'income', ?, ?)",
            (user_id, now, gross, description),
        )
        conn.execute(
            "INSERT INTO transactions(user_id, created_at, kind, amount, description) VALUES (?, ?, 'mandatory', ?, ?)",
            (user_id, now, fee, f"Обязательный вычет {percent:g}%"),
        )
        conn.execute("UPDATE months SET budget=budget+? WHERE user_id=? AND month=?", (net, user_id, key))
    return fee, net, True


def _add_budget_reduction(user_id, kind, column, amount, description, request_id=None, created_at=None):
    key = month_key(created_at)
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


def add_rent(user_id: int, amount: float, description="Квартира", request_id=None):
    return _add_budget_reduction(user_id, "rent", "rent", amount, description, request_id)


def add_to_savings(user_id: int, amount: float, description="Накопления", request_id=None):
    return _add_budget_reduction(user_id, "save", "saved", amount, description, request_id)


def add_bulk_expenses(user_id: int, items: list[tuple[float, str]], request_id=None) -> bool:
    key = month_key()
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


def daily_expenses(user_id: int, day=None) -> float:
    day = day or date.today()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions "
            "WHERE user_id=? AND kind='expense' AND created_at>=? AND created_at<?",
            (user_id, day.isoformat(), (day + timedelta(days=1)).isoformat()),
        ).fetchone()
        return float(row["total"] or 0)


def daily_expense_transactions(user_id: int, day=None):
    day = day or date.today()
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM transactions WHERE user_id=? AND kind='expense' "
            "AND created_at>=? AND created_at<? ORDER BY id DESC",
            (user_id, day.isoformat(), (day + timedelta(days=1)).isoformat()),
        ).fetchall()


def average_daily_expense(user_id: int, day=None) -> float:
    day = day or date.today()
    start = financial_period_start(day)
    days_elapsed = (day - start).days + 1
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions "
            "WHERE user_id=? AND kind='expense' AND created_at>=? AND created_at<?",
            (user_id, start.isoformat(), (day + timedelta(days=1)).isoformat()),
        ).fetchone()
    return float(row["total"] or 0) / max(1, days_elapsed)


def recent_transactions(user_id: int, limit=15):
    safe_limit = max(1, min(int(limit), 100))
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, created_at, kind, amount, description FROM transactions "
            "WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, safe_limit),
        ).fetchall()
