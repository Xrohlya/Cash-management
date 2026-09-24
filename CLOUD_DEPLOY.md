# Cloud deployment

Architecture: GitHub Pages Mini App → HTTPS FastAPI → PostgreSQL.

Render supports FastAPI web services and managed PostgreSQL. Use a paid PostgreSQL instance for permanent financial data; Render documents that free Postgres expires after 30 days.

## 1. Create PostgreSQL
In Render: New → PostgreSQL. Choose a paid plan for permanent storage. Copy the Internal Database URL.

## 2. Create API
New → Web Service → connect Xrohlya/Cash-management.
Build:
pip install -r backend/requirements.txt
Start:
uvicorn backend.app:app --host 0.0.0.0 --port $PORT

Environment:
BOT_TOKEN = the existing bot token from config/access.py
DATABASE_URL = PostgreSQL Internal Database URL
WEBAPP_MAX_AGE = 86400

## 3. Initialize schema
Run once in the Render shell:
psql "$DATABASE_URL" -f backend/schema.sql

## 4. Migrate the existing database
Do NOT upload budget.db to GitHub.
On the local machine, copy the real budget.db into the project as data/budget.db, set DATABASE_URL to the Render PostgreSQL URL, then run:
python backend/migrate_sqlite.py

Verify counts and totals before switching the bot.

## 5. Mini App
Set config.js:
window.CASH_API_URL = 'https://YOUR-SERVICE.onrender.com';

The Mini App sends Telegram initData in:
Authorization: tma <initData>

The API validates Telegram's HMAC signature and derives the user ID from verified data. It never trusts a user_id supplied by the browser.

## 6. Bot
The existing bot must also be switched from SQLite repository calls to PostgreSQL before the local bot is retired. Do not delete the local budget.db; keep it as a backup until cloud operation has been verified.

Telegram's official Mini App documentation explicitly says initData must be validated on the server and initDataUnsafe must not be trusted.
