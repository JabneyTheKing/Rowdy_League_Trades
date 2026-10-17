"""Conservative historical wire pools and temporary coverage for lineup holes."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

POSITIONS=('QB','RB','WR','TE','K','DEF')
METHOD=("Use rostered players with recorded game participation first. Fill remaining legal slots with a temporary "
        "waiver estimate: the mean of the five highest-scoring available players at that position that week (fewer if fewer exist). "
        "Availability is reconstructed from the draft and completed league transactions: unowned at the first NFL game's calendar-day "
        "start, clear of the league's drop-to-waiver delay, and not acquired by any team during that NFL week. "
        "Exclude players already in the hypothetical roster. Multiple replacement slots use distinct candidates from that sample, "
        "each valued at the sample mean; a sample player cannot cover two slots. Use actual league scoring, not top-12/24 starter averages. "
        "Replacements do not persist to future weeks or count as real transactions. This is a hindsight, optimistic pickup assumption, "
        "not guaranteed claim success or a forecast. Nonparticipation can reflect injury, bye or another absence; no injury diagnosis is inferred. "
        "No auto-upgrade for a participating starter who scored poorly. Partial weeks get no replacement estimates until complete. "
        "All roster scenarios use this same rule. No cap/FAAB constraints or changes to other managers' choices are simulated.")


def build_context(picks, transactions, starts, weekly, players, stat_rows, partial_week=None, waiver_days=2):
    try:
        from .advanced_trackers import participated
    except ImportError:
        from advanced_trackers import participated
    ordered=sorted((t for t in transactions if t.get('status')=='complete'),key=lambda t:(t['status_updated'],t['transaction_id']))
    pools={};active={}
    for w, scores in weekly.items():
        week=int(w)
        date=starts.get(week, starts.get(w))
        start=datetime.fromisoformat(date).replace(tzinfo=ZoneInfo('America/New_York'))
        next_date=starts.get(week+1,starts.get(str(week+1)))
        end=datetime.fromisoformat(next_date).replace(tzinfo=start.tzinfo) if next_date else start+timedelta(days=7)
        begin_ms=int(start.timestamp()*1000);end_ms=int(end.timestamp()*1000)
        owners={str(p['player_id']):p['roster_id'] for p in picks};last_drop={}
        acquisitions=set()
        for t in ordered:
            if t['status_updated']<begin_ms:
                for pid in (t.get('drops') or {}):owners.pop(pid,None);last_drop[pid]=t['status_updated']
                owners.update(t.get('adds') or {})
            elif t['status_updated']<end_ms:
                acquisitions.update(t.get('adds') or {})
        active[w]=[pid for pid,value in scores.items() if participated(stat_rows[w].get(pid,{}),value)]
        pools[w]={pos:[] for pos in POSITIONS}
        for pid in active[w]:
            pos=players.get(pid,{}).get('position')
            if pos not in pools[w] or pid in owners or pid in acquisitions:continue
            if pid in last_drop and last_drop[pid]+waiver_days*86400000>begin_ms:continue
            pools[w][pos].append({'player_id':pid,'points':scores[pid]})
        for pool in pools[w].values():pool.sort(key=lambda r:(-r['points'],r['player_id']))
    return {'pools':pools,'active':active,'partial_week':partial_week,'methodology':METHOD,'sample_size':5}


def lineup_with_cover(roster, slots, players, points, week, context=None, restored=()):
    try:
        from .advanced_trackers import optimal_lineup
    except ImportError:
        from advanced_trackers import optimal_lineup
    if context is None or context.get('partial_week')==int(week):
        return optimal_lineup(roster,slots,players,points)
    roster=set(roster);active=set(context['active'][str(week)])|set(restored)
    eligible=roster & active
    metadata=dict(players);values=dict(points);candidates=set(eligible);proxies=set();samples={}
    for pos,pool in context['pools'][str(week)].items():
        sample=[p for p in pool if p['player_id'] not in roster][:context['sample_size']]
        if not sample:continue
        average=round(sum(p['points'] for p in sample)/len(sample),2)
        samples[pos]={'average':average,'players':sample}
        for i,entry in enumerate(sample):
            proxy=f'__wire_{pos}_{i+1}'
            metadata[proxy]={'position':pos,'full_name':f'Waiver cover ({pos})'}
            values[proxy]=average;proxies.add(proxy);candidates.add(proxy)
    result=optimal_lineup(candidates,slots,metadata,values,replacement_ids=proxies)
    replacements=[]
    for row in result['lineup']:
        pid=row['player_id']
        if pid in proxies:
            pos=metadata[pid]['position'];row['replacement']=True
            replacements.append({'slot':row['slot'],'position':pos,'points':row['points'],**samples[pos]})
    result['waiver_replacements']=replacements
    result['replacement_points']=round(sum(r['points'] for r in replacements),2)
    result['unavailable_roster_players']=sorted(roster-active)
    result['unfilled_slots']=[r['slot'] for r in result['lineup'] if r['player_id'] is None]
    return result


def write_audit(report,root):
    def name(pid):return report['players'].get(pid,{}).get('full_name') or pid
    lines=['# Weekly hypothetical waiver coverage','',report['waiver_replacements']['methodology'],'',
           f"Updated {report['updated_at']}. Through Week {report['through_week']}.",'',
           'The samples below belong to each hypothetical roster; they are not real claims. All source pool candidates are stored in data/report.json.','',
           '| Team | View | Week | Scenario | Slot | Estimated points | Available sample: player (actual points) |',
           '|---|---|---:|---|---|---:|---|']
    for view in ('team_impact','injury_adjusted'):
        for key,c in report[view].items():
            for week in c['weeks']:
                for scenario in ('drafted','trades_only','wire_only','all_moves'):
                    for row in week[scenario].get('waiver_replacements',[]):
                        sample=', '.join(f"{name(p['player_id'])} ({p['points']:.2f})" for p in row['players'])
                        lines.append(f"| {key.replace('_',' ').title()} | {view} | {week['week']} | {scenario} | {row['slot']} | {row['points']:.2f} | {sample} |")
    (root/'reports/waiver_replacement_methodology.md').write_text('\n'.join(lines)+'\n')


def write_krunky_analysis(report,root):
    c=report['team_impact']['krunky'];t=c['totals'];adjusted=report['injury_adjusted']['krunky']
    weeks=c['weeks'];best=max(weeks,key=lambda w:w['trade_impact'],default=None);worst=min(weeks,key=lambda w:w['trade_impact'],default=None)
    def fmt(v):return f'{v:+.2f}'
    effect='added' if t['trade_impact']>=0 else 'cost'
    lines=['# How Krunky’s trades have impacted the season','',
           f"Updated {report['updated_at']}. Through Week {report['through_week']}"+(' (partial).' if report.get('partial_week') else ' (complete).'),'',
           f"Under the stated lineup and waiver assumptions, Krunky’s trades have **{effect} {abs(t['trade_impact']):.2f} potential starting-lineup points** compared with making the recorded waiver/free-agent moves without making the trades. "
           'This is a comparison of weekly optimal lineups, not simply all points received minus all points sent. A bench upgrade earns nothing unless it changes a legal starting lineup.','',
           '## We do not assume he leaves bye or injury holes at zero','',METHOD,'',
           'The drafted roster is a starting inventory, not a requirement to field unavailable players. Kicker and defense are covered too when those slots have no suitable rostered player. '
           'This matters for Krunky because the original draft did not include a defense: comparing later roster moves with a permanent zero at that slot would exaggerate improvement.','',
           '## Four comparisons','',
           '| Roster scenario | Season-to-date optimal points, including temporary cover |','|---|---:|',
           f"| Original drafted team | {t['drafted']:.2f} |",f"| Draft plus eligible trades only | {t['trades_only']:.2f} |",
           f"| Draft plus recorded waiver/free-agent moves only | {t['wire_only']:.2f} |",f"| Team after all eligible moves | {t['all_moves']:.2f} |",'',
           f"**Trade impact with wire moves held fixed: {fmt(t['trade_impact'])}.** All moves minus wire-only is the main measure of how trading changed the team’s available starting production.",'',
           f"**Trades considered without wire moves: {fmt(t['trade_only_impact'])}.** This answers a different question: how did trades change the original draft, with temporary waiver coverage allowed on both sides?",'',
           f"**Wire baseline impact: {fmt(t['wire_impact'])}.** This is wire-only minus the covered draft baseline. Together with the main trade impact, it equals **{fmt(t['total_impact'])} total improvement**.",'',
           f"The trade/wire interaction is **{fmt(t['interaction'])}**, already included in the main trade impact. It measures how the value of trading changes when the recorded wire moves are also available; it must not be added again.",'',
           '## When the benefit or cost occurred','',
           '| Week | Draft with cover | Wire-only with cover | All moves with cover | Trading impact |','|---:|---:|---:|---:|---:|']
    for w in weeks:lines.append(f"| {w['week']} | {w['drafted']['points']:.2f} | {w['wire_only']['points']:.2f} | {w['all_moves']['points']:.2f} | {fmt(w['trade_impact'])} |")
    if best:lines+=['',f"The highest weekly trading impact was Week {best['week']} ({fmt(best['trade_impact'])}); the lowest was Week {worst['week']} ({fmt(worst['trade_impact'])})."]
    lines+=['','## Injury-adjusted sensitivity','',
            f"With the separately documented injury estimates, the trade-impact figure is **{fmt(adjusted['totals']['trade_impact'])}**, a change of **{fmt(adjusted['injury_swing']['trade_impact'])}**. "
            'The same waiver cover applies, but a player restored by a supported injury estimate can fill the slot instead. Injury credit and waiver cover are never both assigned to the same slot. '
            'This remains a limited estimate: unverified injuries and insufficient earlier baselines are not invented.','',
            '## What this does and does not establish','',
            'These figures describe hindsight potential under explicit assumptions. They do not prove how many actual wins the trades created: that would require actual start/sit choices and matchup outcomes. '
            'They do not value future draft picks or long-term dynasty value. The same real-world waiver availability is held fixed across hypothetical worlds, and the mean of top available performers is an optimistic retrospective pickup assumption. '
            'The model does not claim the manager would have known the scores, won every claim, or made the same decisions in a different season. Only eligible roster transactions since August 23 count.','',
            '[Weekly lineup details](krunky_team_impact.md) · [Waiver samples and methodology](waiver_replacement_methodology.md) · [Injury-adjusted details](krunky_injury_adjusted.md) · [Latest visuals](latest_visuals.md)']
    (root/'reports/krunky_season_trade_impact.md').write_text('\n'.join(lines)+'\n')
