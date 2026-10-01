import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl
from fastapi import Header, HTTPException
from config import settings
from database.repository import ensure_user


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
