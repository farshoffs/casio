# CASIO 2026 Dukascopy — Route A vs Route B Backtest

Generated from `data/xauusd_m5_dukascopy_research.csv`. Entry period: **2026-01-01 UTC → 2026-09-16T13:30:00+00:00** (dataset is currently YTD, not a complete 2026 calendar year).

## Frozen test assumptions

- Starting balance: **RM100** for each route independently.
- Risk: **5% of current equity per filled trade**, compounded trade by trade.
- RR: **1:2 to 1:4**, selected before replay from structural runway and setup quality.
- Execution: M5 retracement fill model; stop-first if both stop and target are touched in the same M5 candle.
- Cost model: **1.0 bps round trip** converted to R. No separate broker-specific spread/slippage model beyond that cost assumption.
- No 2026 parameter optimization/grid search is performed in this job; the two route definitions are frozen before results are calculated.
- Pre-2026 bars are used only for causal indicator/market-structure warm-up. All counted entries are in 2026.

## Route definitions

**Route A — Structural Asymmetric:** CASIO `DISPLACEMENT_RETRACE` structural engine. London/NY structural setup, liquidity/structure context, displacement, retracement entry (FVG50 when available, otherwise displacement-body 50%), structural stop, and 2R/3R/4R target chosen from available external-liquidity runway.

**Route B — Precision A+:** premium subset of Route A. Requires FVG retracement, HTF trend alignment, M15 structure alignment, clean displacement, fresh internal/external liquidity, quality score >=5/6, and >=2R structural runway. Defaults to 2R and only stretches to 3R/4R on stronger A+ evidence.

## Headline comparison

| Route | Trades | Trades/30d | Win rate | Avg win R | Avg loss R | Expectancy R | PF | Net R | End balance RM | Return % | Max DD % | 8/mo + 70% objective |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| A Structural Asymmetric | 94 | 10.91 | 30.85% | 2.57 | 1.05 | 0.071 | 1.10 | 6.65 | 100.67 | 0.67% | 69.41% | NO |
| B Precision A+ | 1 | 0.12 | 0.00% | n/a | 1.09 | -1.089 | 0.00 | -1.09 | 94.56 | -5.44% | 5.44% | NO |

## Route A — month by month

| month | trades | win_rate | net_r | pnl_rm | ending_balance_rm |
|---|---|---|---|---|---|
| 2026-01 | 7 | 0.00 | -7.39 | -31.59 | 68.41 |
| 2026-02 | 10 | 10.00 | -7.34 | -21.82 | 46.58 |
| 2026-03 | 9 | 44.44 | 6.76 | 15.62 | 62.21 |
| 2026-04 | 16 | 18.75 | -3.67 | -13.23 | 48.97 |
| 2026-05 | 14 | 35.71 | 2.30 | 3.47 | 52.44 |
| 2026-06 | 9 | 0.00 | -9.46 | -20.18 | 32.27 |
| 2026-07 | 12 | 58.33 | 10.35 | 19.28 | 51.54 |
| 2026-08 | 8 | 37.50 | 1.60 | 2.87 | 54.41 |
| 2026-09 | 9 | 66.67 | 13.49 | 46.26 | 100.67 |
| 2026-10 | 0 | — | 0.00 | 0.00 | — |
| 2026-11 | 0 | — | 0.00 | 0.00 | — |
| 2026-12 | 0 | — | 0.00 | 0.00 | — |

## Route B — month by month

| month | trades | win_rate | net_r | pnl_rm | ending_balance_rm |
|---|---|---|---|---|---|
| 2026-01 | 1 | 0.00 | -1.09 | -5.44 | 94.56 |
| 2026-02 | 0 | — | 0.00 | 0.00 | — |
| 2026-03 | 0 | — | 0.00 | 0.00 | — |
| 2026-04 | 0 | — | 0.00 | 0.00 | — |
| 2026-05 | 0 | — | 0.00 | 0.00 | — |
| 2026-06 | 0 | — | 0.00 | 0.00 | — |
| 2026-07 | 0 | — | 0.00 | 0.00 | — |
| 2026-08 | 0 | — | 0.00 | 0.00 | — |
| 2026-09 | 0 | — | 0.00 | 0.00 | — |
| 2026-10 | 0 | — | 0.00 | 0.00 | — |
| 2026-11 | 0 | — | 0.00 | 0.00 | — |
| 2026-12 | 0 | — | 0.00 | 0.00 | — |

## Target distribution

- **Route A:** 2R: 36, 3R: 46, 4R: 12
- **Route B:** 2R: 1

## Notes

This report is a research backtest, not a profitability guarantee. The useful comparison is whether either frozen route can hold frequency, hit rate, expectancy, PF, and drawdown together on the same 2026 Dukascopy sample.

Raw filled trades and monthly summaries are saved beside this report for audit/replay.
