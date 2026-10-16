import unittest
from scripts.advanced_trackers import positional_scores, optimal_lineup, draft_comparison, positional_summary
from scripts.update import evaluate


class AdvancedTrackerTests(unittest.TestCase):
    def test_positional_average_and_actual_participation(self):
        players = {'a': {'position':'TE'}, 'b':{'position':'TE'}, 'zero':{'position':'TE'}, 'ir':{'position':'TE'}}
        points = {'1':{'a':15, 'b':5, 'zero':0, 'ir':0}}
        rows = {'1':{'a':{'stats':{'gp':1}}, 'b':{'stats':{'off_snp':20}},
                     'zero':{'stats':{'off_snp':3}}, 'ir':{'stats':{'gms_active':1}}}}
        adjusted, baseline = positional_scores(points, rows, players, {'TE':2})
        self.assertEqual(baseline['1']['TE']['average'], 10)
        self.assertEqual(adjusted['1'], {'a':5,'b':-5,'zero':-10,'ir':0})

    def test_exact_assignment_saves_multi_position_player_for_needed_slot(self):
        players = {'a':{'fantasy_positions':['RB','WR']}, 'b':{'position':'RB'}, 'c':{'position':'TE'}}
        result = optimal_lineup(players, ['RB','WR','FLEX'], players, {'a':20,'b':19,'c':18})
        self.assertEqual(result['points'],57)
        self.assertEqual([r['player_id'] for r in result['lineup']], ['b','a','c'])
        self.assertEqual(len({r['player_id'] for r in result['lineup']}),3)

    def test_negative_required_slot_and_unfillable_slot(self):
        result = optimal_lineup(['d'], ['DEF','QB'], {'d':{'position':'DEF'}}, {'d':-3})
        self.assertEqual(result['points'],-3)
        self.assertEqual(result['filled_slots'],1)
        self.assertIsNone(result['lineup'][1]['player_id'])

    def test_draft_vs_trades_no_retroactivity_and_no_pickup_pool(self):
        picks = [{'player_id':'a','roster_id':3}]
        players = {p:{'position':'RB'} for p in ['a','b','waiver']}
        trade = {'id':'t','processed_at':1,'first_scoring_week':2,
                 'sides':[{'roster_id':3,'received':['b'],'sent':['a']}]}
        weekly = {str(w):{'a':10,'b':20,'waiver':100} for w in [1,2,3]}
        result = draft_comparison(picks,[trade],3,['RB'],players,weekly,3)
        self.assertEqual([r['delta'] for r in result['weeks']],[0,10,10])
        self.assertEqual(result['delta'],20)
        self.assertEqual(result['draft_roster'],['a'])
        self.assertNotIn('waiver', result['weeks'][-1]['trade_roster'])
        # Retrying rebuilds, rather than appends, the same totals.
        self.assertEqual(result,draft_comparison(picks,[trade],3,['RB'],players,weekly,3))

    def test_player_window_exception_and_retrade_remove_old_owner(self):
        picks=[{'player_id':'a','roster_id':3}]
        players={p:{'position':'RB'} for p in ['a','b','c']}
        t1={'id':'1','processed_at':1,'first_scoring_week':1,
            'player_first_scoring_week':{'a':2,'b':2},
            'sides':[{'roster_id':3,'received':['b'],'sent':['a']}]}
        t2={'id':'2','processed_at':2,'first_scoring_week':3,
            'sides':[{'roster_id':3,'received':['c'],'sent':['b']}]}
        weekly={str(w):{'a':10,'b':20,'c':15} for w in [1,2,3]}
        result=draft_comparison(picks,[t2,t1],3,['RB'],players,weekly,3)
        self.assertEqual([r['trade_roster'] for r in result['weeks']],[['a'],['b'],['c']])
        self.assertEqual(result['delta'],15)

    def test_positional_trade_preserves_player_windows(self):
        trade={'id':'1','first_scoring_week':1,'player_first_scoring_week':{'a':2},
               'sides':[{'roster_id':1,'received':['a'],'sent':['b']}]}
        result=evaluate(trade,{'1':{'a':100,'b':2},'2':{'a':3,'b':1}},2)
        self.assertEqual(result['sides'][0]['delta'],0)

    def test_jabney_drop_cost_and_krunky_trade_only(self):
        raw={'claims':[{'transaction_id':'t','player_id':'a','roster_id':3,'points':5}]}
        adj={'claims':[{'transaction_id':'t','player_id':'a','roster_id':3,'dropped_player_id':'b',
                       'first_week':1,'last_week':1,'points':2,'status':'scored'}]}
        empty={'claims':[]}
        j=positional_summary('jabney',3,[],[],raw,adj,empty,empty)
        k=positional_summary('krunky',3,[],[],raw,adj,empty,empty)
        self.assertEqual((j['raw_total'],j['total']),(5,2))
        self.assertEqual(j['moves'][0]['sent'],['b'])
        self.assertEqual(k['total'],0)

