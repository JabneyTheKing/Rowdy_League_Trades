import unittest
from scripts.update import score, normalize, evaluate, leaderboard, infer_week, stat_map
from datetime import datetime, timezone


class TrackerTests(unittest.TestCase):
    def test_te_premium_and_negative_points(self):
        self.assertEqual(score({'rec': 6, 'bonus_rec_te': 6, 'rec_yd': 57, 'fum_lost': 1},
                               {'rec': .5, 'bonus_rec_te': .5, 'rec_yd': .1, 'fum_lost': -2}), 9.7)

    def test_three_team_pick_ownership(self):
        t = {'transaction_id': 't', 'status_updated': 1, 'roster_ids': [1, 2, 3],
             'adds': {'a': 1, 'b': 2, 'c': 3}, 'drops': {'a': 3, 'b': 1, 'c': 2},
             'draft_picks': [{'owner_id': 1, 'previous_owner_id': 2, 'roster_id': 3, 'season': '2027', 'round': 2}]}
        n = normalize(t, {str(i): {'name': str(i)} for i in (1, 2, 3)}, 4)
        self.assertEqual(n['sides'][0]['received'], ['a'])
        self.assertEqual(n['sides'][0]['sent'], ['b'])
        self.assertEqual(len(n['sides'][0]['picks_received']), 1)
        self.assertEqual(len(n['sides'][1]['picks_sent']), 1)
        self.assertEqual(n['sides'][2]['picks_sent'], [])

    def test_scores_continue_after_roster_change_and_exclude_previous_weeks(self):
        t = {'id': 'x', 'first_scoring_week': 3, 'sides': [{'received': ['a'], 'sent': ['b']}]}
        weekly = {'2': {'a': 100, 'b': 0}, '3': {'a': 12, 'b': 3}, '4': {'a': 8, 'b': 4}}
        r = evaluate(t, weekly, 4)['sides'][0]
        self.assertEqual(r['delta'], 13)
        self.assertEqual(r['received_points'], 20)

    def test_pending_not_zero_point_loss(self):
        t = {'first_scoring_week': 5, 'sides': [{'received': ['a'], 'sent': ['b']}]}
        self.assertEqual(evaluate(t, {}, 4)['sides'][0]['status'], 'pending')

    def test_missing_scores_excluded_from_leaderboard(self):
        t = {'first_scoring_week': 1, 'sides': [{'roster_id': 1, 'received': ['a'], 'sent': ['b']}]}
        r = evaluate(t, {'1': {'a': 20}}, 1)
        board = leaderboard([r], {'1': {'name': 'A', 'team': 'A'}})
        self.assertEqual(board[0]['delta'], 0)
        self.assertEqual(board[0]['incomplete_trades'], 1)

    def test_first_full_week_uses_date_not_sleeper_leg(self):
        ts = datetime(2026, 9, 29, 16, tzinfo=timezone.utc).timestamp() * 1000
        self.assertEqual(infer_week({'status_updated': ts, 'leg': 3}, {3: '2026-09-24', 4: '2026-10-01'}, 4), 4)

    def test_stats_shape_change_fails(self):
        with self.assertRaises(ValueError):
            stat_map({})


if __name__ == '__main__':
    unittest.main()
