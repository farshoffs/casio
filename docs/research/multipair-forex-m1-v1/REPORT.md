# CASIO Multi-Pair Forex M1 Research v1

Date: 2026-09-24

## User target

- Start RM100
- Risk 5% of current equity per entry
- Minimum RR 1:3
- Target WR 70%

## Data

User-supplied FxPro M1 data:
- EURUSD: 3,584,839 rows, 2017-01-01 22:05 UTC -> 2026-09-24 15:38 UTC, SHA256 `733470dfc42b5babe806ab2e3308b07a9c244f7dec6d7ced2006dc95c4898c06`
- GBPUSD: 3,589,010 rows, 2017-01-01 22:05 UTC -> 2026-09-24 15:19 UTC, SHA256 `f47e8218a4d00aaae65f3d7496dcf40638f5efacc47417a8c21b103d5c9b831c`
- GBPJPY: 3,606,586 rows, 2017-01-01 22:13 UTC -> 2026-09-24 15:32 UTC, SHA256 `fd845d8cf5226019fc5a9e30dd345bf0017b6c90ceae72b705a2970058c548e1`

Raw files are each >100MB and cannot be stored through the normal GitHub contents API. The exact dataset manifest/fingerprints are committed so the uploaded originals are auditable.

## Common execution

- causal resampling from M1 to M5/M15/H1/H4/D1 as needed
- fixed 3R in the common screen
- real structural stop only
- no BE/protected-stop conversion
- one active position per strategy/pair
- M1 stop/target chronology; same-M1 stop wins
- gross WR is the primary target metric
- 1bp round-trip sensitivity is recorded separately where available; it is not used to manufacture the headline WR

## Technique families screened

1. EMA Ribbon Break (D1/H4 + M15)
2. Donchian-10 D1/H4 breakout
3. Tick-volume momentum continuation
4. ADX/DI momentum rotation
5. CASIO NY Precision v1 transfer
6. NY opening-hour precision transfer
7. BBMA Reentry MTF transfer (real SL, no protected stop)
8. ICT pre-NY liquidity sweep -> MSS/FVG retrace
9. Silver Bullet 10:00-11:00 NY transfer
10. London/Asia sweep -> MSS/FVG retrace
11. Previous-day high/low sweep -> MSS/FVG retrace
12. Pure S&D first retest + lower-TF confirmation
13. Naked S/R rejection/reversal + lower-TF confirmation
14. Bermula-style Accurate-Fast transfer (H4 direction -> M15 breakout/retest -> M1 3-5m confirmation)
15. FiboRSI8 public-SOP variants at fixed 3R
16. New bounded MTF deep-retracement precision search: 2,430 predeclared combinations, 2017-2022 development / 2023-2026 validation.

## Hard result

**No tested strategy or bounded new-precision variant reached 70% WR at 3R.**

Across the new precision grid, target-70 passes with meaningful development + validation samples: **0**. The highest WR among variants with at least 30 total pooled trades was about **40.43%**, still far below 70%.

## Existing / transferred families — best meaningful rows

| Pair | Strategy | Trades | WR | Gross R | RM100 @5% gross | Gross max DD | Avg/mo | Min/mo |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| EURUSD | FIBORSI8_23_77_HTF32.5 | 2947 | 30.74% | +677R | RM335831751828.01 | 82.20% | 25.22 | 14 |
| EURUSD | FIBORSI8_20_80 | 1831 | 28.89% | +285R | RM127435.85 | 86.49% | 15.71 | 7 |
| GBPJPY | FIBORSI8_23_77_HTF32.5 | 2753 | 28.77% | +415R | RM2447256.73 | 96.28% | 23.53 | 3 |
| GBPUSD | FIBORSI8_20_80 | 1784 | 28.08% | +220R | RM6745.34 | 93.83% | 15.30 | 8 |
| GBPJPY | FIBORSI8_20_80 | 1771 | 27.84% | +201R | RM2849.72 | 97.05% | 15.10 | 6 |
| GBPUSD | FIBORSI8_23_77_HTF32.5 | 2867 | 26.68% | +193R | RM40.63 | 99.66% | 24.58 | 12 |
| GBPUSD | BBMA_REENTRY | 1534 | 26.60% | +98R | RM48.03 | 94.88% | 13.08 | 4 |
| GBPJPY | TICKVOL_MOMENTUM | 2930 | 26.25% | +146R | RM3.45 | 99.51% | 25.03 | 12 |
| GBPUSD | BERMULA_ACCURATE_FAST | 1522 | 25.95% | +58R | RM7.42 | 98.75% | 12.99 | 4 |
| GBPUSD | NAKED_SR_REVERSAL | 2545 | 25.54% | +55R | RM0.17 | 99.98% | 21.81 | 7 |

Important: FiboRSI8 has some high gross-R totals because it generates thousands of trades near a ~27-31% WR; at 5% risk its path DD remains extreme and the cost sensitivity is poor. This is not a 70%-WR solution.

## Best new bounded precision candidate

Frozen candidate from the joint grid:
- New York window
- H1/H4 aligned
- M5 ADX >= 28
- M5 displacement body >= 1.0 ATR
- body/range >= 0.72
- break prior 8 M5 bars
- volume ratio >= 1.0
- 70.5% retracement
- M1 micro-BOS confirmation after touch
- structural lower-TF SL
- fixed 3R

Pooled across the three pairs: **108 trades, 37 wins, 34.26% WR, +40R gross, PF 1.56 gross.**

| Pair | Trades | WR | Net R gross | PF gross | RM100 @5% | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| EURUSD | 37 | 32.43% | +11R | 1.44 | RM148.41 | 37.86% |
| GBPUSD | 44 | 38.64% | +24R | 1.89 | RM269.40 | 27.52% |
| GBPJPY | 27 | 29.63% | +5R | 1.26 | RM115.43 | 36.98% |

Pooled chronological illustration at 5% per completed trade: RM100 -> **RM461.53**, max DD **43.92%**. This is an illustration, not a clean multi-pair portfolio model because concurrent cross-pair exposure is not netted.

Yearly pooled gross R:

| Year | Trades | WR | Net R | PF |
|---:|---:|---:|---:|---:|
| 2017 | 8 | 25.00% | +0R | 1.00 |
| 2018 | 19 | 15.79% | -7R | 0.56 |
| 2019 | 7 | 28.57% | +1R | 1.20 |
| 2020 | 12 | 33.33% | +4R | 1.50 |
| 2021 | 10 | 30.00% | +2R | 1.29 |
| 2022 | 12 | 66.67% | +20R | 6.00 |
| 2023 | 9 | 44.44% | +7R | 2.40 |
| 2024 | 11 | 36.36% | +5R | 1.71 |
| 2025 | 13 | 38.46% | +7R | 1.88 |
| 2026 | 7 | 28.57% | +1R | 1.20 |

## Verdict

Broadening from XAUUSD to EURUSD/GBPUSD/GBPJPY **did not reveal a 70%-WR / 3R system**. The strongest robust-looking new precision family sits in the mid-30% WR range, which is mathematically strong at 3R but does not meet the requested target.

These FX pairs do provide independent opportunity without loosening entries, but the 70% WR target remains the binding constraint.

No threshold is promoted to production from this search. Further work should add new market families (indices/crypto) or reconsider the 70% requirement rather than overfit these three FX histories.
