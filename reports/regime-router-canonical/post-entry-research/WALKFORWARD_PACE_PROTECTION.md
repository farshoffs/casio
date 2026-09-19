# RR10 Pace-Dependent Protection — Walk-Forward Iteration

## Scope

Research only. No live RR10 strategy files were changed.

Frozen:
- M15 0591 entry
- H1/H4 MTF router
- TREND / MIXED classification
- original structural stop at entry
- fixed 3R target
- one active trade at a time
- 5% current-equity risk

Only post-entry management is changed in this research.

Rule family:
- identify a slow market from M15 ATR / entry price
- after price first reaches +0.5R, move stop to entry beginning on the **next genuine FxPro M5 bar**
- no same-bar lookahead
- breakeven exits free the one-active-trade slot, so every candidate is replayed sequentially

Data:
- FxPro M15: 2017-01-02 -> 2026-09-18
- FxPro M5: same period
- comparable research starts 2017-03-04 after warm-up

## Fixed-threshold stability grid

The earlier 0.13% finding was not a single-threshold accident.

Representative sequential results:

| Slow threshold | 2017-2023 Exp | DD | 2020-2023 Exp | 2024-2026 Exp | DD | Recent trades/30d |
|---:|---:|---:|---:|---:|---:|---:|
| 0.10% | +0.063R | 74.02% | +0.010R | +0.480R | 41.27% | 7.64 |
| 0.12% | +0.075R | 72.59% | -0.007R | +0.458R | 38.18% | 7.67 |
| **0.14%** | **+0.098R** | **62.71%** | **+0.023R** | +0.433R | **34.93%** | 7.70 |
| 0.16% | +0.095R | 64.07% | +0.023R | +0.425R | 38.18% | 7.76 |

The useful region is broad around roughly **0.14%-0.16%**, not only 0.13%.

### 0.14% all-mode rule by year

- 2017: -0.064R
- 2018: +0.150R
- 2019: +0.452R
- 2020: -0.088R
- 2021: +0.049R
- 2022: +0.092R
- 2023: +0.026R
- 2024: +0.169R
- 2025: +0.500R
- 2026 YTD: +0.652R

This fixes 2018 and 2022, materially reduces old-period DD, and preserves modern profitability, but 2020 remains negative.

## Pseudo-walk-forward fixed-threshold check

Candidate thresholds:
- 0.08% through 0.16% in 0.01 increments
- same +0.5R -> breakeven action

For each test year from 2020 onward, the threshold was selected using **only earlier calendar years**, using an objective that penalizes unstable annual expectancy and drawdown.

The training process selected 0.16% throughout the evaluated forward years.

Test-year results:
- 2020: -0.057R
- 2021: +0.049R
- 2022: +0.066R
- 2023: +0.026R
- 2024: +0.094R
- 2025: +0.530R
- 2026 YTD: +0.681R

Six of seven forward-year slices are positive.

Important limitation:
- the broad pace-protection hypothesis was developed after examining this same historical dataset
- this is a robustness / pseudo-OOS check, not a pristine unseen-data test

The persistent failure is 2020.

## Why 2020 behaves differently

At an all-mode 0.14% threshold, the 2020 split is:

### TREND
- 35 trades
- +0.057R expectancy
- slow-market eligible TREND subset: +0.563R expectancy

### MIXED
- 33 trades
- -0.242R expectancy
- slow-market eligible MIXED subset: -0.261R expectancy

So the 2020 deterioration is concentrated in MIXED, while slow TREND management is useful.

A similar pattern appears in the recent sample:
- 2024-2025 slow MIXED management is weaker
- slow TREND management remains much healthier

This motivated a **mode-specific management threshold**, without changing the entry/router.

## Mode-specific pace protection

Research architecture:

### TREND
Treat ATR/price below roughly 0.14%-0.16% as slow.

### MIXED
Require a materially slower market, around 0.09%-0.10%, before enabling +0.5R breakeven protection.

Normal/faster trades remain canonical RR10.

### Neighbourhood test

Three nearby candidates were replayed sequentially:

