from datetime import datetime

from database.operations import _claim_request


def post_income(conn, user_id, gross, description, key, source_id=None, request_id=None):
    source = None
    if source_id is not None:
        source = conn.execute(
            "SELECT name,withholding_percent FROM income_sources WHERE id=? AND user_id=? AND active=1",
            (source_id, user_id),
        ).fetchone()
        if not source:
            raise ValueError("Источник дохода удалён. Выберите другой источник.")
    percent = float(source["withholding_percent"]) if source else 0
    fee = round(gross * percent / 100, 2)
    net = round(gross - fee, 2)
    if not _claim_request(conn, user_id, request_id):
        return fee, net, False, None
    now = datetime.now().isoformat(timespec="seconds")
    income = conn.execute(
        "INSERT INTO transactions(user_id,created_at,kind,amount,description,income_source_id) "
        "VALUES (?, ?, 'income', ?, ?, ?) RETURNING id",
        (user_id, now, gross, description or (source["name"] if source else "Доход"), source_id),
    ).fetchone()
    if fee:
        conn.execute(
            "INSERT INTO transactions(user_id,created_at,kind,amount,description,income_source_id) "
            "VALUES (?, ?, 'mandatory', ?, ?, ?)",
            (user_id, now, fee, f"Удержание {percent:g}% · {source['name']}", source_id),
        )
    conn.execute("UPDATE months SET budget=budget+? WHERE user_id=? AND month=?", (net, user_id, key))
    return fee, net, True, int(income["id"])
