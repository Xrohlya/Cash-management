import getpass
import os
import shutil
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
BACKUP_PATH = ROOT / ".env.before-aiven"


def main() -> None:
    database_url = os.environ.get("NEW_DATABASE_URL") or getpass.getpass(
        "Новый DATABASE_URL (ввод скрыт): "
    )
    database_url = database_url.strip()
    if not database_url.startswith(("postgres://", "postgresql://")):
        raise SystemExit("DATABASE_URL должен начинаться с postgres:// или postgresql://")

    with psycopg.connect(database_url, connect_timeout=20) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

    original = ENV_PATH.read_text(encoding="utf-8")
    lines = original.splitlines()
    replacement = f"DATABASE_URL={database_url}"
    updated = False
    for index, line in enumerate(lines):
        if line.startswith("DATABASE_URL="):
            lines[index] = replacement
            updated = True
            break
    if not updated:
        lines.append(replacement)

    shutil.copy2(ENV_PATH, BACKUP_PATH)
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"DATABASE_URL обновлён. Предыдущий .env сохранён в {BACKUP_PATH.name}")


if __name__ == "__main__":
    main()
