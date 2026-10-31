from types import SimpleNamespace
import time
import unittest
from unittest.mock import AsyncMock, patch

from bot.routes.common import pending
from bot.routes.income_matching import confirm_matched_income, suggest_income
from services.categories import normalize_expense_category, normalize_new_expense_category
from services.text_matching import income_hint, income_suggestions

SOURCES = [{"id": 7, "name": "Кафе Север", "active": 1, "withholding_percent": 6},
           {"id": 8, "name": "Офис", "active": 1, "withholding_percent": 3},
           {"id": 9, "name": "Кафе Севр", "active": 0, "withholding_percent": 90}]


class MatchingTests(unittest.TestCase):
    def test_source_hint_does_not_include_amount_or_income_prefix(self):
        self.assertEqual(income_hint("получил 30 000,50 ₽ от Кафе Север"), "кафе север")
        self.assertEqual(income_hint("доход 5000"), "")
        self.assertEqual(income_hint("получил 1000 Офис 2"), "офис 2")

    def test_typo_suggests_only_supplied_active_sources(self):
        self.assertEqual(income_suggestions("получил 30000 кафе севр", SOURCES)[0]["id"], 7)
        self.assertEqual(income_suggestions("получил 30000 кафе севр", SOURCES[1:2]), [])
        self.assertEqual(income_suggestions("получил 30000", SOURCES), [])

    def test_new_categories_handle_typos_but_historical_names_stay_unchanged(self):
        for text, expected in [("продкты", "Еда"), ("таксси", "Такси"), ("кафэ", "Кафе")]:
            self.assertEqual(normalize_new_expense_category(text), expected)
        for text in ["Моя поездка", "Ева", "Урок вокала"]:
            self.assertEqual(normalize_new_expense_category(text), normalize_expense_category(text))
        self.assertEqual(normalize_expense_category("продкты"), "Продкты")


class IncomeConfirmationTests(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        pending.clear()

    async def test_suggestion_does_not_post_income(self):
        message = SimpleNamespace(text="получил 30000 кафе севр", from_user=SimpleNamespace(id=101))
        with patch("bot.routes.income_matching.delete_user_message", new_callable=AsyncMock), patch("bot.routes.income_matching.send_transient", new_callable=AsyncMock), patch("bot.routes.income_matching.add_income_from_source") as post:
            await suggest_income(message, 30000, SOURCES[:2])
        post.assert_not_called()
        self.assertEqual(pending[101]["amount"], 30000)

    async def test_confirmation_is_per_user_one_time_and_has_idempotency_key(self):
        pending[101] = {"kind": "matched_income", "token": "abc", "expires": time.monotonic() + 300,
                        "amount": 30000, "sources": {7: ("Кафе Север", 6)}}
        callback = SimpleNamespace(data="match_income:abc:7", from_user=SimpleNamespace(id=202))
        with patch("bot.routes.income_matching.list_income_sources", return_value=SOURCES), patch("bot.routes.income_matching.add_income_from_source") as post, patch("bot.routes.income_matching.update_status", new_callable=AsyncMock):
            await confirm_matched_income(callback)
            post.assert_not_called()
            callback.from_user.id = 101
            await confirm_matched_income(callback)
            await confirm_matched_income(callback)
        post.assert_called_once_with(101, 30000, 7, "Кафе Север", request_id="income-match:101:abc", expected_source=("Кафе Север", 6))

    async def test_changed_withholding_requires_new_confirmation(self):
        pending[101] = {"kind": "matched_income", "token": "abc", "expires": time.monotonic() + 300,
                        "amount": 30000, "sources": {7: ("Кафе Север", 5)}}
        callback = SimpleNamespace(data="match_income:abc:7", from_user=SimpleNamespace(id=101), message=object())
        with patch("bot.routes.income_matching.list_income_sources", return_value=SOURCES), patch("bot.routes.income_matching.add_income_from_source") as post, patch("bot.routes.income_matching.edit_interface", new_callable=AsyncMock):
            await confirm_matched_income(callback)
        post.assert_not_called()
        self.assertNotIn(101, pending)
