"""Evidence-limited injury estimates; actual scores are never overwritten."""
import concurrent.futures
from datetime import date, datetime, timezone
from html.parser import HTMLParser
import json
import re
import time
import urllib.parse
import urllib.request

try:
    from .advanced_trackers import participated, optimal_lineup
except ImportError:
    from advanced_trackers import participated, optimal_lineup

NFL = 'https://www.nfl.com'
TEAM_CODES = dict(zip(
    'Cardinals Falcons Ravens Bills Panthers Bears Bengals Browns Cowboys Broncos Lions Packers Texans Colts Jaguars Chiefs Raiders Chargers Rams Dolphins Vikings Patriots Saints Giants Jets Eagles Steelers 49ers Seahawks Buccaneers Titans Commanders'.split(),
    'ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LV LAC LAR MIA MIN NE NO NYG NYJ PHI PIT SF SEA TB TEN WAS'.split()))


def normalized_name(value):
    words = re.sub(r'[^a-z0-9 ]', '', value.lower()).split()
    if words and words[-1] in ('jr','sr','ii','iii','iv','v'):
        words.pop()
    return ''.join(words)


class Tables(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=None; self.cell=None
        self.link=None; self.next_url=None; self.words=[]; self.table_count=0
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=='table': self.table_count+=1
        if tag=='tr': self.row=[]
        if tag in ('td','th') and self.row is not None: self.cell=[]
        if tag=='a': self.link=[attrs.get('href',''),attrs.get('aria-label','')]
    def handle_data(self, data):
        self.words.append(data)
        if self.cell is not None: self.cell.append(data)
        if self.link is not None: self.link[1]+=' '+data
    def handle_endtag(self, tag):
        if tag in ('td','th') and self.cell is not None:
            self.row.append(' '.join(' '.join(self.cell).split())); self.cell=None
        if tag=='tr' and self.row is not None:
            self.rows.append(self.row); self.row=None
        if tag=='a' and self.link is not None:
            if 'next page' in self.link[1].lower(): self.next_url=urllib.parse.urljoin(NFL,self.link[0])
            self.link=None


def download(url):
    request=urllib.request.Request(url,headers={'Cache-Control':'no-cache'})
    with urllib.request.urlopen(request,timeout=25) as response:
        html=response.read().decode('utf-8')
    parser=Tables();parser.feed(html)
    return parser


def collect_evidence(root, season, through, partial_week, tracking_start):
    """Cache completed weekly reports and past months; refresh the latest week/month."""
    path=root/'data/injury_evidence.json'
    cache=json.loads(path.read_text()) if path.exists() else {}
    if cache.get('season')!=str(season): cache={'season':str(season),'weekly':{},'reserve':{}}
    errors=[]; today=datetime.now(timezone.utc).date()
    def weekly_job(week):
        key=str(week);old=cache['weekly'].get(key)
        if old and week < through and old.get('complete'): return key,old,None
        url=f'{NFL}/injuries/league/{season}/reg{week}'
        try:
            parser=download(url);plain=' '.join(parser.words)
            if not re.search(rf'Injuries\s*-\s*WEEK\s*{week}\b',plain,re.I) or str(season) not in plain:
                raise ValueError('Wrong season/week in NFL injury report')
            rows=[{'name':r[0],'position':r[1],'injury':r[2],'practice':r[3],'status':r[4]}
                  for r in parser.rows if len(r)==5 and r[0]!='Player']
            if parser.table_count<10 or len(rows)<30: raise ValueError('Incomplete NFL injury report table')
            return key,{'url':url,'rows':rows,'complete':week!=partial_week,
                        'fetched_at':datetime.now(timezone.utc).isoformat()},None
        except Exception as exc:
            return key,old,f'{url}: {exc}'
    # Capture reserve placements from the project cutoff onward. In-season IR is
    # only evidence for the first four team games, not an indefinite absence.
    begin=date.fromisoformat(tracking_start)
    end=min(today,date(int(season)+1,2,1))
    months=[];year,month=begin.year,begin.month
    while (year,month)<=(end.year,end.month):
        months.append((year,month));year,month=(year+1,1) if month==12 else (year,month+1)
    def reserve_job(ym):
        year,month=ym;key=f'{year}-{month:02d}';old=cache['reserve'].get(key)
        if old and old.get('complete') and ym<(today.year,today.month):return key,old,None
        root_url=f'{NFL}/transactions/league/reserve-list/{year}/{month}'
        known=set((old or {}).get('sources',[])) | {root_url}
        records={(r['date'],r['name'],r['team'],r['description']):r for r in (old or {}).get('rows',[])}
        errors=[];terminal=False;deadline=time.monotonic()+100
        # The archive occasionally serves a stale page for a pagination URL.
        # Keep verified rows, revisit discovered links, and never erase history.
        for scan in range(2):
            queue=sorted(known);seen=set()
            while queue:
                if time.monotonic()>deadline:
                    errors.append('Reserve refresh time budget reached; retained verified records');queue=[];break
                url=queue.pop(0)
                if url in seen:continue
                if len(seen)>=50:
                    errors.append('Reserve pagination limit');break
                seen.add(url)
                try:
                    parser=download(url)
                    if not parser.table_count:raise ValueError('Missing reserve transaction table')
                    dated=[r for r in parser.rows if len(r)==6 and re.fullmatch(r'\d{2}/\d{2}',r[2])]
                    for r in dated:
                        when=f'{year}-{r[2].replace("/","-")}'
                        if when>=tracking_start:
                            entry={'date':when,'name':r[3],
                                   'team':TEAM_CODES.get(r[1].split()[0] if r[1] else ''),
                                   'description':r[5],'source':url}
                            records[(when,r[3],entry['team'],r[5])]=entry
                    at_cutoff=dated and min(f'{year}-{r[2].replace("/","-")}' for r in dated)<tracking_start
                    if not parser.next_url or at_cutoff:terminal=True
                    elif parser.next_url not in seen:
                        known.add(parser.next_url);queue.append(parser.next_url)
                except Exception as exc:errors.append(f'{url}: {exc}')
            # Second pass revisits all discovered pages to reconcile cached responses.
        if not terminal:errors.append('Reserve archive pagination incomplete; retained verified rows only')
        value={'rows':sorted(records.values(),key=lambda r:(r['date'],r['name'])),
               'sources':sorted(known),'complete':terminal and not errors,
               'fetched_at':datetime.now(timezone.utc).isoformat()}
        return key,value,'; '.join(errors) if errors else None
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        jobs=[('weekly',pool.submit(weekly_job,w)) for w in range(1,through+1)]
        jobs += [('reserve',pool.submit(reserve_job,ym)) for ym in months]
        for kind,job in jobs:
            key,value,error=job.result()
            if value:cache[kind][key]=value
            if error:errors.append(error)
    cache['errors']=errors;cache['updated_at']=datetime.now(timezone.utc).isoformat()
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(cache,indent=2,sort_keys=True)+'\n')
    return cache


