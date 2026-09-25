import hashlib
import hmac
import json
import time
import unittest
from urllib.parse import urlencode

from fastapi import HTTPException

from backend import main


def signed_init_data(token: str, user_id: int) -> str:
    fields = {
        "auth_date": str(int(time.time())),
        "query_id": "test-query",
        "user": json.dumps({"id": user_id, "first_name": "Test"}, separators=(",", ":")),
    }
    check = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


class TelegramAuthTest(unittest.TestCase):
    def setUp(self):
        self.original_token = main.settings.BOT_TOKEN
        main.settings.BOT_TOKEN = "123456:test-token"

    def tearDown(self):
        main.settings.BOT_TOKEN = self.original_token

    def test_valid_signature_returns_signed_user(self):
        user = main.verify_init_data(signed_init_data(main.settings.BOT_TOKEN, 4242))
        self.assertEqual(user["id"], 4242)

    def test_tampered_user_is_rejected(self):
        data = signed_init_data(main.settings.BOT_TOKEN, 4242).replace("4242", "9999")
        with self.assertRaises(HTTPException):
            main.verify_init_data(data)


if __name__ == "__main__":
    unittest.main()
