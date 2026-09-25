#!/bin/bash
set -e
cd "$(dirname "$0")"

PYTHON=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then PYTHON="$candidate"; break; fi
done
if [ -z "$PYTHON" ]; then
  echo "Python 3 не найден. Нужен Python 3.11+."
  read -r -p "Нажмите Enter..."
  exit 1
fi

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Создан .env. Добавьте BOT_TOKEN и при необходимости WEBAPP_URL, затем запустите снова."
  read -r -p "Нажмите Enter..."
  exit 1
fi

if [ ! -d ".venv" ]; then
  "$PYTHON" -m venv .venv
fi
source .venv/bin/activate

REQUIREMENTS_HASH="$(shasum -a 256 requirements.txt | awk '{print $1}')"
INSTALLED_HASH="$(cat .venv/.requirements.sha256 2>/dev/null || true)"
if [ "$REQUIREMENTS_HASH" != "$INSTALLED_HASH" ]; then
  echo "Устанавливаю зависимости..."
  python -m pip install -q -r requirements.txt
  printf '%s\n' "$REQUIREMENTS_HASH" > .venv/.requirements.sha256
fi

python - <<'PY'
from config.settings import require_bot_token
require_bot_token()
PY

if lsof -tiTCP:8787 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Старая версия бота ещё работает на порту 8787."
  echo "Остановите её через Ctrl+C в старом терминале и запустите задачу снова."
  exit 1
fi

mkdir -p logs
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8788 > logs/api.log 2>&1 &
API_PID=$!

cleanup() {
  kill "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

for _ in {1..30}; do
  if curl -fsS http://127.0.0.1:8788/health >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$API_PID" 2>/dev/null; then
    break
  fi
  sleep 1
done
if ! curl -fsS http://127.0.0.1:8788/health >/dev/null 2>&1; then
  echo "API не запустился. Проверьте logs/api.log"
  tail -n 40 logs/api.log
  exit 1
fi

echo "API: http://127.0.0.1:8788/health"
echo "Бот запущен. Для остановки нажмите Ctrl+C."
python app.py
