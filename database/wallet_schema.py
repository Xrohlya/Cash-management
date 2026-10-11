def create_wallet_schema(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS wallet_entries (
        transaction_id BIGINT PRIMARY KEY, user_id BIGINT NOT NULL,
        operation TEXT NOT NULL, source TEXT NOT NULL, destination TEXT NOT NULL,
        original_id BIGINT, original_data TEXT
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_wallet_refunds ON wallet_entries(user_id,original_id)")
