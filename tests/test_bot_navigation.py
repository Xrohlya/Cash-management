import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bot.routes import budget, reports


class BotNavigationTests(unittest.IsolatedAsyncioTestCase):
    async def test_help_contains_clear_action(self):
        callback = SimpleNamespace(from_user=SimpleNamespace(id=101))
        with patch.object(budget, "edit_interface", new_callable=AsyncMock) as edit, \
             patch.object(budget, "answer_callback", new_callable=AsyncMock):
            await budget.cb_help(callback)
        markup = edit.call_args.kwargs["reply_markup"]
        actions = [b.callback_data for row in markup.inline_keyboard for b in row if b.callback_data]
        self.assertEqual(actions, ["clear_chat", "status"])

    async def test_empty_history_still_offers_both_export_formats(self):
        callback = SimpleNamespace(from_user=SimpleNamespace(id=101))
        with patch.object(reports, "recent_transactions", return_value=[]) as recent, \
             patch.object(reports, "edit_interface", new_callable=AsyncMock) as edit, \
             patch.object(reports, "answer_callback", new_callable=AsyncMock):
            await reports.cb_history(callback)
        recent.assert_called_once_with(101)
        actions = [b.callback_data for row in edit.call_args.kwargs["reply_markup"].inline_keyboard for b in row if b.callback_data]
        self.assertEqual(actions, ["report", "excel", "status"])

    async def test_excel_callback_exports_only_the_callers_period(self):
        callback = SimpleNamespace(from_user=SimpleNamespace(id=202))
        period = date(2026, 10, 8), date(2026, 11, 8)
        with patch.object(reports, "parse_report_period", return_value=period) as parse, \
             patch("services.excel_report.build_excel_report", return_value="/tmp/test.xlsx") as build, \
             patch.object(reports, "replace_interface_with_document", new_callable=AsyncMock) as send, \
             patch.object(reports, "answer_callback", new_callable=AsyncMock):
            await reports.cb_excel(callback)
        parse.assert_called_once_with(202)
        build.assert_called_once_with(202, *period)
        self.assertEqual(send.call_args.args[1], "/tmp/test.xlsx")

    async def test_export_failure_keeps_history_navigation(self):
        callback = SimpleNamespace(from_user=SimpleNamespace(id=101))
        with patch.object(reports, "parse_report_period", side_effect=ValueError("<error>")), \
             patch.object(reports, "edit_interface", new_callable=AsyncMock) as edit, \
             patch.object(reports, "answer_callback", new_callable=AsyncMock):
            await reports.cb_report(callback)
        self.assertIn("&lt;error&gt;", edit.call_args.args[1])
        self.assertIn("reply_markup", edit.call_args.kwargs)
