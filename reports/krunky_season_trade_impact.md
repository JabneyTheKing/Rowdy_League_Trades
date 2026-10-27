# How Krunky’s trades have impacted the season

Updated 2026-10-27T03:23:40.525180+00:00. Through Week 6 (complete).

Under the stated lineup and waiver assumptions, Krunky’s trades have **added 63.68 potential starting-lineup points** compared with making the recorded waiver/free-agent moves without making the trades. This is a comparison of weekly optimal lineups, not simply all points received minus all points sent. A bench upgrade earns nothing unless it changes a legal starting lineup.

## We do not assume he leaves bye or injury holes at zero

Use rostered players with recorded game participation first. Fill remaining legal slots with a temporary waiver estimate: the mean of the five highest-scoring available players at that position that week (fewer if fewer exist). Availability is reconstructed from the draft and completed league transactions: unowned at the first NFL game's calendar-day start, clear of the league's drop-to-waiver delay, and not acquired by any team during that NFL week. Exclude players already in the hypothetical roster. Multiple replacement slots use distinct candidates from that sample, each valued at the sample mean; a sample player cannot cover two slots. Use actual league scoring, not top-12/24 starter averages. Replacements do not persist to future weeks or count as real transactions. This is a hindsight, optimistic pickup assumption, not guaranteed claim success or a forecast. Nonparticipation can reflect injury, bye or another absence; no injury diagnosis is inferred. No auto-upgrade for a participating starter who scored poorly. Partial weeks get no replacement estimates until complete. All roster scenarios use this same rule. No cap/FAAB constraints or changes to other managers' choices are simulated.

The drafted roster is a starting inventory, not a requirement to field unavailable players. Kicker and defense are covered too when those slots have no suitable rostered player. This matters for Krunky because the original draft did not include a defense: comparing later roster moves with a permanent zero at that slot would exaggerate improvement.

## Four comparisons

| Roster scenario | Season-to-date optimal points, including temporary cover |
|---|---:|
| Original drafted team | 852.38 |
| Draft plus eligible trades only | 921.10 |
| Draft plus recorded waiver/free-agent moves only | 834.56 |
| Team after all eligible moves | 898.24 |

**Trade impact with wire moves held fixed: +63.68.** All moves minus wire-only is the main measure of how trading changed the team’s available starting production.

**Trades considered without wire moves: +68.72.** This answers a different question: how did trades change the original draft, with temporary waiver coverage allowed on both sides?

**Wire baseline impact: -17.82.** This is wire-only minus the covered draft baseline. Together with the main trade impact, it equals **+45.86 total improvement**.

The trade/wire interaction is **-5.04**, already included in the main trade impact. It measures how the value of trading changes when the recorded wire moves are also available; it must not be added again.

## When the benefit or cost occurred

| Week | Draft with cover | Wire-only with cover | All moves with cover | Trading impact |
|---:|---:|---:|---:|---:|
| 1 | 176.66 | 167.26 | 186.96 | +19.70 |
| 2 | 147.02 | 141.92 | 153.02 | +11.10 |
| 3 | 118.94 | 106.84 | 118.44 | +11.60 |
| 4 | 134.72 | 142.86 | 162.46 | +19.60 |
| 5 | 148.74 | 143.44 | 118.36 | -25.08 |
| 6 | 126.30 | 132.24 | 159.00 | +26.76 |

The highest weekly trading impact was Week 6 (+26.76); the lowest was Week 5 (-25.08).

## Injury-adjusted sensitivity

With the separately documented injury estimates, the trade-impact figure is **+63.68**, a change of **+0.00**. The same waiver cover applies, but a player restored by a supported injury estimate can fill the slot instead. Injury credit and waiver cover are never both assigned to the same slot. This remains a limited estimate: unverified injuries and insufficient earlier baselines are not invented.

## What this does and does not establish

These figures describe hindsight potential under explicit assumptions. They do not prove how many actual wins the trades created: that would require actual start/sit choices and matchup outcomes. They do not value future draft picks or long-term dynasty value. The same real-world waiver availability is held fixed across hypothetical worlds, and the mean of top available performers is an optimistic retrospective pickup assumption. The model does not claim the manager would have known the scores, won every claim, or made the same decisions in a different season. Only eligible roster transactions since August 23 count.

[Weekly lineup details](krunky_team_impact.md) · [Waiver samples and methodology](waiver_replacement_methodology.md) · [Injury-adjusted details](krunky_injury_adjusted.md) · [Latest visuals](latest_visuals.md)
