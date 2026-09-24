import hashlib
import hmac
import json
import os
import time
from datetime import date, datetime, timedelta
from urllib.parse import parse_qsl

import psycopg
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

BOT_TOKEN = os.environ["BOT_TOKEN"]
DATABASE_URL = os.environ["DATABASE_URL"]
WEBAPP_MAX_AGE = int(os.getenv("WEBAPP_MAX_AGE", "86400"))
FINANCIAL_DAY = 20

app = FastAPI(title="Cash Management API")


class MoneyInput(BaseModel):
    amount: float
    description: str = ""


def db():
    return psycopg.connect(DATABASE_URL)


def verify_init_data(init_data: str) -> int:
    if not init_data:
        raise HTTPException(401, "Telegram authorization required")
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise HTTPException(401, "Invalid Telegram initData")
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        raise HTTPException(401, "Invalid Telegram signature")
    auth_date = int(pairs.get("auth_date", "0"))
    if time.time() - auth_date > WEBAPP_MAX_AGE:
        raise HTTPException(401, "Telegram authorization expired")
    user = json.loads(pairs.get("user", "{}"))
    user_id = int(user["id"])
    return user_id


def user_id_from_header(authorization: str | None) -> int:
    if not authorization or not authorization.startswith("tma "):
        raise HTTPException(401, "Missing Telegram initData")
    return verify_init_data(authorization[4:])


def financial_start(d: date) -> date:
    if d.day >= FINANCIAL_DAY:
        return date(d.year, d.month, FINANCIAL_DAY)
    if d.month == 1:
        return date(d.year - 1, 12, FINANCIAL_DAY)
    return date(d.year, d.month - 1, FINANCIAL_DAY)


def financial_end(d: date) -> date:
    s = financial_start(d)
    if s.month == 12:
        return date(s.year + 1, 1, FINANCIAL_DAY)
    return date(s.year, s.month + 1, FINANCIAL_DAY)


def ensure_user(cur, uid: int):
    cur.execute("INSERT INTO users(user_id) VALUES(%s) ON CONFLICT(user_id) DO NOTHING", (uid,))


def state(uid: int):
    today = date.today()
    start, end = financial_start(today), financial_end(today)
    with db() as conn:
        with conn.cursor() as cur:
            ensure_user(cur, uid)
            cur.execute("""SELECT mandatory_percent, savings FROM users WHERE user_id=%s""", (uid,))
            u = cur.fetchone()
            cur.execute("""SELECT COALESCE(budget,0), COALESCE(spent,0), COALESCE(rent,0), COALESCE(saved,0)
                           FROM months WHERE user_id=%s AND month=%s""", (uid, start.isoformat()))
            m = cur.fetchone() or (0,0,0,0)
            cur.execute("""SELECT COALESCE(SUM(amount),0) FROM transactions
                           WHERE user_id=%s AND kind='expense' AND created_at >= %s AND created_at < %s""",
                        (uid, today.isoformat(), (today + timedelta(days=1)).isoformat()))
            today_spent = float(cur.fetchone()[0] or 0)
    budget, spent, rent, saved = map(float, m)
    available = budget - spent - rent - saved
    days_left = max((end - today).days, 1)
    return {
        "period": f"{start:%d.%m.%Y} — {(end-timedelta(days=1)):%d.%m.%Y}",
        "available": round(available,2),
        "today": round(today_spent,2),
        "daily_limit": round(available/days_left,2),
        "spent": round(spent,2),
        "rent": round(rent,2),
        "saved": round(saved,2),
        "savings": round(float(u[1] or 0),2),
        "mandatory_percent": float(u[0] or 6),
    }


@app.get("/health")
def health():
    with db() as conn:
        conn.execute("SELECT 1")
    return {"ok": True}


@app.get("/api/state")
def api_state(authorization: str | None = Header(default=None)):
    return state(user_id_from_header(authorization))


@app.post("/api/expense")
def expense(payload: MoneyInput, authorization: str | None = Header(default=None)):
    uid = user_id_from_header(authorization)
    if payload.amount <= 0:
        raise HTTPException(400, "Amount must be positive")
    with db() as conn:
        with conn.cursor() as cur:
            ensure_user(cur, uid)
            cur.execute("INSERT INTO transactions(user_id,kind,amount,description,created_at) VALUES(%s,'expense',%s,%s,%s)",
                        (uid, payload.amount, payload.description or "Расход", datetime.now().isoformat(timespec="seconds")))
            start = financial_start(date.today()).isoformat()
            cur.execute("UPDATE months SET spent=spent+%s WHERE user_id=%s AND month=%s",
                        (payload.amount, uid, start))
    return state(uid)


@app.post("/api/income")
def income(payload: MoneyInput, authorization: str | None = Header(default=None)):
    uid = user_id_from_header(authorization)
    if payload.amount <= 0:
        raise HTTPException(400, "Amount must be positive")
    mandatory = round(payload.amount * 0.06, 2)
    net = payload.amount - mandatory
    now = datetime.now().isoformat(timespec="seconds")
    start = financial_start(date.today()).isoformat()
    with db() as conn:
        with conn.cursor() as cur:
            ensure_user(cur, uid)
            cur.execute("INSERT INTO transactions(user_id,kind,amount,description,created_at) VALUES(%s,'income',%s,'Доход',%s)", (uid,payload.amount,now))
            cur.execute("INSERT INTO transactions(user_id,kind,amount,description,created_at) VALUES(%s,'mandatory',%s,'Обязательный вычет 6%%',%s)", (uid,mandatory,now))
            cur.execute("""INSERT INTO months(user_id,month,budget,spent,rent,saved)
                           VALUES(%s,%s,%s,0,0,0)
                           ON CONFLICT(user_id,month) DO UPDATE SET budget=months.budget+EXCLUDED.budget""",
                        (uid,start,net))
    return state(uid)


@app.post("/api/save")
def save(payload: MoneyInput, authorization: str | None = Header(default=None)):
    uid = user_id_from_header(authorization)
    if payload.amount <= 0:
        raise HTTPException(400, "Amount must be positive")
    start = financial_start(date.today()).isoformat()
    now = datetime.now().isoformat(timespec="seconds")
    with db() as conn:
        with conn.cursor() as cur:
            ensure_user(cur, uid)
            cur.execute("INSERT INTO transactions(user_id,kind,amount,description,created_at) VALUES(%s,'save',%s,'Накопления',%s)",
                        (uid,payload.amount,now))
            cur.execute("""INSERT INTO months(user_id,month,budget,spent,rent,saved)
                           VALUES(%s,%s,0,0,0,%s)
                           ON CONFLICT(user_id,month) DO UPDATE SET saved=months.saved+EXCLUDED.saved""",
                        (uid,start,payload.amount))
            cur.execute("UPDATE users SET savings=savings+%s WHERE user_id=%s", (payload.amount,uid))
    return state(uid)
