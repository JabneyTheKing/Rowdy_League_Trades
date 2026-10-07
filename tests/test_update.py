import unittest
from scripts.update import score, normalize, evaluate, leaderboard, infer_week, stat_map, waiver_champion, acquisition_results, rebuild_master, on_or_after
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

    def test_waiver_points_stop_when_player_leaves_roster(self):
        managers = {'1': {'name': 'Manager', 'team': 'Team'}}
        claim = {'transaction_id': 'claim', 'type': 'waiver', 'status': 'complete',
                 'status_updated': datetime(2026, 9, 15, tzinfo=timezone.utc).timestamp() * 1000,
                 'adds': {'p': 1}, 'settings': {'waiver_bid': 7}}
        trade = {'transaction_id': 'trade', 'type': 'trade', 'status': 'complete',
                 'status_updated': datetime(2026, 10, 2, tzinfo=timezone.utc).timestamp() * 1000,
                 'drops': {'p': 1}}
        weeks = {1: '2026-09-10', 2: '2026-09-17', 3: '2026-09-24', 4: '2026-10-01'}
        weekly = {'1': {'p': 100}, '2': {'p': 10}, '3': {'p': 20}, '4': {'p': 30}}
        result = waiver_champion([trade, claim], managers, weeks, weekly, 4)
        self.assertEqual(result['claims'][0]['first_week'], 2)
        self.assertEqual(result['claims'][0]['last_week'], 4)
        self.assertEqual(result['claims'][0]['points'], 60)
        self.assertEqual(result['standings'][0]['faab_spent'], 7)

    def test_free_agent_add_is_not_a_waiver_claim(self):
        managers = {'1': {'name': 'Manager', 'team': 'Team'}}
        add = {'transaction_id': 'add', 'type': 'free_agent', 'status': 'complete',
               'status_updated': 1, 'adds': {'p': 1}}
        result = waiver_champion([add], managers, {}, {}, 0)
        self.assertEqual(result['claims'], [])

    def test_august_23_tracking_cutoff_uses_eastern_date(self):
        before = {'created': datetime(2026, 8, 22, 23, 59,
                                      tzinfo=timezone.utc).timestamp() * 1000}
        # 04:00 UTC is midnight EDT on August 23.
        boundary = {'created': datetime(2026, 8, 23, 4, 0,
                                        tzinfo=timezone.utc).timestamp() * 1000}
        self.assertFalse(on_or_after(before, '2026-08-23'))
        self.assertTrue(on_or_after(boundary, '2026-08-23'))

    def test_rebuild_master_combines_three_components(self):
        trades = [{'roster_id': 1, 'manager': 'A', 'team': 'A', 'delta': -5,
                   'trade_count': 1}]
        waivers = {'standings': [{'roster_id': 1, 'points': 20, 'claim_count': 2}]}
        free_agents = {'standings': [{'roster_id': 1, 'points': 12.5, 'claim_count': 3}],
                       'claims': []}
        result = rebuild_master(trades, waivers, free_agents)
        self.assertEqual(result['standings'][0]['score'], 27.5)

    def test_free_agent_pickup_uses_same_ownership_scoring(self):
        managers = {'1': {'name': 'Manager', 'team': 'Team'}}
        add = {'transaction_id': 'add', 'type': 'free_agent', 'status': 'complete',
               'status_updated': datetime(2026, 9, 15, tzinfo=timezone.utc).timestamp() * 1000,
               'adds': {'p': 1}}
        result = acquisition_results([add], managers, {2: '2026-09-17'},
                                     {'2': {'p': 9.5}}, 2, 'free_agent')
        self.assertEqual(result['standings'][0]['points'], 9.5)

    def test_acquisition_subtracts_drop_from_same_transaction(self):
        managers = {'1': {'name': 'Manager', 'team': 'Team'}}
        claim = {'transaction_id': 'claim', 'type': 'waiver', 'status': 'complete',
                 'status_updated': datetime(2026, 9, 15, tzinfo=timezone.utc).timestamp() * 1000,
                 'adds': {'new': 1}, 'drops': {'old': 1},
                 'settings': {'waiver_bid': 4}}
        result = waiver_champion([claim], managers, {2: '2026-09-17'},
                                  {'2': {'new': 10, 'old': 5}}, 2)
        row = result['claims'][0]
        self.assertEqual(row['pickup_points'], 10)
        self.assertEqual(row['dropped_points'], 5)
        self.assertEqual(row['points'], 5)
        self.assertEqual(result['standings'][0]['points'], 5)


if __name__ == '__main__':
    unittest.main()
