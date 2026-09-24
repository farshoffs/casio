# Bermula Accurate-Fast — RM100 / 5% Current-Equity Risk

Updated: 2026-09-24

## Frozen system

- Data: user-supplied FxPro XAUUSD M1
- History: 2017-01-02 to 2026-09-24
- H4 Bermula/S&R = direction only
- M15 Bermula edge retest = setup
- M1 confirmation = 3-5 minutes after retest
- Retest remains within +/-10% of M15 Bermula edge
- Real structural SL behind M15 Bermula zone
- Fixed RR = 1:3
- No BE / protected SL
- One position at a time
- Start equity = RM100
- Risk = 5% of current equity per entry
- Equity is carried continuously across years; it is not reset annually

## Overall

- Trades: 125
- Wins: 44
- Losses: 81
- Win rate: 35.20%
- Additive result: +51R
- RM100 -> RM735.05
- Total compounded return: +635.05%
- Maximum compounded-equity drawdown: 27.52%
- Max win streak: 3
- Max loss streak: 6

The main equity result is gross of historical spread/slippage because the M1 CSV does not contain bid/ask quotes. Under the previously used 1bp round-trip sensitivity, final equity is approximately RM542.65 and maximum drawdown is approximately 28.80%.

## Year-by-year — continuous compounding

| Year | Trades | W-L | WR | Net R | Start RM | End RM | Year return | Max DD | Max L streak |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2017 | 11 | 3-8 | 27.27% | +1R | 100.00 | 100.90 | +0.90% | 14.26% | 3 |
| 2018 | 13 | 6-7 | 46.15% | +11R | 100.90 | 162.98 | +61.53% | 14.26% | 3 |
| 2019 | 13 | 6-7 | 46.15% | +11R | 162.98 | 263.26 | +61.53% | 18.55% | 4 |
| 2020 | 6 | 1-5 | 16.67% | -2R | 263.26 | 234.26 | -11.02% | 14.26% | 3 |
| 2021 | 10 | 4-6 | 40.00% | +6R | 234.26 | 301.19 | +28.57% | 9.75% | 2 |
| 2022 | 19 | 6-13 | 31.58% | +5R | 301.19 | 357.63 | +18.74% | 26.49% | 6 |
| 2023 | 17 | 7-10 | 41.18% | +11R | 357.63 | 569.57 | +59.27% | 18.55% | 4 |
| 2024 | 13 | 3-10 | 23.08% | -1R | 569.57 | 518.66 | -8.94% | 15.46% | 3 |
| 2025 | 15 | 4-11 | 26.67% | +1R | 518.66 | 515.98 | -0.52% | 23.71% | 5 |
| 2026 YTD | 8 | 4-4 | 50.00% | +8R | 515.98 | 735.05 | +42.46% | 5.00% | 1 |

Note that +1R additive in a year does not necessarily mean positive compounded return. Example: 2025 has +1R additive but the account falls -0.52%, because multiplicative 5% losses and 15% wins create volatility drag.

## 2026 month-by-month

2026 begins with the carried-forward 2025 closing equity of RM515.98.

| Month | Trades | W-L | WR | Net R | Start RM | End RM | Return | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Jan | 0 | 0-0 | — | 0R | 515.98 | 515.98 | 0.00% | 0.00% |
| Feb | 0 | 0-0 | — | 0R | 515.98 | 515.98 | 0.00% | 0.00% |
| Mar | 3 | 1-2 | 33.33% | +1R | 515.98 | 535.52 | +3.79% | 5.00% |
| Apr | 0 | 0-0 | — | 0R | 535.52 | 535.52 | 0.00% | 0.00% |
| May | 0 | 0-0 | — | 0R | 535.52 | 535.52 | 0.00% | 0.00% |
| Jun | 1 | 1-0 | 100% | +3R | 535.52 | 615.85 | +15.00% | 0.00% |
| Jul | 1 | 1-0 | 100% | +3R | 615.85 | 708.23 | +15.00% | 0.00% |
| Aug | 2 | 1-1 | 50.00% | +2R | 708.23 | 773.74 | +9.25% | 5.00% |
| Sep* | 1 | 0-1 | 0.00% | -1R | 773.74 | 735.05 | -5.00% | 5.00% |

*2026 data ends on 2026-09-24.

## Interpretation

This money-management model makes the advantage and risk very visible.

At 5% current-equity risk:
- a loss multiplies equity by 0.95;
- a 3R win multiplies equity by 1.15.

The system grew RM100 to RM735.05 gross in the historical sequence, but the path was not smooth. The worst peak-to-trough equity drawdown was 27.52%, and the longest losing streak was six trades. 2022 and 2025 demonstrate that a positive additive-R year can still be difficult under aggressive compounding.

This is the frozen Accurate-Fast research candidate and no thresholds were changed for this RM100 test.
