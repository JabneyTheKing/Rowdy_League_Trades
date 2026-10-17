import unittest
from scripts.injury_adjustment import Tables, normalized_name, adjust_scores, adjusted_team, map_evidence


def fixtures():
    players={'p':{'full_name':'Test Player','position':'RB','team':'KC'}}
    weekly={str(w):{'p':v,'KC':5} for w,v in enumerate([10,20,0,100],1)}
    rows={str(w):{'p':{'team':'KC','date':f'2026-09-{w*7:02d}','stats':{'gp':1} if w!=3 else {'gms_active':1},
                       'player':{'injury_status':'IR'}},
                  'KC':{'date':f'2026-09-{w*7:02d}','stats':{'gp':1}}} for w in range(1,5)}
    evidence={'weekly':{str(w):{'url':f'https://www.nfl.com/{w}','rows':[], 'complete':True} for w in range(1,5)},'reserve':{},'errors':[]}
    evidence['weekly']['3']['rows']=[{'name':'Test Player','position':'RB','injury':'Knee','status':'Out'}]
    return players,weekly,rows,evidence


class InjuryTests(unittest.TestCase):
    def test_actual_scores_untouched_prior_games_only_and_current_status_ignored(self):
        players,weekly,rows,evidence=fixtures()
        adjusted,audit=adjust_scores(weekly,rows,players,evidence,4)
        self.assertEqual(adjusted['3']['p'],15)
        self.assertEqual(weekly['3']['p'],0)
        self.assertEqual([r['week'] for r in audit['adjustments'][0]['sample']],[1,2])
        self.assertEqual(adjusted['1']['p'],10)

    def test_bye_and_unplayed_games_never_get_estimates(self):
        players,weekly,rows,evidence=fixtures();del rows['3']['KC']
        self.assertEqual(adjust_scores(weekly,rows,players,evidence,4)[0]['3']['p'],0)

    def test_out_label_does_not_override_actual_participation(self):
        players,weekly,rows,evidence=fixtures();rows['3']['p']['stats']={'off_snp':1}
        self.assertEqual(adjust_scores(weekly,rows,players,evidence,4)[0]['3']['p'],0)

    def test_insufficient_or_injury_listed_sample_is_not_imputed(self):
        players,weekly,rows,evidence=fixtures()
        evidence['weekly']['1']['rows']=[{'name':'Test Player','position':'RB','injury':'Ankle','status':'Questionable'}]
        adjusted,audit=adjust_scores(weekly,rows,players,evidence,4)
        self.assertEqual(adjusted['3']['p'],0)
        self.assertEqual(audit['insufficient_baselines'][0]['sample_games'],1)

    def test_partial_week_and_healthy_scratch_not_imputed(self):
        players,weekly,rows,evidence=fixtures();evidence['weekly']['3']['complete']=False
        self.assertEqual(adjust_scores(weekly,rows,players,evidence,4)[0]['3']['p'],0)
        evidence['weekly']['3']['complete']=True;evidence['weekly']['3']['rows']=[]
        self.assertEqual(adjust_scores(weekly,rows,players,evidence,4)[0]['3']['p'],0)

    def test_ir_minimum_counts_games_not_byes_and_stops_at_four(self):
        players,weekly,rows,evidence=fixtures()
        evidence['reserve']={'2026-08':{'rows':[{'name':'Test Player','team':'KC','date':'2026-08-30',
                                             'description':'Reserve/Injured','source':'https://www.nfl.com/ir'}]}}
        for w in range(1,7):
            weekly[str(w)]={'p':0,'KC':5}
            rows[str(w)]={'p':{'team':'KC','stats':{}},'KC':{'date':f'2026-10-{w:02d}','stats':{'gp':1}}}
        del rows['2']['KC']
        _,confirmed,_,_=map_evidence(evidence,players,rows,weekly,6)
        self.assertEqual([w for w in ['1','2','3','4','5','6'] if confirmed.get(w,{}).get('p',{}).get('kind')=='ir_minimum'],['1','3','4','5'])

    def test_html_table_and_next_page(self):
        parser=Tables();parser.feed('<table><tr><td><a href="/p">Test Player</a></td><td>RB</td><td>Knee</td><td>DNP</td><td>Out</td></tr></table><a href="/next?after=x">Next Page</a>')
        self.assertEqual(parser.rows,[['Test Player','RB','Knee','DNP','Out']])
        self.assertEqual(parser.next_url,'https://www.nfl.com/next?after=x')
        self.assertEqual(normalized_name('Kenneth Walker III'),'kennethwalker')

    def test_adjustment_reoptimizes_bench_not_added_blindly(self):
        from scripts.advanced_trackers import team_impact
        players={'p':{'position':'RB'},'backup':{'position':'RB'}}
        picks=[{'player_id':p,'roster_id':1} for p in players]
        actual=team_impact(picks,[],1,['RB'],players,{'1':{'p':0,'backup':12}},1)
        actual['current_roster']=list(players)
        audit={'adjustments':[{'week':1,'player_id':'p','estimated':15}], 'insufficient_baselines':[],'source_errors':[]}
        result=adjusted_team(actual,{'1':{'p':15,'backup':12}},players,['RB'],audit)
        self.assertEqual(result['totals']['all_moves'],15)
        self.assertEqual(result['totals']['trade_impact'],0)
        self.assertEqual(result['injury_swing']['total_impact'],0) # Both worlds get same treatment.
