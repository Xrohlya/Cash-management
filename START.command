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

PID_FILE=".bot.pid"
if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Бот уже запущен (PID $OLD_PID)."
    echo "Сначала остановите старый процесс командой: kill $OLD_PID"
    exit 1
  fi
fi
printf '%s\n' "$$" > "$PID_FILE"

cleanup() {
  rm -f "$PID_FILE"
}
trap cleanup EXIT INT TERM

python app.py
