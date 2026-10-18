# Krunky — Team Impact

Updated 2026-10-18T04:47:23.858857+00:00. Through Week 5 (complete).
## Temporary waiver coverage

Use rostered players with recorded game participation first. Fill remaining legal slots with a temporary waiver estimate: the mean of the five highest-scoring available players at that position that week (fewer if fewer exist). Availability is reconstructed from the draft and completed league transactions: unowned at the first NFL game's calendar-day start, clear of the league's drop-to-waiver delay, and not acquired by any team during that NFL week. Exclude players already in the hypothetical roster. Multiple replacement slots use distinct candidates from that sample, each valued at the sample mean; a sample player cannot cover two slots. Use actual league scoring, not top-12/24 starter averages. Replacements do not persist to future weeks or count as real transactions. This is a hindsight, optimistic pickup assumption, not guaranteed claim success or a forecast. Nonparticipation can reflect injury, bye or another absence; no injury diagnosis is inferred. No auto-upgrade for a participating starter who scored poorly. Partial weeks get no replacement estimates until complete. All roster scenarios use this same rule. No cap/FAAB constraints or changes to other managers' choices are simulated.

[Replacement samples](waiver_replacement_methodology.md)


Each week optimizes the legal starting lineup for four roster scenarios, using that week’s raw league fantasy points. This accounts for positional need, flex competition and bench depth without adding arbitrary positional multipliers. The original draft is the baseline; only eligible transactions since August 23 change a scenario. Later moves do not affect earlier weeks. Actual weekly rosters are reconstructed using the existing per-player eligibility rules. Both adds and drops change availability, including standalone releases so departed players cannot keep filling a starting slot. Standalone releases are not separately awarded a transaction score.

**Attribution convention:** process the recorded waiver/free-agent moves without trades for the wire-only counterfactual. Wire impact = wire-only minus draft. Trade impact = all moves minus wire-only. These add exactly to total improvement; trade impact includes trade/wire interactions. For transparency, trades-only minus draft and the interaction term are also shown. This is a fixed-move counterfactual, not proof of causation: it holds recorded pickup decisions constant, ignores budget/roster-cap feasibility in hypothetical worlds, and skips removal of players absent in that world. It does not invent alternate pickups or value draft picks. Optimal lineups use hindsight, not actual start/sit choices.

| Scenario | Cumulative optimal points |
|---|---:|
| Original draft | 726.08 |
| Draft + trades only | 756.80 |
| Draft + waiver / FA moves only | 702.32 |
| All moves (weekly team) | 739.24 |

| Attribution | Improvement |
|---|---:|
| Waiver / FA baseline impact | -23.76 |
| Trade impact with wire moves held fixed | +36.92 |
| **Total improvement** | **+13.16** |
| Trades-only effect (reference, not additive) | +30.72 |
| Trade / wire interaction (included in trade impact) | +6.20 |

| Week | Draft | Trades only | Wire only | All moves | Wire impact | Trade impact | Total gain |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 176.66 | 196.36 | 167.26 | 186.96 | -9.40 | 19.70 | 10.30 |
| 2 | 147.02 | 159.02 | 141.92 | 153.02 | -5.10 | 11.10 | 6.00 |
| 3 | 118.94 | 130.54 | 106.84 | 118.44 | -12.10 | 11.60 | -0.50 |
| 4 | 134.72 | 154.32 | 142.86 | 162.46 | 8.14 | 19.60 | 27.74 |
| 5 | 148.74 | 116.56 | 143.44 | 118.36 | -5.30 | -25.08 | -30.38 |

## Current roster inventory

Captured at refresh time; upcoming games and trades are not backfilled into earlier weeks.

Brandon Aubrey, Caleb Williams, Malik Nabers, Jalen Coker, Jayden Higgins, Colston Loveland, Travis Kelce, Stefon Diggs, James Conner, DK Metcalf, Kyler Murray, D'Andre Swift, Jonathan Taylor, Amon-Ra St. Brown, Rachaad White, Kenneth Walker, Parker Washington, Carolina Panthers

Replaying completed eligible moves from the draft matches this live roster.

## Week 1 — lineup with and without trades

