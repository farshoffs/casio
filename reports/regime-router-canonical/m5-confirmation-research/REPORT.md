# RR10 Genuine FxPro M5 Confirmation Study

## Scope

Research only. **No live RR10 strategy files were changed.**

The canonical RR10 M15/H1/H4 router remains frozen:
- M15 0591 impulse -> pullback -> confirmation
- completed H1/H4 context
- existing TREND / MIXED routing
- support window = 2
- H4 ADX strong-trend threshold = 18
- session exclusion
- HTF alignment
- confirmed M15-close canonical signal
- original M15 structural 0591 stop
- one active trade at a time
- fixed 3R target from the actual research entry to the original M15 structural stop
- 5% current-equity risk

M5 is used **only as a conditional confirmation layer** for previously identified questionable RR10 signals.

## Data integrity

M15:
- `fxpro_xauusd_newm15.csv`
- SHA-256: `b0ea989c3f9f2b9d86c066eff1a65c1359eee080f9cc92839daffa8f847626bd`
- 229,303 bars
- 2017-01-02 23:00 UTC -> 2026-09-18 20:45 UTC

M5:
- `fxpro_xauusd_m5.csv`
- SHA-256: `c74a2b4f669a005c45190a8c6eada8a9fd8bb7bb7aaaf04198a4044696d480fa`
- 687,746 bars
- 2017-01-02 23:00 UTC -> 2026-09-18 20:55 UTC

Resampling the M5 feed to M15 matched the supplied M15 OHLC on more than **99.998% of bars**. Only a handful of bars had tiny discrepancies. The feeds are therefore suitable for an intrabar confirmation study.

The M5-resolution baseline reproduced the canonical annual 3R trade counts and expectancy exactly, providing an additional integrity check.

## Which M15 signals require M5?

Normal/favourable RR10 signals enter normally.

M5 is required only for the research "questionable" states:

### Questionable MIXED
- router mode = MIXED
- H4 aligned with trade direction
- H4 ER20 < 0.25
- normalized H4 pace < 1.10

### Questionable TREND
- router mode = TREND
- no recent same-direction V1 confirmation
- normalized H4 pace < 1.00

In the baseline:
- 2017-2023: about 20% of accepted trades were in these questionable states
- 2020-2023: about 20%
- 2024-2026: about 17%

This preserves the existing RR10 path for the large majority of signals.

## M5 confirmation definitions

### M5-A — structure confirmation

After the M15 signal:
1. require an M5 pullback against the signal direction
2. the pullback must trade through the original M15 signal close
3. then require an M5 directional close that breaks the immediately preceding M5 structure and reclaims the M15 entry level
4. enter at the confirming M5 close

LONG and SHORT are mirrored.

The original M15 structural stop is retained.

### M5-B — micro 0591

Run the original 0591 impulse/pullback/confirmation pattern on M5:
- impulse range >= 1.20 M5 ATR
- body fraction >= 0.55
- close-location threshold 0.72 / 0.28
- breakout of the prior 20 M5 bars
- pullback and confirmation within the same 4-bar 0591 state logic

The M5 impulse must begin **after** the M15 signal. This prevents using a micro setup that was already in progress before RR10 fired.

Enter at the confirming M5 close and keep the original M15 structural stop.

### M5-C — combined

Accept the earliest valid:
- M5-A structure confirmation, or
- M5-B micro 0591 confirmation.

## Waiting / invalidation rules

While waiting for M5:
- if the original M15 structural stop is hit, cancel the setup
- if the original M15 3R target is already reached before confirmation, cancel rather than chase
- no other M15 signal is accepted while the setup is pending
- after M5 confirmation, the target is recalculated to 3R from the actual M5 entry to the unchanged M15 structural stop
- stop-first convention remains in force on M5 bars

Confirmation windows tested:
- 10 minutes
- 15 minutes
- 20 minutes
- 25 minutes
- 30 minutes
- robustness checks also extended to 45 minutes

## Baseline

