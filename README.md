# Latest visuals

[Open the automatically refreshed gallery for all trackers](reports/latest_visuals.md).

# Rowdy League Trades

Automated post-trade fantasy production for **Rowdy Football League**, Sleeper league `1312064355625369600`.

Every automated tracker uses **August 23, 2026 at 12:00 a.m. Eastern** as its season boundary. Sleeper transactions created before that date are discarded before trades, waiver claims, ownership windows, or rankings are calculated.

## Trackers

Automated graphics: [Krunky](visuals/krunky.png) · [Ryan](visuals/ryan.png) · [Jabney](visuals/jabney.png) · [Veto Vindicator](visuals/veto_vindicator.png) · [League Leaderboard](visuals/leaderboard.png) · [Waiver Champion](visuals/waiver_champion.png) · [Most Improved](visuals/most_improved.png) · [Rebuild King](visuals/rebuild_king.png)

- [Krunky Fleece-O-Meter](reports/krunky.md)
- [Ryan Self-Fleece-O-Meter](reports/ryan.md) — includes the Redemption Zone
- [Jabney Underdog Tracker](reports/jabney.md) — follows the comeback one trade at a time
- [Veto Vindicator](reports/veto_vindicator.md)
- [League Trade Leaderboard](reports/leaderboard.md) — all managers and trade details
- [Waiver Champion](reports/waiver_champion.md) — successful waiver claims ranked by net improvement over players dropped in the same transactions
- [Most Improved](reports/most_improved.md) — combined improvement from trades, waivers, and free-agent pickups
- [Rebuild King](reports/rebuild_king.md) — the same net-improvement formula, counting only moves that begin scoring in Week 2 or later
- [Machine-readable report](data/report.json) — for ChatGPT and future graphics

GitHub Actions refreshes every six hours, on changes to tracker code/config, and from **Actions → Update trade trackers → Run workflow**. No Sleeper login, API key, or paid service is needed. Scheduled runs can be delayed by GitHub; the report shows its actual update time. GitHub may disable schedules in inactive public repos after 60 days.

## What the numbers mean

**Trade +/- = fantasy points produced by players received − points produced by players sent**, from the first scoring week through the last completed week. Both sides use the same window. Bench production counts. Scores keep accumulating after players are traded again or dropped. Every trade is evaluated separately, so a player in successive trades contributes to multiple trade evaluations.

The leaderboard totals each manager's scored trade deltas. This rewards cumulative player production, not lineup decisions or full dynasty value. Older trades have more time to accumulate points; unequal player counts also affect totals. Future draft picks, original pick owners, and FAAB are displayed separately and never silently valued at zero. Pick-only trades are tracked but do not count as scored player trades. Pending weeks and incomplete trade scores are excluded from rankings.

The Waiver Champion includes successful waiver claims and excludes ordinary free-agent adds. A pickup earns all league-scoring points, including bench production, from its first eligible full week through the last full week before that manager drops or trades the player. When that acquisition transaction also contains a drop, the dropped player's production over the same scoring window is subtracted. Standalone drops are ignored. The standings show net improvement, claim count, FAAB spent, and each manager's best transaction.

**Most Improved Score = Trade +/- + net waiver improvement + net free-agent improvement.** Waiver and free-agent pickups earn production only while owned by that manager. If an acquisition transaction contains a drop, the dropped player's production over that same window is subtracted. Standalone drops are ignored. Because ownership scoring ends when the added player is dropped or traded, an acquisition followed by a trade does not receive overlapping pickup points after the trade.

**Rebuild King** uses that identical formula and ownership logic but excludes moves whose first eligible scoring week was Week 1. It measures the best roster pivot after the opening week.

Week totals use this league's exact scoring, including half-PPR and the extra 0.5 points per tight-end reception. Actual matchup `players_points` are preferred. An **undocumented** Sleeper weekly stats endpoint supplies production for players absent from league rosters. Its response shape is validated, and calculated stats must reproduce matchup player scores for every tracked player available in both sources; a mismatch fails the refresh instead of publishing questionable numbers. A player absent from a successfully fetched, full completed-week stats response has no recorded production and counts as zero. API failures stop publication.

