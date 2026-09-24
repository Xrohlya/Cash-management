import os
import sqlite3
import psycopg

SQLITE_PATH = os.getenv("SQLITE_PATH", "data/budget.db")
DATABASE_URL = os.environ["DATABASE_URL"]

with sqlite3.connect(SQLITE_PATH) as s, psycopg.connect(DATABASE_URL) as p:
    s.row_factory = sqlite3.Row
    pc = p.cursor()
    pc.execute(open("backend/schema.sql", encoding="utf-8").read())

    for table in ("users", "months", "transactions"):
        rows = s.execute(f"SELECT * FROM {table}").fetchall()
        print(table, len(rows))

    for r in s.execute("SELECT * FROM users"):
        pc.execute("""INSERT INTO users(user_id,mandatory_percent,savings,status_chat_id,status_message_id)
                      VALUES(%s,%s,%s,%s,%s)
                      ON CONFLICT(user_id) DO UPDATE SET mandatory_percent=EXCLUDED.mandatory_percent,
                      savings=EXCLUDED.savings,status_chat_id=EXCLUDED.status_chat_id,status_message_id=EXCLUDED.status_message_id""",
                   (r["user_id"],r["mandatory_percent"],r["savings"],r["status_chat_id"],r["status_message_id"]))

    for r in s.execute("SELECT * FROM months"):
        pc.execute("""INSERT INTO months(user_id,month,budget,spent,rent,saved)
                      VALUES(%s,%s,%s,%s,%s,%s)
                      ON CONFLICT(user_id,month) DO UPDATE SET budget=EXCLUDED.budget,spent=EXCLUDED.spent,
                      rent=EXCLUDED.rent,saved=EXCLUDED.saved""",
                   (r["user_id"],r["month"],r["budget"],r["spent"],r["rent"],r["saved"]))

    for r in s.execute("SELECT * FROM transactions"):
        pc.execute("""INSERT INTO transactions(id,user_id,kind,amount,description,created_at)
                      VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING""",
                   (r["id"],r["user_id"],r["kind"],r["amount"],r["description"],r["created_at"]))
    pc.execute("SELECT setval(pg_get_serial_sequence('transactions','id'), COALESCE((SELECT MAX(id) FROM transactions),1), true)")
    p.commit()
print("Migration completed.")
