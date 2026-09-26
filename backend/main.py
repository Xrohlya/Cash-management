import hashlib
import hmac
import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qsl

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import settings
from database.db import init_db
from database.repository import (
    add_recurring_payment,
    add_expense,
    add_income,
    add_rent,
    add_to_savings,
    apply_due_recurring_payments,
    delete_recurring_payment,
    ensure_user,
    get_percent,
    get_status_snapshot,
    list_recurring_payments,
    recent_transactions,
    set_financial_day,
)
from services.analytics import clear_goal, current_period_stats, set_goal
from services.parser import extract_date, parse_expense, strip_date_words


WEBAPP_DIR = Path(__file__).resolve().parent.parent / "webapp"


class Operation(BaseModel):
    amount: float = Field(gt=0, le=1_000_000_000)
    description: str = Field(default="", max_length=255)
    request_id: str = Field(min_length=8, max_length=100)


class PeriodSettings(BaseModel):
    financial_day: int = Field(ge=1, le=28)


class SiriExpense(BaseModel):
    text: str = Field(min_length=1, max_length=255)


class GoalSettings(BaseModel):
    target: float = Field(gt=0, le=1_000_000_000)
    target_date: date


class RecurringPayment(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    amount: float = Field(gt=0, le=1_000_000_000)
    kind: str = Field(pattern="^(expense|rent)$")
    day_of_month: int = Field(ge=1, le=28)


def verify_init_data(init_data: str) -> dict:
    if not init_data:
        raise HTTPException(401, "Откройте приложение из Telegram.")
    if not settings.BOT_TOKEN:
        raise HTTPException(500, "BOT_TOKEN is not configured")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise HTTPException(401, "Некорректные данные Telegram.")

    data_check_string = "\n".join(f"{key}={pairs[key]}" for key in sorted(pairs))
    secret_key = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise HTTPException(401, "Подпись Telegram не прошла проверку.")

    try:
        auth_date = int(pairs.get("auth_date", "0"))
        if abs(time.time() - auth_date) > settings.INIT_DATA_TTL_SECONDS:
            raise HTTPException(401, "Сессия Telegram устарела. Откройте приложение снова.")
        user = json.loads(pairs["user"])
        user["id"] = int(user["id"])
        return user
    except HTTPException:
        raise
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(401, "Некорректный профиль Telegram.") from exc


def current_user(x_telegram_init_data: str = Header(default="")) -> int:
    user = verify_init_data(x_telegram_init_data)
    ensure_user(user["id"], user.get("first_name", ""), user.get("username", ""))
    return user["id"]


def siri_user(x_siri_token: str = Header(default="")) -> int:
    if not settings.SIRI_API_TOKEN or not settings.SIRI_USER_ID:
        raise HTTPException(503, "Siri integration is not configured")
    if not hmac.compare_digest(x_siri_token, settings.SIRI_API_TOKEN):
        raise HTTPException(401, "Invalid Siri token")
    ensure_user(settings.SIRI_USER_ID)
    return settings.SIRI_USER_ID


def state(user_id: int):
    apply_due_recurring_payments(user_id)
    snapshot = get_status_snapshot(user_id)
    end = snapshot["end"]
    goal = snapshot.get("goal")
    return {
        "available": round(snapshot["remaining"], 2),
        "today": round(snapshot["spent_today"], 2),
        "daily_limit": round(snapshot["daily_limit"], 2),
        "days_left": max(1, snapshot["days_left"]),
        "spent": round(snapshot["spent"], 2),
        "rent": round(snapshot["rent"], 2),
        "saved_this_month": round(snapshot["saved"], 2),
        "savings": round(snapshot["savings"], 2),
        "budget": round(snapshot["budget"], 2),
        "mandatory_percent": snapshot["mandatory_percent"],
        "financial_day": snapshot["financial_day"],
        "period_start": snapshot["start"].isoformat(),
        "period_end": (end - timedelta(days=1)).isoformat(),
        "goal": (
            {
                "target": float(goal["target"]),
                "target_date": goal["target_date"],
                "current": round(snapshot["savings"], 2),
                "progress": min(100, round(snapshot["savings"] / float(goal["target"]) * 100, 1)),
            }
            if goal and float(goal["target"]) > 0
            else None
        ),
    }


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Cash Management API", version="2.0.0", lifespan=lifespan)
if settings.ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Telegram-Init-Data"],
    )
app.mount("/static", StaticFiles(directory=WEBAPP_DIR / "static"), name="static")


@app.get("/", include_in_schema=False)
def webapp():
    return FileResponse(WEBAPP_DIR / "index.html")


@app.get("/health")
def health():
    return {"ok": True, "version": "2.0.0"}


@app.get("/api/state")
def api_state(user_id: int = Depends(current_user)):
    return state(user_id)