def map_evidence(evidence, players, stat_rows, weekly, through):
    index={}
    for pid,p in players.items():
        if p.get('position') in ('QB','RB','WR','TE','K'):
            index.setdefault(normalized_name(p.get('full_name') or ''),[]).append(pid)
    def identify(name,position=None):
        ids=index.get(normalized_name(name),[])
        if position: ids=[pid for pid in ids if players[pid].get('position')==position]
        return ids[0] if len(ids)==1 else None
    listed={};confirmed={};unmatched=[]
    for w,entry in evidence['weekly'].items():
        if int(w)>through: continue
        listed[w]={};confirmed[w]={}
        for r in entry['rows']:
            pid=identify(r['name'],r['position'])
            if not pid:
                if r['position'] in ('QB','RB','WR','TE','K'):unmatched.append({'week':int(w),'name':r['name']})
                continue
            if r['injury']:
                listed[w][pid]=r['injury']
                reason=r['injury'].lower()
                noninjury=any(x in reason for x in ('rest','personal','not injury','suspension'))
                if r['status'].lower()=='out' and not noninjury:
                    confirmed[w][pid]={'reason':r['injury'],'source':entry['url'],'kind':'weekly_out'}
    # Use the NFL team's actual participation to exclude byes and unplayed games.
    team_games={}
    for w,rows in stat_rows.items():
        team_games[w]={pid:row.get('date','')[:10] for pid,row in rows.items()
                       if pid in TEAM_CODES.values() and participated(row,weekly[w].get(pid,0)) and row.get('date')}
    for batch in evidence['reserve'].values():
        for row in batch['rows']:
            # Practice-squad injuries, NFI, PUP, and suspensions are not assumed to be NFL IR.
            if row['description'].strip()!='Reserve/Injured':continue
            pid=identify(row['name']);team=row['team']
            if not pid or not team:continue
            eligible=[w for w in sorted(team_games,key=int) if team_games[w].get(team,'')>row['date']][:4]
            for w in eligible:
                confirmed.setdefault(w,{})[pid]={'reason':'Injured reserve: first four team games after placement',
                                                'source':row['source'],'kind':'ir_minimum','placed_on':row['date']}
                listed.setdefault(w,{})[pid]='Injured reserve'
    return listed,confirmed,team_games,unmatched