By default only completed weeks are included. Automatic detection conservatively uses NFL state and `last_scored_leg`; use the workflow input or CLI to set a verified completed week if Sleeper lags. The date of the first NFL game in each weekly stats response determines the first full week after processing. Trades processed on a game day start the next week by default; use an override when appropriate. The five known Krunky/Ryan player trades have explicit start-week overrides matching the original trackers.

## Configuration

`config/settings.json` sets the league, tracker roster IDs, and first-scoring-week overrides keyed by Sleeper transaction ID. Krunky is roster 1; Ryan is roster 6 (Sleeper display name `Potatomain`); Jabney is roster 3 (team `Allen Wake`). Manager labels elsewhere use current Sleeper names; historical ownership changes are not reconstructed.

`config/vetoed_trades.json` records vetoes once, using Sleeper player IDs, the first scoring week, received/sent assets, an eligibility date (`made_on` or `made_on_or_after`), and optional roster IDs/picks. Entries without a date at or after the tracking boundary are excluded. The public transaction history fetched for this league did not expose the two known vetoes, so both are seeded manually. Veto production is hypothetical and does not enter the completed-trade leaderboard. Player points alone do not establish whether a veto was justified.

## Run locally

Python 3.11+; no third-party dependencies:

```bash
python -m unittest discover -s tests -v
python scripts/update.py
# Only if Week 5 is confirmed complete:
python scripts/update.py --through-week 5
```

`data/snapshot.json` preserves normalized managers, source transactions, weekly points, league scoring/settings, and week dates. `data/report.json` contains evaluated trades, vetoes, waiver claims, rankings, and tracked player names. `.cache/players-2026.json` locally caches player names/positions/teams; it refreshes at most once daily. League chat message contents are not collected.

