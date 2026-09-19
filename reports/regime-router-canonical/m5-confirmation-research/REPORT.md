# RR10 Conditional M5 Confirmation Research — Secondary Feed

## Scope

Research only. **No live RR10 files are modified.**

The canonical M15/H1/H4 RR10 router and 0591 signal logic are frozen. M5 is used only when an otherwise-valid M15 RR10 signal is classified as questionable by the existing research hypotheses:

- MIXED: H4 aligned with direction + H4 ER20 < 0.25 + normalized H4 pace < 1.10
- TREND: no recent V1 confirmation + normalized H4 pace < 1.00

Normal/favourable RR10 signals enter immediately exactly as before.

### Data limitation

This first M5 pass uses the repository's **OctaFX / Octa Markets MT4 secondary XAUUSD M5 dataset**, not FxPro M5.
- M5 coverage used: 2016-01-03T23:05:00+00:00 -> 2026-01-30T21:55:00+00:00
- M5 rows used after warm-up cut: 701,154
- Resampled M15 rows: 234,859
- Raw RR10 candidate signals from 2017-03-04 onward: 552

Therefore this is a **cross-broker robustness experiment**, not execution-grade FxPro validation.

## M5 confirmation variants

- **A / STRUCTURE**: after a pullback/opposite M5 bar, require a directional M5 close breaking the prior 3-bar local extreme with >=45% body and on the correct side of M5 EMA20.
- **B / MICRO0591**: require an M5 0591 confirmation in the same direction; a confirmation in the last two completed M5 bars can validate immediately.
- **C / EITHER**: accept the first A or B confirmation.
- Windows tested: 15 and 30 minutes.

For delayed entries the original M15 structural stop is preserved. The 3R target is recalculated from the actual confirmed M5 entry to that same structural stop. Stop-first is used on an M5 bar if stop and target collide.

## Aggregate results

| Policy | 2017-2023 | 2020-2023 | 2024-2025 |
|---|---|---|---|
| IMMEDIATE | 318 trades, 27.36% WR, +0.094R exp, PF 1.13, 3.83/30d, DD 71.29% | 249 trades, 27.31% WR, +0.092R exp, PF 1.13, 5.11/30d, DD 71.29% | 130 trades, 36.15% WR, +0.446R exp, PF 1.70, 5.34/30d, DD 43.41% |
| A15_STRUCTURE | 279 trades, 27.24% WR, +0.090R exp, PF 1.12, 3.36/30d, DD 65.07% | 218 trades, 27.06% WR, +0.083R exp, PF 1.11, 4.48/30d, DD 65.07% | 117 trades, 33.33% WR, +0.333R exp, PF 1.50, 4.80/30d, DD 47.47% |
| A30_STRUCTURE | 287 trades, 26.83% WR, +0.073R exp, PF 1.10, 3.45/30d, DD 71.55% | 225 trades, 26.67% WR, +0.067R exp, PF 1.09, 4.62/30d, DD 71.55% | 120 trades, 34.17% WR, +0.367R exp, PF 1.56, 4.92/30d, DD 47.00% |
| B15_MICRO0591 | 269 trades, 28.25% WR, +0.130R exp, PF 1.18, 3.24/30d, DD 49.39% | 210 trades, 28.57% WR, +0.143R exp, PF 1.20, 4.31/30d, DD 49.39% | 116 trades, 34.48% WR, +0.379R exp, PF 1.58, 4.76/30d, DD 43.41% |
| B30_MICRO0591 | 271 trades, 28.04% WR, +0.122R exp, PF 1.17, 3.26/30d, DD 51.73% | 212 trades, 28.30% WR, +0.132R exp, PF 1.18, 4.35/30d, DD 51.73% | 116 trades, 34.48% WR, +0.379R exp, PF 1.58, 4.76/30d, DD 44.70% |
| C15_EITHER | 285 trades, 27.72% WR, +0.109R exp, PF 1.15, 3.43/30d, DD 59.83% | 223 trades, 27.80% WR, +0.112R exp, PF 1.16, 4.58/30d, DD 59.83% | 121 trades, 33.06% WR, +0.322R exp, PF 1.48, 4.97/30d, DD 49.65% |
| C30_EITHER | 292 trades, 27.05% WR, +0.082R exp, PF 1.11, 3.51/30d, DD 67.28% | 229 trades, 27.07% WR, +0.083R exp, PF 1.11, 4.70/30d, DD 67.28% | 121 trades, 34.71% WR, +0.388R exp, PF 1.59, 4.97/30d, DD 47.00% |

## Pre-registered development selection rule

A candidate is considered development-promising only if, versus IMMEDIATE on 2017-2023, it:
- retains at least 85% of trade frequency,
- improves expectancy, and
- reduces max drawdown.

Selected by development data only: **B30_MICRO0591**.

The 2024-2025 result for that candidate is treated as the holdout check and was not used to choose it.

## Important interpretation

Because the M5 feed is from a different broker than the FxPro M15 research base, a positive result here means the *idea is robust enough to justify an FxPro-M5 validation*. It does not justify deployment by itself.

A full deployment decision still requires genuine FxPro XAUUSD M5 history aligned to the FxPro M15 feed.

No TradingView Pine, cBot, canonical RR10 Python engine, or live configuration was changed.