@app.get("/api/transactions")
def api_transactions(
    limit: int = Query(default=30, ge=1, le=100),
    user_id: int = Depends(current_user),
):
    return [dict(row) for row in recent_transactions(user_id, limit)]


@app.get("/api/analytics")
def api_analytics(user_id: int = Depends(current_user)):
    stats = current_period_stats(user_id)
    return {
        "average": round(stats["avg"], 2),
        "forecast": round(stats["forecast"], 2),
        "categories": [
            {
                "name": name,
                "amount": round(amount, 2),
                "count": stats["category_counts"].get(name, 0),
            }
            for name, amount in sorted(stats["categories"].items(), key=lambda item: item[1], reverse=True)
        ],
        "daily": [
            {"date": day, "amount": round(amount, 2)}
            for day, amount in sorted(stats["daily"].items())
        ],
    }


@app.post("/api/siri/expense", response_class=PlainTextResponse)
def api_siri_expense(op: SiriExpense, user_id: int = Depends(siri_user)):
    query = op.text.casefold().strip()
    snapshot = get_status_snapshot(user_id)
    if "остат" in query:
        return (
            f"Осталось {snapshot['remaining']:.0f} рублей. "
            f"Лимит на день {snapshot['daily_limit']:.0f} рублей."
        )
    if "сегодня" in query and ("потрат" in query or "расход" in query):
        return f"Сегодня потрачено {snapshot['spent_today']:.0f} рублей."
    if "потрат" in query or "расходы за месяц" in query:
        return f"За текущий период потрачено {snapshot['spent']:.0f} рублей."

    amount, description = parse_expense(strip_date_words(op.text))
    if amount is None or amount <= 0:
        raise HTTPException(422, "Назовите сумму цифрами, например: 500 рублей еда.")

    expense_date = extract_date(op.text)
    created_at = None
    if expense_date:
        created_at = datetime.combine(expense_date, datetime.min.time()).replace(hour=12)

    request_id = f"siri-{uuid.uuid4().hex}"
    if not add_expense(user_id, amount, description, request_id, created_at):
        raise HTTPException(409, "Недостаточно средств в доступном бюджете.")

    snapshot = get_status_snapshot(user_id)
    return (
        f"Записано: {amount:g} рублей, {description}. "
        f"Осталось {snapshot['remaining']:.0f} рублей."
    )


@app.post("/api/goal")
def api_set_goal(goal: GoalSettings, user_id: int = Depends(current_user)):
    set_goal(user_id, goal.target, goal.target_date)
    return state(user_id)


@app.post("/api/goal/clear")
def api_clear_goal(user_id: int = Depends(current_user)):
    clear_goal(user_id)
    return state(user_id)


@app.get("/api/recurring")
def api_recurring(user_id: int = Depends(current_user)):
    apply_due_recurring_payments(user_id)
    return [dict(row) for row in list_recurring_payments(user_id)]


@app.post("/api/recurring")
def api_add_recurring(payment: RecurringPayment, user_id: int = Depends(current_user)):
    add_recurring_payment(
        user_id,
        payment.title,
        payment.amount,
        payment.kind,
        payment.day_of_month,
    )
    apply_due_recurring_payments(user_id)
    return [dict(row) for row in list_recurring_payments(user_id)]


@app.post("/api/recurring/{payment_id}/delete")
def api_delete_recurring(payment_id: int, user_id: int = Depends(current_user)):
    delete_recurring_payment(user_id, payment_id)
    return [dict(row) for row in list_recurring_payments(user_id)]


@app.post("/api/expense")
def api_expense(op: Operation, user_id: int = Depends(current_user)):
    if not add_expense(user_id, op.amount, op.description or "Расход", op.request_id):
        raise HTTPException(409, "Недостаточно средств в доступном бюджете.")
    return state(user_id)


@app.post("/api/income")
def api_income(op: Operation, user_id: int = Depends(current_user)):
    add_income(
        user_id,
        op.amount,
        get_percent(user_id),
        op.description or "Доход",
        op.request_id,
    )
    return state(user_id)


@app.post("/api/rent")
def api_rent(op: Operation, user_id: int = Depends(current_user)):
    if not add_rent(user_id, op.amount, op.description or "Квартира", op.request_id):
        raise HTTPException(409, "Недостаточно средств в доступном бюджете.")
    return state(user_id)


@app.post("/api/save")
def api_save(op: Operation, user_id: int = Depends(current_user)):
    if not add_to_savings(user_id, op.amount, op.description or "Накопления", op.request_id):
        raise HTTPException(409, "Недостаточно средств в доступном бюджете.")
    return state(user_id)


@app.post("/api/settings/period")
def api_set_period(settings_data: PeriodSettings, user_id: int = Depends(current_user)):
    set_financial_day(user_id, settings_data.financial_day)
    return state(user_id)
