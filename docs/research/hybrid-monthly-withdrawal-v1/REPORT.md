# CASIO Hybrid Monthly Withdrawal Router v1

Date: 2026-09-25

## Objective
Hard monthly gates:
1. >=8 completed trades.
2. >=+4R realized net result.

## Architecture
Tier 1: frozen EURUSD/GBPUSD/GBPJPY 2R core router.
Tier 2: frozen high-quality 1R sweep overlay from month start.
Tier 3: filtered 2.5R-3R M5 sweep rescue after 10 completed quality-overlay trades if combined month is below +4R.
Development-hour expectancy thresholds (2017-2022):
- XAUUSD >= 0.05R
- EURUSD >= 0.10R
- GBPUSD >= 0.10R
- GBPJPY >= 0.025R
Tier 4: after 325 broad-rescue completions without reaching +4R, remove the hour restriction for the remainder of the month.

One open position per symbol. Core entry priority, then quality overlay, then broad rescue. Once >=8 completed trades and >=+4R are reached, stop new entries; already-open trades finish, and trading can resume if they drag the completed result back below +4R.

## Historical result
Jan-2017 through Aug-2026 (116 completed months):
- 116/116 months pass
- minimum monthly result +4.0R
- average +5.00R/month
- minimum 8 trades/month
- median 22 trades/month
- average 49.38 trades/month
- worst month 676 trades
- total accepted trades 5,728

Standalone 4-market sweep comparison:
- 116/116 months
- 69.20 trades/month average
- 19 median
- 695 worst month
- +5.42R/month average

Hybrid reduces average turnover ~29% but does not remove the extreme tail.

## 2026 Jan-Aug
| Month | Trades | Core | Quality | Broad | Net R | RM100 @5% monthly reset |
|---|---:|---:|---:|---:|---:|---:|
| Jan | 31 | 0 | 15 | 16 | +5.0R | RM116.97 |
| Feb | 33 | 1 | 15 | 17 | +9.0R | RM142.97 |
| Mar | 308 | 6 | 71 | 231 | +4.0R | RM50.75 |
| Apr | 35 | 0 | 20 | 15 | +4.0R | RM112.40 |
| May | 25 | 0 | 12 | 13 | +5.0R | RM120.39 |
| Jun | 41 | 0 | 16 | 25 | +5.5R | RM118.44 |
| Jul | 12 | 0 | 10 | 2 | +4.0R | RM119.25 |
| Aug | 9 | 0 | 9 | 0 | +5.0R | RM126.99 |

Independent RM100 monthly-reset profit Jan-Aug: +RM108.16.

March 2026 demonstrates the key issue: +4R additive after 308 trades still turns RM100 into RM50.75 at 5% current-equity risk because geometric volatility drag dominates.

## Engine contribution
- Broad sweep: 3,666 trades, 30.01% WR, +475.5R, +0.130R/trade
- 2R core: 61 accepted trades, 45.90% WR, +23R, +0.377R/trade
- Quality 1R overlay: 2,001 trades, 52.02% WR, +81R, +0.040R/trade

## Cost stress
Constant friction in R per accepted trade:
- 0.0000R: 116/116 months remain >=+4R
- 0.0025R: 71/116
- 0.0050R: 70/116
- 0.0100R: 63/116
- 0.0200R: 57/116
- 0.0500R: 37/116

## Verdict
Statistical monthly-R gate: PASS.
Live monthly-withdrawal implementation at 5% current-equity risk: NOT READY.

The next redesign should cap rescue turnover and/or change rescue sizing so hundreds of rescue trades cannot destroy cash equity despite a positive additive-R month.
