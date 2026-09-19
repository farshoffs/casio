# RR10 Softer MIXED Efficiency Research — Pace-Aware Iteration

## Scope

Research only. **No live RR10 strategy files were changed.**

The canonical RR10 entry/router remains frozen:
- 0591 impulse -> pullback -> confirmation
- completed H1/H4 MTF context
- existing TREND / MIXED routing
- support window = 2
- H4 ADX strong-trend threshold = 18
- session exclusion
- HTF alignment
- confirmed M15-close entry
- structural 0591 stop
- fixed 3R target
- one active trade at a time
- 5% current-equity risk

This iteration researches a **softer post-router MIXED-regime quality condition**.

Data:
- `fxpro_xauusd_newm15.csv`
- SHA-256: `b0ea989c3f9f2b9d86c066eff1a65c1359eee080f9cc92839daffa8f847626bd`
- XAUUSD M15
- coverage: 2017-01-02 23:00 UTC -> 2026-09-18 20:45 UTC
- test start: 2017-03-04 after warm-up

## Manual-trading observation supplied by user

The user noted that 500-800 points historically took materially longer to travel than similar nominal point moves today.

The CSV supports the change in market speed/range.

### Median M15 range

| Year | Median M15 range | Median M15 range % |
|---:|---:|---:|
| 2017 | $0.91 | 0.0725% |
| 2018 | $0.94 | 0.0741% |
| 2019 | $1.02 | 0.0738% |
| 2020 | $2.36 | 0.1318% |
| 2021 | $1.73 | 0.0965% |
| 2022 | $1.90 | 0.1063% |
| 2023 | $1.66 | 0.0855% |
| 2024 | $2.40 | 0.0996% |
| 2025 | $4.40 | 0.1290% |
| 2026 YTD | $8.65 | 0.1915% |

### Median daily range

| Year | Median daily range | Median daily range % |
|---:|---:|---:|
| 2017 | $10.95 | 0.8765% |
| 2018 | $10.14 | 0.7975% |
| 2019 | $11.50 | 0.8418% |
| 2020 | $22.84 | 1.2820% |
| 2021 | $19.23 | 1.0621% |
| 2022 | $20.55 | 1.1533% |
| 2023 | $19.23 | 0.9921% |
| 2024 | $26.70 | 1.1171% |
| 2025 | $45.01 | 1.3476% |
| 2026 YTD | $90.93 | 2.0355% |

The observation is therefore real even after partially normalizing for gold's price level.

However, it does not by itself explain RR10 failure. RR10 uses a structural/ATR-derived stop and R-multiple target, so it scales with volatility rather than demanding a fixed 500/800-point move.

Baseline 3R winner median holding time was not monotonically longer in the old regime:
- 2017: 5.25h
- 2018: 4.25h
- 2019: 7.63h
- 2020: 7.38h
- 2021: 7.25h
- 2022: 6.25h
- 2023: 6.38h
- 2024: 12.00h
- 2025: 5.88h
- 2026 YTD: 6.13h

Therefore raw point speed should **not** be used as a hard filter.

## Pace variable

To incorporate the user's observation safely, market pace is normalized:

`pace = completed H4 ATR as % of price / rolling median of completed H4 ATR% over the prior 120 H4 bars`

This asks whether current movement is fast or slow **relative to the market's own recent regime**, avoiding a hard dollar/point threshold.

## Baseline

| Period | Trades | WR | Expectancy | PF | Trades/30d | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| 2017-2023 development | 540 | 24.63% | -0.015R | 0.98 | 6.50 | 93.26% |
| 2020-2023 weak block | 295 | 23.73% | -0.051R | 0.93 | 6.06 | 89.31% |
| 2024-2026 holdout | 244 | 40.57% | +0.623R | 2.05 | 7.38 | 35.50% |

## Softer candidates

### A — Previous hard ER gate
MIXED requires ER20 >= 0.25.

This was effective but removed too many trades:
- 2020-2023: ~4.1 trades/30d
- 2024-2026: ~5.7 trades/30d

### B — Low-ER requires support >= 3
TREND is unchanged.
For MIXED:
- ER20 >= 0.25: normal RR10 support requirement remains
- ER20 < 0.25: require support >= 3

