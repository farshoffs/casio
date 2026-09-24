# ICT Strict MTF FxPro M1 Backtest — CASIO Rules

Date: 2026-09-24

## User rules

- XAUUSD FxPro M1
- Start RM100
- Risk 5% of current equity per entry
- Fixed 1:3
- Real SL only
- No BE / protected SL
- New York session only, DST-aware
- MTF mandatory
- Target WR 60%-80%
- Target >=8 trades per completed month
- One position at a time
- M1 execution and SL/TP resolution

## MTF hierarchy tested

Primary practical strict-MTF model:

D1/H4 direction
-> H1 draw on liquidity
-> M15 premium/discount location
-> M5 liquidity sweep + MSS/displacement
-> M1 MSS + FVG
-> M1 FVG 50% retrace entry
-> structural SL beyond M5 raid
-> fixed 3R target

Operational details are causal:
- D1/H4 direction uses confirmed BOS/pivot state.
- H1 draw uses completed H1 rolling liquidity range.
- M15 uses only completed M15 dealing-range premium/discount.
- M5 sweep uses prior completed M5 liquidity.
- M5 MSS requires displacement and microstructure break.
- M1 MSS and FVG are formed after the M5 MSS closes.
- Entry is only on a later M1 retrace to the M1 FVG CE.
- Entry must still occur inside 07:00-11:00 America/New_York.
- Same-M1 SL/TP collision resolves as SL.

## Strictness audit

Three stricter variants were tested before the practical hierarchy.

1. D1 + H4 + H1 all aligned + M15 FVG POI + M5 MSS + M1 FVG:
   - 12 trades
   - 16.67% WR
   - -4R gross

2. D1/H4 aligned + H1 DOL + M15 FVG POI:
   - 21 trades
   - 23.81% WR
   - -1R gross

3. D1/H4 aligned + H1 DOL + M15 FVG or order block POI:
   - 26 trades
   - 26.92% WR
   - +2R gross

These versions are too sparse to satisfy the user's frequency target. Stacking more mandatory timeframe patterns did not eliminate losing trades.

## Primary practical strict-MTF result

Full 2017-2026 YTD:

- Trades: 319
- Wins: 91
- Losses: 228
- WR: 28.53%
- Gross net: +45R
- Expectancy: +0.141R/trade
- PF: 1.197
- RM100 -> RM278.28 with continuous 5% current-equity risk
- Max compounded drawdown: 64.57%
- Longest win streak: 6
- Longest loss streak: 13

1bp round-trip sensitivity:
- +30.68R
- expectancy +0.096R/trade
- PF 1.129
- RM100 -> RM135.92
- max DD 70.73%

The 1bp figure is a sensitivity assumption, not measured FxPro bid/ask spread.

## Continuous RM100 / 5% path by year

| Year | Trades | W-L | WR | Net R | Start RM | End RM | Return | Max DD |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2017 | 23 | 7-16 | 30.43% | +5R | 100.00 | 117.07 | +17.07% | 36.98% |
| 2018 | 24 | 7-17 | 29.17% | +4R | 117.07 | 130.21 | +11.22% | 34.59% |
| 2019 | 33 | 12-21 | 36.36% | +15R | 130.21 | 237.26 | +82.21% | 26.49% |
| 2020 | 36 | 9-27 | 25.00% | 0R | 237.26 | 208.95 | -11.93% | 48.67% |
| 2021 | 31 | 9-22 | 29.03% | +5R | 208.95 | 237.81 | +13.82% | 26.49% |
| 2022 | 31 | 12-19 | 38.71% | +17R | 237.81 | 480.13 | +101.89% | 30.17% |
| 2023 | 37 | 11-26 | 29.73% | +7R | 480.13 | 588.64 | +22.60% | 31.15% |
| 2024 | 29 | 4-25 | 13.79% | -13R | 588.64 | 285.58 | -51.48% | 59.35% |
| 2025 | 39 | 12-27 | 30.77% | +9R | 285.58 | 382.51 | +33.94% | 33.66% |
| 2026 YTD | 36 | 8-28 | 22.22% | -4R | 382.51 | 278.28 | -27.25% | 42.61% |

## 2026 month by month

| Month | Trades | W-L | WR | Net R | Start RM | End RM | Return |
|---|---:|---:|---:|---:|---:|---:|---:|
| Jan | 6 | 2-4 | 33.33% | +2R | 382.51 | 412.03 | +7.72% |
| Feb | 5 | 0-5 | 0% | -5R | 412.03 | 318.82 | -22.62% |
| Mar | 6 | 1-5 | 16.67% | -2R | 318.82 | 283.70 | -11.02% |
| Apr | 2 | 1-1 | 50% | +2R | 283.70 | 309.95 | +9.25% |
| May | 2 | 0-2 | 0% | -2R | 309.95 | 279.73 | -9.75% |
| Jun | 8 | 2-6 | 25% | 0R | 279.73 | 271.94 | -2.78% |
| Jul | 4 | 2-2 | 50% | +4R | 271.94 | 324.57 | +19.36% |
| Aug | 1 | 0-1 | 0% | -1R | 324.57 | 308.35 | -5.00% |
| Sep* | 2 | 0-2 | 0% | -2R | 308.35 | 278.28 | -9.75% |

*Data ends 2026-09-24.

## Frequency / acceptance

Across 115 completed audit months:
- average trades/month: 2.76
- median: 3
- minimum: 0
- months with >=8 trades: 2 / 115
- months with WR between 60%-80%: 9 / 115

## Verdict

FAIL against the current CASIO target.

Strict MTF improves the full-history gross expectancy versus the looser ICT baseline, but it does not produce the requested 60%-80% WR or >=8 trades/month. The strictest MTF variants actually become too sparse and still lose.

The result indicates that MTF is useful for context and filtering, but simply adding more mandatory timeframe agreement does not remove all bad trades.

The best next research direction is not another RR sweep. If ICT is to be pursued further, the missing discretionary variable to mechanize is likely the quality of the draw on liquidity / PD-array selection rather than adding another timeframe filter.
