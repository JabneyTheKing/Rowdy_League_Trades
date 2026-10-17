"""Separate positional-value and draft-versus-trade optimal-lineup reports."""
from pathlib import Path

BASELINE_SIZES = {'QB': 12, 'RB': 30, 'WR': 42, 'TE': 12, 'K': 12, 'DEF': 12}
FLEX = {'FLEX': {'RB', 'WR', 'TE'}, 'SUPER_FLEX': {'QB', 'RB', 'WR', 'TE'},
        'REC_FLEX': {'WR', 'TE'}, 'WRRB_FLEX': {'WR', 'RB'}}


def participated(row, points):
    stats = row.get('stats', {})
    # gms_active alone is also supplied for IR players. Require actual involvement.
    return points != 0 or any((stats.get(k) or 0) > 0 for k in
        ('gp', 'off_snp', 'def_snp', 'st_snp', 'pass_att', 'rush_att', 'rec_tgt',
         'rec', 'fga', 'xpa', 'kick_ret', 'punt_ret'))


def positional_scores(weekly, stat_rows, players, sizes=None):
    sizes = sizes or BASELINE_SIZES
    adjusted, baselines = {}, {}
    for week, points in weekly.items():
        rows = stat_rows[week]
        active = {p for p, value in points.items() if participated(rows.get(p, {}), value)}
        position = {p: (rows.get(p, {}).get('player') or {}).get('position') or
                    players.get(p, {}).get('position') for p in points}
        pools = {pos: sorted((points[p] for p in active if position[p] == pos), reverse=True)[:n]
                 for pos, n in sizes.items()}
        baselines[week] = {pos: {'average': sum(values)/len(values) if values else 0,
                                'sample_size': len(values), 'target_size': sizes[pos]}
                           for pos, values in pools.items()}
        # Keep precision through the weekly calculation; round transaction totals later.
        adjusted[week] = {p: value - baselines[week][position[p]]['average']
                          if p in active and position[p] in sizes else 0.0
                          for p, value in points.items()}
    return adjusted, baselines


def optimal_lineup(roster, slots, players, points):
    """Exact assignment by slot bitmask; fill legal slots, then maximize points."""
    slots = [s for s in slots if s not in ('BN', 'IR')]
    supported = set(BASELINE_SIZES) | set(FLEX)
    if set(slots) - supported:
        raise ValueError('Unsupported starting slots: ' + str(set(slots) - supported))
    dp = {0: (0.0, [])}
    for pid in sorted(set(roster)):
        player = players.get(pid, {})
        eligible = set(player.get('fantasy_positions') or [player.get('position')])
        value = points.get(pid, 0.0)
        for mask, (total, lineup) in list(dp.items()):
            for i, slot in enumerate(slots):
                if mask & (1 << i) or not eligible.intersection(FLEX.get(slot, {slot})):
                    continue
                next_mask = mask | (1 << i)
                candidate = total + value
                if next_mask not in dp or candidate > dp[next_mask][0]:
                    dp[next_mask] = (candidate, lineup + [(i, pid, value)])
    mask = max(dp, key=lambda m: (m.bit_count(), dp[m][0]))
    total, selected = dp[mask]
    selected = {i: (pid, value) for i, pid, value in selected}
    return {'points': round(total, 2), 'filled_slots': mask.bit_count(),
            'lineup': [{'slot': slot, 'player_id': selected.get(i, (None, 0))[0],
                        'points': selected.get(i, (None, 0))[1]} for i, slot in enumerate(slots)]}


def draft_comparison(picks, trades, rid, slots, players, weekly, through):
    original = {str(p['player_id']) for p in picks if p['roster_id'] == rid}
    if not original:
        raise ValueError(f'No verified draft picks for roster {rid}')
    rows = []
    for week in range(1, through + 1):
        roster = set(original)
        for trade in sorted(trades, key=lambda t: (t['processed_at'], t['id'])):
            for side in trade['sides']:
                if side['roster_id'] != rid:
                    continue
                for direction in ('sent', 'received'):
                    for pid in side[direction]:
                        first = trade.get('player_first_scoring_week', {}).get(pid, trade['first_scoring_week'])
                        if first <= week:
                            if direction == 'sent':
                                roster.discard(pid)
                            else:
                                roster.add(pid)
        before = optimal_lineup(original, slots, players, weekly[str(week)])
        after = optimal_lineup(roster, slots, players, weekly[str(week)])
        rows.append({'week': week, 'drafted': before, 'traded': after,
                     'trade_roster': sorted(roster), 'delta': round(after['points']-before['points'], 2)})
    draft_total = round(sum(r['drafted']['points'] for r in rows), 2)
    trade_total = round(sum(r['traded']['points'] for r in rows), 2)
    return {'draft_roster': sorted(original), 'weeks': rows,
            'draft_total': draft_total, 'trade_total': trade_total,
            'delta': round(trade_total-draft_total, 2)}


