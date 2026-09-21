# Structural Displacement Retrace MTF — Full-History FxPro Test

Status: **REJECTED as the next base engine in its current form**

Test date: 2026-09-22

## Test definition

Source rules:
- `casio/structural_frequency_research.py`
- mode = `DISPLACEMENT_RETRACE`
- causal D1/H4/H1/M15 structure from completed higher-timeframe bars
- M5 displacement + BOS context
- FVG50 entry when an FVG exists, otherwise displacement-body 50% retracement
- structural stop behind recent M5 invalidation
- one active trade at a time
- conservative stop-first resolution
- maximum hold = 216 M5 bars
- round-trip friction = 1 bp, converted into R

Dataset:
- FxPro XAUUSD M5
- 687,746 bars
- 2017-01-02 23:00 UTC through 2026-09-18 20:55 UTC

Targets tested:
1. 3.0R target + minimum 3.0R external-liquidity runway
2. 3.5R target + minimum 3.5R external-liquidity runway

Risk report:
- each calendar year starts at RM100
- 5% of current equity risk per trade
- 2026 monthly table compounds continuously from RM100 on Jan 1

## Full-history conclusion

The latest-60d discovery result did **not** survive full-history validation.

| Metric | 3R | 3.5R |
|---|---:|---:|
| Trades | 1,257 | 1,193 |
| Avg trades/month | 10.74 | 10.20 |
| Minimum calendar month | 1 | 1 |
| Months >=8 trades | 95/117 | 89/117 |
| Win rate | 27.45% | 25.73% |
| Net R | -76.02R | -52.40R |
| Expectancy | -0.060R | -0.044R |
| PF | 0.923 | 0.945 |
| Positive calendar years | 4/10 | 4/10 |
| Longest win streak | 6 | 5 |
| Longest loss streak | 22 | 27 |
| Worst yearly 5%-risk DD | 95.53% | 93.53% |
| Median yearly ending RM | RM46.12 | RM39.02 |
| Worst yearly ending RM | RM5.87 | RM8.87 |

This fails the research gates decisively.

## Why the 60-day result failed

The loose `EXTERNAL_SWEEP` body-retracement branch supplied most of the frequency and most of the losses.

### 3.5R playbook contribution

| Playbook | Trades | WR | Net R | Exp/trade | PF |
|---|---:|---:|---:|---:|---:|
| EXTERNAL_SWEEP | 990 | 25.35% | -78.38R | -0.079R | 0.901 |
| SESSION_EXPANSION_RETEST | 54 | 29.63% | +12.37R | +0.229R | 1.300 |
| TREND_PULLBACK | 149 | 26.85% | +13.60R | +0.091R | 1.113 |

The two structurally directional branches were positive in aggregate at 3.5R, but together they generated only ~1.7 trades/month. They cannot meet the frequency requirement alone.

This confirms the earlier secondary-feed finding: **loose external-sweep body retracement is not robust. External sweeps must remain strict-FVG or be rejected.**

## Yearly result

See `annual_compare.csv`.

The only clearly strong period was 2023-2024. 2017, 2019-2021 and 2025 were materially negative. 2026 is positive but with unacceptable drawdown.

At 3.5R:
- 2023: +39.84R, RM100 -> RM453.29
- 2024: +20.83R, RM100 -> RM163.89
- 2026 YTD: +17.02R, RM100 -> RM154.59
- 2020: -40.32R, RM100 -> RM8.87
- 2021: -32.43R, RM100 -> RM12.94
- 2025: -14.05R, RM100 -> RM33.64

This is regime dependence, not a universal base edge.

## 2026 3.5R monthly audit

| Month | Trades | W-L | TP | SL | Time exit | Net R | PF | Max W streak | Max L streak | Start RM | End RM | Return | DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Jan | 6 | 0-6 | 0 | 6 | 0 | -6.35 | 0.00 | 0 | 6 | 100.00 | 72.16 | -27.84% | 27.84% |
| Feb | 7 | 0-7 | 0 | 7 | 0 | -7.23 | 0.00 | 0 | 7 | 72.16 | 49.78 | -31.01% | 31.01% |
| Mar | 8 | 3-5 | 3 | 5 | 0 | +5.27 | 2.03 | 1 | 3 | 49.78 | 61.80 | +24.15% | 14.69% |
| Apr | 16 | 3-13 | 3 | 13 | 0 | -3.23 | 0.76 | 1 | 8 | 61.80 | 49.58 | -19.77% | 35.27% |
| May | 12 | 4-8 | 3 | 8 | 1 | +2.59 | 1.31 | 1 | 4 | 49.58 | 53.57 | +8.05% | 19.50% |
| Jun | 9 | 1-8 | 0 | 8 | 1 | -6.66 | 0.21 | 1 | 8 | 53.57 | 37.82 | -29.40% | 35.10% |
| Jul | 10 | 7-3 | 7 | 3 | 0 | +20.93 | 7.71 | 2 | 1 | 37.82 | 97.75 | +158.46% | 5.32% |
| Aug | 10 | 4-6 | 4 | 6 | 0 | +7.39 | 2.17 | 2 | 3 | 97.75 | 133.06 | +36.12% | 15.00% |
| Sep* | 13 | 4-9 | 4 | 9 | 0 | +4.31 | 1.46 | 3 | 4 | 133.06 | 154.59 | +16.18% | 19.31% |

*Through 2026-09-18.

2026 3.5R totals:
- 91 trades
- 24 target hits
- 65 SL exits
- 2 time exits
- +17.02R
- +0.187R/trade
- PF 1.25
- RM100 -> RM154.59
- max closed-equity DD 65.23%

A positive 2026 is not sufficient because January-February cut RM100 to RM49.78 before the later recovery.

## Research decision

**Reject `DISPLACEMENT_RETRACE` as an all-playbook base engine.**

Do not tune it by year.

Keep these findings:
1. `EXTERNAL_SWEEP + DISP_BODY50` is rejected.
2. Strict-FVG external sweep remains the only external-sweep version worth further testing.
3. `TREND_PULLBACK` displacement retrace remains a possible quality component, but is too sparse alone.
4. `SESSION_EXPANSION_RETEST` has some positive long-run evidence but is also too sparse and still needs the v2 redesign.
5. 3.5R is less bad than 3R on full history, but neither version qualifies.

Next test from the research plan:
- **Strict-FVG External Sweep + Session Expansion Retest v2 as separate engines**, then
- **Regime-Gated Tick-Volume Momentum** for frequency.

Do not combine engines until each survives its standalone test.
