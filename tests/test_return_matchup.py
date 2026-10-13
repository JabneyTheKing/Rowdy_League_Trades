import unittest
from scripts.update import conner_metcalf


class ReturnMatchupTests(unittest.TestCase):
    def rows(self, stats):
        return [{'player_id':'4137', 'stats':stats}]

    def test_old_scores_and_active_only_do_not_start(self):
        p={'stats/6':self.rows({'gms_active':1})}
        r=conner_metcalf(p, {'5':{'5846':100,'4137':20},'6':{'5846':30,'4137':0}},6)
        self.assertIsNone(r['first_scoring_week'])
        self.assertEqual((r['metcalf_points'],r['conner_points']),(0,0))

    def test_zero_point_return_starts_both_counters_and_recalculates(self):
        p={'stats/6':self.rows({'gms_active':1}), 'stats/7':self.rows({'off_snp':5}),
           'stats/8':self.rows({})}
        w={'6':{'5846':100,'4137':0},'7':{'5846':12,'4137':0},'8':{'5846':8,'4137':0}}
        r=conner_metcalf(p,w,7)
        self.assertEqual(r['first_scoring_week'],7)
        self.assertEqual(r['metcalf_points'],12)
        self.assertEqual(conner_metcalf(p,w,8)['metcalf_points'],20)
        self.assertEqual(conner_metcalf(p,w,8)['metcalf_points'],20)