class TeamImpactTests(unittest.TestCase):
    def test_bench_gain_is_not_lineup_gain_and_components_reconcile(self):
        from scripts.advanced_trackers import team_impact
        picks=[{'player_id':'a','roster_id':1},{'player_id':'b','roster_id':1}]
        players={p:{'position':'RB'} for p in ['a','b','c','d']}
        events=[{'id':'t','processed_at':1,'kind':'trade',
                 'sent':[{'player_id':'b','roster_id':1,'first_week':1}],
                 'received':[{'player_id':'c','roster_id':1,'first_week':1}]},
                {'id':'w','processed_at':2,'kind':'waiver','sent':[],
                 'received':[{'player_id':'d','roster_id':1,'first_week':1}]}]
        result=team_impact(picks,events,1,['RB'],players,{'1':{'a':20,'b':1,'c':15,'d':25}},1)
        t=result['totals']
        self.assertEqual(t['trade_impact'],0) # Trade gained 14 raw points, all on bench.
        self.assertEqual(t['wire_impact'],5)
        self.assertEqual(t['trade_impact']+t['wire_impact'],t['total_impact'])

    def test_standalone_drop_removes_player_only_in_wire_worlds(self):
        from scripts.advanced_trackers import team_impact
        picks=[{'player_id':'a','roster_id':1}]
        players={'a':{'position':'WR'}}
        event={'id':'drop','processed_at':1,'kind':'free_agent','received':[],
               'sent':[{'player_id':'a','roster_id':1,'first_week':2}]}
        result=team_impact(picks,[event],1,['WR'],players,{'1':{'a':10},'2':{'a':20}},2)
        self.assertEqual(result['weeks'][0]['all_moves']['points'],10)
        self.assertEqual(result['weeks'][1]['all_moves']['points'],0)
        self.assertEqual(result['weeks'][1]['trades_only']['points'],20)
        self.assertEqual(result['totals']['wire_impact'],-20)

    def test_trade_and_wire_overlap_is_explicit_not_double_counted(self):
        from scripts.advanced_trackers import team_impact
        picks=[{'player_id':'a','roster_id':1}]
        players={p:{'position':'RB'} for p in ['a','b','c']}
        events=[{'id':kind,'kind':kind,'processed_at':i,'sent':[],
                 'received':[{'player_id':pid,'roster_id':1,'first_week':1}]}
                for i,kind,pid in [(1,'trade','b'),(2,'free_agent','c')]]
        t=team_impact(picks,events,1,['RB'],players,{'1':{'a':10,'b':20,'c':25}},1)['totals']
        self.assertEqual(t['trade_only_impact'],10)
        self.assertEqual(t['trade_impact'],0)
        self.assertEqual(t['interaction'],-10)
        self.assertEqual(t['total_impact'],15)
