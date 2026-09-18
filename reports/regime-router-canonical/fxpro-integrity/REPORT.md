# RR10 FxPro M15 Integrity Backtest — Uploaded CSV — 10% Risk

- Input file: `fxpro_xauusd_m15.csv`
- SHA-256: `033ca1c3ab921a04d8def943d7586d7e718fec14ef94597146959e7b35151a4d`
- Rows: **64,136**; symbol: **XAUUSD**; timeframe: **M15**; duplicate timestamps: **0**.
- Data coverage: **2024-01-01T23:00:00+00:00** through **2026-09-18T00:00:00+00:00**.
- Test window: **2026-01-01T00:00:00+00:00** through **2026-09-18T00:15:00+00:00**.
- Starting equity: **RM100**.
- Risk: **10% of current equity per closed trade**.
- Engine: **RR10 canonical** from `feature/regime-router-dashboard-research`.
- Execution: one active trade at a time; entry at confirmed M15 close; stop-first if SL and TP collide on one bar.
- Targets tested independently: **2R, 3R, 4R, 5R**. A different target can change later trade availability because an open trade blocks new entries.
- This is a **risk-sizing sensitivity rerun only**. RR10 entry/exit selection rules are unchanged.

## Results

| RR | Trades | Win rate | Expectancy | PF | Trades / 30d | RM100 → | Max DD |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2R | 79 | 51.90% | +0.557R | 2.16 | 9.12 | **RM3,218.45** | **34.39%** |
| 3R | 69 | 43.48% | +0.739R | 2.31 | 7.96 | **RM4,302.87** | **44.16%** |
| 4R | 66 | 37.88% | +0.894R | 2.44 | 7.62 | **RM5,986.10** | **46.86%** |
| 5R | 66 | 33.33% | +1.000R | 2.50 | 7.62 | **RM7,255.68** | **57.64%** |

## Integrity checks

- Before applying 10% sizing, the replay reproduced the existing 5% integrity checksum exactly for all four RR variants.
- The **3R 5% checksum** reproduced exactly: 69 trades, 43.48% win rate, +0.739R expectancy, PF 2.31, RM895.69 ending equity, and 22.62% max drawdown.
- Changing risk from 5% to 10% does **not** change RR10's trade sequence, win rate, expectancy in R, profit factor, or trade frequency. It changes only the compounded equity path, RM profit/loss, and percentage drawdown.
- There were **no same-bar SL/TP collisions** in the 2026 closed trades for any tested RR.
- September is partial in this file (latest bar opens at 2026-09-18 00:00 UTC), so its 3 trades must not be treated as a completed-month frequency result.

## 5% versus 10% risk

| RR | End balance @ 5% | Max DD @ 5% | End balance @ 10% | Max DD @ 10% |
|---:|---:|---:|---:|---:|
| 2R | RM708.92 | 18.55% | RM3,218.45 | 34.39% |
| 3R | RM895.69 | 22.62% | RM4,302.87 | 44.16% |
| 4R | RM1,164.66 | 26.49% | RM5,986.10 | 46.86% |
| 5R | RM1,418.60 | 32.45% | RM7,255.68 | 57.64% |

The higher compounding rate materially increases both terminal equity and drawdown. In this sample, the 10% 5R path experiences a peak-to-trough drawdown of **57.64%**.

## Frequency against the stated goal

| RR | Avg trades / completed month (Jan-Aug) | Minimum completed-month trades | Completed months with ≥8 trades |
|---:|---:|---:|---:|
| 2R | 9.50 | 4 | 7/8 |
| 3R | 8.25 | 4 | 4/8 |
| 4R | 7.88 | 4 | 5/8 |
| 5R | 7.88 | 4 | 4/8 |

None of the 2R-5R variants produces at least 8 trades in every completed month. The 10% risk rerun does not alter those frequency figures.
