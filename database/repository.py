import re
from calendar import monthrange
from datetime import date, datetime, timedelta

from config.settings import DATABASE_URL, DEFAULT_MANDATORY_PERCENT
from database.db import get_connection


DEFAULT_FINANCIAL_DAY = 20

CATEGORY_ALIASES = {
    "еда": "Еда",
    "продукты": "Еда",
    "продукты питания": "Еда",
    "питание": "Еда",
    "обед": "Еда",
    "ужин": "Еда",
    "завтрак": "Еда",
    "кафе": "Кафе",
    "кофейня": "Кафе",
    "ресторан": "Кафе",
    "доставка": "Кафе",
    "сигареты": "Сигареты",
    "сигарета": "Сигареты",
    "сиги": "Сигареты",
    "бензин": "Бензин",
    "топливо": "Бензин",
    "заправка": "Бензин",
    "такси": "Такси",
    "магазин": "Магазин",
    "аптека": "Здоровье",
    "лекарства": "Здоровье",
    "транспорт": "Транспорт",
    "метро": "Транспорт",
    "подписка": "Подписки",
    "подписки": "Подписки",
    "ai": "Подписки",
    "кредит": "Кредиты",
    "ипотека": "Кредиты",
    "жкх": "Дом и связь",
    "коммуналка": "Дом и связь",
    "интернет": "Дом и связь",
    "телефон": "Дом и связь",
    "одежда": "Одежда",
    "развлечения": "Развлечения",
    "расход": "Разное",
    "разное": "Разное",
    "прочее": "Разное",
}


