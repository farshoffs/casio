# CASIO Hybrid Core v1 — Independent Feed Validation

Date: 2026-09-24

## Frozen rules
No Hybrid Core v1 trading parameter was changed after the FxPro research result.

Architecture:
- H4 regime / direction
- completed H1 veto
- M15 explicit setup events from V1 Momentum and Structural Frequency
- 2-M15-bar same-module/direction event cooldown
- one live portfolio position
- fixed 3R
- real structural SL
- no BE / protected SL
- 180-calendar-day shadow-health gate
- minimum 20 completed shadow setups per module
- module enabled only when completed trailing shadow net-R sum > 0
- 1 bp round-trip research-cost sensitivity

Independent feeds are M5. SL/TP is therefore resolved on M5; if both are touched in one M5 bar the result is conservatively a stop. Same-M5 ambiguity was negligible: 1 selected Dukascopy trade and 2 selected OctaFX trades.

## Independent result

| Feed | Coverage | Trades | WR | Net R @1bp | Exp/trade | PF | RM100 @1% | Max DD @1% |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Dukascopy research BID M5 | 2025-06-23 to 2026-09-16 | 366 | 30.33% | +68.90R | +0.188R | 1.264 | RM187.25 | 19.59% |
| OctaFX / Octa Markets MT4 M5 | 2016-07-01 to 2026-01-30 | 1,766 | 25.82% | **-20.72R** | **-0.0117R** | **0.985** | **RM62.23** | **56.23%** |

## OctaFX year-by-year

| Year | Trades | WR | Net R @1bp | PF |
|---:|---:|---:|---:|---:|
| 2017 | 171 | 25.15% | -9.00R | 0.934 |
| 2018 | 257 | 24.12% | -23.73R | 0.885 |
| 2019 | 141 | 26.95% | +3.57R | 1.033 |
| 2020 | 280 | 27.86% | +22.64R | 1.109 |
| 2021 | 152 | 22.37% | -21.94R | 0.821 |
| 2022 | 180 | 24.44% | -11.19R | 0.921 |
| 2023 | 111 | 28.83% | +11.78R | 1.142 |
| 2024 | 204 | 24.02% | -17.10R | 0.894 |
| 2025 | 240 | 27.92% | +19.18R | 1.107 |

Only 4 of the 9 complete 2017-2025 years are positive.

Module contribution on OctaFX:
- V1: 1,302 trades, -13.28R after 1 bp
- Structural Frequency: 464 trades, -7.44R after 1 bp

Both modules fail on the older independent feed.

## Cost sensitivity

OctaFX:
- 0 bp: +58.0R, PF 1.044, RM100@1% -> RM136.73, max DD 39.36%
- 0.5 bp: +18.64R, PF 1.014, RM92.25, max DD 43.22%
- 1 bp: -20.72R, PF 0.985, RM62.23, max DD 56.23%

Therefore the failure is not purely caused by the 1 bp friction assumption. The gross edge itself is too weak.

Dukascopy remains robust from 0-2 bp in its recent window:
- 0 bp: +78.0R, PF 1.306
- 1 bp: +68.90R, PF 1.264
- 2 bp: +59.79R, PF 1.223

## Exact three-feed overlap
Common window: 2025-06-23 through 2026-01-30.

| Feed | Trades | WR | Net R @1bp | PF | RM100@1% | DD |
|---|---:|---:|---:|---:|---:|---:|
| FxPro M1 | 97 | 37.11% | +44.26R | 1.705 | RM152.77 | 8.25% |
| Dukascopy M5 | 155 | 28.39% | +16.25R | 1.142 | RM114.74 | 19.59% |
| OctaFX M5 | 94 | 26.60% | +2.37R | 1.033 | RM100.92 | 21.89% |

All three feeds are positive in the recent overlap, but the magnitude is highly feed-sensitive.

## Frequency on OctaFX 2017-2025
- 108 complete calendar months
- average 16.07 selected trades/month
- median 16.5
- 78/108 months have >=8 trades
- 11 zero-trade months, primarily when the causal shadow-health gate disables both modules

## Decision

**REJECT Hybrid Core v1 as production-ready.**

The recent FxPro and Dukascopy results are real enough to justify the research idea, but the frozen system does not generalize to the older independent OctaFX history.

No parameters should be retuned on OctaFX to rescue v1. The next research version must be a new predeclared hypothesis, not a threshold adjustment to this failed validation.