Sources: [Sleeper API documentation](https://docs.sleeper.com/) and live Sleeper read-only responses. The weekly stats fallback is not part of the documented API and may need maintenance if Sleeper changes it.

## DK Metcalf vs. James Conner

[Comparison report](reports/metcalf_vs_conner.md) · [Visual](visuals/metcalf_vs_conner.png)

Both counters stay at zero until Conner records on-field participation after his current IR absence. Both start in his return week (Week 6 or later), including his return game; no earlier points count. Subsequent updates recalculate totals using league scoring.


## Positional value and team-context trackers

The original trackers remain available. Six additional views refresh in the same six-hour workflow:

| View | Jabney | Krunky |
|---|---|---|
| Positional value | [Report](reports/jabney_positional.md) · [Visual](visuals/jabney_positional.png) | [Report](reports/krunky_positional.md) · [Visual](visuals/krunky_positional.png) |
| Draft vs. trades only | [Report](reports/jabney_draft_vs_trades.md) · [Visual](visuals/jabney_draft_vs_trades.png) | [Report](reports/krunky_draft_vs_trades.md) · [Visual](visuals/krunky_draft_vs_trades.png) |
| Team impact, including wire moves | [Report](reports/jabney_team_impact.md) · [Visual](visuals/jabney_team_impact.png) | [Report](reports/krunky_team_impact.md) · [Visual](visuals/krunky_team_impact.png) |

**Positional value:** subtract the average of each week's top participating QB12/RB30/WR42/TE12/K12/DEF12 from each player's league-scored points. Missed games/byes contribute zero; active zero-point games can be negative. These are above-benchmark points, not percentages. Jabney includes trades plus net waiver/FA moves; Krunky includes trades. Existing ownership and eligibility windows apply.

**Draft vs. trades:** optimize the original drafted roster and its trades-only evolution independently each week. Waiver/FA moves and non-trade drops are ignored. Trades out remove players, trades in add players. The draft establishes inventory only; no pre-August-23 transaction is scored.

**Team impact:** optimize four weekly worlds: draft, trades only, wire only, and all moves. All completed eligible adds and drops change roster availability, including standalone releases (not individually scored). Wire impact = wire-only minus draft. Trade impact = all-moves minus wire-only. These sum to total improvement; the trade/wire interaction is explicitly shown and included in trade impact. Recorded wire moves are held fixed; hypothetical worlds do not enforce roster caps or invent alternate decisions. This estimates hindsight lineup impact, not causal proof, actual win/loss impact, or dynasty value.

The exact optimizer honors every starting slot, including both flex spots, kicker and defense, with no player used twice. Earlier weeks use only then-eligible transactions. Reports show every weekly lineup; visuals show weekly totals and the latest scoring week's optimum. Live roster inventory is separately captured and checked against draft-plus-transaction replay.


## Injury-adjusted estimates and Gibbs of War

Gibbs of War is roster 2, managed by TheRealNoodleMan. It now has the same four-scenario [Team Impact report](reports/gibbs_of_war_team_impact.md) and [visual](visuals/gibbs_of_war_team_impact.png).

Separate injury-adjusted reports and visuals:

| Team | Report | Visual |
|---|---|---|
| Jabney | [Injury-adjusted impact](reports/jabney_injury_adjusted.md) | [PNG](visuals/jabney_injury_adjusted.png) |
| Krunky | [Injury-adjusted impact](reports/krunky_injury_adjusted.md) | [PNG](visuals/krunky_injury_adjusted.png) |
| Gibbs of War | [Injury-adjusted impact](reports/gibbs_of_war_injury_adjusted.md) | [PNG](visuals/gibbs_of_war_injury_adjusted.png) |

Actual scores remain unchanged. For supported completed-game injury absences, the estimate uses the player's mean league points in **at least two earlier participating games without a weekly injury listing**. This is a participation proxy, not guaranteed perfect health. No future games or previous-season scores inform the estimate. All four roster scenarios are reoptimized with the same estimated player scores, so replacements, depth, and positional needs still determine the effect.

Evidence comes from archived [NFL weekly injury reports](https://www.nfl.com/injuries/league/2026/reg5) and [dated reserve transactions](https://www.nfl.com/transactions/league/reserve-list/2026/10), cached in `data/injury_evidence.json`. Qualifying evidence is injury-related OUT status or the first four team games after an explicit Reserve/Injured placement. In-game injuries, PUP/NFI, byes, unplayed games, longer IR absences without fresh evidence, and insufficient baselines remain unadjusted. Today's injury label is never applied backward.

This is intentionally a **limited injury estimate**, not a fully healthy-team simulation. The reports list every estimate, its earlier sample and source, confirmed absences without a baseline, and other zero-participation games left unchanged. Source failures are shown on the visuals and reports; previously verified archive records are retained. All 19 visuals run in the existing six-hour update workflow.

## Realistic waiver coverage in lineup comparisons

Jabney, Krunky and Gibbs of War's team-impact and separate injury-adjusted views, plus the draft-versus-trades views, use participating rostered players first. When a legal starting slot remains uncovered, use the mean league-scoring output of the **five highest-scoring actually available waiver players at that position that week** (or fewer if fewer exist). This replaces earlier empty-slot/zero assumptions. It is a hindsight estimate of a strong waiver pickup, not a top-12/24 starter average or a guaranteed claim.

Availability is reconstructed from league draft picks and transactions: candidates must be unowned at the start of the first game day, clear the league's drop waiver delay, and remain unclaimed during the week. Exclude players in the hypothetical roster. Use distinct candidates for multiple holes, never upgrade a participating player just for scoring poorly, and apply the same rule to every roster scenario. Temporary cover does not persist or count as a real acquisition. Partial weeks receive no coverage estimates until complete. Supported injury estimates are applied first; a slot never receives both credits.

The original production-based trackers are unchanged. These assumptions affect lineup-based counterfactual comparisons.

- [How Krunky's trades impacted the season](reports/krunky_season_trade_impact.md)
- [Full replacement methodology and weekly player samples](reports/waiver_replacement_methodology.md)
- [Updated tracker visuals](reports/latest_visuals.md)

The explanation, samples, totals and visuals are regenerated together by the scheduled workflow.
