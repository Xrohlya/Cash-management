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
  echo "Файл .env не найден."
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

python tools/backup_postgres.py

echo ""
read -r -p "Нажмите Enter..."
