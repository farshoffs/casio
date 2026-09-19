# RR10 Softer MIXED Research — Stalled H4 Alignment Iteration

## Scope

Research only. **No live RR10 strategy files were changed.**

Frozen canonical RR10:
- M15 0591 impulse -> pullback -> confirmation
- completed H1/H4 context
- current TREND / MIXED routing
- support window = 2
- H4 ADX strong-trend threshold = 18
- primary-session exclusion
- HTF alignment requirement
- confirmed M15-close entry
- structural 0591 stop
- fixed 3R target
- one active trade at a time
- 5% current-equity risk

Data:
- `fxpro_xauusd_newm15.csv`
- SHA-256: `b0ea989c3f9f2b9d86c066eff1a65c1359eee080f9cc92839daffa8f847626bd`
- 229,303 XAUUSD M15 bars
- coverage: 2017-01-02 23:00 UTC -> 2026-09-18 20:45 UTC
- test start: 2017-03-04 after warm-up

Development:
- 2017-03-04 -> 2023-12-31
- weak-block focus: 2020-2023

Holdout:
- 2024 -> 2026 YTD

## Starting point

Previous pace-aware Candidate C:
- healthy ER -> normal RR10
- low ER but adequate pace -> normal RR10
- low ER + slow pace -> require support >= 3

This improved the weak block but still cut frequency more than desired.

## New finding: not all H4 alignment is useful

Inside canonical MIXED signals with:
- H4 ER20 < 0.25
- normalized H4 pace < 0.90

the historical development sample showed a striking split.

For baseline-entered trades in 2020-2023:
- H4 **not aligned** with trade: 27 trades, 5 wins, 18.52% WR, -0.259R expectancy
- H4 **aligned** with trade: 16 trades, 0 wins, 0.00% WR, -1.000R expectancy

Across the full 2017-2023 development period:
- H4 not aligned: 46 trades, 17.39% WR, -0.304R
- H4 aligned: 21 trades, 0 wins, -1.000R

This relationship does **not** remain that extreme in the 2024-2026 holdout:
- low-ER / slow-pace / H4-aligned subgroup: 15 baseline trades, 5 wins, 33.33% WR, +0.333R

Therefore the historical 0% result must not be treated as a universal law. The useful interpretation is narrower:

> In MIXED mode, H4 alignment can become stale when directional efficiency is weak and pace is subdued. H4 alignment alone should not automatically be treated as stronger evidence.

## Grid research

Tested:
- ER thresholds: 0.15, 0.20, 0.25, 0.30
- normalized H4 pace thresholds: 0.80, 0.90, 1.00, 1.10
- action only when MIXED + low ER + low pace + H4 aligned:
  - veto the entry
  - or require support >= 3

TREND entries are untouched in every candidate.

## Best balanced candidate — S1

### Rule

TREND:
- unchanged

MIXED:
- normal RR10 unless all three conditions are true:
  1. H4 ER20 < **0.25**
  2. normalized H4 pace < **1.10**
  3. H4 bias is aligned with the RR10 direction

If all three are true:
- **skip that MIXED entry**

Interpretation:
- healthy directional efficiency -> trade normally
- fast expansion -> trade normally
- H4 not aligned -> existing RR10 logic already handles the MIXED setup
- only veto a technically H4-aligned setup when the H4 trend is simultaneously inefficient and not moving faster than its recent norm

This is a **stalled-H4-alignment veto**, not a replacement router.

## Main comparison

| Period | Policy | Trades | WR | Expectancy | PF | Trades/30d | Max DD |
|---|---|---:|---:|---:|---:|---:|---:|
| 2017-2023 | Baseline RR10 | 540 | 24.63% | -0.015R | 0.98 | 6.50 | 93.26% |
| 2017-2023 | **S1** | **495** | **25.86%** | **+0.034R** | **1.05** | **5.95** | **82.34%** |
| 2020-2023 | Baseline RR10 | 295 | 23.73% | -0.051R | 0.93 | 6.06 | 89.31% |
| 2020-2023 | **S1** | **266** | **25.56%** | **+0.023R** | **1.03** | **5.46** | **78.84%** |
| 2024-2026 | Baseline RR10 | 244 | 40.57% | +0.623R | 2.05 | 7.38 | 35.50% |
| 2024-2026 | **S1** | **219** | **42.01%** | **+0.680R** | **2.17** | **6.62** | **31.15%** |