def adjust_scores(weekly, stat_rows, players, evidence, through, minimum_games=2):
    listed,confirmed,team_games,unmatched=map_evidence(evidence,players,stat_rows,weekly,through)
    adjusted={w:dict(scores) for w,scores in weekly.items()};audit=[];unresolved=[]
    for w in sorted(weekly,key=int):
        for pid,reason in confirmed.get(w,{}).items():
            row=stat_rows[w].get(pid,{})
            # Player-row team is historical; never use today's injury designation.
            team=row.get('team') or (row.get('player') or {}).get('team')
            if not team or team not in team_games[w]:continue
            if participated(row,weekly[w].get(pid,0)):continue
            if w not in evidence['weekly'] or not evidence['weekly'][w].get('complete'):continue
            sample=[]
            for previous in range(1,int(w)):
                pw=str(previous)
                if pw not in evidence['weekly'] or not evidence['weekly'][pw].get('complete'):continue
                if pid in listed.get(pw,{}) or pid in confirmed.get(pw,{}):continue
                value=weekly[pw].get(pid,0)
                if participated(stat_rows[pw].get(pid,{}),value):sample.append({'week':previous,'points':value})
            if len(sample)<minimum_games:
                unresolved.append({'week':int(w),'player_id':pid,'reason':'Not enough prior injury-unlisted games',
                                   'sample_games':len(sample),'source':reason['source']});continue
            estimate=round(sum(x['points'] for x in sample)/len(sample),2)
            adjusted[w][pid]=estimate
            audit.append({'week':int(w),'player_id':pid,'actual':weekly[w].get(pid,0),'estimated':estimate,
                          'sample':sample,**reason})
    other_absences=[]
    for w,points in weekly.items():
        for pid,value in points.items():
            row=stat_rows[w].get(pid,{})
            team=row.get('team') or (row.get('player') or {}).get('team')
            if players.get(pid,{}).get('position') not in ('QB','RB','WR','TE','K'):continue
            if team not in team_games[w] or participated(row,value) or pid in confirmed.get(w,{}):continue
            other_absences.append({'week':int(w),'player_id':pid,'reason':'No qualifying injury evidence; may be healthy scratch or other absence'})
    return adjusted,{'adjustments':audit,'insufficient_baselines':unresolved,'unmatched_names':unmatched,
                     'confirmed':confirmed,'team_games':team_games,'source_errors':evidence.get('errors',[]),'other_absences':other_absences}


def adjusted_team(actual, adjusted, players, slots, audit, replacement_context=None):
    try:
        from .waiver_replacements import lineup_with_cover
    except ImportError:
        from waiver_replacements import lineup_with_cover
    result={'weeks':[],'current_roster':actual['current_roster'],'draft_roster':actual['draft_roster']}
    scenarios=('drafted','trades_only','wire_only','all_moves')
    relevant=set();coverage=[]
    for original in actual['weeks']:
        w=str(original['week']);row={'week':original['week']}
        pool=set()
        for key in scenarios:
            roster=original[key]['roster'];pool.update(roster)
            restored=[r['player_id'] for r in audit['adjustments'] if r['week']==int(w)]
            row[key]=lineup_with_cover(roster,slots,players,adjusted[w],w,replacement_context,restored);row[key]['roster']=roster
        relevant.update((int(w),pid) for pid in pool)
        d,t,wire,all_moves=(row[s]['points'] for s in scenarios)
        row.update({'total_impact':round(all_moves-d,2),'trade_impact':round(all_moves-wire,2),
                    'wire_impact':round(wire-d,2),'trade_only_impact':round(t-d,2),
                    'interaction':round(all_moves-wire-t+d,2)})
        result['weeks'].append(row)
    result['totals']={s:round(sum(r[s]['points'] for r in result['weeks']),2) for s in scenarios}
    result['totals'].update({k:round(sum(r[k] for r in result['weeks']),2) for k in
                            ('total_impact','trade_impact','wire_impact','trade_only_impact','interaction')})
    result['adjustments']=[r for r in audit['adjustments'] if (r['week'],r['player_id']) in relevant]
    result['insufficient_baselines']=[r for r in audit['insufficient_baselines'] if (r['week'],r['player_id']) in relevant]
    result['other_absences']=[r for r in audit.get('other_absences',[]) if (r['week'],r['player_id']) in relevant]
    result['actual_totals']=actual['totals']
    result['injury_swing']={k:round(result['totals'][k]-actual['totals'][k],2) for k in ('trade_impact','wire_impact','total_impact')}
    result['source_errors']=audit['source_errors']
    return result


