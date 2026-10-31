"""Local safety net for daily backups while the user's bot is running."""
import asyncio
import logging
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent


def backup_is_due(now=None):
    now = time.time() if now is None else now
    backups = list((ROOT / "backups").glob("postgres_backup_*.json"))
    newest = max((path.stat().st_mtime for path in backups), default=0)
    return now - newest >= 24 * 60 * 60


async def run_backup():
    log_path = ROOT / "logs" / "backup.log"
    log_path.parent.mkdir(exist_ok=True)
    with log_path.open("a", encoding="utf-8") as stream:
        log_path.chmod(0o600)
        process = await asyncio.create_subprocess_exec(
            sys.executable, str(ROOT / "tools" / "backup_postgres.py"),
            "--output-dir", str(ROOT / "backups"), cwd=ROOT,
            stdout=stream, stderr=stream,
        )
        try:
            code = await process.wait()
        except asyncio.CancelledError:
            if process.returncode is None:
                process.terminate()
                await process.wait()
            raise
    if code:
        logging.error("Резервная копия не создана: код %s; подробности в logs/backup.log", code)
    else:
        logging.info("Резервная копия всех пользователей создана и проверена")
    return code == 0


async def backup_loop():
    from config.settings import DATABASE_URL

    if not DATABASE_URL:
        return
    while True:
        try:
            if await asyncio.to_thread(backup_is_due):
                await run_backup()
        except Exception:
            logging.exception("Не удалось проверить резервную копию; повтор через час")
        await asyncio.sleep(60 * 60)
