from database.db import get_connection
from database.income_posting import post_income
from database.periods import ensure_month, financial_period_end_for_start, financial_period_start, month_key
from database.users import ensure_user

def list_income_sources(user_id: int):
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
    ensure_month(user_id)
    key = month_key(user_id)
    with get_connection() as conn:
        return post_income(conn, user_id, gross, description, key, source_id, request_id)[:3]
