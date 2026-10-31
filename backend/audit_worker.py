import asyncio
import logging

from database.audit import audit_balances


async def audit_loop():
    while True:
        try:
            result = await asyncio.to_thread(audit_balances)
            for finding in result["findings"]:
                logging.error("BALANCE AUDIT: user=%s scope=%s field=%s differs; no automatic correction",
                              finding["user_id"], finding["scope"], finding["field"])
            if not result["findings"]:
                logging.info("Balance audit: %s checks passed; %s periods skipped",
                             result["checked"], len(result["skipped"]))
        except Exception:
            logging.exception("Balance audit unavailable; no data changed")
        await asyncio.sleep(6 * 60 * 60)
