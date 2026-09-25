"""Compatibility module. Secrets are loaded only from environment variables."""

import os

from config.settings import BOT_NAME, BOT_TOKEN


def _id_set(name: str) -> set[int]:
    result = set()
    for value in os.getenv(name, "").split(","):
        value = value.strip()
        if value:
            result.add(int(value))
    return result


ADMIN_USER_IDS = _id_set("ADMIN_USER_IDS")
ADMIN_GROUP_ID = int(os.environ["ADMIN_GROUP_ID"]) if os.getenv("ADMIN_GROUP_ID") else None
ALLOW_ADMIN_GROUP_MESSAGES = False
