# RR10 Mode-Specific Filter + Walk-Forward Research

## Scope

Research only. No live RR10 strategy files were changed.

Frozen canonical RR10:
- M15 0591 impulse -> pullback -> confirmation
- completed H1/H4 MTF context
- existing TREND / MIXED router
- support window = 2
- H4 ADX strong-trend threshold = 18
- session exclusion
- HTF alignment
- confirmed M15-close entry
- structural 0591 stop
- fixed 3R target for this filter experiment
- one active trade at a time
- 5% current-equity risk

Dataset:
- `fxpro_xauusd_newm15.csv`
- SHA-256: `b0ea989c3f9f2b9d86c066eff1a65c1359eee080f9cc92839daffa8f847626bd`
- 229,303 XAUUSD M15 bars
- coverage: 2017-01-02 23:00 UTC -> 2026-09-18 20:45 UTC
- research scoring begins 2017-03-04 after warm-up

## Hypotheses tested

### MIXED
Continue the stalled-H4 hypothesis:

Skip only when all are true:
- router mode = MIXED
- H4 aligns with the RR10 direction
- H4 ER20 < 0.25
- normalized H4 pace < 1.10

Support-composition variants were also tested:
- only veto when recent V1 is absent
- only veto when support <= 2
- only veto when structural-frequency support is absent
- only veto when Outcome support is absent

### TREND
Test the historical clue:

Skip only when all are true:
- router mode = TREND
- no recent V1 confirmation
- normalized H4 pace is below a threshold

Pace thresholds tested:
- 0.80
- 0.90
- 1.00
- 1.10
- 1.20

TREND and MIXED filters were then combined and replayed sequentially. Skipping a trade frees the one-active-trade slot, so later entries are re-evaluated rather than post-hoc deleting trades.

## Confirmation-composition result for stalled MIXED

The development-sample stalled-MIXED subgroup is unusually weak:

2017-2023:
- 45 trades
- 11.11% WR
- -0.556R expectancy
- -25R

2020-2023:
- 29 trades
- 6.90% WR
- -0.724R expectancy
- -21R

However, support composition does not provide an obvious rescue rule.

2017-2023 stalled-MIXED subgroup:
- recent V1 present: 42/45 trades, -0.619R expectancy
- recent V1 absent: 3/45 trades, +0.333R
- recent Outcome support: 0/45
- recent Structural Frequency support: 0/45
- recent Structural Portfolio support: 5/45, -0.200R

So simply asking for V1 does not improve this subgroup; V1 is already present on almost all of it.

Important holdout warning:
2024-2026 stalled-MIXED subgroup:
- 26 baseline trades
- 26.92% WR
- +0.077R expectancy

The historical relationship weakens materially in recent data. This is why the stalled-H4 rule must remain research-only.

## TREND no-V1 + slow-pace result

Using pace < 1.00:

2017-2023:
- 65 TREND trades
- 20.00% WR
- -0.200R expectancy
- -13R

2020-2023:
- 30 trades
- 16.67% WR
- -0.333R expectancy
- -10R

But 2024-2026 reverses:
- 16 trades
- 43.75% WR
- +0.750R expectancy
- +12R

Therefore **no-V1 + slow pace is not a stable standalone veto**.

It can improve the sequential portfolio because skipping those entries changes which later RR10 setups are available, but the subgroup itself is profitable in the recent holdout. This is an important robustness warning.

## Most balanced combined research candidate

The best compromise in the tested family was:

### C2
MIXED:
- veto H4-aligned MIXED when ER20 < 0.25 and normalized pace < 1.10

TREND:
- veto no-V1 TREND when normalized pace < 1.00

Everything else is canonical RR10.

### Aggregate comparison

| Period | Policy | Trades | WR | Expectancy | PF | Trades/30d | Max DD |
|---|---|---:|---:|---:|---:|---:|---:|
| 2017-2023 | Baseline | 540 | 24.63% | -0.015R | 0.98 | 6.50 | 93.26% |
| 2017-2023 | **C2** | **439** | **26.42%** | **+0.057R** | **1.08** | 5.28 | **82.07%** |
| 2020-2023 | Baseline | 295 | 23.73% | -0.051R | 0.93 | 6.06 | 89.31% |
| 2020-2023 | **C2** | **238** | **26.89%** | **+0.076R** | **1.10** | 4.89 | **75.32%** |
| 2024-2026 | Baseline | 244 | 40.57% | +0.623R | 2.05 | 7.38 | 35.50% |
| 2024-2026 | **C2** | **207** | **41.55%** | **+0.662R** | **2.13** | 6.26 | **30.17%** |

