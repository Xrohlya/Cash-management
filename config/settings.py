import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

BOT_NAME = os.getenv("BOT_NAME", "Мой Бюджет").strip() or "Мой Бюджет"
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip().rstrip("/")
WEBAPP_RELEASE = "20261001-4"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
SQLITE_PATH = Path(os.getenv("SQLITE_PATH", str(BASE_DIR / "data" / "budget.db"))).expanduser()

DEFAULT_MANDATORY_PERCENT = float(os.getenv("DEFAULT_MANDATORY_PERCENT", "6"))
CURRENCY = "₽"
INIT_DATA_TTL_SECONDS = int(os.getenv("INIT_DATA_TTL_SECONDS", "86400"))
DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", "10"))
SIRI_API_TOKEN = os.getenv("SIRI_API_TOKEN", "").strip()
SIRI_USER_ID = int(os.getenv("SIRI_USER_ID", "0") or "0")
ALLOWED_ORIGINS = [
    value.strip().rstrip("/")
    for value in os.getenv("ALLOWED_ORIGINS", WEBAPP_URL).split(",")
    if value.strip()
]


def versioned_webapp_url(url: str) -> str:
    if not url:
        return ""
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}v={WEBAPP_RELEASE}"


def require_bot_token() -> str:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not configured. Add it to .env or the hosting environment.")
    return BOT_TOKEN
