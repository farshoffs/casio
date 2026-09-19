# RR10 TREND vs MIXED Diagnostic — Router Frozen

## Scope

Research only. No live RR10 strategy files were changed.

Canonical RR10 remains frozen:
- M15 0591 impulse -> pullback -> confirmation
- completed H1/H4 MTF context
- existing TREND / MIXED router logic
- support window = 2
- strong-trend H4 ADX threshold = 18
- session exclusion
- HTF alignment
- confirmed M15-close entry
- structural 0591 stop
- fixed 3R target
- one active trade at a time
- 5% current-equity risk model

Data:
- `fxpro_xauusd_newm15.csv`
- SHA-256: `b0ea989c3f9f2b9d86c066eff1a65c1359eee080f9cc92839daffa8f847626bd`
- 229,303 XAUUSD M15 bars
- coverage: 2017-01-02 23:00 UTC -> 2026-09-18 20:45 UTC
- analysis start: 2017-03-04 after warm-up

## 2017-2023 router split

| Mode | Trades | Share | Wins | Win rate | Expectancy | Net R |
|---|---:|---:|---:|---:|---:|---:|
| TREND | 317 | 58.7% | 81 | 25.55% | +0.022R | +7R |
| MIXED | 223 | 41.3% | 52 | 23.32% | -0.067R | -15R |

The aggregate result is simple:
- TREND was slightly profitable across 2017-2023.
- MIXED produced the net drag.

But the yearly split shows two separate failure mechanisms rather than one universal bad mode.

## Year by year

| Year | MIXED trades | MIXED WR | MIXED expectancy | MIXED net R | TREND trades | TREND WR | TREND expectancy | TREND net R |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2017* | 16 | 37.50% | +0.500R | +8R | 57 | 19.30% | -0.228R | -13R |
| 2018 | 42 | 19.05% | -0.238R | -10R | 52 | 23.08% | -0.077R | -4R |
| 2019 | 33 | 30.30% | +0.212R | +7R | 45 | 35.56% | +0.422R | +19R |
| 2020 | 33 | 21.21% | -0.152R | -5R | 35 | 25.71% | +0.029R | +1R |
| 2021 | 38 | 23.68% | -0.053R | -2R | 40 | 25.00% | 0.000R | 0R |
| 2022 | 33 | 24.24% | -0.030R | -1R | 42 | 21.43% | -0.143R | -6R |
| 2023 | 28 | 14.29% | -0.429R | -12R | 46 | 30.43% | +0.217R | +10R |

Interpretation:
- 2017: TREND failure; MIXED strong.
- 2018: both modes weak.
- 2019: both modes strong.
- 2020: MIXED weak; TREND slightly positive.
- 2021: both roughly flat/weak.
- 2022: TREND is the larger problem.
- 2023: MIXED is extremely weak while TREND is strongly positive.

This explains why one universal regime filter has been difficult to find.

## Winner-vs-loser diagnostics

### TREND — 2017-2023

| Feature | Winner mean | Loser mean | Winner median | Loser median |
|---|---:|---:|---:|---:|
| H4 ADX | 32.13 | 31.93 | 29.35 | 29.79 |
| H4 ADX slope, 3 bars | +1.29 | +1.36 | +0.83 | +1.91 |
| H4 ER20 | 0.368 | 0.344 | 0.370 | 0.315 |
| Normalized H4 pace | 1.023 | 1.039 | 0.991 | 0.997 |
| H4 bias persistence | 16.37 | 14.96 | 11.0 | 10.5 |
| EMA20/50 separation / ATR | 1.332 | 1.327 | 1.112 | 1.383 |
| +DI/-DI separation | 16.76 | 17.33 | 14.88 | 16.87 |
| Support count | 1.815 | 1.657 | 2 | 2 |

There is **no strong standalone H4 threshold** separating TREND winners from losers in 2017-2023.

The strongest structural clue is the confirmation composition, not raw H4 ADX/ER:

TREND with recent V1 confirmation:
- 201 trades
- 30.85% WR
- +0.234R expectancy
- +47R

TREND without recent V1 confirmation:
- 116 trades
- 16.38% WR
- -0.345R expectancy
- -40R

However, this relationship weakens materially in the 2024-2026 holdout:
- with V1 support: +0.789R
- without V1 support: +0.756R