C2 improves expectancy and drawdown in all three aggregate blocks, but reduces frequency.

## C2 year by year

| Year | Trades | WR | Expectancy | PF | Trades/30d | Max DD |
|---:|---:|---:|---:|---:|---:|---:|
| 2017* | 62 | 22.58% | -0.097R | 0.88 | 6.14 | 44.78% |
| 2018 | 71 | 21.13% | -0.155R | 0.80 | 5.84 | 74.15% |
| 2019 | 68 | 33.82% | +0.353R | 1.53 | 5.59 | 34.59% |
| 2020 | 56 | 26.79% | +0.071R | 1.10 | 4.59 | 44.70% |
| 2021 | 59 | 30.51% | +0.220R | 1.32 | 4.85 | 31.15% |
| 2022 | 66 | 22.73% | -0.091R | 0.88 | 5.42 | 75.32% |
| 2023 | 57 | 28.07% | +0.123R | 1.17 | 4.68 | 42.61% |
| 2024 | 67 | 35.82% | +0.433R | 1.67 | 5.49 | 30.17% |
| 2025 | 79 | 45.57% | +0.823R | 2.51 | 6.49 | 23.02% |
| 2026 YTD | 61 | 42.62% | +0.705R | 2.23 | 7.01 | 22.62% |

The unresolved years remain **2018 and 2022**.

C2 repairs 2020, 2021 and 2023 but does not repair 2018 or 2022.

## Rolling walk-forward threshold selection

A compact parameter family was defined:
- MIXED ER thresholds: 0.15 / 0.20 / 0.25 / 0.30
- MIXED pace thresholds: 0.90 / 1.00 / 1.10
- TREND no-V1 pace thresholds: none / 0.90 / 1.00 / 1.10

For each test year, parameters were selected using only earlier calendar years with a risk-adjusted training objective that penalized unstable annual expectancy and drawdown and required >=5 trades/30d in training.

This is a **pseudo-OOS robustness check**, not a pristine untouched experiment: the general hypotheses were developed after inspecting this historical dataset.

| Test year | Selected | Trades | WR | Expectancy | PF | Max DD |
|---:|---|---:|---:|---:|---:|---:|
| 2020 | M ER<0.15 pace<1.10 + T pace<1.10 | 57 | 26.32% | +0.053R | 1.07 | 48.20% |
| 2021 | M ER<0.20 pace<1.10 + T pace<1.10 | 61 | 29.51% | +0.180R | 1.26 | 33.06% |
| 2022 | M ER<0.25 pace<1.10 + T pace<1.10 | 61 | 22.95% | **-0.082R** | 0.89 | 69.70% |
| 2023 | M ER<0.25 pace<1.00 + T pace<1.10 | 56 | 26.79% | +0.071R | 1.10 | 54.96% |
| 2024 | M ER<0.25 pace<1.00 + T pace<1.10 | 68 | 35.29% | +0.412R | 1.64 | 33.66% |
| 2025 | M ER<0.25 pace<1.10 + T pace<1.10 | 79 | 45.57% | +0.823R | 2.51 | 23.02% |
| 2026 YTD | M ER<0.25 pace<1.10 + T pace<1.10 | 58 | 41.38% | +0.655R | 2.12 | 28.54% |

Six of seven rolling test years are positive; **2022 still fails**.

Across those annual test slices:
- 440 trades
- 146 winners
- 33.18% WR
- +144R total
- +0.327R average expectancy

Do not treat this as one deployable equity curve because the selected rule changes between calendar years.

## What the mode-specific research established

1. **MIXED**
   - stalled-H4 is a real historical failure pattern
   - support composition does not provide a simple rescue rule
   - recent holdout behavior is much better, so a permanent hard veto remains questionable

2. **TREND**
   - no-V1 + slow pace is historically weak
   - but it reverses to strongly positive in 2024-2026
   - therefore this is not a stable standalone filter

3. **Combined**
   - C2 materially improves historical aggregate drawdown and expectancy
   - C2 also improves 2024-2026 aggregate drawdown
   - but frequency falls and the TREND mechanism is not stable enough for deployment
   - 2018 and 2022 remain unresolved

## Conclusion

**Do not deploy C2 yet.**

The research is promising at the portfolio level, but the TREND filter has a regime-reversal problem and the system still has a 2022 failure.

The next research target should be 2018 and 2022 specifically, with emphasis on variables not yet represented strongly in the router:
- higher-timeframe trend age / transition state beyond H4
- D1 context
- impulse quality / stop distance normalized by volatility
- whether the bad TREND setup is early continuation or late-cycle continuation

No Pine, cBot, canonical Python engine or live RR10 configuration was changed.