def write_reports(report, root):
    def name(pid):
        return (report['players'].get(pid, {}).get('full_name') or pid or 'Empty slot').replace('|', '/')
    intro = (f"Updated {report['updated_at']}. Through Week {report['through_week']}"
             + (' (PARTIAL; available scores and baselines will change).' if report.get('partial_week') else ' (complete).'))
    for key in ('jabney', 'krunky'):
        p = report['positional_value'][key]
        lines = [f'# {key.title()} — Positional Value', '', intro, '',
            'Weekly value = league fantasy points minus the average of that week’s top participating players at the same position. '
            'Pools: QB 12, RB 30, WR 42, TE 12, K 12, DEF 12. RB/WR depths allow for the two flex spots. '
            'Actual league scoring includes TE premium. Byes and missed games contribute zero, not a negative baseline. '
            'An active player scoring zero does receive the baseline deduction. Partial weeks are provisional. '
            'Negative values mean below this benchmark, not a negative real-life contribution. Picks/FAAB are unvalued.', '',
            'Only eligible transactions since August 23 count. Trade and acquisition scoring windows match the original trackers. '
            'Trades continue as independent comparisons after players leave. Pickup/drop comparisons end at the pickup’s release. '
            'Standalone drops are ignored. Krunky includes trades; Jabney also includes waivers and free agents.', '',
            '| Component | Raw net points | Positional net value |', '|---|---:|---:|']
        for c in p['components']:
            lines.append(f"| {c['label']} | {c['raw']:+.2f} | {c['adjusted']:+.2f} |")
        lines += [f"| **Total** | **{p['raw_total']:+.2f}** | **{p['total']:+.2f}** |", '',
                  '## Transactions', '', '| Move | Received / added | Sent / dropped | Raw net | Adjusted net | Status |',
                  '|---|---|---|---:|---:|---|']
        for row in p['moves']:
            lines.append(f"| {row['label']} | {', '.join(name(x) for x in row['received']) or '—'} | {', '.join(name(x) for x in row['sent']) or '—'} | {row['raw']:+.2f} | {row['adjusted']:+.2f} | {row['status']} |")
        lines += ['', '## Weekly positional baselines', '', '| Week | QB | RB | WR | TE | K | DEF |', '|---:|---:|---:|---:|---:|---:|---:|']
        for w, b in report['positional_value']['baselines'].items():
            lines.append(f'| {w} | ' + ' | '.join(f"{b[pos]['average']:.2f} (n={b[pos]['sample_size']})" for pos in BASELINE_SIZES) + ' |')
        (root / f'reports/{key}_positional.md').write_text('\n'.join(lines)+'\n')
        c = report['draft_vs_trades'][key]
        lines = [f'# {key.title()} — Draft vs. Trades', '', intro, '',
            'Each week compares two hindsight-optimal legal starting lineups using raw league fantasy points: '
            'the original drafted roster, and that roster adjusted only for eligible trades completed since August 23. '
            'Trades take effect using the existing verified player/week windows; future trades cannot change earlier weeks. '
            'Waiver/free-agent adds and all non-trade drops are ignored. Drafted players remain available until traded away, '
            'and players received through trades are included even if originally obtained elsewhere via free agency. '
            'The draft is the starting inventory, not a scored pre-cutoff transaction. '
            'No bench points are added; each player fills at most one slot. Kicker, defense and both flex slots count. '
            'Fill all possible slots, then maximize points; unfillable slots score zero. '
            'This measures potential lineup production, not actual start/sit decisions, record, or dynasty value.', '',
            '| Week | Drafted team optimum | Trade-adjusted optimum | Trading impact |', '|---:|---:|---:|---:|']
        for row in c['weeks']:
            lines.append(f"| {row['week']} | {row['drafted']['points']:.2f} | {row['traded']['points']:.2f} | {row['delta']:+.2f} |")
        lines += [f"| **Total** | **{c['draft_total']:.2f}** | **{c['trade_total']:.2f}** | **{c['delta']:+.2f}** |", '', '## Original drafted roster', '', ', '.join(name(x) for x in c['draft_roster']), '']
        for row in c['weeks']:
            lines += [f"## Week {row['week']} optimal lineups", '', '| Slot | Drafted player | Points | Trade-adjusted player | Points |', '|---|---|---:|---|---:|']
            for a,b in zip(row['drafted']['lineup'], row['traded']['lineup']):
                lines.append(f"| {a['slot']} | {name(a['player_id'])} | {a['points']:.2f} | {name(b['player_id'])} | {b['points']:.2f} |")
        (root / f'reports/{key}_draft_vs_trades.md').write_text('\n'.join(lines)+'\n')


