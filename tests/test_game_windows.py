import unittest
from datetime import datetime, timezone
from scripts.update import player_first_week, evaluate, acquisition_results


class GameWindowTests(unittest.TestCase):
    starts = {5: '2026-10-08', 6: '2026-10-15'}
    dates = {'5': {'sun': '2026-10-11', 'thu': '2026-10-08', 'drop': '2026-10-11'}}

    def move(self, day, kind='free_agent', adds=None, drops=None):
        return {'transaction_id': str(day), 'status': 'complete', 'type': kind,
                'status_updated': datetime(2026, 10, day, 12, tzinfo=timezone.utc).timestamp()*1000,
                'adds': adds or {}, 'drops': drops or {}}

    def test_friday_trade_counts_sunday_but_not_thursday(self):
        move = self.move(9)
        weeks = {p: player_first_week(move, p, self.starts, self.dates, 5) for p in ('sun','thu')}
        trade = {'first_scoring_week': min(weeks.values()), 'player_first_scoring_week': weeks,
                 'sides': [{'received': ['sun','thu'], 'sent': []}]}
        weekly = {'5': {'sun': 15.8, 'thu': 3.4}, '6': {'sun': 10, 'thu': 5}}
        self.assertEqual(evaluate(trade, weekly, 5)['sides'][0]['received_points'], 15.8)
        self.assertEqual(evaluate(trade, weekly, 6)['sides'][0]['received_points'], 30.8)

    def test_friday_pickups_subtract_sunday_drops(self):
        for kind in ('waiver', 'free_agent'):
            move = self.move(9, kind, {'sun': 1}, {'drop': 1})
            result = acquisition_results([move], {'1': {'name':'A','team':'A'}}, self.starts,
                {'5': {'sun':10, 'drop':5}}, 5, kind, game_dates=self.dates)
            self.assertEqual(result['standings'][0]['points'], 5)

    def test_release_before_sunday_stops_pickup_scoring(self):
        add = self.move(7, adds={'sun':1})
        for day in (9,11):
            release = self.move(day, drops={'sun':1})
            result = acquisition_results([add,release], {'1': {'name':'A','team':'A'}}, self.starts,
                {'5': {'sun':10}}, 5, 'free_agent', game_dates=self.dates)
            self.assertEqual(result['standings'][0]['points'], 0)

    def test_thursday_drop_points_before_friday_add_are_excluded(self):
        move = self.move(9, adds={'sun':1}, drops={'thu':1})
        result = acquisition_results([move], {'1': {'name':'A','team':'A'}}, self.starts,
            {'5': {'sun':10,'thu':50}}, 5, 'free_agent', game_dates=self.dates)
        self.assertEqual(result['standings'][0]['points'], 10)
