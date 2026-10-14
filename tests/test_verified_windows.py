import unittest
from scripts.update import trade_scoring_windows, evaluate


class VerifiedWindowTests(unittest.TestCase):
    def test_verified_week_beats_same_day_exclusion(self):
        t={'transaction_id':'t','status_updated':1790835380582,'adds':{'a':1},'drops':{'b':1}}
        config={'first_scoring_week_overrides':{'t':4}}
        first, players=trade_scoring_windows(t,config,{4:'2026-10-01'},
                                           {'4':{'a':'2026-10-04','b':'2026-10-01'}},4)
        self.assertEqual(players,{'a':4,'b':4})
        result=evaluate({'first_scoring_week':first,'player_first_scoring_week':players,
                         'sides':[{'received':['a'],'sent':['b']}]},
                         {'4':{'a':11.5,'b':10.9}},4)
        self.assertEqual(result['sides'][0]['delta'],0.6)

    def test_player_exception_still_excludes_pretrade_game(self):
        t={'transaction_id':'t','status_updated':1791526598635,'adds':{'a':1,'b':1}}
        config={'first_scoring_week_overrides':{'t':5},
                'player_first_scoring_week_overrides':{'t':{'b':6}}}
        self.assertEqual(trade_scoring_windows(t,config,{}, {},5),(5,{'a':5,'b':6}))
