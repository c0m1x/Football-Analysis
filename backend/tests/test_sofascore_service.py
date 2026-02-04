import unittest

from services.sofascore_service import SofaScoreService


class TestSofaScoreServiceParsing(unittest.TestCase):
    def setUp(self):
        self.svc = SofaScoreService()

    def test_flatten_stats_legacy_shape(self):
        raw = {
            "statistics": [
                {
                    "groups": [
                        {
                            "statisticsItems": [
                                {"name": "Ball possession", "home": "55%", "away": "45%"},
                                {"name": "Total passes", "home": 400, "away": 320},
                            ]
                        }
                    ]
                }
            ]
        }
        flat = self.svc._flatten_stats(raw)
        self.assertIn("ball_possession", flat)
        self.assertEqual(flat["ball_possession"]["home"], "55%")
        self.assertEqual(flat["total_passes"]["away"], 320)

    def test_flatten_stats_alt_homeValue_shape(self):
        raw = {
            "statistics": [
                {
                    "groups": [
                        {
                            "statisticsItems": [
                                {"name": "Accurate passes", "homeValue": "300 (85%)", "awayValue": "250 (80%)"}
                            ]
                        }
                    ]
                }
            ]
        }
        flat = self.svc._flatten_stats(raw)
        self.assertEqual(flat["accurate_passes"]["home"], "300 (85%)")
        self.assertEqual(flat["accurate_passes"]["away"], "250 (80%)")

    def test_flatten_stats_new_nested_value_shape(self):
        raw = {
            "statistics": {
                "groups": {
                    "items": [
                        {
                            "label": "Expected goals (xG)",
                            "homeValue": {"value": "1.23"},
                            "awayValue": {"displayValue": "0.75"},
                        }
                    ]
                }
            }
        }
        flat = self.svc._flatten_stats(raw)
        self.assertEqual(flat["xg"]["home"], "1.23")
        self.assertEqual(flat["xg"]["away"], "0.75")

    def test_normalize_event_tactical_stats_does_not_crash(self):
        event = {
            "id": 111,
            "homeTeam": {"id": 10, "name": "Home"},
            "awayTeam": {"id": 20, "name": "Away"},
            "homeScore": {"current": 2},
            "awayScore": {"current": 1},
            "startTimestamp": 1700000000,
        }

        stats_raw = {
            "statistics": [
                {
                    "groups": [
                        {
                            "statisticsItems": [
                                {"name": "Ball possession", "home": {"value": "55%"}, "away": {"value": "45%"}},
                                {"name": "Total shots", "home": {"value": 10}, "away": {"value": 8}},
                                {"name": "Shots on target", "home": {"value": 5}, "away": {"value": 3}},
                                {"name": "Expected goals (xG)", "home": {"value": "1.2"}, "away": {"value": "0.7"}},
                                {"name": "Total passes", "home": {"value": 450}, "away": {"value": 360}},
                                {"name": "Accurate passes", "home": {"value": "380 (84%)"}, "away": {"value": "280 (78%)"}},
                            ]
                        }
                    ]
                }
            ]
        }

        out = self.svc.normalize_event_tactical_stats(event=event, team_id=10, stats_raw=stats_raw)
        self.assertFalse(out.get("estimated"))
        self.assertEqual(out["match_info"]["result"], "W")
        self.assertEqual(out["possession_control"]["possession_percent"], 55.0)
        self.assertEqual(out["expected_metrics"]["xG"], 1.2)
        self.assertIsNotNone(out["possession_control"]["passes_per_minute"])


if __name__ == "__main__":
    unittest.main()
