"""Additive tables: existing balances and transaction history are untouched."""


def create_planning_schema(conn, postgres: bool):
    identity = "BIGSERIAL PRIMARY KEY" if postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS expected_income (
            id {identity}, user_id BIGINT NOT NULL, title TEXT NOT NULL,
            amount DOUBLE PRECISION NOT NULL, due_date TEXT NOT NULL,
            source_id BIGINT, status TEXT NOT NULL DEFAULT 'planned',
            confirmed_at TEXT, confirmed_transaction_id BIGINT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS category_limits (
            user_id BIGINT NOT NULL, category TEXT NOT NULL,
            amount DOUBLE PRECISION NOT NULL,
            PRIMARY KEY (user_id, category)
        )
    """)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS operation_undo (
            id {identity}, user_id BIGINT NOT NULL,
            created_at TEXT NOT NULL, transaction_id BIGINT NOT NULL,
            original_data TEXT NOT NULL,
            UNIQUE (user_id, transaction_id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_expected_income_user_due ON expected_income(user_id,status,due_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_operation_undo_user ON operation_undo(user_id,id)")