| Slot | Wire-only player | Points | All-moves player | Points |
|---|---|---:|---|---:|
| QB | Caleb Williams | 37.26 | Caleb Williams | 37.26 |
| RB | Jonathan Taylor | 23.60 | Kenneth Walker | 32.60 |
| RB | Chase Brown | 16.30 | Chase Brown | 16.30 |
| WR | Jalen Coker | 29.80 | Jalen Coker | 29.80 |
| WR | Denzel Boston | 12.90 | DJ Moore | 18.50 |
| TE | Travis Kelce | 10.10 | Travis Kelce | 10.10 |
| FLEX | DJ Moore | 18.50 | Jonathan Taylor | 23.60 |
| FLEX | Parker Washington | 16.80 | Parker Washington | 16.80 |
| K | Brandon Aubrey | 1.00 | Brandon Aubrey | 1.00 |
| DEF | Los Angeles Chargers | 1.00 | Los Angeles Chargers | 1.00 |
## Week 2 — lineup with and without trades

| Slot | Wire-only player | Points | All-moves player | Points |
|---|---|---:|---|---:|
| QB | Caleb Williams | 8.72 | Caleb Williams | 8.72 |
| RB | Rachaad White | 11.30 | Rachaad White | 11.30 |
| RB | Chase Brown | 9.70 | Kenneth Walker | 20.80 |
| WR | Jalen Coker | 10.60 | Jalen Coker | 10.60 |
| WR | Denzel Boston | 18.00 | Denzel Boston | 18.00 |
| TE | Travis Kelce | 25.10 | Travis Kelce | 25.10 |
| FLEX | Jonathan Taylor | 27.20 | Jonathan Taylor | 27.20 |
| FLEX | Parker Washington | 13.30 | Parker Washington | 13.30 |
| K | Brandon Aubrey | 16.00 | Brandon Aubrey | 16.00 |
| DEF | Tampa Bay Buccaneers | 2.00 | Tampa Bay Buccaneers | 2.00 |
## Week 3 — lineup with and without trades

| Slot | Wire-only player | Points | All-moves player | Points |
|---|---|---:|---|---:|
| QB | Bryce Young | 14.64 | Bryce Young | 14.64 |
| RB | Jonathan Taylor | 8.20 | Rachaad White | 10.60 |
| RB | Rachaad White | 10.60 | Kenneth Walker | 20.30 |
| WR | Emeka Egbuka | 8.70 | DJ Moore | 9.70 |
| WR | DJ Moore | 9.70 | DK Metcalf | 10.60 |
| TE | Travis Kelce | 13.90 | Travis Kelce | 13.90 |
| FLEX | DK Metcalf | 10.60 | Jonathan Taylor | 8.20 |
| FLEX | Parker Washington | 11.50 | Parker Washington | 11.50 |
| K | Brandon Aubrey | 10.00 | Brandon Aubrey | 10.00 |
| DEF | Kansas City Chiefs | 9.00 | Kansas City Chiefs | 9.00 |
## Week 4 — lineup with and without trades

| Slot | Wire-only player | Points | All-moves player | Points |
|---|---|---:|---|---:|
| QB | Bryce Young | 21.46 | Bryce Young | 21.46 |
| RB | Ollie Gordon | 17.00 | Ollie Gordon | 17.00 |
| RB | Chase Brown | 13.60 | Kenneth Walker | 30.40 |
| WR | Malik Nabers | 20.20 | Malik Nabers | 20.20 |
| WR | DK Metcalf | 14.00 | DK Metcalf | 14.00 |
| TE | Travis Kelce | 3.50 | Colston Loveland | 11.70 |
| FLEX | Jonathan Taylor | 22.20 | Jonathan Taylor | 22.20 |
| FLEX | Rhamondre Stevenson | 16.90 | Amon-Ra St. Brown | 11.50 |
| K | Brandon Aubrey | 10.00 | Brandon Aubrey | 10.00 |
| DEF | Kansas City Chiefs | 4.00 | Kansas City Chiefs | 4.00 |
## Week 5 — lineup with and without trades

| Slot | Wire-only player | Points | All-moves player | Points |
|---|---|---:|---|---:|
| QB | Waiver cover (QB) | 17.08 | Kyler Murray | 18.26 |
| RB | Ollie Gordon | 14.80 | Ollie Gordon | 14.80 |
| RB | Rhamondre Stevenson | 16.00 | Jonathan Taylor | 9.70 |
| WR | Malik Nabers | 23.60 | Malik Nabers | 23.60 |
| WR | Emeka Egbuka | 14.20 | DK Metcalf | 3.80 |
| TE | Waiver cover (TE) | 11.26 | Colston Loveland | 3.90 |
| FLEX | Denzel Boston | 12.10 | Amon-Ra St. Brown | 9.90 |
| FLEX | Parker Washington | 27.40 | Parker Washington | 27.40 |
| K | Brandon Aubrey | 5.00 | Brandon Aubrey | 5.00 |
| DEF | Jacksonville Jaguars | 2.00 | Jacksonville Jaguars | 2.00 |