| Period | Trades | WR | Expectancy | PF | Trades/30d | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| 2017-2023 | 540 | 24.63% | -0.015R | 0.98 | 6.50 | 93.26% |
| 2020-2023 | 295 | 23.73% | -0.051R | 0.93 | 6.06 | 89.31% |
| 2024-2026 | 244 | 40.57% | +0.623R | 2.05 | 7.38 | 35.50% |

## A / B / C comparison — 15 minute confirmation window

### M5-A

| Period | Trades | WR | Expectancy | PF | Trades/30d | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| 2017-2023 | 455 | 26.37% | +0.055R | 1.07 | 5.47 | 79.67% |
| 2020-2023 | 242 | 26.45% | +0.058R | 1.08 | 4.97 | 75.32% |
| 2024-2026 | 218 | 40.83% | +0.633R | 2.07 | 6.59 | 31.15% |

### M5-B

| Period | Trades | WR | Expectancy | PF | Trades/30d | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| 2017-2023 | 443 | 26.41% | +0.056R | 1.08 | 5.33 | 82.07% |
| 2020-2023 | 241 | 26.97% | +0.079R | 1.11 | 4.95 | 75.32% |
| 2024-2026 | 208 | 41.35% | +0.654R | 2.11 | 6.29 | 30.17% |

### M5-C

| Period | Trades | WR | Expectancy | PF | Trades/30d | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| 2017-2023 | 458 | 26.42% | +0.057R | 1.08 | 5.51 | 79.67% |
| 2020-2023 | 245 | 26.53% | +0.061R | 1.08 | 5.03 | 75.32% |
| 2024-2026 | 218 | 40.83% | +0.633R | 2.07 | 6.59 | 31.15% |

## Window result

Short confirmation is materially better in the weak historical block.

### M5-C

| Window | 2020-2023 expectancy | Trades/30d | DD | 2024-2026 expectancy | Trades/30d | DD |
|---:|---:|---:|---:|---:|---:|---:|
| 10m | +0.079R | 4.95 | 75.32% | +0.645R | 6.47 | 30.17% |
| **15m** | **+0.061R** | **5.03** | **75.32%** | **+0.633R** | **6.59** | **31.15%** |
| 20m | +0.040R | 5.13 | 75.32% | +0.618R | 6.65 | 31.15% |
| 25m | +0.024R | 5.22 | 75.32% | +0.632R | 6.74 | 31.15% |
| 30m | +0.004R | 5.32 | 76.80% | +0.636R | 6.80 | 31.15% |

A 45-minute window deteriorated further in the weak block.

Interpretation: when a questionable M15 RR10 setup is genuinely going to confirm on M5, the useful confirmation usually needs to happen quickly. Allowing late M5 confirmation admits lower-quality continuation.

The 10-minute window has the highest weak-period expectancy but is more selective. **15 minutes is the more practical quality/frequency compromise in this family.**

## M5-C 15m year by year

| Year | Trades | WR | Expectancy | PF | Trades/30d | Max DD |
|---:|---:|---:|---:|---:|---:|---:|
| 2017* | 64 | 23.44% | -0.063R | 0.92 | 6.34 | 48.74% |
| 2018 | 77 | 22.08% | -0.117R | 0.85 | 6.33 | 73.17% |
| 2019 | 72 | 33.33% | +0.333R | 1.50 | 5.92 | 37.86% |
| 2020 | 58 | 25.86% | +0.034R | 1.05 | 4.75 | 48.20% |
| 2021 | 61 | 29.51% | +0.180R | 1.26 | 5.01 | 31.15% |
| 2022 | 67 | 23.88% | -0.045R | 0.94 | 5.51 | 75.32% |
| 2023 | 59 | 27.12% | +0.085R | 1.12 | 4.85 | 48.20% |
| 2024 | 69 | 36.23% | +0.449R | 1.70 | 5.66 | 30.17% |
| 2025 | 85 | 44.71% | +0.788R | 2.43 | 6.99 | 20.82% |
| 2026 YTD | 64 | 40.63% | +0.625R | 2.05 | 7.36 | 22.62% |

