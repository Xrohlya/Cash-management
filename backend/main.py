import hashlib
import hmac
import json
import time
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qsl

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import settings
from database.db import init_db
from database.repository import (
    add_expense,
    add_income,
    add_rent,
    add_to_savings,
    daily_expenses,
    ensure_user,
    financial_period_end,
    financial_period_start,
    get_month,
    get_percent,
    get_savings,
    recent_transactions,
)
from services.analytics import current_period_stats
from tools.render_bootstrap import migrate_from_environment


WEBAPP_DIR = Path(__file__).resolve().parent.parent / "webapp"


class Operation(BaseModel):
    amount: float = Field(gt=0, le=1_000_000_000)
    description: str = Field(default="", max_length=255)
    request_id: str = Field(min_length=8, max_length=100)


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


def state(user_id: int):
    month = get_month(user_id)
    start = financial_period_start()
    end = financial_period_end()
    remaining = (
        float(month["budget"])
        - float(month["spent"])
        - float(month["rent"])
        - float(month["saved"])
    )
    days = max(1, (end - date.today()).days)
    return {
        "available": round(remaining, 2),
        "today": round(daily_expenses(user_id), 2),
        "daily_limit": round(remaining / days, 2),
        "days_left": days,
        "spent": round(float(month["spent"]), 2),
        "rent": round(float(month["rent"]), 2),
        "saved_this_month": round(float(month["saved"]), 2),
        "savings": round(get_savings(user_id), 2),
        "budget": round(float(month["budget"]), 2),
        "mandatory_percent": get_percent(user_id),
        "period_start": start.isoformat(),
        "period_end": (end - timedelta(days=1)).isoformat(),
    }


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    migrate_from_environment()
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
            {"name": name, "amount": round(amount, 2)}
            for name, amount in sorted(stats["categories"].items(), key=lambda item: item[1], reverse=True)
        ],
    }


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
