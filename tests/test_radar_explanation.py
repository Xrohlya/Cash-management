import unittest

from services.radar_text import explain_radar


class RadarExplanationTests(unittest.TestCase):
    def radar(self, forecast=-45976.94, available=59356.39, elapsed=3, target=1000):
        return {
            "projected_balance": forecast, "reserved": 1500,
            "target_balance": target, "safe_today": 1960.57,
            "calculation": {"available": available, "elapsed_days": elapsed,
                            "daily_average": 3708.33, "forecast_days": 28},
        }

    def test_shortfall_explains_tempo_and_is_not_a_debt(self):
        text = explain_radar(self.radar())
        self.assertIn("не хватит 45 977 ₽", text["title"])
        self.assertIn("3 708 ₽/день", text["pace"])
        self.assertIn("28 дн.", text["pace"])
        self.assertIn("до 1 961 ₽", text["guidance"])
        self.assertIn("Предварительный", text["notice"])
        self.assertIn("не долг", text["notice"])

    def test_positive_forecast_below_target_is_not_a_negative_balance(self):
        text = explain_radar(self.radar(forecast=400))
        self.assertIn("останется 400 ₽", text["title"])
        self.assertEqual(text["target_gap"], "До желаемого остатка не хватает 600 ₽.")

    def test_insufficient_reserve_does_not_promise_target(self):
        text = explain_radar(self.radar(available=500))
        self.assertIn("недостаточно", text["guidance"])
        self.assertIn("лимит — 0 ₽", text["guidance"])

    def test_mature_forecast_and_zero_target(self):
        text = explain_radar(self.radar(forecast=2000, elapsed=15, target=0))
        self.assertNotIn("Предварительный", text["notice"])
        self.assertIn("15 дн.", text["notice"])
        self.assertEqual(text["target_gap"], "")
