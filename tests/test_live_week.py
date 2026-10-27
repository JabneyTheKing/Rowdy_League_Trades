import unittest
from scripts.update import live_scoring_week

class LiveWeekTests(unittest.TestCase):
    state = {'season': '2026', 'season_type': 'regular', 'week': 7}

    def test_includes_played_week_despite_unfinalized_league(self):
        self.assertEqual(live_scoring_week(self.state, '2026', 6, [{'stats': {'off_snp': 1}}]), 7)

    def test_does_not_include_unplayed_week(self):
        for rows in ([], [{'stats': {}}], [{'stats': {'gms_active': 1}}]):
            self.assertIsNone(live_scoring_week(self.state, '2026', 6, rows))

    def test_does_not_include_wrong_season_or_postseason(self):
        rows = [{'stats': {'pass_att': 1}}]
        self.assertIsNone(live_scoring_week(self.state, '2025', 6, rows))
        self.assertIsNone(live_scoring_week(dict(self.state, season_type='post'), '2026', 6, rows))
        self.assertIsNone(live_scoring_week(self.state, '2026', 7, rows))