Therefore a hard “TREND requires V1” rule would over-filter recent profitable trades.

A softer interaction is more plausible for future research:
- TREND
- no recent V1 confirmation
- slow relative H4 pace

That combination was historically weaker while avoiding a blanket removal of modern TREND trades.

### MIXED — 2017-2023

| Feature | Winner mean | Loser mean | Winner median | Loser median |
|---|---:|---:|---:|---:|
| H4 ADX | 20.67 | 20.99 | 20.28 | 18.86 |
| H4 ADX slope, 3 bars | -0.82 | -1.55 | -0.93 | -1.51 |
| H4 ER20 | 0.213 | 0.157 | 0.192 | 0.138 |
| Normalized H4 pace | 0.977 | 0.995 | 0.950 | 0.945 |
| H4 bias persistence | 2.75 | 1.74 | 0 | 0 |
| EMA20/50 separation / ATR | 0.748 | 0.685 | 0.626 | 0.639 |
| +DI/-DI separation | 7.57 | 6.69 | 6.00 | 5.05 |
| Support count | 2.058 | 2.018 | 2 | 2 |

H4 ER20 was the clearest development-sample separator for MIXED trades.

But this **reverses in the 2024-2026 holdout**:
- recent MIXED winners mean ER20: ~0.148
- recent MIXED losers mean ER20: ~0.205

Therefore ER should not be used as a hard standalone rule. This confirms why the earlier hard ER filter was too aggressive.

## Robust MIXED clue: H4 alignment

One simple relationship is more stable across both samples.

2017-2023 MIXED:
- H4 not aligned: 152 trades, 24.34% WR, -0.026R expectancy
- H4 aligned: 71 trades, 21.13% WR, -0.155R expectancy

2024-2026 MIXED:
- H4 not aligned: 49 trades, 40.82% WR, +0.633R expectancy
- H4 aligned: 40 trades, 25.00% WR, 0.000R expectancy

So within MIXED mode, **H4 alignment is consistently the weaker subgroup**.

This supports the previous stalled-H4 hypothesis:
- H4 alignment is not automatically beneficial when the router is MIXED.
- A technically aligned H4 can represent a mature/stalled move rather than a fresh continuation.
- The interaction with efficiency and pace is more credible than ER alone.

## Direction check

No permanent LONG/SHORT filter is justified.

Across 2017-2023:
- MIXED SHORT: 108 trades, -0.074R expectancy
- MIXED LONG: 115 trades, -0.061R expectancy
- TREND SHORT: 138 trades, -0.043R expectancy
- TREND LONG: 179 trades, +0.073R expectancy

But the yearly direction flips:
- 2017 TREND LONG was -14R while TREND SHORT was +1R.
- 2018 TREND LONG was -9R while TREND SHORT was +5R.
- 2020 TREND LONG was +6R while TREND SHORT was -5R.
- 2022 TREND SHORT was -9R while TREND LONG was +3R.
- 2023 TREND LONG was +11R while TREND SHORT was -1R.

The failure is regime-dependent, not permanently directional.

## Holdout context

2024-2026 baseline:
- TREND: 155 trades, 44.52% WR, +0.781R expectancy, +121R
- MIXED: 89 trades, 33.71% WR, +0.348R expectancy, +31R

Both modes are profitable in the recent regime.

This is why deleting MIXED or making TREND much stricter would be a mistake.

## Research conclusion

The simple mode split gives a clearer architecture for future research:

1. **MIXED problem**
   - historically the aggregate drag
   - especially bad in 2018, 2020 and 2023
   - H4-aligned MIXED is consistently weaker in both development and holdout
   - ER alone is not robust; use ER only as an interaction with pace/alignment

2. **TREND problem**
   - not broadly bad across 2017-2023
   - failures are concentrated in 2017, 2018 and 2022
   - raw H4 ADX, ER, pace, persistence and EMA separation do not provide a stable standalone threshold
   - absence of recent V1 confirmation is a strong historical clue, but it does not remain discriminative in the recent holdout

3. **Next research should remain mode-specific**
   - MIXED: continue with stalled-H4 alignment + efficiency/pace interaction
   - TREND: test a softer “no V1 confirmation + slow pace” condition rather than requiring V1 on every TREND trade

No Pine, cBot, canonical Python engine or live RR10 configuration was modified.
