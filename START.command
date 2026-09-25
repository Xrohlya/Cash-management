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
python -m pip install -q -r requirements.txt

python - <<'PY'
from config.settings import require_bot_token
require_bot_token()
PY

mkdir -p logs
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8788 > logs/api.log 2>&1 &
API_PID=$!

cleanup() {
  kill "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

sleep 1
if ! kill -0 "$API_PID" 2>/dev/null; then
  echo "API не запустился. Проверьте logs/api.log"
  tail -n 40 logs/api.log
  exit 1
fi

echo "API: http://127.0.0.1:8788/health"
echo "Важно: сначала остановите старую копию бота с тем же токеном."
python app.py