### Changes versus baseline

2020-2023:
- expectancy: -0.051R -> **+0.023R**
- PF: 0.93 -> **1.03**
- DD: 89.31% -> **78.84%**
- frequency: 6.06 -> **5.46 trades/30d**

2024-2026 holdout:
- WR: 40.57% -> **42.01%**
- expectancy: +0.623R -> **+0.680R**
- PF: 2.05 -> **2.17**
- DD: 35.50% -> **31.15%**
- frequency: 7.38 -> **6.62 trades/30d**

Unlike the earlier hard ER filter, this candidate improves the recent holdout drawdown rather than making it worse.

## S1 year by year

| Year | Trades | WR | Expectancy | PF | Trades/30d | Max DD |
|---:|---:|---:|---:|---:|---:|---:|
| 2017* | 70 | 24.29% | -0.029R | 0.96 | 6.93 | 58.03% |
| 2018 | 84 | 21.43% | -0.143R | 0.82 | 6.90 | 68.87% |
| 2019 | 75 | 33.33% | +0.333R | 1.50 | 6.16 | 37.86% |
| 2020 | 59 | 25.42% | **+0.017R** | 1.02 | 4.84 | 48.20% |
| 2021 | 70 | 27.14% | **+0.086R** | 1.12 | 5.75 | 34.59% |
| 2022 | 71 | 22.54% | -0.099R | 0.87 | 5.84 | 78.84% |
| 2023 | 66 | 27.27% | **+0.091R** | 1.13 | 5.42 | 50.79% |
| 2024 | 71 | 35.21% | **+0.408R** | 1.63 | 5.82 | 30.17% |
| 2025 | 86 | 46.51% | **+0.860R** | 2.61 | 7.07 | 20.82% |
| 2026 YTD | 62 | 43.55% | **+0.742R** | 2.31 | 7.13 | 22.62% |

## Alternative S2 — support instead of veto

Same trigger:
- MIXED
- ER20 < 0.25
- pace < 1.10
- H4 aligned

Instead of vetoing, require support >= 3.

2020-2023:
- 267 trades
- 25.47% WR
- +0.019R expectancy
- PF 1.03
- 5.48 trades/30d
- 79.90% DD

2024-2026:
- 221 trades
- 42.08% WR
- +0.683R expectancy
- PF 2.18
- 6.68 trades/30d
- 31.15% DD

S2 is almost identical to S1 because support >= 3 is rare inside this particular stalled-H4 subgroup.

## What this iteration says

### Promising
S1 is a better compromise than the earlier hard ER gate:
- retains more trades
- fixes combined 2020-2023 expectancy
- improves recent holdout expectancy
- improves recent holdout drawdown
- leaves TREND completely untouched
- uses only completed-H4 information available at entry

### Still unresolved
- 2018 remains clearly poor
- 2022 remains clearly poor
- development-era DD is still much too high
- recent frequency falls from ~7.4 to ~6.6 trades/30d, still below the user's preferred ~8/month

## Research conclusion

**S1 is the most promising regime-quality candidate so far, but it is still research-only.**

It is materially more balanced than:
- hard ER cutoff
- H4 persistence-only filter
- raw ADX filters
- ATR-shock filters
- simple support>=3 low-ER filter

The next research target should now be **2018 and 2022 specifically**, because S1 already repairs 2020, 2021 and 2023 reasonably well.

The correct next question is not “how do we make S1 stricter?” It is:

> What common state is present in 2018 and 2022 losses that is not present in 2019 and 2024-2026 winners?

That should be diagnosed before adding another filter.

No Pine, cBot, canonical Python engine or live RR10 configuration was modified.
