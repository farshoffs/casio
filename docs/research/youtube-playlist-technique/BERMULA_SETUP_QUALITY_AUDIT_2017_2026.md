# Bermula Setup-Quality Audit — 2017-2026 YTD

Updated: 2026-09-24

## Frozen architecture

```text
H4 Bermula/S&R break -> direction only
M15 Bermula/S&R -> setup
M15 breakout -> pullback/retest
M1 confirmation -> entry
M15 structural stop
3R benchmark
one position at a time
```

The prior full-history 3R baseline was 694 trades, 26.37% WR, +38R gross, PF 1.074, 25R max DD. A simple 1bp round-trip price-cost sensitivity reduced it to -2.26R.

## Audit

All 800 unique confirmed signals were labeled and compared using M15 breakout strength, zone age/touches, pullback delay, retest depth, M1 confirmation delay/strength/close location, H4-state age, nested-M1-Bermula attempts, MFE and fixed-R outcomes.

Time blocks used to reject unstable ideas:
- discovery: 2017-2022;
- validation block: 2023-2025;
- 2026 YTD reference.

These are not pristine out-of-sample blocks because the audit inspected them while designing candidate filters.

## Rejected / weak filters

Larger M15 breakout candles, larger M1 confirmation candles, generic freshness counts, deep-retest requirements and H4-state-age thresholds were inconsistent.

A strict nested-M1-Bermula implementation that reused the H4/M15 1.5-ATR pivot/departure rule qualified only about 1.9% of setups. It is rejected as too restrictive for the lower timeframe.

## Candidate A — developed M1 confirmation

Require M1 confirmation to occur 3-5 minutes after the M15 retest, rather than immediately or late.

| Period | Trades | WR | Net R | Exp | PF | DD |
|---|---:|---:|---:|---:|---:|---:|
| 2017-2022 | 120 | 30.00% | +24R | +0.200R | 1.286 | 11R |
| 2023-2025 | 53 | 32.08% | +15R | +0.283R | 1.417 | 6R |
| 2026 YTD | 11 | 45.45% | +9R | +0.818R | 2.500 | 2R |
| **All** | **184** | **31.52%** | **+48R** | **+0.261R** | **1.381** | **11R** |

1bp sensitivity: +38.44R, +0.209R/trade, PF 1.29, DD 11.68R.

Gross yearly R: 2017 +2, 2018 +8, 2019 +10, 2020 -7, 2021 +4, 2022 +7, 2023 +12, 2024 +3, 2025 0, 2026 YTD +9.

A broader 3-8 minute window remains positive: 390 trades, 28.72% WR, +58R gross, PF 1.209, 13R DD, +35.88R after 1bp. This supports a plateau rather than one magical exact minute.

## Candidate B — edge retest + developed confirmation

Derived / hypothesis rule:
- confirmation 3-5 minutes after M15 retest;
- retest remains within +/-10% of M15 zone width around the broken Bermula edge;
- all other rules unchanged;
- fixed 3R benchmark.

| Period | Trades | WR | Net R | Exp | PF | DD |
|---|---:|---:|---:|---:|---:|---:|
| 2017-2022 | 72 | 36.11% | +32R | +0.444R | 1.696 | 6R |
| 2023-2025 | 45 | 31.11% | +11R | +0.244R | 1.355 | 5R |
| 2026 YTD | 8 | 50.00% | +8R | +1.000R | 3.000 | 1R |
| **All** | **125** | **35.20%** | **+51R** | **+0.408R** | **1.630** | **6R** |

1bp sensitivity: +44.85R, +0.359R/trade, PF 1.528, DD 6.35R.

Gross yearly R:
- 2017 +1
- 2018 +11
- 2019 +11
- 2020 -2
- 2021 +6
- 2022 +5
- 2023 +11
- 2024 -1
- 2025 +1
- 2026 YTD +8

The 1bp sensitivity remains positive in every year except 2020 and 2024.

### RM100 illustration — Candidate B, 3R

Gross current-equity compounding:
- 1% risk: RM162.66, max DD 5.91%
- 2% risk: RM252.80, max DD 11.62%
- 5% risk: RM735.05, max DD 27.52%

With 1bp sensitivity:
- 1%: RM152.99
- 2%: RM223.73
- 5%: RM542.65

These are research-sample results, not forward expectations.

## Robustness

Neighboring settings remain positive rather than collapsing outside one exact threshold. Examples include 3-5 minutes with <=5%, <=10% and <=15% edge depth, and 3-6 / 3-7 minutes with <=10% depth.

## Frequency trade-off

- baseline 3R: 694 trades
- 3-8 minute confirmation: 390
- 3-5 minute confirmation: 184
- edge +/-10% + 3-5 minute confirmation: 125

Candidate B is only about 1.1 trades per calendar month and cannot meet an 8-trades/month requirement by itself.

## Interpretation

The strongest discriminator is not simply candle size. It is retest behavior:

```text
H4 direction
 -> M15 Bermula breakout
 -> controlled return near the broken Bermula edge
 -> allow M1 a few bars to build local structure
 -> M1 microstructure break
 -> entry
 -> M15 structural stop
 -> 3R benchmark
```

This is consistent with the lower-timeframe lesson concept of confirmation / another Bermula at the entry area, but the exact creator-native micro-Bermula geometry remains unresolved.

## Research decision

Freeze two candidates and stop threshold optimization on this file:

1. **Bermula Developed Confirmation** — M1 confirm 3-8 minutes after retest. More trades, lower selectivity.
2. **Bermula Accurate-Fast** — M1 confirm 3-5 minutes after retest + retest stays within +/-10% of the M15 Bermula edge. Fewer trades, much stronger historical quality metrics.

Next validation should use untouched forward data or an independent data source/instrument.
