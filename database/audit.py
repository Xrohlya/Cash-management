"""Consistent read-only input for the financial audit."""
from database import db
from services.balance_audit import audit_tables

TABLES = ("users", "months", "transactions", "period_openings",
          "extra_accounts", "account_transactions", "wallet_entries")


def audit_balances(today=None):
    with db.get_connection() as conn:
        if db.DATABASE_URL:
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        else:
            conn.execute("PRAGMA query_only=ON")
            conn.execute("BEGIN")
        tables = {table: [dict(row) for row in conn.execute(f"SELECT * FROM {table}").fetchall()]
                  for table in TABLES}
    return audit_tables(tables, today)
