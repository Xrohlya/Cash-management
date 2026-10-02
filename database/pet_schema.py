def create_pet_schema(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS pet_layout (
        user_id BIGINT NOT NULL, item TEXT NOT NULL, x DOUBLE PRECISION NOT NULL,
        y DOUBLE PRECISION NOT NULL, PRIMARY KEY(user_id,item)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS pet_album (
        user_id BIGINT NOT NULL, event TEXT NOT NULL, title TEXT NOT NULL,
        recorded_at TEXT NOT NULL, PRIMARY KEY(user_id,event)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS pet_minigame (
        user_id BIGINT PRIMARY KEY, day TEXT NOT NULL, token TEXT NOT NULL,
        sequence TEXT NOT NULL, started DOUBLE PRECISION NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS pet_appearance (
        user_id BIGINT PRIMARY KEY, color TEXT NOT NULL DEFAULT 'original'
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS pet_item_upgrades (
        user_id BIGINT NOT NULL, item TEXT NOT NULL, level INTEGER NOT NULL,
        PRIMARY KEY(user_id, item)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS pet_daily_budget (
        user_id BIGINT NOT NULL, day TEXT NOT NULL, allowance DOUBLE PRECISION NOT NULL,
        PRIMARY KEY(user_id, day)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS pet_world (
        user_id BIGINT PRIMARY KEY, pet TEXT NOT NULL DEFAULT 'robot',
        name TEXT NOT NULL DEFAULT '', xp INTEGER NOT NULL DEFAULT 0,
        coins INTEGER NOT NULL DEFAULT 0, motion INTEGER NOT NULL DEFAULT 1
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS pet_rewards (
        user_id BIGINT NOT NULL, day TEXT NOT NULL, mission TEXT NOT NULL,
        xp INTEGER NOT NULL, coins INTEGER NOT NULL,
        PRIMARY KEY(user_id, day, mission)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS pet_inventory (
        user_id BIGINT NOT NULL, item TEXT NOT NULL,
        PRIMARY KEY(user_id, item)
    )""")
