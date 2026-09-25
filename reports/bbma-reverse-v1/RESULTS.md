# BBMA Reverse v1 — Pure Direction-Inversion Test

Date: 2026-09-25

Branch: `research/bbma-reverse-v1-20260925`

## Experiment

This is an isolation test of one hypothesis only:

> Are the frozen BBMA Cleaner Core signals directionally backwards?

The original accepted signal is inverted at the final signal boundary:

- original LONG -> reversed SHORT
- original SHORT -> reversed LONG

No BBMA feature, MTF gate, family definition, freshness rule, cadence filter, stop-distance filter, entry timing, management rule, or exit rule was deliberately optimized for the reversed system.

The source engine is the frozen `casio/bbma_cleaner_robustness.py`.

## Important limitation

The current canonical GitHub M5 dataset is **Dukascopy XAUUSD bid M5**, not the old full FxPro research feed. It currently ends at **2026-08-21 20:55 UTC**. Therefore the 2026 section below is Jan 1 through Aug 21 only.

This v1 also deliberately retains the frozen original management, including the historical +0.50R trigger -> +0.25R protected-stop rule and 50% at 3R / 50% at 4R. That is necessary for a clean direction-only A/B test, but it means this result is **not** compliant with the later real-SL/no-protection rule.

All results below are gross before realistic spread/slippage stress.

## Same-data A/B — full available 2020-01-09 to 2026-08-21

| Metric | Original BBMA | BBMA Reverse v1 |
|---|---:|---:|
| Trades | 925 | 942 |
| Positive exits | 62.38% | 57.22% |
| Avg R/trade | +0.0428R | **+0.0521R** |
| Profit factor | 1.130 | **1.170** |
| Net R | +39.61R | **+49.04R** |
| Trades/month | 11.56 | 11.78 |
| RM100 continuous compounding* | ~RM227.62 | **RM388.81** |

\* Original continuous equity is reconstructed from the same yearly 5%-risk multiplicative return factors. Reverse v1 is reported directly by the replay.

The inversion improves aggregate gross expectancy on this Dukascopy window, but it does **not** dominate consistently by year.

## Calendar-year comparison — RM100 reset each year

| Year | Original BBMA end RM | Reverse v1 end RM | Reverse v1 WR | Reverse v1 Avg R | Reverse v1 PF | Reverse max DD |
|---|---:|---:|---:|---:|---:|---:|
| 2020 | 126.65 | **75.04** | 54.35% | -0.0231R | 0.928 | 57.59% |
| 2021 | 48.31 | **180.58** | 65.19% | +0.1070R | 1.434 | 22.83% |
| 2022 | 149.90 | **111.76** | 56.52% | +0.0378R | 1.124 | 40.61% |
| 2023 | 200.27 | **126.78** | 55.10% | +0.0584R | 1.182 | 46.13% |
| 2024 | 102.90 | **177.79** | 56.46% | +0.1059R | 1.351 | 32.21% |
| 2025 | 119.31 | **138.76** | 59.26% | +0.0733R | 1.238 | 48.72% |
| 2026 to Aug 21 | 100.95 | **82.09** | 52.94% | -0.0145R | 0.958 | 56.60% |

The striking feature is **regime swapping**: years where the original is weak can be strong for the reverse (especially 2021), while some strong original years are materially weaker when reversed (2020, 2022, 2023, and 2026 YTD).

## 2026 Reverse v1 monthly — RM100 continuous equity

| Month | Trades | W-L | Positive rate | Avg R | Net R | PF | End RM | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Jan | 12 | 5-7 | 41.67% | -0.0128R | -0.15R | 0.967 | 97.41 | 19.14% |
| Feb | 11 | 6-5 | 54.55% | -0.0145R | -0.16R | 0.962 | 95.26 | 12.11% |
| Mar | 14 | 5-9 | 35.71% | -0.3952R | -5.53R | 0.184 | 71.66 | 25.70% |
| Apr | 14 | 6-8 | 42.86% | -0.0753R | -1.05R | 0.818 | 66.61 | 22.83% |
| May | 9 | 4-5 | 44.44% | -0.4064R | -3.66R | 0.215 | 55.15 | 17.21% |
| Jun | 13 | 5-8 | 38.46% | +0.1688R | +2.19R | 1.453 | 59.91 | 17.84% |
| Jul | 13 | 11-2 | 84.62% | +0.0815R | +1.06R | 1.627 | 62.99 | 5.00% |
| Aug 1-21 | 16 | 12-4 | 75.00% | +0.3637R | +5.82R | 2.988 | **82.09** | 10.96% |

2026 partial totals:

- 102 trades
- 54 positive / 48 non-positive
- 52.94% positive rate
- -0.0145R/trade
- PF 0.958
- -1.48R
- ~12.75 trades/month
- RM100 -> **RM82.09**
- max compounded DD **56.60%**
- longest positive streak 9
- longest losing streak 5
- 67 stop exits
- 4 TP2 exits
- 31 opposite-signal exits

## Conclusion

The pure inversion hypothesis is **not validated as a universal fix**.

There is a real signal in the result worth investigating: over the full 2020-Aug-2026 Dukascopy sample, the reverse has higher gross Avg R, PF, Net R, and compounded ending equity than the original. But it fails badly in 2020 and again in 2026 YTD, with drawdowns above 50%.

Therefore the evidence is more consistent with:

> the BBMA event may sometimes identify an exhaustion/reversal location, but whether continuation or reversal is favored is regime-dependent.

Do not promote Reverse v1. Keep it as the clean control experiment.

A separate follow-up should be named Reverse v2 rather than modifying v1 if testing the current rules: real SL, no BE/protected stop, fixed 1:3, and cost stress.
