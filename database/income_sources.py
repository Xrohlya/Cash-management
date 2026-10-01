from datetime import datetime
from database.db import get_connection

def list_income_sources(user_id: int):
    from database.repository import ensure_user, financial_period_start, financial_period_end_for_start
    ensure_user(user_id)
    start = financial_period_start(user_id)
    end = financial_period_end_for_start(start)
    with get_connection() as conn:
        return conn.execute(
            "SELECT s.id,s.name,s.withholding_percent,s.active,"
            "COALESCE(SUM(CASE WHEN t.kind='income' AND t.created_at>=? AND t.created_at<? THEN t.amount ELSE 0 END),0) gross_total,"
            "COALESCE(SUM(CASE WHEN t.kind='mandatory' AND t.created_at>=? AND t.created_at<? THEN t.amount ELSE 0 END),0) withheld_total "
            "FROM income_sources s LEFT JOIN transactions t ON t.income_source_id=s.id "
            "WHERE s.user_id=? GROUP BY s.id,s.name,s.withholding_percent,s.active ORDER BY s.id",
            (start.isoformat(), end.isoformat(), start.isoformat(), end.isoformat(), user_id),
        ).fetchall()


def create_income_source(user_id: int, name: str, withholding_percent: float):
    from database.repository import ensure_user
    ensure_user(user_id)
    clean_name = " ".join(name.split())[:80]
    with get_connection() as conn:
        if conn.execute(
            "SELECT 1 FROM income_sources WHERE user_id=? AND lower(name)=lower(?)",
            (user_id, clean_name),
        ).fetchone():
            raise ValueError("Источник с таким названием уже существует")
        conn.execute(
            "INSERT INTO income_sources(user_id,name,withholding_percent) VALUES (?, ?, ?)",
            (user_id, clean_name, round(withholding_percent, 2)),
        )


def update_income_source(user_id: int, source_id: int, name: str, withholding_percent: float):
    clean_name = " ".join(name.split())[:80]
    with get_connection() as conn:
        duplicate = conn.execute(
            "SELECT 1 FROM income_sources WHERE user_id=? AND lower(name)=lower(?) AND id<>?",
            (user_id, clean_name, source_id),
        ).fetchone()
        if duplicate:
            raise ValueError("Источник с таким названием уже существует")
        cursor = conn.execute(
            "UPDATE income_sources SET name=?,withholding_percent=? WHERE user_id=? AND id=?",
            (clean_name, round(withholding_percent, 2), user_id, source_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("Источник не найден")


def delete_income_source(user_id: int, source_id: int):
    with get_connection() as conn:
        used = conn.execute(
            "SELECT 1 FROM transactions WHERE user_id=? AND income_source_id=? LIMIT 1",
            (user_id, source_id),
        ).fetchone()
        if used:
            conn.execute(
                "UPDATE income_sources SET active=0 WHERE user_id=? AND id=?", (user_id, source_id)
            )
        else:
            conn.execute("DELETE FROM income_sources WHERE user_id=? AND id=?", (user_id, source_id))


def find_income_source(user_id: int, text: str):
    normalized = " ".join(text.casefold().split())
    sources = list_income_sources(user_id)
    matches = [source for source in sources if int(source["active"]) and source["name"].casefold() in normalized]
    return max(matches, key=lambda source: len(source["name"])) if matches else None


def add_income_from_source(user_id: int, gross: float, source_id: int, description="Доход", request_id=None):
    from database.repository import ensure_month, month_key, _claim_request
    ensure_month(user_id)
    key = month_key(user_id)
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        source = conn.execute(
            "SELECT name,withholding_percent FROM income_sources WHERE id=? AND user_id=? AND active=1",
            (source_id, user_id),
        ).fetchone()
        if not source:
            raise ValueError("Источник дохода не найден")
        fee = round(gross * float(source["withholding_percent"]) / 100, 2)
        net = round(gross - fee, 2)
        if not _claim_request(conn, user_id, request_id):
            return fee, net, False
        conn.execute(
            "INSERT INTO transactions(user_id,created_at,kind,amount,description,income_source_id) "
            "VALUES (?, ?, 'income', ?, ?, ?)",
            (user_id, now, gross, description or source["name"], source_id),
        )
        if fee:
            conn.execute(
                "INSERT INTO transactions(user_id,created_at,kind,amount,description,income_source_id) "
                "VALUES (?, ?, 'mandatory', ?, ?, ?)",
                (user_id, now, fee, f"Удержание {float(source['withholding_percent']):g}% · {source['name']}", source_id),
            )
        conn.execute("UPDATE months SET budget=budget+? WHERE user_id=? AND month=?", (net, user_id, key))
    return fee, net, True

