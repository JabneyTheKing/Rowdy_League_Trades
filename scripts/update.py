"""Read-only Sleeper ingestion and post-trade production reports; stdlib only."""
import argparse
import concurrent.futures
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import time
import urllib.request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
API = 'https://api.sleeper.app'


def fetch(path):
    for attempt in range(3):
        try:
            request = urllib.request.Request(API + path, headers={'User-Agent': 'RowdyLeagueTradeTracker/1.0'})
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.load(response)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def stat_map(payload):
    # This stats endpoint is undocumented; validate its shape and fail visibly.
    if not isinstance(payload, list) or not payload:
        raise ValueError('Empty or unsupported weekly stats response')
    if any('player_id' not in row or not isinstance(row.get('stats'), dict) for row in payload):
        raise ValueError('Unsupported weekly stats row')
    return {str(row['player_id']): row for row in payload}


def score(stats, settings):
    return float(sum((Decimal(str(value)) * Decimal(str(stats.get(key, 0)))
                      for key, value in settings.items()), Decimal(0)))


def normalize(trade, managers, first_week):
    sides = []
    for roster in trade['roster_ids']:
        picks = trade.get('draft_picks') or []
        sides.append({
            'roster_id': roster, 'manager': managers[str(roster)]['name'],
            'received': sorted(p for p, owner in (trade.get('adds') or {}).items() if owner == roster),
            'sent': sorted(p for p, owner in (trade.get('drops') or {}).items() if owner == roster),
            'picks_received': [p for p in picks if p['owner_id'] == roster and p['previous_owner_id'] != roster],
            'picks_sent': [p for p in picks if p['previous_owner_id'] == roster and p['owner_id'] != roster],
            'faab_received': sum(x['amount'] for x in (trade.get('waiver_budget') or []) if x['receiver'] == roster),
            'faab_sent': sum(x['amount'] for x in (trade.get('waiver_budget') or []) if x['sender'] == roster),
        })
    return {'id': trade['transaction_id'], 'processed_at': trade['status_updated'],
            'first_scoring_week': first_week, 'sides': sides}


def evaluate(trade, weekly, through):
    result = dict(trade)
    result['sides'] = []
    weeks = range(trade['first_scoring_week'], through + 1)
    for side in trade['sides']:
        row = dict(side)
        missing = []
        totals = {}
        for direction in ('received', 'sent'):
            assets = []
            for player in side[direction]:
                values = []
                for week in weeks:
                    value = weekly.get(str(week), {}).get(player)
                    if value is None:
                        missing.append({'player_id': player, 'week': week})
                    else:
                        values.append(value)
                assets.append({'player_id': player, 'points': round(sum(values), 2)})
            row[direction + '_players'] = assets
            totals[direction] = round(sum(p['points'] for p in assets), 2)
        row.update({'received_points': totals['received'], 'sent_points': totals['sent'],
                    'delta': round(totals['received'] - totals['sent'], 2),
                    'missing_scores': missing,
                    'status': 'pending' if trade['first_scoring_week'] > through else ('incomplete' if missing else 'scored')})
        result['sides'].append(row)
    return result


def leaderboard(trades, managers):
    result = []
    for rid, manager in managers.items():
        rows = [s for t in trades for s in t['sides'] if str(s.get('roster_id')) == rid]
        ranked = [s for s in rows if s['status'] == 'scored' and (s['received'] or s['sent'])]
        result.append({'roster_id': int(rid), 'manager': manager['name'], 'team': manager['team'],
                       'trade_count': len(rows), 'scored_trades': len(ranked),
                       'pending_trades': sum(s['status'] == 'pending' for s in rows),
                       'incomplete_trades': sum(s['status'] == 'incomplete' for s in rows),
                       'has_unvalued_assets': any(s.get('picks_received') or s.get('picks_sent') or s.get('faab_received') or s.get('faab_sent') for s in rows),
                       'delta': round(sum(s['delta'] for s in ranked), 2)})
    return sorted(result, key=lambda r: (-r['delta'], r['manager'].lower()))


def infer_week(trade, starts, through):
    date = datetime.fromtimestamp(trade['status_updated'] / 1000, ZoneInfo('America/New_York')).date().isoformat()
    for week, start in sorted(starts.items()):
        if date < start:
            return week
    return through + 1


