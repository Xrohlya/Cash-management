"""Durable, coalesced summary refreshes; no financial operations are replayed."""
import time
from uuid import uuid4

from database.db import get_connection


def create_sync_schema(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS telegram_sync (
        user_id BIGINT PRIMARY KEY,
        revision BIGINT NOT NULL DEFAULT 1,
        attempts INTEGER NOT NULL DEFAULT 0,
        next_attempt DOUBLE PRECISION NOT NULL DEFAULT 0,
        lease_until DOUBLE PRECISION NOT NULL DEFAULT 0,
        lease_token TEXT NOT NULL DEFAULT ''
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_telegram_sync_due ON telegram_sync(next_attempt,lease_until)")


def mark_dirty(conn, user_id):
    conn.execute("""INSERT INTO telegram_sync(user_id) VALUES (?)
        ON CONFLICT(user_id) DO UPDATE SET revision=telegram_sync.revision+1,
        next_attempt=0,attempts=0""", (user_id,))


def enqueue(user_id):
    with get_connection() as conn:
        mark_dirty(conn, user_id)


def claim(user_id=None, *, now=None):
    now = time.time() if now is None else now
    token = uuid4().hex
    with get_connection() as conn:
        where = "next_attempt<=? AND lease_until<=?"
        params = [now, now]
        if user_id is not None:
            where += " AND user_id=?"
            params.append(user_id)
        row = conn.execute(
            f"SELECT user_id FROM telegram_sync WHERE {where} ORDER BY next_attempt,user_id LIMIT 1",
            tuple(params),
        ).fetchone()
        if row is None:
            return None
        # Conditional claim works across overlapping deployments/processes.
        claimed = conn.execute("""UPDATE telegram_sync SET lease_until=?,lease_token=?
            WHERE user_id=? AND next_attempt<=? AND lease_until<=?
            RETURNING user_id,revision,attempts,lease_token""",
            (now + 300, token, row["user_id"], now, now)).fetchone()
        return dict(claimed) if claimed else None


def finish(job, *, delay=None, now=None):
    now = time.time() if now is None else now
    with get_connection() as conn:
        if delay is None:
            conn.execute("DELETE FROM telegram_sync WHERE user_id=? AND revision=? AND lease_token=?",
                         (job["user_id"], job["revision"], job["lease_token"]))
        else:
            conn.execute("""UPDATE telegram_sync SET attempts=attempts+1,next_attempt=?,
                lease_until=0,lease_token='' WHERE user_id=? AND revision=? AND lease_token=?""",
                (now + delay, job["user_id"], job["revision"], job["lease_token"]))
        # A newer operation arrived while this revision was being sent.
        conn.execute("""UPDATE telegram_sync SET lease_until=0,lease_token=''
            WHERE user_id=? AND revision<>? AND lease_token=?""",
            (job["user_id"], job["revision"], job["lease_token"]))