| TREND threshold | MIXED threshold | 2017-23 Exp | 2020-23 Exp | 2024-26 Exp | Recent trades/30d |
|---:|---:|---:|---:|---:|---:|
| 0.14% | 0.10% | +0.091R | +0.030R | +0.448R | 7.70 |
| **0.15%** | **0.10%** | **+0.080R** | **+0.023R** | **+0.456R** | **7.70** |
| 0.16% | 0.10% | +0.083R | +0.027R | +0.443R | 7.73 |

This is a stable neighbourhood rather than one isolated parameter.

## Midpoint candidate P15/10

Research rule:
- TREND: if M15 ATR / price < **0.15%**, then after +0.5R move stop to entry from next M5 bar
- MIXED: same protection only if M15 ATR / price < **0.10%**
- otherwise manage canonical RR10 unchanged

### Year by year

| Year | Trades | 3R wins | BE exits | Losses | Expectancy | PF | Max DD |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2017* | 78 | 9 | 37 | 32 | -0.064R | 0.84 | 51.48% |
| 2018 | 99 | 15 | 51 | 33 | **+0.121R** | 1.36 | 39.59% |
| 2019 | 85 | 20 | 36 | 29 | **+0.365R** | 2.07 | 22.62% |
| 2020 | 68 | 13 | 16 | 39 | **0.000R** | 1.00 | 42.61% |
| 2021 | 81 | 11 | 41 | 29 | **+0.049R** | 1.14 | 38.73% |
| 2022 | 76 | 13 | 24 | 39 | **0.000R** | 1.00 | 70.80% |
| 2023 | 76 | 11 | 35 | 30 | **+0.039R** | 1.10 | 44.70% |
| 2024 | 83 | 19 | 23 | 41 | **+0.193R** | 1.39 | 40.97% |
| 2025 | 100 | 30 | 30 | 40 | **+0.500R** | 2.25 | 31.50% |
| 2026 YTD | 69 | 29 | 2 | 38 | **+0.710R** | 2.29 | 22.62% |

### Aggregate

2017-2023:
- baseline: 540 trades, -0.015R, PF 0.98, max DD 93.26%
- P15/10: 563 trades, **+0.080R**, PF **1.19**, max DD **70.80%**
- frequency: ~6.79 trades/30d

2020-2023:
- baseline: -0.051R
- P15/10: **+0.023R**
- max DD: **70.80%** vs 89.31% baseline

2024-2026:
- baseline: +0.623R, PF 2.05, DD 35.50%, ~7.45 trades/30d
- P15/10: **+0.456R**, PF **1.97**, DD **40.97%**, ~**7.70 trades/30d**

This repairs/neutralizes every year from 2018 through 2023, but 2017 remains negative.

## Important interpretation of win rate

Breakeven protection changes the outcome distribution.

P15/10 2017-2023:
- 92 full 3R wins
- 240 breakeven exits
- 231 losses

So conventional "3R win rate" falls because many trades are converted to breakeven rather than full winners.

The useful comparison is:
- baseline loss rate: 75.37%
- P15/10 loss rate: 41.03%

P15/10 increases expectancy by reducing full -1R losses, not by creating more 3R winners.

## Conclusion

This iteration is materially more promising than another entry filter.

What is supported:
1. Slow-market breakeven protection is a robust historical mechanism across a broad threshold band.
2. TREND and MIXED should not use the same pace threshold.
3. The mode-specific 0.14-0.16 TREND / 0.09-0.10 MIXED neighbourhood repairs most of 2018-2023 without destroying modern profitability.
4. Recent frequency remains near the user's desired ~8 trades/month.

What is not yet solved:
- 2017 remains negative.
- 2017-2023 max DD is still ~70%, which is too high for deployment.
- the mode-specific rule was discovered after examining 2020, so it needs additional robustness validation.
- recent holdout expectancy is lower than canonical RR10.

**Do not deploy yet.**

Next research should focus specifically on the remaining 2017 TREND losses and on whether the breakeven action itself can be improved (for example a later trigger or a small locked-profit stop) without giving back the 2018/2022 repair.

No Pine, cBot, canonical Python engine or live RR10 configuration was modified.
