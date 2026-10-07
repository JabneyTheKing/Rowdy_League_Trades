# Rowdy League Trades

Automated post-trade fantasy production for **Rowdy Football League**, Sleeper league `1312064355625369600`.

Every automated tracker uses **August 23, 2026 at 12:00 a.m. Eastern** as its season boundary. Sleeper transactions created before that date are discarded before trades, waiver claims, ownership windows, or rankings are calculated.

## Trackers

- [Krunky Fleece-O-Meter](reports/krunky.md)
- [Ryan Self-Fleece-O-Meter](reports/ryan.md) — includes the Redemption Zone
- [Veto Vindicator](reports/veto_vindicator.md)
- [League Trade Leaderboard](reports/leaderboard.md) — all managers and trade details
- [Waiver Champion](reports/waiver_champion.md) — successful waiver claims ranked by points captured
- [Machine-readable report](data/report.json) — for ChatGPT and future graphics

GitHub Actions refreshes every six hours, on changes to tracker code/config, and from **Actions → Update trade trackers → Run workflow**. No Sleeper login, API key, or paid service is needed. Scheduled runs can be delayed by GitHub; the report shows its actual update time. GitHub may disable schedules in inactive public repos after 60 days.

## What the numbers mean

**Trade +/- = fantasy points produced by players received − points produced by players sent**, from the first scoring week through the last completed week. Both sides use the same window. Bench production counts. Scores keep accumulating after players are traded again or dropped. Every trade is evaluated separately, so a player in successive trades contributes to multiple trade evaluations.

The leaderboard totals each manager's scored trade deltas. This rewards cumulative player production, not lineup decisions or full dynasty value. Older trades have more time to accumulate points; unequal player counts also affect totals. Future draft picks, original pick owners, and FAAB are displayed separately and never silently valued at zero. Pick-only trades are tracked but do not count as scored player trades. Pending weeks and incomplete trade scores are excluded from rankings.

The Waiver Champion includes successful waiver claims and excludes ordinary free-agent adds. A pickup earns all league-scoring points, including bench production, from its first eligible full week through the last full week before that manager drops or trades the player. The standings total those points and also show claim count, FAAB spent, and each manager's best pickup.

Week totals use this league's exact scoring, including half-PPR and the extra 0.5 points per tight-end reception. Actual matchup `players_points` are preferred. An **undocumented** Sleeper weekly stats endpoint supplies production for players absent from league rosters. Its response shape is validated, and calculated stats must reproduce matchup player scores for every tracked player available in both sources; a mismatch fails the refresh instead of publishing questionable numbers. A player absent from a successfully fetched, full completed-week stats response has no recorded production and counts as zero. API failures stop publication.

By default only completed weeks are included. Automatic detection conservatively uses NFL state and `last_scored_leg`; use the workflow input or CLI to set a verified completed week if Sleeper lags. The date of the first NFL game in each weekly stats response determines the first full week after processing. Trades processed on a game day start the next week by default; use an override when appropriate. The five known Krunky/Ryan player trades have explicit start-week overrides matching the original trackers.

## Configuration

`config/settings.json` sets the league, tracker roster IDs, and first-scoring-week overrides keyed by Sleeper transaction ID. Krunky is roster 1; Ryan is roster 6 (Sleeper display name `Potatomain`), identified from the two specified Ryan trades. Manager labels elsewhere use current Sleeper names; historical ownership changes are not reconstructed.

`config/vetoed_trades.json` records vetoes once, using Sleeper player IDs, the first scoring week, received/sent assets, and optional roster IDs/picks. The public transaction history fetched for this league did not expose the two known vetoes. Both are seeded here; the preseason veto's managers remain unconfirmed. Veto production is hypothetical and does not enter the completed-trade leaderboard. Player points alone do not establish whether a veto was justified.

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
