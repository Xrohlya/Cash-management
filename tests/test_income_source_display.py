import unittest
from unittest.mock import patch

from bot.routes.settings import income_sources_text


class IncomeSourceDisplayTests(unittest.TestCase):
    def test_net_income_uses_recorded_withholding(self):
        source = dict(name="Кафе", active=1, withholding_percent=6,
                      gross_total=10000, withheld_total=500)
        with patch("bot.routes.settings.list_income_sources", return_value=[source]):
            text = income_sources_text(123)
        self.assertIn("Доход: 10 000 ₽", text)
        self.assertIn("удержано: 500 ₽", text)
        self.assertIn("Чистый доход: <b>9 500 ₽</b>", text)

    def test_zero_income_source_is_visible(self):
        source = dict(name="Офис", active=1, withholding_percent=0,
                      gross_total=0, withheld_total=0)
        with patch("bot.routes.settings.list_income_sources", return_value=[source]):
            text = income_sources_text(123)
        self.assertIn("Офис", text)
        self.assertIn("Чистый доход: <b>0 ₽</b>", text)
