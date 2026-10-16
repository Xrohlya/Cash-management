import unittest
from datetime import date

from services.budget import status_from_snapshot


class BudgetPeriodLabelTests(unittest.TestCase):
    def test_forecast_uses_selected_period_end(self):
        snapshot = dict.fromkeys(
            ("savings", "budget", "spent", "recurring", "rent", "saved",
             "remaining", "daily_limit", "spent_today", "forecast"), 0
        )
        snapshot.update(start=date(2026, 10, 8), end=date(2026, 11, 8),
                        days_left=27, goal=None)
        text = status_from_snapshot(snapshot)
        self.assertIn("Прогноз остатка к 07.11.2026", text)
        self.assertNotIn("к 19-му", text)