def positional_summary(key, rid, raw_trades, adjusted_trades, raw_waivers, adj_waivers, raw_fa, adj_fa):
    moves, components = [], []
    originals = {t['id']: t for t in raw_trades}
    for t in adjusted_trades:
        side = next((s for s in t['sides'] if s['roster_id'] == rid), None)
        if side is None:
            continue
        raw = next(s for s in originals[t['id']]['sides'] if s['roster_id'] == rid)
        moves.append({'label': f'Trade {len(moves)+1}', 'transaction_id': t['id'], 'kind': 'Trades',
                      'received': side['received'], 'sent': side['sent'], 'status': side['status'],
                      'raw': raw['delta'], 'adjusted': side['delta']})
    if key == 'jabney':
        for label, raws, adjusted in [('Waivers', raw_waivers, adj_waivers), ('Free agents', raw_fa, adj_fa)]:
            original = {(r['transaction_id'],r['player_id']):r for r in raws['claims']}
            for row in adjusted['claims']:
                if row['roster_id'] != rid:
                    continue
                raw = original[(row['transaction_id'],row['player_id'])]
                moves.append({'label': f"{label}: W{row['first_week']}–{row['last_week']}" if row['first_week'] <= row['last_week'] else f'{label}: pending',
                              'transaction_id': row['transaction_id'], 'kind': label,
                              'received': [row['player_id']], 'sent': [row['dropped_player_id']] if row['dropped_player_id'] else [],
                              'status': row['status'], 'raw': raw['points'], 'adjusted': row['points']})
    for label in (['Trades', 'Waivers', 'Free agents'] if key == 'jabney' else ['Trades']):
        rows = [r for r in moves if r['kind'] == label and r['status'] == 'scored']
        components.append({'label': label, 'raw': round(sum(r['raw'] for r in rows),2),
                           'adjusted': round(sum(r['adjusted'] for r in rows),2)})
    return {'moves': moves, 'components': components,
            'raw_total': round(sum(c['raw'] for c in components),2),
            'total': round(sum(c['adjusted'] for c in components),2)}


def team_impact(picks, events, rid, slots, players, weekly, through):
    """Four fixed-move counterfactuals; wire-first attribution sums to total gain."""
    original = {str(p['player_id']) for p in picks if p['roster_id'] == rid}
    if not original:
        raise ValueError(f'No draft baseline for roster {rid}')
    scenarios = {'drafted': set(), 'trades_only': {'trade'},
                 'wire_only': {'waiver', 'free_agent'}, 'all_moves': {'trade','waiver','free_agent'}}
    weeks = []
    for week in range(1, through+1):
        row = {'week': week}
        for scenario, kinds in scenarios.items():
            roster = set(original)
            for event in sorted(events, key=lambda e: (e['processed_at'], e['id'])):
                if event['kind'] not in kinds:
                    continue
                for direction in ('sent', 'received'):
                    for asset in event[direction]:
                        if asset['roster_id'] != rid or asset['first_week'] > week:
                            continue
                        if direction == 'sent':
                            roster.discard(asset['player_id'])
                        else:
                            roster.add(asset['player_id'])
            row[scenario] = optimal_lineup(roster, slots, players, weekly[str(week)])
            row[scenario]['roster'] = sorted(roster)
        d,t,w,a = (row[s]['points'] for s in scenarios)
        row.update({'total_impact': round(a-d,2), 'trade_impact': round(a-w,2),
                    'wire_impact': round(w-d,2), 'trade_only_impact': round(t-d,2),
                    'interaction': round(a-w-t+d,2)})
        weeks.append(row)
    totals = {s: round(sum(r[s]['points'] for r in weeks),2) for s in scenarios}
    totals.update({k: round(sum(r[k] for r in weeks),2) for k in
                   ('total_impact','trade_impact','wire_impact','trade_only_impact','interaction')})
    return {'weeks': weeks, 'totals': totals, 'draft_roster': sorted(original)}


