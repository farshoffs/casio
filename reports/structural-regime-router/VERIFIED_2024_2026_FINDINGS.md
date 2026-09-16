# CASIO Structural Regime Router — Verified Secondary-Feed Findings

Verified from GitHub Actions run `35102678909` using the separate OctaFX/Octa Markets MT4 XAUUSD M5 base. The secondary feed ends on 2026-01-30, so the 2026 figures below are partial and are **not** the current Sep-2026 market.

No production or TradingView strategy was changed.

## Causal routing tested

- `TREND_PULLBACK` -> `DISPLACEMENT_RETRACE`
- `EXTERNAL_SWEEP` -> `STRICT_FVG`, London only
- `SESSION_EXPANSION_RETEST` -> disabled pending redesign
- target = 3.5R
- minimum external-liquidity runway = 3.5R
- no ADX/RSI routing
- no year/date is used as a trading rule

## QUALITY_CORE

| Period | Trades | Trades/30d | WR | Avg winner | Avg loser | Expectancy | PF | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Latest 60d | 2 | 1.00 | 50.00% | 3.392R | 1.124R | +1.134R | 3.018 | 1.124R |
| 2026 partial | 0 | 0.00 | — | — | — | — | — | — |
| 2025 | 26 | 2.14 | 53.85% | 3.384R | 1.103R | +1.313R | 3.580 | 3.262R |
| 2024 | 26 | 2.13 | 53.85% | 3.074R | 1.094R | +1.151R | 3.279 | 2.243R |

## LONDON_CORE

| Period | Trades | Trades/30d | WR | Avg winner | Avg loser | Expectancy | PF | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Latest 60d | 3 | 1.50 | 33.33% | 3.392R | 1.074R | +0.415R | 1.579 | 2.148R |
| 2026 partial | 1 | 1.00 | 0.00% | — | 1.062R | -1.062R | 0.000 | 0.000R |
| 2025 | 27 | 2.22 | 48.15% | 3.380R | 1.098R | +1.058R | 2.858 | 3.262R |
| 2024 | 27 | 2.21 | 44.44% | 3.017R | 1.095R | +0.733R | 2.205 | 3.352R |

## ROBUST_CORE

| Period | Trades | Trades/30d | WR | Avg winner | Avg loser | Expectancy | PF | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Latest 60d | 3 | 1.50 | 33.33% | 3.392R | 1.074R | +0.415R | 1.579 | 2.148R |
| 2026 partial | 1 | 1.00 | 0.00% | — | 1.062R | -1.062R | 0.000 | 0.000R |
| 2025 | 33 | 2.71 | 42.42% | 3.384R | 1.091R | +0.808R | 2.285 | 7.412R |
| 2024 | 35 | 2.87 | 42.86% | 3.099R | 1.091R | +0.705R | 2.131 | 4.457R |

## Interpretation

The secondary feed confirms a useful quality core but not the desired frequency. `ROBUST_CORE` clears the WR/expectancy/PF quality floor in both 2024 and 2025, while producing only about 2.7-2.9 trades per month. `QUALITY_CORE` improves quality further but reduces frequency to about 2.1 trades per month.

The important structural finding is that loose body-retracement `EXTERNAL_SWEEP` entries were the main source of degradation. External sweeps behaved materially better when a real M5 FVG was required, particularly in London. `TREND_PULLBACK` can retain displacement-retracement execution. The current `SESSION_EXPANSION_RETEST` implementation did not earn inclusion and is disabled in this challenger.

Therefore the next research problem is **not to loosen the quality core to manufacture eight trades per month**. The next problem is to redesign/add independent structural sub-techniques—especially the session-expansion/retest branch—until the combined portfolio approaches the frequency target while the existing quality core remains frozen.

All 2024/2025/Jan-2026 secondary results are now discovery/robustness data. They must not be presented as untouched out-of-sample evidence. Current-market validation remains the fresh Dukascopy feed.
