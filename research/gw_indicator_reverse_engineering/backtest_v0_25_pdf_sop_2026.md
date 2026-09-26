# GW XAUUSD Indicator Playbook — 2026 SOP Backtest v0.25

Dataset: FxPro XAUUSD M1 supplied by user.

Test period actually available in the uploaded file:
- 2026-01-01 through 2026-09-24 00:21 UTC.
- Therefore this is 2026 YTD, not a complete Jan-Dec year.

## Canonical reproducible translation of the PDF SOP

Primary execution timeframe: M5.
M3 is treated as optional precision, not automatically combined into the primary test, because the playbook identifies M5 as the primary working chart and M3 as precision "when needed."

Indicators:
- SMA20(close)
- MACD 12/26/9 EMA/EMA

Bias/context:
- BUY: latest completed H1 close > H1 SMA20 and H1 MACD > signal.
- SELL: latest completed H1 close < H1 SMA20 and H1 MACD < signal.
- M15 must not clearly contradict H1. "Clear contradiction" = price and MACD both on the opposite side.
- M5 must be on the intended side at trigger.

Timing:
New-entry windows in MYT:
- 08:50-09:30
- 10:30-11:15
- 12:30-13:30
- 13:30-14:00
- 14:45-15:30
- 18:45-19:30
- 20:45-21:30
- 22:45-23:15

The playbook says a setup can trigger "near" the end of a window; this was quantified as up to 30 minutes after the end. The 16:30-17:00 risk-control period and 17:30-18:30 observation/lull period were not treated as aggressive new-entry windows.

M5 trigger:
- trade-direction candle closes on the correct side of SMA20;
- MACD cross in the same direction occurred on current bar or one of the previous 3 closed M5 bars;
- trigger close is no more than 0.50 ATR14 away from SMA20 ("not extended");
- current/previous 2 M5 bars pulled back/touched within 0.25 ATR14 of SMA20;
- entry at the next M1 open after the M5 candle closes.

Risk:
- real structural SL beyond the trigger structure;
- structure = extreme of current + previous 2 M5 bars;
- 0.10 ATR14 buffer beyond the structure;
- TP = exactly 3 x actual risk distance;
- one active trade at a time;
- no BE / protected SL;
- if SL and TP touch inside the same M1 candle, SL is counted first (conservative);
- start RM100, risk 5% of current equity per trade;
- no spread/commission model because the input file has no bid/ask or commission data.

## Main result — M5 primary SOP

- Trades: 43
- Wins: 16
- Losses: 27
- Win rate: 37.21%
- Net: +21R
- Expectancy: +0.488R/trade
- Profit factor: 1.78
- RM100 -> RM234.26
- Return: +134.26%
- Max drawdown: 22.62%
- Max win streak: 3
- Max loss streak: 5
- Median SL distance: $5.07
- Mean SL distance: $5.94
- Median trade duration: 20 minutes
- Mean trade duration: 51.2 minutes

At fixed 1:3, pre-cost breakeven WR is 25%, so 37.21% is positive expectancy, but it does not meet the historical 60-80% WR research target and trade frequency is below 8 trades/month.

## Monthly

| Month | Trades | W | L | WR | Net R | End equity |
|---|---:|---:|---:|---:|---:|---:|
| Jan | 7 | 1 | 6 | 14.29% | -3R | RM84.54 |
| Feb | 5 | 3 | 2 | 60.00% | +7R | RM116.03 |
| Mar | 6 | 2 | 4 | 33.33% | +2R | RM124.99 |
| Apr | 3 | 1 | 2 | 33.33% | +1R | RM129.72 |
| May | 7 | 2 | 5 | 28.57% | +1R | RM132.75 |
| Jun | 2 | 0 | 2 | 0.00% | -2R | RM119.81 |
| Jul | 6 | 2 | 4 | 33.33% | +2R | RM129.05 |
| Aug | 5 | 4 | 1 | 80.00% | +11R | RM214.43 |
| Sep* | 2 | 1 | 1 | 50.00% | +2R | RM234.26 |

*Sep data ends 24 Sep.

Minimum month = 2 trades. Average = 4.78 trades/month.

## Direction split

- BUY: 19 trades, 5W/14L, 26.32% WR, +1R.
- SELL: 24 trades, 11W/13L, 45.83% WR, +20R.

This is descriptive only; do not remove BUY rules solely from this YTD sample without out-of-sample validation.

## Window split

| Window | Trades | WR | Net R |
|---|---:|---:|---:|
| 08:50-09:30 | 4 | 0.0% | -4R |
| 10:30-11:15 | 5 | 60.0% | +7R |
| 12:30-13:30 | 2 | 50.0% | +2R |
| 13:30-14:00 | 2 | 100.0% | +6R |
| 14:45-15:30 | 8 | 50.0% | +8R |
| 18:45-19:30 | 10 | 20.0% | -2R |
| 20:45-21:30 | 8 | 37.5% | +4R |
| 22:45-23:15 | 4 | 25.0% | 0R |

Small samples: window-level results are not sufficient evidence to optimize/remove timetable slots yet.

## Sensitivity to "near SMA20"

Everything fixed except maximum trigger close distance from SMA20:

| Max distance | Trades | WR | Net R | End equity | Max DD |
|---|---:|---:|---:|---:|---:|
| 0.25 ATR | 13 | 30.77% | +3R | RM110.23 | 18.55% |
| 0.50 ATR | 43 | 37.21% | +21R | RM234.26 | 22.62% |
| 0.75 ATR | 102 | 33.33% | +34R | RM353.94 | 36.41% |
| 1.00 ATR | 159 | 25.16% | +1R | RM59.84 | 68.47% |

This supports the playbook's "do not chase" rule: allowing entries as far as 1 ATR from SMA20 destroys the equity profile.

## Qualitative skip-filter stress test

The PDF also contains qualitative filters ("flat", "whipsaw", "oversized candle"). Because it gives no exact numeric thresholds, an additional non-optimized strict encoding was tested:
- >=3 SMA-side changes in 5 bars = whipsaw;
- SMA20 5-bar movement <0.20 ATR = flat;
- trigger TR >1.8 x median prior-10 TR = oversized;
- H1 neutral if >=3 SMA-side changes / 5 bars or >=2 MACD crosses / 5 bars.

Result:
- 13 M5 trades
- 3 wins / 10 losses
- 23.08% WR
- -1R
- RM100 -> RM91.06

Therefore these arbitrary numeric interpretations should NOT be promoted to the official rules. The qualitative filters need to be reverse-engineered/defined more precisely before they are coded into the primary backtest.

## M3 diagnostic

Using the same direct SOP on M3 only:
- 46 trades
- 23.91% WR
- -2R
- RM100 -> RM77.27
- Max DD 54.96%

Combining every valid M3 and M5 trigger:
- 81 trades
- 28.40% WR
- +11R
- RM100 -> RM127.06
- Max DD 57.65%

This supports keeping M5 as the primary systematic trigger and treating M3 as discretionary precision rather than blindly accepting every M3 signal.

## Important limitation

The SOP does not reproduce every published MPL Telegram signal. For example, the supplied 11 Sep 2026 M5 SELL signal at ~10:50 MYT is not generated by this exact playbook because the playbook requires a recent MACD cross. This is expected: this PDF is an original rules-based operating SOP built from the reconstructed indicator, not a claim that MPL's unpublished signal-selection logic has been perfectly cloned.