def normalize_expense_category(description: str) -> str:
    value = " ".join((description or "").strip().split())
    if not value:
        return "Расход"
    value = re.sub(r"^[\W_]+|[\W_]+$", "", value, flags=re.UNICODE).strip()
    if not value:
        return "Разное"
    key = value.casefold()
    if key in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[key]
    tokens = re.findall(r"[a-zа-яё0-9]+", key)
    token_categories = {CATEGORY_ALIASES[token] for token in tokens if token in CATEGORY_ALIASES}
    if tokens and len(token_categories) == 1 and all(token in CATEGORY_ALIASES for token in tokens):
        return token_categories.pop()
    keyword_categories = {
        "Еда": ("пятероч", "перекрест", "магнит", "лента", "ашан", "вкусвилл", "дикси", "продукт"),
        "Кафе": ("кафе", "ресторан", "бар", "столов", "кофейн", "доставка еды"),
        "Бензин": ("бензин", "топливо", "заправ", "азс", "газпромнефть", "лукойл", "роснефть"),
        "Такси": ("такси", "яндекс го", "uber", "ситимобил"),
        "Сигареты": ("сигарет", "табак", "вейп", "vape"),
        "Здоровье": ("аптек", "лекар", "врач", "анализ", "стоматолог"),
        "Транспорт": ("метро", "автобус", "проезд", "транспорт", "электричк"),
        "Подписки": ("подписк", "яндекс плюс", "icloud", "netflix", "spotify", "оплата ai", "openai", "chatgpt"),
        "Кредиты": ("кредит", "ипотек", "рассрочк", "заём", "займ"),
        "Дом и связь": ("жкх", "коммунал", "электричеств", "квартплат", "интернет", "мобильн", "телефон"),
        "Одежда": ("одежд", "обув", "куртк", "футболк", "брюк", "джинс"),
        "Развлечения": ("кино", "театр", "игр", "концерт", "развлеч"),
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


def get_financial_day(user_id: int) -> int:
    ensure_user(user_id)
    with get_connection() as conn:
        row = conn.execute("SELECT financial_day FROM users WHERE user_id=?", (user_id,)).fetchone()
    return int(row["financial_day"] or DEFAULT_FINANCIAL_DAY)


def set_financial_day(user_id: int, financial_day: int):
    if not 1 <= financial_day <= 28:
        raise ValueError("День начала периода должен быть от 1 до 28.")
    ensure_user(user_id)
    with get_connection() as conn:
        conn.execute("UPDATE users SET financial_day=? WHERE user_id=?", (financial_day, user_id))
    # The new current period may have a different key. Rebuild only its summary
    # from immutable transaction history, leaving all prior periods untouched.
    rebuild_month_from_transactions(user_id, financial_period_start(user_id))


def financial_period_start(user_id: int, dt=None) -> date:
    dt = dt or datetime.now()
    financial_day = get_financial_day(user_id)
    return financial_period_start_for_day(financial_day, dt)


def financial_period_start_for_day(financial_day: int, dt=None) -> date:
    dt = dt or datetime.now()
    if dt.day >= financial_day:
        return date(dt.year, dt.month, financial_day)
    if dt.month == 1:
        return date(dt.year - 1, 12, financial_day)
    return date(dt.year, dt.month - 1, financial_day)


def financial_period_end(user_id: int, dt=None) -> date:
    start = financial_period_start(user_id, dt)
    return financial_period_end_for_start(start)


def financial_period_end_for_start(start: date) -> date:
    if start.month == 12:
        return date(start.year + 1, 1, start.day)
    return date(start.year, start.month + 1, start.day)


def month_key(user_id: int, dt=None):
    return financial_period_start(user_id, dt).isoformat()


def ensure_month(user_id: int, key=None):
    key = key or month_key(user_id)
    ensure_user(user_id)
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO months(user_id, month) VALUES (?, ?)", (user_id, key))


def get_month(user_id: int, key=None):
    key = key or month_key(user_id)
    ensure_month(user_id, key)
    with get_connection() as conn:
        return conn.execute("SELECT * FROM months WHERE user_id=? AND month=?", (user_id, key)).fetchone()


def get_status_snapshot(user_id: int, today: date | None = None) -> dict:
    today = today or date.today()
    apply_due_recurring_payments(user_id, today)
    if DATABASE_URL:
        with get_connection() as conn:
            row = conn.execute(
                """
                WITH ins_user AS (
                    INSERT INTO users(user_id, mandatory_percent)
                    VALUES (?, ?)
                    ON CONFLICT (user_id) DO NOTHING
                ),
                u AS (
                    SELECT mandatory_percent, financial_day, savings, status_chat_id, status_message_id
                    FROM users
                    WHERE user_id=?
                ),
                period AS (
                    SELECT
                        u.*,
                        CASE
                            WHEN EXTRACT(DAY FROM ?::date)::int >= u.financial_day THEN
                                make_date(EXTRACT(YEAR FROM ?::date)::int, EXTRACT(MONTH FROM ?::date)::int, u.financial_day)
                            ELSE
                                make_date(
                                    EXTRACT(YEAR FROM (?::date - INTERVAL '1 month'))::int,
                                    EXTRACT(MONTH FROM (?::date - INTERVAL '1 month'))::int,
                                    u.financial_day
                                )
                        END AS start_date
                    FROM u
                ),
                ins_month AS (
                    INSERT INTO months(user_id, month)
                    SELECT ?, start_date::text FROM period
                    ON CONFLICT (user_id, month) DO NOTHING
                    RETURNING 1
                ),
                m AS (
                    SELECT months.budget, months.spent, months.rent, months.saved
                    FROM months, period
                    WHERE months.user_id=? AND months.month=period.start_date::text
                ),
                d AS (
                    SELECT COALESCE(SUM(amount), 0) AS spent_today
                    FROM transactions
                    WHERE user_id=? AND kind='expense' AND created_at>=? AND created_at<?
                ),
                g AS (
                    SELECT target, target_date FROM goals WHERE user_id=?
                )
                SELECT
                    period.mandatory_percent,
                    period.financial_day,
                    period.savings,
                    period.status_chat_id,
                    period.status_message_id,
                    period.start_date::text AS start_date,
                    m.budget,
                    m.spent,
                    m.rent,
                    m.saved,
                    d.spent_today,
                    g.target,
                    g.target_date,
                    (SELECT COUNT(*) FROM ins_month) AS inserted_months
                FROM period
                CROSS JOIN m
                CROSS JOIN d
                LEFT JOIN g ON TRUE
                """,
                (
                    user_id,
                    DEFAULT_MANDATORY_PERCENT,
                    user_id,
                    today.isoformat(),
                    today.isoformat(),
                    today.isoformat(),
                    today.isoformat(),
                    today.isoformat(),
                    user_id,
                    user_id,
                    user_id,
                    today.isoformat(),
                    (today + timedelta(days=1)).isoformat(),
                    user_id,
                ),
            ).fetchone()
        start = date.fromisoformat(row["start_date"])
        end = financial_period_end_for_start(start)
        budget = float(row["budget"])
        spent = float(row["spent"])
        rent = float(row["rent"])
        saved = float(row["saved"])
        savings = float(row["savings"])
        remaining = budget - spent - rent - saved
        days_left = max(0, (end - today).days)
        days_elapsed = max(1, (today - start).days + 1)
        avg = spent / days_elapsed
        forecast = remaining - max(0, avg) * max(0, (end - today).days)
        goal = None
        if row["target"] is not None and row["target_date"] is not None:
            goal = {"target": row["target"], "target_date": row["target_date"]}
        return {
            "start": start,
            "end": end,
            "financial_day": int(row["financial_day"] or DEFAULT_FINANCIAL_DAY),
            "mandatory_percent": float(row["mandatory_percent"]),
            "budget": budget,
            "spent": spent,
            "rent": rent,
            "saved": saved,
            "savings": savings,
            "remaining": remaining,
            "days_left": days_left,
            "daily_limit": remaining / days_left if days_left else remaining,
            "spent_today": float(row["spent_today"] or 0),
            "forecast": forecast,
            "goal": goal,
            "status_message": (
                (int(row["status_chat_id"]), int(row["status_message_id"]))
                if row["status_chat_id"] is not None and row["status_message_id"] is not None
                else None
            ),
        }

    ensure_user(user_id)
    with get_connection() as conn:
        user = conn.execute(
            "SELECT mandatory_percent, financial_day, savings, status_chat_id, status_message_id "
            "FROM users WHERE user_id=?",
            (user_id,),
        ).fetchone()
        financial_day = int(user["financial_day"] or DEFAULT_FINANCIAL_DAY)
        start = financial_period_start_for_day(financial_day, today)
        end = financial_period_end_for_start(start)
        key = start.isoformat()
        conn.execute("INSERT OR IGNORE INTO months(user_id, month) VALUES (?, ?)", (user_id, key))
        month = conn.execute(
            "SELECT budget, spent, rent, saved FROM months WHERE user_id=? AND month=?",
            (user_id, key),
        ).fetchone()
        daily_row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions "
            "WHERE user_id=? AND kind='expense' AND created_at>=? AND created_at<?",
            (user_id, today.isoformat(), (today + timedelta(days=1)).isoformat()),
        ).fetchone()
        goal = conn.execute(
            "SELECT target, target_date FROM goals WHERE user_id=?",
            (user_id,),
        ).fetchone()

    budget = float(month["budget"])
    spent = float(month["spent"])
    rent = float(month["rent"])
    saved = float(month["saved"])
    savings = float(user["savings"])
    remaining = budget - spent - rent - saved
    days_left = max(0, (end - today).days)
    days_elapsed = max(1, (today - start).days + 1)
    avg = spent / days_elapsed
    forecast = remaining - max(0, avg) * max(0, (end - today).days)
    return {
        "start": start,
        "end": end,
        "financial_day": financial_day,
        "mandatory_percent": float(user["mandatory_percent"]),
        "budget": budget,
        "spent": spent,
        "rent": rent,
        "saved": saved,
        "savings": savings,
        "remaining": remaining,
        "days_left": days_left,
        "daily_limit": remaining / days_left if days_left else remaining,
        "spent_today": float(daily_row["total"] or 0),
        "forecast": forecast,
        "goal": goal,
        "status_message": (
            (int(user["status_chat_id"]), int(user["status_message_id"]))
            if user["status_chat_id"] is not None and user["status_message_id"] is not None
            else None
        ),
    }


