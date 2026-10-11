from html import escape
from services.budget import money


def history_line(row, labels):
    operation = row["wallet_operation"]
    label = "+ ВОЗВРАТ" if operation == "refund" else "ПЕРЕВОД" if operation == "transfer" else "РАСХОД СО СЧЁТА" if row["kind"] == "wallet_expense" else labels.get(row["kind"], row["kind"])
    return f"{label}: {money(abs(float(row['amount'])))} ₽ — {escape(row['description'])}"