def markdown(report, players):
    def name(pid):
        return players.get(pid, {}).get('full_name') or pid
    def clean(value):
        return str(value).replace('|', '/').replace('\n', ' ')
    def detail(trades, roster=None):
        lines = []
        for trade in trades:
            sides = [s for s in trade['sides'] if roster is None or s.get('roster_id') == roster]
            if not sides:
                continue
            lines += ['### ' + clean(trade.get('label', 'Trade ' + trade['id'])), '',
                      f"First scoring week: **{trade['first_scoring_week']}**", '',
                      '| Manager | Received | Sent | Points in | Points out | +/- | Status |',
                      '|---|---|---|---:|---:|---:|---|']
            notes = []
            for side in sides:
                assets = lambda direction: ', '.join(f"{name(p['player_id'])} ({p['points']:.2f})" for p in side[direction + '_players']) or '—'
                lines.append(f"| {clean(side['manager'])} | {clean(assets('received'))} | {clean(assets('sent'))} | {side['received_points']:.2f} | {side['sent_points']:.2f} | {side['delta']:+.2f} | {side['status']} |")
                for direction in ('received', 'sent'):
                    if side.get('picks_' + direction):
                        labels = ', '.join(f"{p['season']} round {p['round']}" + (f" (original roster {p['roster_id']})" if 'roster_id' in p else '') for p in side['picks_' + direction])
                        notes += ['', f"{clean(side['manager'])} picks {direction}: {labels}. Value not included in points."]
                if side.get('faab_received') or side.get('faab_sent'):
                    notes += ['', f"FAAB received: {side.get('faab_received', 0)}; sent: {side.get('faab_sent', 0)}. Not included in points."]
                if side['missing_scores']:
                    notes += ['', '**Incomplete score coverage; excluded from the leaderboard.**']
            lines += notes + ['']
        return '\n'.join(lines) or 'No trades yet.\n'
    intro = (f"# Rowdy League Trades\n\nUpdated {report['updated_at']}. Season {report['season']}; scored through Week {report['through_week']}.\n\n"
             "Player production includes bench points and continues after subsequent trades or drops. Each trade is a separate counterfactual: received minus sent over the same weeks. Repeated players can appear in multiple trades. This is a production leaderboard, not a complete dynasty-value ranking. Picks and FAAB remain listed but unvalued.\n\n")
    board = ['## League Trade Leaderboard', '', '| Rank | Manager | Team | Trade +/- | Scored | Total trades | Unvalued assets |', '|---:|---|---|---:|---:|---:|---|']
    for rank, row in enumerate(report['leaderboard'], 1):
        board.append(f"| {rank} | {clean(row['manager'])} | {clean(row['team'])} | {row['delta']:+.2f} | {row['scored_trades']} | {row['trade_count']} | {'Yes' if row['has_unvalued_assets'] else 'No'} |")
    sections = {'leaderboard.md': intro + '\n'.join(board) + '\n\n' + detail(report['trades']),
                'krunky.md': intro + '## Krunky Fleece-O-Meter\n\n' + detail(report['trades'], report['trackers']['krunky']),
                'ryan.md': intro + '## Ryan Self-Fleece-O-Meter\n\nPositive trade +/- = Redemption Zone. Negative trade +/- = Self-Fleece Zone.\n\n' + detail(report['trades'], report['trackers']['ryan']),
                'veto_vindicator.md': intro + '## Veto Vindicator\n\nHypothetical player production only. A points gap does not by itself settle whether a veto was justified, especially when picks are involved.\n\n' + detail(report['vetoed_trades'])}
    for filename, content in sections.items():
        (ROOT / 'reports' / filename).write_text(content)


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--through-week', type=int, help='Explicit completed scoring week, 0–18')
    args = parser.parse_args()
    config = json.loads((ROOT / 'config/settings.json').read_text())
    vetoes = json.loads((ROOT / 'config/vetoed_trades.json').read_text())
    lid = config['league_id']
    if not lid:
        print('Configure league_id in config/settings.json to enable Sleeper updates.')
        return
    prefix = f'/v1/league/{lid}'
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {k: pool.submit(fetch, path) for k, path in {
            'league': prefix, 'users': prefix + '/users', 'rosters': prefix + '/rosters',
            'state': '/v1/state/nfl'}.items()}
        raw = {k: task.result() for k, task in jobs.items()}
    league = raw['league']
    if not league or league['sport'] != 'nfl':
        raise ValueError('Expected a valid NFL league')
    season = league['season']
    # NFL state reflects the advancing calendar; last_scored_leg is preferred when available.
    state = raw['state']
    if args.through_week is not None:
        through = args.through_week
    elif str(state['season']) == str(season):
        through = min(int(state['week']) - 1, int(league['settings'].get('last_scored_leg', int(state['week']) - 1)))
    elif int(state['season']) > int(season):
        through = 18
    else:
        through = 0
    if not 0 <= through <= 18:
        raise ValueError('Completed week must be between 0 and 18')
    cache = ROOT / f'.cache/players-{season}.json'
    if not cache.exists() or time.time() - cache.stat().st_mtime > 86400:
        players_all = fetch('/v1/players/nfl')
        players = {pid: {k: p.get(k) for k in ('full_name', 'position', 'team')} for pid, p in players_all.items()}
        write_json(cache, players)
    else:
        players = json.loads(cache.read_text())
    users = {u['user_id']: u for u in raw['users']}
    managers = {}
    for r in raw['rosters']:
        u = users.get(r['owner_id'], {})
        managers[str(r['roster_id'])] = {'user_id': r['owner_id'], 'name': u.get('display_name', str(r['roster_id'])),
                                         'team': (u.get('metadata') or {}).get('team_name', '')}
    paths = {f'transactions/{w}': f'{prefix}/transactions/{w}' for w in range(0, 19)}
    for w in range(1, through + 1):
        paths[f'matchups/{w}'] = f'{prefix}/matchups/{w}'
        paths[f'stats/{w}'] = f'/stats/nfl/{season}/{w}?season_type=regular'
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {k: pool.submit(fetch, path) for k, path in paths.items()}
        payloads = {k: task.result() for k, task in jobs.items()}
    tx = {t['transaction_id']: t for k, rows in payloads.items() if k.startswith('transactions/') for t in rows if t['type'] == 'trade'}
    completed = sorted((t for t in tx.values() if t['status'] == 'complete'), key=lambda t: t['status_updated'])
    tracked = {pid for t in completed for pid in [*(t.get('adds') or {}), *(t.get('drops') or {})]}
    tracked.update(pid for t in vetoes for s in t['sides'] for direction in ('received', 'sent') for pid in s[direction])
    weekly, starts, checks = {}, {}, []
    for w in range(1, through + 1):
        rows = stat_map(payloads[f'stats/{w}'])
        starts[w] = min(r['date'][:10] for r in rows.values() if r.get('date'))
        matchup_points = {pid: value for m in payloads[f'matchups/{w}'] for pid, value in (m.get('players_points') or {}).items() if value is not None}
        values = {}
        for pid in tracked:
            calculated = round(score(rows.get(pid, {}).get('stats', {}), league['scoring_settings']), 2)
            if pid in matchup_points:
                values[pid] = matchup_points[pid]
                if abs(calculated - matchup_points[pid]) > .011:
                    checks.append({'week': w, 'player_id': pid, 'stats_points': calculated, 'matchup_points': matchup_points[pid]})
            else:
                # Full completed-week stats: no stat row means no recorded production.
                values[pid] = calculated
        weekly[str(w)] = values
    if checks:
        raise ValueError('Weekly stats do not reproduce league player points: ' + json.dumps(checks))
    trades = []
    for t in completed:
        first = config['first_scoring_week_overrides'].get(t['transaction_id'], infer_week(t, starts, through))
        trades.append(evaluate(normalize(t, managers, first), weekly, through))
    report = {'league_id': lid, 'league_name': league['name'], 'season': season,
              'updated_at': datetime.now(timezone.utc).isoformat(), 'through_week': through,
              'trackers': config['trackers'], 'managers': managers, 'players': {pid: players.get(pid, {}) for pid in sorted(tracked)}, 'trades': trades,
              'noncompleted_trade_count': len(tx) - len(completed),
              'vetoed_trades': [evaluate(t, weekly, through) for t in vetoes],
              'leaderboard': leaderboard(trades, managers)}
    # Publish only after all endpoints and scoring consistency checks have passed.
    write_json(ROOT / 'data/snapshot.json', {'league': {k: league[k] for k in ('league_id','name','season','scoring_settings','settings')},
                                           'managers': managers, 'transactions': list(tx.values()),
                                           'weekly_points': weekly, 'week_start_dates': starts})
    write_json(ROOT / 'data/report.json', report)
    markdown(report, players)
    print(f"Updated {league['name']}: {len(trades)} trades; through Week {through}; scoring cross-check passed.")


if __name__ == '__main__':
    run()
