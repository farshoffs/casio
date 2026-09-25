# CASIO TradeIndicator Quality V2 — Robustness Audit

Date: 2026-09-25
Dataset: user-supplied FxPro XAUUSD M1, 2017-01-02 through 2026-09-24
Execution: H1 causal zones -> M15 signal -> M1 execution, structural SL, fixed 3R, one position, stop-first, no BE/protected stop/partials/averaging.

## Baseline QUALITY_V2

- 624 trades
- 31.73% WR
- +0.269R/trade
- PF 1.394
- +168R
- RM100 continuous @5% -> RM33,762
- max DD 64.07%
- longest loss streak 15
- ~5.35 trades/month

Splits:
- 2017-2021: +0.227R/trade, PF 1.327
- 2022-2024: +0.223R/trade, PF 1.321
- 2025-2026: +0.458R/trade, PF 1.720

## Drawdown anatomy

Longest loss streak: 15 consecutive SLs, 2022-02-14 through 2022-04-14.
Composition:
- 9 Supply Break/Hold
- 6 Demand Rejection

2022:
- 66 trades
- 22.73% WR
- -0.091R/trade
- -6R
- PF 0.882
- RM100 -> RM59.48
- max DD 61.78%

Both sleeves were weak in 2022:
- Demand Rejection: -0.111R/trade
- Supply Break/Hold: -0.083R/trade

## Monthly audit

- 117 observed months
- 65 positive
- 42 negative
- 10 flat
- median 5 trades/month
- only 18 months >=8 trades
- longest negative-month run: 4 months (Mar-Jun 2026), -12R

## Zone-touch audit

Prior touches were highly informative:

| Prior touches | Trades | WR | Exp/trade | PF | Net R |
|---|---:|---:|---:|---:|---:|
| 0 (first) | 279 | 30.11% | +0.204R | 1.292 | +57R |
| 1-3 | 252 | 35.71% approx | ~+0.43R | >1.6 | +108R approx |
| 4+ | 93 | 25.81% | +0.032R | 1.043 | +3R |

The 4+ touch group was especially harmful in 2022:
- Demand 4+: -2R
- Supply 4+: -4R

This supports the causal hypothesis that zones materially degrade after repeated tests.

## QUALITY V2.1 — Touch Cap <=3

Exact full M1 replay after excluding signals with more than 3 prior touches:

- 548 trades
- 32.66% WR
- +0.307R/trade
- PF 1.455
- +168R
- RM100 continuous @5% -> RM44,149
- max DD **53.74%** (vs 64.07%)
- longest loss streak **10** (vs 15)

Splits:
- Train 2017-2021: +0.304R/trade, PF 1.451
- Validation 2022-2024: +0.247R/trade, PF 1.359
- Holdout-like 2025-2026: +0.410R/trade, PF 1.632

Calendar years:
- 2017 +0.574R
- 2018 +0.077R
- 2019 +0.306R
- 2020 +0.263R
- 2021 +0.259R
- 2022 -0.018R
- 2023 +0.283R
- 2024 +0.467R
- 2025 +0.556R
- 2026 YTD +0.255R

Only 2022 remains slightly negative (-1R); all other years are positive in arithmetic R.

Cost stress:
- 0.02R/trade: +0.287R/trade, PF 1.417
- 0.05R/trade: +0.257R/trade, PF 1.363
- 0.10R/trade: +0.207R/trade, PF 1.279

Frequency falls to ~4.74 trades/month average, median 4.

## Supply overextension diagnostic

For Supply Break/Hold, signals where price was roughly 0.75-1.25 H1 ATR from EMA20 were unusually stable:
- 115 trades
- 37.39% WR
- +0.496R/trade
- PF 1.79

This band was positive in train, validation and pseudo-holdout and remained +0.25R/trade in 2022.

A strict combined replay (Touch <=3 + Supply extension 0.75-1.25 ATR) produced:
- 323 trades
- 34.67% WR
- +0.387R/trade
- PF 1.592
- 2022 +0.20R/trade
- validation +0.419R/trade
- pseudo-holdout +0.333R/trade
- 5% max DD 62.85%
- only ~2.98 trades/month
- 2021 negative and 2026 almost flat

Therefore it is too selective and does not improve full-path DD enough to replace Touch-Cap V2.1.

## MFE / MAE audit

Among eventual losing trades in baseline Quality V2:
- 50.7% first reached at least +0.5R
- 30.3% reached at least +1R
- 8.2% reached at least +2R before ultimately hitting SL

Among winners:
- median MAE ~0.46R
- 46.5% experienced at least 0.5R adverse excursion
- 18.7% experienced at least 0.8R adverse excursion before reaching 3R

Interpretation:
- a +0.5R BE/protected-stop rule would materially rewrite the loss distribution and inflate positive-exit statistics;
- tighter stops would also kill a meaningful fraction of genuine 3R winners.
- no exit-management shortcut is accepted.

## Risk stress for V2.1 Touch Cap

Same trade sequence, different current-equity risk:

| Risk/trade | Ending RM | Max DD |
|---:|---:|---:|
| 1% | RM486.69 | 13.18% |
| 2% | RM1,959.62 | 24.81% |
| 3% | RM6,578.29 | 35.05% |
| 4% | RM18,540.06 | 44.59% |
| 5% | RM44,149.30 | 53.74% |

This is not a recommendation to change risk. It demonstrates that the remaining large drawdown is primarily sequence-risk magnified by the requested 5% sizing.

## Decision

Freeze **QUALITY V2.1 Touch Cap <=3** as the stronger research candidate.

Why:
1. simple causal rule: zones weaken after repeated testing;
2. improves expectancy, PF, max DD and loss-streak length;
3. survives train/validation/2025-26;
4. does not rely on protected-stop or exit manipulation;
5. only 2022 remains slightly negative.

Do not add the narrow Supply EMA-distance filter to production research yet. It looks strong but loses too much frequency and does not materially improve full-history max DD.

Main unresolved problem: frequency (~4.7/month) and 5%-risk drawdown (~54%).
