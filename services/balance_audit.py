"""Read-only reconciliation. Reports differences; never repairs money."""
from datetime import date
from decimal import Decimal
from collections import defaultdict

from database.periods import financial_period_start_for_day, financial_period_end_for_start


def audit_tables(tables, today=None):
    today = today or date.today()
    findings, checked = [], 0
    months = {(r["user_id"], r["month"]): r for r in tables["months"]}
    openings = {(r["user_id"], r["month"]): r for r in tables.get("period_openings", [])}
    transactions = tables["transactions"]
    transactions_by_user = defaultdict(list)
    for row in transactions:
        transactions_by_user[row["user_id"]].append(row)

    def money(value):
        return Decimal(str(value)).quantize(Decimal("0.01"))

    def compare(user_id, scope, field, actual, expected):
        nonlocal checked
        checked += 1
        if money(actual) != money(expected):
            findings.append({"user_id": user_id, "scope": scope, "field": field,
                             "actual": str(money(actual)), "expected": str(money(expected)),
                             "difference": str(money(actual) - money(expected))})

    skipped = []
    for user in tables["users"]:
        uid = user["user_id"]
        start = financial_period_start_for_day(int(user.get("financial_day") or 20), today)
        end = financial_period_end_for_start(start)
        key = (uid, start.isoformat())
        if key not in months or key not in openings:
            skipped.append({"user_id": uid, "reason": "Current period or opening marker is absent"})
            continue
        totals = {}
        for row in transactions_by_user[uid]:
            if start.isoformat() <= row["created_at"][:10] < end.isoformat():
                totals[row["kind"]] = totals.get(row["kind"], Decimal(0)) + Decimal(str(row["amount"]))
        total = lambda kind: totals.get(kind, Decimal(0))
        expected = {
            "budget": money(openings[key]["amount"]) + total("income") - total("mandatory"),
            "spent": total("expense") + total("recurring") + total("account_transfer") - total("account_return"),
            "rent": total("rent"), "saved": total("save"),
        }
        for field, amount in expected.items():
            compare(uid, start.isoformat(), field, months[key][field], amount)

    by_id = {row["id"]: row for row in transactions}
    legacy_by_account, entries_by_user = defaultdict(list), defaultdict(list)
    for row in tables.get("account_transactions", []):
        legacy_by_account[(row["user_id"], row["account_id"])].append(row)
    for entry in tables.get("wallet_entries", []):
        entries_by_user[entry["user_id"]].append(entry)
    for account in tables.get("extra_accounts", []):
        uid, account_id = account["user_id"], account["id"]
        wallet = f"account:{account_id}"
        expected = Decimal(0)
        for row in legacy_by_account[(uid, account_id)]:
            expected += Decimal(str(row["amount"])) * (1 if row["kind"] == "in" else -1)
        for entry in entries_by_user[uid]:
            row = by_id.get(entry["transaction_id"])
            if not row or row["user_id"] != uid:
                continue
            amount = Decimal(str(row["amount"]))
            if entry["operation"] == "transfer":
                if entry["destination"] == wallet:
                    expected += amount
                if entry["source"] == wallet:
                    expected -= amount
            elif entry["source"] == wallet:
                expected -= amount
        compare(uid, wallet, "balance", account["balance"], expected)
    return {"checked": checked, "findings": findings, "skipped": skipped,
            "scope": "Current main-period totals and extra accounts; savings baseline and closed legacy periods are not verified"}