Compared with baseline:
- 2020: -0.059R -> **+0.034R**
- 2021: -0.026R -> **+0.180R**
- 2022: -0.093R -> **-0.045R**
- 2023: -0.027R -> **+0.085R**
- 2024: +0.350R -> **+0.449R**
- 2025: +0.768R -> **+0.788R**
- 2026: +0.739R -> +0.625R

2018 and 2022 remain the unresolved years.

## What M5 is actually doing

The improvement comes primarily from **filtering questionable entries**, not from obtaining a cheaper entry.

For M5-A confirmations, the confirming close is commonly a little worse than the original M15 close because the strategy waits for a reclaim/break before entering.

Therefore:
- M5 confirmation is adding information quality
- it is not acting primarily as an entry-price optimizer

This is desirable for the current experiment because it isolates the value of M5 confirmation itself.

## Confirmation selectivity

Among baseline questionable signals:

2017-2023:
- M5-A 15m confirmed about 18%
- M5-B 15m confirmed about 4%
- M5-C 15m confirmed about 21%

2020-2023:
- M5-A ~9%
- M5-B ~5%
- M5-C ~14%

2024-2026:
- M5-A ~24%
- M5-B produced almost no 15-minute confirmation in the baseline questionable subgroup
- M5-C therefore behaves almost exactly like A in the recent holdout

This means M5-B is **very selective** and often behaves more like a hard veto than a flexible confirmation mechanism.

## Full 2017-2026 context

Using the same continuous gross 3R / 5%-risk replay:

| Policy | Trades | WR | Expectancy | PF | Trades/30d | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 784 | 29.59% | +0.184R | 1.26 | 6.75 | 93.26% |
| M5-A 15m | 673 | 31.05% | +0.242R | 1.35 | 5.79 | 79.67% |
| M5-B 15m | 651 | 31.18% | +0.247R | 1.36 | 5.60 | 82.07% |
| **M5-C 15m** | **676** | **31.07%** | **+0.243R** | **1.35** | **5.82** | **79.67%** |

Ending-balance figures are intentionally omitted here because compounded 5% gross backtests can make terminal RM values look more meaningful than the underlying drawdown/risk actually warrants.

## Exploratory mode-specific hybrid

An additional exploratory combination was checked:

- questionable MIXED -> require M5-B
- questionable TREND -> accept M5-C
- 15-minute window

Results:

2017-2023:
- +0.064R expectancy
- 77.98% max DD
- 5.43 trades/30d

2020-2023:
- +0.070R expectancy
- 75.32% max DD
- 4.99 trades/30d

2024-2026:
- +0.653R expectancy
- 31.15% max DD
- 6.44 trades/30d

It is slightly stronger on aggregate quality than pure M5-C, but M5-B remains extremely selective. Treat this as secondary evidence, not a deployment candidate yet.

## Research conclusion

The genuine M5 data supports the idea.

Most important findings:
1. M5 should **not** be required for every RR10 trade. Universal M5 confirmation cuts frequency dramatically and performs worse.
2. Conditional M5 confirmation on questionable states improves the weak historical block.
3. A short confirmation window is better than waiting 30-45 minutes.
4. M5-A provides the most interpretable confirmation.
5. M5-B is useful but very rare.
6. M5-C 15m is the most balanced pure A/B/C candidate because it keeps structure confirmation while allowing occasional micro-0591 rescue.
7. 2018 and 2022 remain negative, although 2022 improves materially.
8. The recent holdout retains positive expectancy and lower drawdown, but frequency falls below the user's preferred ~8/month.

**Promising research result, not yet a deployment recommendation.**

Next research should investigate whether the M5-C gate can be applied more narrowly to preserve more frequency while keeping the drawdown improvement—especially separating the unresolved 2018/2022 TREND state from the already-improved MIXED state.

No Pine, cBot, canonical Python RR10 engine, or live strategy configuration was modified.
