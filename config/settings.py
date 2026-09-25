import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

BOT_NAME = os.getenv("BOT_NAME", "Мой Бюджет").strip() or "Мой Бюджет"
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip().rstrip("/")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
SQLITE_PATH = Path(os.getenv("SQLITE_PATH", str(BASE_DIR / "data" / "budget.db"))).expanduser()

DEFAULT_MANDATORY_PERCENT = float(os.getenv("DEFAULT_MANDATORY_PERCENT", "6"))
CURRENCY = "₽"
INIT_DATA_TTL_SECONDS = int(os.getenv("INIT_DATA_TTL_SECONDS", "86400"))
DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", "10"))
ALLOWED_ORIGINS = [
    value.strip().rstrip("/")
    for value in os.getenv("ALLOWED_ORIGINS", WEBAPP_URL).split(",")
    if value.strip()
]


def require_bot_token() -> str:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not configured. Add it to .env or the hosting environment.")
    return BOT_TOKEN