Results:
- 2020-2023: 200 trades, 27.50% WR, +0.100R, PF 1.14, 4.11 trades/30d, 68.10% DD
- 2024-2026: 189 trades, 41.27% WR, +0.651R, PF 2.11, 5.72 trades/30d, 44.70% DD

Still too restrictive.

### C — Pace-aware soft confirmation — best compromise in this iteration

TREND entries: unchanged.

MIXED entries:
1. If H4 ER20 >= 0.25 -> use normal RR10.
2. If ER20 < 0.25 but normalized H4 pace >= 0.90 -> use normal RR10.
3. Only when **both** directional efficiency is poor **and** market pace is slow relative to its recent regime -> require support >= 3 instead of the normal 2.

This does not hard-block low-ER MIXED trades. It asks for one extra existing RR10 confirmation only in the low-efficiency + slow-pace combination.

### Candidate C results

| Period | Trades | WR | Expectancy | PF | Trades/30d | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| 2017-2023 | 477 | 26.21% | +0.048R | 1.07 | 5.74 | 84.65% |
| 2020-2023 | 254 | 25.59% | +0.024R | 1.03 | 5.22 | 74.02% |
| 2024-2026 | 221 | 41.18% | +0.647R | 2.10 | 6.68 | 37.86% |

Versus baseline:
- weak-block trade frequency falls only from 6.06 -> 5.22 trades/30d, rather than ~4.1 under the hard gate
- weak-block expectancy improves from -0.051R -> +0.024R
- weak-block max DD improves from 89.31% -> 74.02%
- holdout expectancy improves slightly from +0.623R -> +0.647R
- holdout PF improves from 2.05 -> 2.10
- holdout frequency remains materially closer to baseline: 6.68 vs 7.38 trades/30d
- holdout DD is slightly worse: 37.86% vs 35.50%

## Candidate C year by year

| Year | Trades | WR | Expectancy | PF | Trades/30d | Max DD |
|---:|---:|---:|---:|---:|---:|---:|
| 2017* | 69 | 23.19% | -0.072R | 0.91 | 6.83 | 63.50% |
| 2018 | 84 | 21.43% | -0.143R | 0.82 | 6.90 | 69.15% |
| 2019 | 70 | 37.14% | +0.486R | 1.77 | 5.75 | 32.11% |
| 2020 | 59 | 23.73% | -0.051R | 0.93 | 4.84 | 50.09% |
| 2021 | 62 | 27.42% | +0.097R | 1.13 | 5.10 | 30.53% |
| 2022 | 69 | 24.64% | -0.014R | 0.98 | 5.67 | 74.02% |
| 2023 | 64 | 26.56% | +0.063R | 1.09 | 5.26 | 55.59% |
| 2024 | 73 | 34.25% | +0.370R | 1.56 | 5.98 | 37.86% |
| 2025 | 86 | 45.35% | +0.814R | 2.49 | 7.07 | 27.52% |
| 2026 YTD | 62 | 43.55% | +0.742R | 2.31 | 7.13 | 25.83% |

## Interpretation

The user's market-speed observation improves the research design, but the useful implementation is **relative pace**, not raw points.

Candidate C is materially softer than the previous hard ER filter:
- it retains ~86% of baseline weak-block frequency
- it retains ~91% of baseline holdout frequency
- it turns the 2020-2023 combined expectancy slightly positive
- it preserves strong 2025-2026 behavior
- it does not alter TREND entries at all

But it is still **not ready to deploy**:
- 2018 remains bad
- 2020 remains negative
- 2022 is only near breakeven
- long-development DD is still very high
- 2024-2026 holdout DD is slightly worse than baseline

## Research direction

The next useful refinement should stay inside Candidate C's architecture and avoid adding new indicators.

Specifically:
- preserve TREND unchanged
- preserve normal MIXED entries when ER is healthy
- preserve low-ER MIXED entries when pace is adequate
- for low-ER + slow-pace MIXED only, research whether support=3 is enough or whether the extra confirmation should be **directional-quality based** (e.g. support composition / both H1-H4 alignment) rather than a simple count

This is more promising than a hard ER cutoff and more consistent with the user's manual observation.

No live strategy deployment is recommended from this iteration.