def write_reports(report,root):
    def name(pid):return report['players'].get(pid,{}).get('full_name') or pid
    for key,c in report['injury_adjusted'].items():
        title='Gibbs of War' if key=='gibbs_of_war' else key.title()
        lines=[f'# {title} — Injury-Adjusted Team Impact', '',
               f"Updated {report['updated_at']}; through Week {report['through_week']}.", '',
               '**Estimate, not actual fantasy points.** The original Team Impact report is unchanged. '
               'The same four roster scenarios and legal starting slots are reoptimized with injury estimates applied equally in every scenario.', '',
               'Only completed-week, zero-participation absences supported by a dated NFL weekly injury OUT report or the first four team games after a documented NFL Reserve/Injured placement qualify. '
               'Byes and unplayed games are excluded. Current injury labels are never applied backward. '
               'An absence is replaced by that player’s mean league points in at least two earlier games with recorded participation and no injury listing in the archived weekly report. '
               'No future games or previous-season points are used. This is an observable participation proxy, not a guarantee of perfect health. '
               'In-game injuries, reduced snaps, PUP/NFI, unverified absences, and longer IR absences without fresh OUT evidence are not adjusted. '
               'Players without a qualifying baseline stay at actual points and are listed below. '
               'Confirmed absence coverage is conservative, so this is not a fully healthy-team simulation.', '',
               'Wire impact = wire-only minus draft. Trade impact = all-moves minus wire-only, including interaction. '
               'The two sum to total improvement. Recorded moves are held fixed; hypothetical caps/budgets and alternate decisions are not modeled. '
               'Only fantasy roster moves from August 23 onward change ownership. Standalone drops affect availability but are not separately scored.', '',
               '| Metric | Actual | Injury-adjusted estimate | Adjustment |', '|---|---:|---:|---:|']
        for metric in ('trade_impact','wire_impact','total_impact'):
            lines.append(f"| {metric.replace('_',' ').title()} | {c['actual_totals'][metric]:+.2f} | {c['totals'][metric]:+.2f} | {c['injury_swing'][metric]:+.2f} |")
        lines += ['', '## Estimated absences', '', '| Week | Player | Actual | Estimate | Earlier sample | Evidence |', '|---:|---|---:|---:|---|---|']
        for row in c['adjustments']:
            sample=', '.join(f"W{x['week']}: {x['points']:.2f}" for x in row['sample'])
            lines.append(f"| {row['week']} | {name(row['player_id'])} | {row['actual']:.2f} | {row['estimated']:.2f} | {sample} | [{row['reason']}]({row['source']}) |")
        if not c['adjustments']:lines.append('| — | No qualifying estimates yet | | | | |')
        lines += ['', '## Confirmed absences without enough baseline data', '']
        lines += [f"- Week {r['week']}: {name(r['player_id'])}; {r['sample_games']} earlier qualifying games. [Evidence]({r['source']})." for r in c['insufficient_baselines']] or ['None.']
        lines += ['', '## Other zero-participation games left unchanged', '',
                  'These are not classified as injuries; they may be healthy scratches or other absences.']
        lines += [f"- Week {r['week']}: {name(r['player_id'])}." for r in c['other_absences']] or ['None.']
        lines += ['', '## Weekly impact', '', '| Week | Actual trade impact | Adjusted trade impact | Actual total gain | Adjusted total gain |', '|---:|---:|---:|---:|---:|']
        for a,b in zip(report['team_impact'][key]['weeks'],c['weeks']):
            lines.append(f"| {a['week']} | {a['trade_impact']:+.2f} | {b['trade_impact']:+.2f} | {a['total_impact']:+.2f} | {b['total_impact']:+.2f} |")
        for row in c['weeks']:
            lines += ['', f"## Week {row['week']} adjusted optimal lineups", '', '| Slot | Wire-only player | Points | All-moves player | Points |', '|---|---|---:|---|---:|']
            for a,b in zip(row['wire_only']['lineup'],row['all_moves']['lineup']):
                lines.append(f"| {a['slot']} | {name(a['player_id']) if a['player_id'] else 'Empty'} | {a['points']:.2f} | {name(b['player_id']) if b['player_id'] else 'Empty'} | {b['points']:.2f} |")
        lines += ['', '## Source health', '', 'Archived NFL injury reports and reserve transactions: `data/injury_evidence.json`.']
        lines += [f'- {e}' for e in c['source_errors']] or ['No retrieval errors this refresh.']
        lines[3:3] = ['## Temporary waiver coverage', '', report.get('waiver_replacements',{}).get('methodology',''), '', 'A restored injury estimate fills its slot before waiver coverage; the same slot never gets both.', '']
        (root/f'reports/{key}_injury_adjusted.md').write_text('\n'.join(lines)+'\n')
