# ICT FxPro M1 Backtest — CASIO Acceptance Rules

Date: 2026-09-24

## Rules

- XAUUSD, user-supplied FxPro M1
- 2017-01-02 through 2026-09-24
- RM100 start
- 5% current-equity risk
- fixed 1:3
- real SL, no BE/protected SL
- New York only, DST-aware via America/New_York
- MTF mandatory
- target WR 60%-80%
- target >=8 trades per completed month
- one position at a time
- M1 resolves SL/TP; same-M1 collision = SL
- main results gross; 1bp round-trip sensitivity reported separately because no bid/ask history is present

## Model A — ICT 2022-style NY model

Mechanical translation:
H4 swing/BOS direction -> raid of 00:00-07:00 NY liquidity during 07:00-10:00 -> M5 MSS/displacement -> M5 FVG -> M1 retrace to FVG 50% -> SL beyond raid -> fixed 3R.

Best full-history version:

- 300 trades
- 86 wins / 214 losses
- 28.67% WR
- +44R gross
- PF 1.206
- RM100 -> RM283.70 gross
- max compounded DD 83.03%
- after 1bp sensitivity: +23.36R, RM100 -> RM101.13, max DD 86.72%
- average cadence about 2.57 trades/month
- 0 of 115 completed audit months reached 8 trades

Yearly gross:
- 2017: 24 trades, 41.67% WR, +16R
- 2018: 28, 32.14%, +8R
- 2019: 30, 26.67%, +2R
- 2020: 27, 22.22%, -3R
- 2021: 31, 32.26%, +9R
- 2022: 35, 42.86%, +25R
- 2023: 42, 35.71%, +18R
- 2024: 32, 12.50%, -16R
- 2025: 32, 18.75%, -8R
- 2026 YTD: 19, 15.79%, -7R

## Model B — ICT New York AM Silver Bullet

Mechanical translation:
H4 direction -> 07:00-10:00 NY parent liquidity -> only 10:00-11:00 NY window -> M1 raid -> M1 MSS/displacement/FVG -> M1 FVG 50% retrace -> SL beyond raid -> fixed 3R.

Full-history strict pre-session version:

- 306 trades
- 82 wins / 224 losses
- 26.80% WR
- +22R gross
- PF 1.098
- RM100 -> RM97.12 gross due geometric drag
- max DD 90.10%
- after 1bp: -14.16R, RM100 -> RM15.59

More frequent range-or-PDH/PDL version:
- 441 trades
- 26.30% WR
- +23R gross
- average 3.76 trades/month
- only 1 of 115 completed months reached >=8 trades
- after 1bp: -31.69R

## 2026 Silver Bullet exception

The strict 10:00-11:00 NY Silver Bullet is strong in 2026 YTD:

- 26 trades
- 13W / 13L
- 50.00% WR
- +26R gross
- RM100 -> RM315.85 if reset on 2026-01-01
- 9.75% max DD
- +24.50R after 1bp
- RM100 -> RM294.16 after 1bp

Monthly:
- Jan: 6 trades, 50% WR, +6R
- Feb: 2, 50%, +2R
- Mar: 4, 50%, +4R
- Apr: 1, 0%, -1R
- May: 1, 0%, -1R
- Jun: 4, 75%, +8R
- Jul: 3, 33.33%, +1R
- Aug: 2, 100%, +6R
- Sep YTD: 3, 33.33%, +1R

This is not accepted as robust because the same frozen rule performs poorly across 2017-2025.

## Verdict

FAIL against current CASIO target.

No tested mechanical ICT version reached:
- 60%-80% full-history WR at fixed 3R, or
- >=8 trades in every completed month.

The strongest full-history WR was about 28.7%.

The main discretionary pieces still not fully encoded are daily draw-on-liquidity selection and premium/discount PD-array quality. Adding them may increase selectivity/quality but would normally reduce frequency further, making the >=8/month target even harder.

The 2026 Silver Bullet result should be tracked as a regime-specific research candidate, not promoted as a verified system.
