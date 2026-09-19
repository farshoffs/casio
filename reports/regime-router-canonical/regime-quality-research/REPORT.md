# RR10 Regime-Quality Filter Research — Router Frozen

## Research rule

This study does **not** modify the canonical RR10 entry/router.

Frozen:
- M15 0591 impulse -> pullback -> confirmation
- completed H1/H4 MTF context
- TREND / MIXED routing logic
- support window = 2
- strong-trend H4 ADX threshold = 18
- session exclusion
- H1/H4 alignment requirement
- one active trade at a time
- confirmed M15-close entry
- fixed structural 0591 stop
- fixed 3R target for this regime-filter experiment
- 5% current-equity risk model

The only researched change is an **extra regime-quality veto after RR10 already says the entry is valid**.

Data:
- `fxpro_xauusd_newm15.csv`
- 229,303 XAUUSD M15 bars
- coverage: 2017-01-02 23:00 UTC -> 2026-09-18 20:45 UTC
- long-history test starts 2017-03-04 after warm-up

Method:
- development period: 2017-03-04 -> 2023-12-31
- weak-block focus: 2020-2023
- holdout: 2024 -> 2026 YTD
- all filters use completed H4 information available at entry
- no future bars are used in the filter

## Baseline

Canonical fixed-3R RR10:

| Period | Trades | WR | Expectancy | PF | Trades/30d | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| 2017-2023 development | 540 | 24.63% | -0.015R | 0.98 | 6.50 | 93.26% |
| 2020-2023 weak block | 295 | 23.73% | -0.051R | 0.93 | 6.06 | 89.31% |
| 2024-2026 holdout | 244 | 40.57% | +0.623R | 2.05 | 7.38 | 35.50% |

## Variables investigated

Completed H4 metrics:
- 20-bar Kaufman-style efficiency ratio (ER20)
- 30-bar efficiency ratio
- 3-bar H4 ADX slope
- EMA20/EMA50 separation normalized by H4 ATR
- H4 ATR divided by its 20-bar rolling median (volatility-shock ratio)
- H4 directional-bias persistence in completed H4 bars
- +DI/-DI separation
- existing support count, alignment count and TREND/MIXED mode

In the 2020-2023 baseline trades the strongest simple separation between winners and losses was **H4 efficiency**:
- losing trades mean ER20: ~0.260
- winning trades mean ER20: ~0.306
- losing median ER20: ~0.211
- winning median ER20: ~0.291

ATR-shock ratio, raw H4 ADX and EMA separation were much less discriminative by themselves.

## Candidate results

### Q1 — Require ER20 >= 0.25 only for MIXED entries

TREND entries remain untouched.
MIXED entries are skipped when completed-H4 ER20 < 0.25.

| Period | Trades | WR | Expectancy | PF | Trades/30d | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| 2017-2023 | 367 | 27.52% | +0.101R | 1.14 | 4.41 | 76.41% |
| 2020-2023 | 199 | 27.64% | +0.106R | 1.15 | 4.09 | 66.42% |
| 2024-2026 | 187 | 41.18% | +0.647R | 2.10 | 5.66 | 44.70% |

Year-by-year expectancy:
- 2017: -0.133R
- 2018: -0.034R
- 2019: +0.520R
- 2020: +0.048R
- 2021: +0.200R
- 2022: -0.019R
- 2023: +0.185R
- 2024: +0.115R
- 2025: +1.056R
- 2026 YTD: +0.704R

This is the strongest direct evidence that low H4 directional efficiency is part of the 2020-2023 failure mode. It turns 2020, 2021 and 2023 positive and nearly neutralizes 2022.

The cost is substantial frequency reduction and a worse holdout max drawdown than baseline.

### Q2 — Require at least 6 completed H4 bars of bias persistence for MIXED entries

TREND entries remain untouched.

| Period | Trades | WR | Expectancy | PF | Trades/30d | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| 2017-2023 | 342 | 26.32% | +0.053R | 1.07 | 4.11 | 73.86% |
| 2020-2023 | 180 | 26.11% | +0.044R | 1.06 | 3.70 | 66.29% |
| 2024-2026 | 170 | 43.53% | +0.741R | 2.31 | 5.14 | 33.66% |

Year-by-year expectancy:
- 2017: -0.228R
- 2018: -0.018R
- 2019: +0.500R
- 2020: +0.026R
- 2021: +0.067R
- 2022: -0.130R
- 2023: +0.200R
- 2024: +0.259R
- 2025: +1.087R
- 2026 YTD: +0.787R

This preserves strong recent quality and improves the 2024-2026 holdout drawdown, but frequency falls too far and 2022 remains weak.

### Q3 — Soft veto: reject only when ER20 < 0.15 AND H4 ADX is falling

This is the least aggressive candidate.

| Period | Trades | WR | Expectancy | PF | Trades/30d | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| 2017-2023 | 431 | 26.22% | +0.049R | 1.07 | 5.18 | 77.67% |
| 2020-2023 | 238 | 25.63% | +0.025R | 1.03 | 4.89 | 77.67% |
| 2024-2026 | 209 | 39.23% | +0.569R | 1.94 | 6.32 | 47.47% |

Year-by-year expectancy:
- 2017: -0.125R
- 2018: -0.091R
- 2019: +0.460R
- 2020: 0.000R
- 2021: +0.161R
- 2022: -0.082R
- 2023: +0.016R
- 2024: +0.159R
- 2025: +0.756R
- 2026 YTD: +0.793R

This retains more trades but does not improve the holdout enough to justify deployment.

## What did not work well

### ATR-shock veto alone
The 2020 pandemic intuition is fundamentally plausible, but H4 ATR / rolling-median ATR did not separate winners from losses strongly enough in this dataset.

### Raw H4 ADX threshold / rising ADX alone
The current router already uses ADX. Requiring a higher or rising ADX by itself removed many trades without solving the weak years consistently.

### EMA20/EMA50 separation normalized by ATR
Useful diagnostically, but not a strong standalone filter.

### +DI/-DI separation
Also weaker than H4 efficiency and persistence.

## Main result

The research supports the hypothesis that the largest technical weakness in the 2020-2023 block is **poor higher-timeframe directional efficiency / persistence**, especially in MIXED mode.

The most promising variable is **H4 efficiency ratio**, not volatility shock and not a larger ADX threshold.

However, no tested filter is ready for deployment.

Why:
1. Q1 improves 2020-2023 materially, but cuts frequency from about 6.1 to 4.1 trades/30d in that block.
2. Q1 also raises the 2024-2026 holdout max DD from 35.5% to 44.7%.
3. Q2 has cleaner holdout behavior but cuts frequency even more.
4. Q3 preserves more trades but weakens recent holdout expectancy and drawdown.
5. 2022 remains difficult even after the strongest simple filters.

## Research verdict

**Promising mechanism, not yet a deployable rule.**

The evidence says:
- do not change RR10 / 0591 / MTF routing
- do not add a blunt volatility filter
- continue research specifically on **MIXED-regime H4 directional efficiency**
- 2022 needs separate diagnosis because it remains the hardest year
- deployment should wait until a filter improves weak years while keeping recent frequency closer to the existing ~7-8 trades/30d and without worsening holdout drawdown

No TradingView Pine, cBot, canonical Python engine or live RR10 configuration was changed by this research.
