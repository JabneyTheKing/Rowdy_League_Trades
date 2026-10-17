import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from scripts.waiver_replacements import build_context, lineup_with_cover


class WaiverCoverageTests(unittest.TestCase):
    def context(self):
        return {'active':{'1':['a','b','c','d','e','starter']},'partial_week':None,'sample_size':5,
                'pools':{'1':{'RB':[{'player_id':p,'points':v} for p,v in zip('abcde',[20,15,10,5,0])]}}}

    def test_mean_of_top_available_and_bye_filled(self):
        r=lineup_with_cover(['hurt'],['RB'],{'hurt':{'position':'RB'}},{'hurt':0},1,self.context())
        self.assertEqual(r['points'],10)
        self.assertEqual(r['replacement_points'],10)
        self.assertEqual(len(r['waiver_replacements'][0]['players']),5)

    def test_never_upgrade_participating_starter_even_negative_score(self):
        r=lineup_with_cover(['starter'],['RB'],{'starter':{'position':'RB'}},{'starter':-2},1,self.context())
        self.assertEqual(r['points'],-2)
        self.assertFalse(r['waiver_replacements'])

    def test_use_bench_before_wire_and_no_double_fill(self):
        p={'starter':{'position':'RB'},'hurt':{'position':'RB'}}
        r=lineup_with_cover(p,['RB','FLEX'],p,{'starter':4,'hurt':0},1,self.context())
        self.assertEqual(r['points'],14)
        self.assertEqual(len(r['waiver_replacements']),1)
        self.assertEqual(len({x['player_id'] for x in r['lineup']}),2)

    def test_exclude_hypothetical_roster_from_sample(self):
        r=lineup_with_cover(['a'],['RB','FLEX'],{'a':{'position':'RB'}},{'a':20},1,self.context())
        self.assertEqual(r['points'],27.5)
        self.assertNotIn('a',[p['player_id'] for p in r['waiver_replacements'][0]['players']])

    def test_restored_injury_prevents_duplicate_waiver_credit(self):
        r=lineup_with_cover(['hurt'],['RB'],{'hurt':{'position':'RB'}},{'hurt':8},1,self.context(),['hurt'])
        self.assertEqual(r['points'],8);self.assertFalse(r['waiver_replacements'])

    def test_partial_week_does_not_replace_unplayed_game(self):
        c=self.context();c['partial_week']=1
        self.assertEqual(lineup_with_cover(['hurt'],['RB'],{'hurt':{'position':'RB'}},{'hurt':0},1,c)['points'],0)

    def test_ownership_midweek_claim_and_waiver_delay(self):
        def ms(day):return int(datetime.fromisoformat(day).replace(tzinfo=ZoneInfo('America/New_York')).timestamp()*1000)
        players={p:{'position':'RB'} for p in ['owned','recent_drop','midweek','available']}
        picks=[{'player_id':'owned','roster_id':1},{'player_id':'recent_drop','roster_id':2}]
        tx=[{'transaction_id':'d','status':'complete','status_updated':ms('2026-09-08'),'drops':{'recent_drop':2}},
            {'transaction_id':'a','status':'complete','status_updated':ms('2026-09-11'),'adds':{'midweek':2}}]
        scores={'1':{p:10 for p in players}};rows={'1':{p:{'stats':{'gp':1}} for p in players}}
        c=build_context(picks,tx,{1:'2026-09-09'},scores,players,rows,waiver_days=2)
        self.assertEqual([p['player_id'] for p in c['pools']['1']['RB']],['available'])
