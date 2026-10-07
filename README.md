# Rowdy League Trades

A read-only Sleeper trade-production tracker with four generated views: Krunky Fleece-O-Meter, Ryan Self-Fleece-O-Meter, Veto Vindicator, and a league-wide Trade Leaderboard.

## Setup

This initial commit contains code only. No live league identities, trades, scores, or configuration are published.

Set `league_id`, tracker roster IDs, and any first-scoring-week overrides in `config/settings.json` to enable updates. Add known vetoes once to `config/vetoed_trades.json`. GitHub Actions then refreshes every six hours, on code/config changes, and manually through **Actions → Update trade trackers → Run workflow**. The workflow commits generated data/reports to this repository; use a private repository if you do not want those files public. No Sleeper credentials or API key are needed.

Python 3.11+, no third-party dependencies:

```bash
python -m unittest discover -s tests -v
python scripts/update.py
# Only after verifying the week is complete:
python scripts/update.py --through-week 5
```

## Scoring

Trade +/- is received-player production minus sent-player production over the same post-trade weeks. Bench points count and production continues after later trades or drops. Each trade is a separate comparison; repeated players can contribute to multiple trades. Picks and FAAB are listed separately and unvalued. Pending/incomplete results and pick-only trades do not enter scored-player rankings. This measures cumulative production, not full dynasty value; older trades and unequal player counts affect comparisons.

Matchup player points use the league's exact scoring. An undocumented weekly stats endpoint supplies points for dropped players. Shape validation and cross-checks against matchup player scores must pass before publishing. Missing API responses stop the update. A player absent from a successfully fetched full completed-week stats response has no recorded production and counts as zero. The fallback may need maintenance if Sleeper changes it.

Automatic completed-week detection conservatively uses NFL state and league `last_scored_leg`. The first full scoring week is inferred from processing dates and weekly game dates. Processing on a game day starts the next week by default; override by transaction ID for your preferred boundary. Current roster owners identify managers; historical ownership changes are not reconstructed.

## Generated files

- `reports/krunky.md`: Krunky Fleece-O-Meter
- `reports/ryan.md`: Ryan Self-Fleece-O-Meter, including Redemption Zone
- `reports/veto_vindicator.md`: hypothetical veto outcomes
- `reports/leaderboard.md`: league rankings and every completed trade
- `data/report.json`: evaluated trades, rankings, and player names
- `data/snapshot.json`: league scoring/settings, normalized managers, transactions, weekly points, and week dates

The player-name catalog is cached locally for up to a day. League chat content is not collected. GitHub schedules can be delayed and may be disabled after 60 days of public-repository inactivity.

Vetoes may need manual entry because transaction history does not necessarily expose them. Each veto uses an ID, label, first scoring week, and sides containing manager, optional roster_id, received/sent player IDs, and optional picks_received/picks_sent arrays. Vetoes remain separate from the completed-trade leaderboard; production alone does not establish whether a veto was justified.

Source: [Sleeper API documentation](https://docs.sleeper.com/). Weekly stats fallback is undocumented.
