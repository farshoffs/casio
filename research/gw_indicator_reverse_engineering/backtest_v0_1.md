# GW/MPL Reverse Engineering — Backtest v0.1

Dataset: `fxpro_xauusd_m1.csv` (FxPro XAUUSD M1), tested on 2026-01-01 through 2026-09-24.

## Evidence-backed hypothesis

This first pass intentionally tests only rules supported by screenshots/messages:

- Blue line candidate: RMA/SMMA(close, 10).
- MTF alignment: H1 + M15 + M3.
- BUY: current candle bullish and price above blue line on all three TFs.
- SELL: current candle bearish and price below blue line on all three TFs.
- Observed entry windows interpreted in Malaysia time (UTC+8):
  - 08:50–09:30
  - 10:30–11:15
  - 13:30–14:30
- Fixed real SL: $4.
- Fixed RR: 1:3, so TP = $12.
- Start equity: RM100.
- Risk: 5% of current equity per trade.
- No BE/protected stop.
- M1 used for intratrade SL/TP resolution.
- If SL and TP are both touched inside the same M1 candle, count SL first (conservative).
- No spread/slippage in v0.1.

## Forensic line check

The M15 RMA(close,10) hypothesis closely reproduces one screenshot:
- 2026-09-14 ~20:42 MYT screenshot blue line ≈ 4296.403.
- FxPro reconstruction at corresponding time gives RMA10 ≈ 4296.371.
- Difference ≈ 0.032.

This is strong evidence that SMMA/RMA(10) is worth keeping as the primary blue-line candidate.

## Candidate A — fresh M3 break near blue line

Extra conditions:
- M3 must newly cross the RMA10 in the trade direction.
- Price must be within $2 of the current M15 RMA10.
- Only the three observed initial-entry windows are used.

2026 YTD result:
- Trades: 32
- Wins: 15
- Losses: 17
- Win rate: 46.88%
- Net: +28R
- RM100 -> RM340.23 at 5% risk / 1:3
- Max drawdown: 14.26%
- Max losing streak: 3

Split:
- Jan–Jun: 26 trades, 46.15% WR, +22R.
- Jul–Sep 24: 6 trades, 50.00% WR, +6R.

Interpretation: strongest quality profile in v0.1, but frequency is far below the >=8 trades/month research target.

## Candidate B — aligned MTF, near M15 blue line

Conditions:
- H1/M15/M3 alignment.
- Price within $2 of M15 RMA10.
- No fresh-cross requirement.
- Re-entry allowed after a prior trade closes.
- Three observed initial-entry windows.

2026 YTD:
- Trades: 77
- Wins: 30
- Losses: 47
- Win rate: 38.96%
- Net: +43R
- RM100 -> RM594.22
- Max drawdown: 36.98%
- Max losing streak: 9

Monthly:
| Month | Trades | W | L | WR | Net R |
|---|---:|---:|---:|---:|---:|
| Jan | 8 | 3 | 5 | 37.50% | +4R |
| Feb | 7 | 3 | 4 | 42.86% | +5R |
| Mar | 2 | 0 | 2 | 0.00% | -2R |
| Apr | 22 | 12 | 10 | 54.55% | +26R |
| May | 10 | 1 | 9 | 10.00% | -6R |
| Jun | 10 | 3 | 7 | 30.00% | +2R |
| Jul | 6 | 3 | 3 | 50.00% | +6R |
| Aug | 5 | 2 | 3 | 40.00% | +3R |
| Sep* | 7 | 3 | 4 | 42.86% | +5R |

*Data ends 24 Sep 2026.

This variant is profitable in aggregate but does **not** meet the minimum-8-trades-every-month rule and does not meet the 60–80% WR target.

## What v0.1 tells us

The raw MTF blue-line rule alone is not enough to explain MPL's claimed quality. The strongest improvement came from requiring a fresh M3 break very close to the M15 blue line, but that reduced frequency sharply.

The next research step should add the still-missing evidence-backed filters rather than optimize arbitrary parameters:
1. MACD 12/26/9 dot/momentum logic.
2. Buyer-vs-seller tick-volume pressure.
3. Purple breakout MA / confirmation line.
4. HTF structural bias / weekly key zones.
5. Exact daily timetable logic (screenshots suggest the "best entry" window changes by day, so treating every observed window as active every day is probably wrong).
6. Telegram zone execution model: 4-dollar entry zone, 4-dollar outer SL, TP ladder at 2R/3R/4R from the zone anchor.
