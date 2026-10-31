# Reliability

## Telegram Summary Delivery

Financial writes enqueue a summary refresh in the same database transaction.
The API also requests refreshes after settings changes. Pending work is stored
in `telegram_sync`, one row per user. Repeated operations coalesce; a refresh
always reads the latest balance rather than storing or replaying an expense.

An immediate background attempt follows the API response. While the API process
is running, a worker checks the queue every 10 seconds. Network failures use
backoff (5 seconds to 5 minutes); Telegram retry-after delays are respected.
An expired 5-minute lease recovers work after a crash. Versioned acknowledgements
cannot remove a newer refresh or another worker's claim. Blocking the bot and
permanent Telegram request errors are logged, not retried indefinitely.

Delivery is at least once, not exactly once. Editing the persistent message is
idempotent. A timed-out first send or missing-message replacement can still
produce a duplicate if Telegram accepted the message but its response was lost.
The local polling bot and API do not share a Telegram editing lock. Existing
single-message behavior remains best effort across those processes.

Free hosting can suspend the API process. Queued work survives in PostgreSQL,
but retries resume only when the service wakes up. No financial write is retried
by this queue. Local bot changes require the user to restart their polling bot.

## Balance Audit

`database/audit.py` reads a consistent, read-only snapshot. The API checks on
startup and every 6 hours while running. Differences are logged as errors;
the audit never fixes or updates balances.

Verified scope:
- Current financial-period budget versus income, withholding and recorded opening.
- Current expense/transfer total, rent and savings contributions versus history.
- Additional-account balances versus legacy and wallet movements, including refunds.

Periods without an opening marker are explicitly skipped. Historical overlapping
period summaries and the initial baseline of accumulated savings are not verified.
A passing audit does not prove the completeness of the original imported history.

## Backups

`tools/backup_postgres.py` reads PostgreSQL with repeatable-read/read-only isolation.
It writes a private temporary file, restores its rows into disposable SQLite,
checks equality and integrity, and only then publishes the completed JSON backup
and prunes older completed files (30 retained). Financial audit differences do
not suppress an otherwise recoverable backup. Logs do not contain credentials.

Run a verification of an existing backup:

```sh
.venv/bin/python tools/verify_backup.py backups/postgres_backup_TIMESTAMP.json
```

This validates JSON row recovery into the application's SQLite schema. It is NOT
a PostgreSQL disaster-recovery drill: PostgreSQL-specific schema, sequences,
permissions, extensions and production cutover still need a separate test.
The verification tool has no option to restore into the working database.

The macOS launch agent retains its 03:15 schedule. Its logs belong in
`~/Library/Logs/CashManagement/`, not on the external project volume. The local
launch-agent test still stalls during Python startup when accessing the external
volume; scheduled execution is not confirmed and may require macOS access approval.
The local
bot also checks hourly for a completed copy newer than 24 hours and starts a
verified backup if needed. These local backups require the Mac to be on, the
project volume mounted and access to Aiven. They are not off-site backups.

Only completed files count toward freshness. Incomplete temporary copies do not
suppress a new attempt. Backups and private financial reports must not be pushed
to GitHub. Full user reset removes that user's pending synchronization entry and
then queues the new zero-state summary; other users are not affected.