def write_team_reports(report, root):
    def name(pid):
        return (report['players'].get(pid, {}).get('full_name') or pid or 'Empty slot').replace('|','/')
    for key in report['team_impact']:
        c=report['team_impact'][key]; t=c['totals']
        title = 'Gibbs of War' if key == 'gibbs_of_war' else key.title()
        lines=[f'# {title} — Team Impact', '',
            f"Updated {report['updated_at']}. Through Week {report['through_week']}" + (' (PARTIAL).' if report.get('partial_week') else ' (complete).'), '',
            'Each week optimizes the legal starting lineup for four roster scenarios, using that week’s raw league fantasy points. '
            'This accounts for positional need, flex competition and bench depth without adding arbitrary positional multipliers. '
            'The original draft is the baseline; only eligible transactions since August 23 change a scenario. '
            'Later moves do not affect earlier weeks. Actual weekly rosters are reconstructed using the existing per-player eligibility rules. '
            'Both adds and drops change availability, including standalone releases so departed players cannot keep filling a starting slot. '
            'Standalone releases are not separately awarded a transaction score.', '',
            '**Attribution convention:** process the recorded waiver/free-agent moves without trades for the wire-only counterfactual. '
            'Wire impact = wire-only minus draft. Trade impact = all moves minus wire-only. '
            'These add exactly to total improvement; trade impact includes trade/wire interactions. '
            'For transparency, trades-only minus draft and the interaction term are also shown. '
            'This is a fixed-move counterfactual, not proof of causation: it holds recorded pickup decisions constant, '
            'ignores budget/roster-cap feasibility in hypothetical worlds, and skips removal of players absent in that world. '
            'It does not invent alternate pickups or value draft picks. Optimal lineups use hindsight, not actual start/sit choices.', '',
            '| Scenario | Cumulative optimal points |', '|---|---:|']
        for field,label in [('drafted','Original draft'),('trades_only','Draft + trades only'),('wire_only','Draft + waiver / FA moves only'),('all_moves','All moves (weekly team)')]:
            lines.append(f'| {label} | {t[field]:.2f} |')
        lines += ['', '| Attribution | Improvement |', '|---|---:|',
                  f"| Waiver / FA baseline impact | {t['wire_impact']:+.2f} |",
                  f"| Trade impact with wire moves held fixed | {t['trade_impact']:+.2f} |",
                  f"| **Total improvement** | **{t['total_impact']:+.2f}** |",
                  f"| Trades-only effect (reference, not additive) | {t['trade_only_impact']:+.2f} |",
                  f"| Trade / wire interaction (included in trade impact) | {t['interaction']:+.2f} |", '',
                  '| Week | Draft | Trades only | Wire only | All moves | Wire impact | Trade impact | Total gain |',
                  '|---:|---:|---:|---:|---:|---:|---:|---:|']
        for row in c['weeks']:
            vals=[row[s]['points'] for s in ('drafted','trades_only','wire_only','all_moves')]+[row[k] for k in ('wire_impact','trade_impact','total_impact')]
            lines.append(f"| {row['week']} | " + ' | '.join(f'{v:.2f}' for v in vals) + ' |')
        lines += ['', '## Current roster inventory', '',
                  'Captured at refresh time; upcoming games and trades are not backfilled into earlier weeks.', '',
                  ', '.join(name(p) for p in c['current_roster']), '',
                  'Replaying completed eligible moves from the draft matches this live roster.', '']
        for row in c['weeks']:
            lines += [f"## Week {row['week']} — lineup with and without trades", '',
                      '| Slot | Wire-only player | Points | All-moves player | Points |', '|---|---|---:|---|---:|']
            for a,b in zip(row['wire_only']['lineup'],row['all_moves']['lineup']):
                lines.append(f"| {a['slot']} | {name(a['player_id'])} | {a['points']:.2f} | {name(b['player_id'])} | {b['points']:.2f} |")
        (root/f'reports/{key}_team_impact.md').write_text('\n'.join(lines)+'\n')