def rebuild_month_from_transactions(user_id: int, start: date):
    end = financial_period_end(user_id, start)
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT kind, amount FROM transactions WHERE user_id=? AND created_at>=? AND created_at<?",
            (user_id, start.isoformat(), end.isoformat()),
        ).fetchall()
        totals = {"income": 0.0, "mandatory": 0.0, "expense": 0.0, "rent": 0.0, "save": 0.0}
        for row in rows:
            if row["kind"] in totals:
                totals[row["kind"]] += float(row["amount"])
        conn.execute("INSERT OR IGNORE INTO months(user_id, month) VALUES (?, ?)", (user_id, start.isoformat()))
        conn.execute(
            "UPDATE months SET budget=?, spent=?, rent=?, saved=? WHERE user_id=? AND month=?",
            (
                round(totals["income"] - totals["mandatory"], 2),
                round(totals["expense"], 2),
                round(totals["rent"], 2),
                round(totals["save"], 2),
                user_id,
                start.isoformat(),
            ),
        )




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
    key = month_key(user_id)
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
    start = financial_period_start(user_id, day)
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


def list_recurring_payments(user_id: int):
    ensure_user(user_id)
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, title, amount, kind, day_of_month, active, last_run "
            "FROM recurring_payments WHERE user_id=? ORDER BY day_of_month, id",
            (user_id,),
        ).fetchall()


def add_recurring_payment(user_id: int, title: str, amount: float, kind: str, day_of_month: int):
    if kind not in {"expense", "rent"}:
        raise ValueError("Некорректный тип регулярного платежа")
    if not 1 <= day_of_month <= 28:
        raise ValueError("День платежа должен быть от 1 до 28")
    ensure_user(user_id)
    today = date.today()
    # A newly created rule starts from its next occurrence. Mark the current
    # month handled when its configured day has already arrived.
    last_run = today.isoformat() if day_of_month <= today.day else None
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO recurring_payments(user_id, title, amount, kind, day_of_month, last_run) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, title[:255], round(amount, 2), kind, day_of_month, last_run),
        )


def delete_recurring_payment(user_id: int, payment_id: int):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM recurring_payments WHERE user_id=? AND id=?",
            (user_id, payment_id),
        )


def apply_due_recurring_payments(user_id: int, today: date | None = None):
    today = today or date.today()
    period_key = today.strftime("%Y-%m")
    payments = list_recurring_payments(user_id)
    applied = []
    for payment in payments:
        if not int(payment["active"]):
            continue
        due_day = min(int(payment["day_of_month"]), monthrange(today.year, today.month)[1])
        if today.day < due_day or (payment["last_run"] or "").startswith(period_key):
            continue
        request_id = f"recurring-{payment['id']}-{period_key}"
        if payment["kind"] == "rent":
            success = add_rent(user_id, float(payment["amount"]), payment["title"], request_id)
        else:
            success = add_expense(user_id, float(payment["amount"]), payment["title"], request_id)
        if not success:
            continue
        with get_connection() as conn:
            conn.execute(
                "UPDATE recurring_payments SET last_run=? WHERE user_id=? AND id=?",
                (today.isoformat(), user_id, payment["id"]),
            )
        applied.append(int(payment["id"]))
    return applied
