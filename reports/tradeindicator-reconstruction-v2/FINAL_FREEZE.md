# CASIO TradeIndicator Portfolio V3 — FINAL FREEZE

Date: 2026-09-25
Data: FxPro XAUUSD M1, 2017-01-02 through 2026-09-24.

## Final decision

**Freeze Portfolio V3 without M5 veto.**

Execution remains:
- causal H1/H4/M15 context
- M1 execution
- one active trade across all sleeves
- real structural SL
- fixed 3R
- same-M1 SL/TP collision = SL first
- no BE, protected SL, partials or averaging

Sleeves:
1. Demand Rejection BUY — H1 bull + strong M15 bullish rejection + zone <=3 prior touches
2. Supply Break & Hold BUY — NY session + H1 ADX >=20 + zone <=3 prior touches
3. Demand Breakdown SELL — H1 -DI>+DI + 0.75–2.0 H1 ATR below EMA20 + <=4 prior touches + non-negative tick-volume z-score
4. Tick-M15 H4 Long — H1/H4 bullish alignment + M15 volume z>=2.5 + displacement/breakout + structural M15 SL

## Final V3 result

- 1,013 trades
- 331 wins / 682 losses
- 32.68% WR
- +311R
- +0.307R/trade
- PF 1.456
- 8.67 trades/month average
- median 8/month
- 75/116 completed months >=8 trades
- max DD at 5% current-equity risk: 51.92%
- longest losing streak: 12

Chronological splits:
- 2017–2021: +0.243R/trade, PF 1.352
- 2022–2024: +0.351R/trade, PF 1.530
- 2025–2026: +0.424R/trade, PF 1.658

2026 YTD through Sep 24:
- 73 trades
- 24W / 49L
- 32.88% WR
- +23R
- +0.315R/trade
- PF 1.469
- RM100 -> RM231.85 at 5% current-equity risk
- max DD 40.97%

## Final M5 veto test

### Strict veto: reject Tick signal if first completed M5 candle is bearish OR EMA9<EMA20

Tick sleeve standalone improved quality, but portfolio degraded:
- portfolio trades 1,013 -> 906
- avg/month 8.67 -> 7.75
- expectancy +0.307R -> +0.280R
- PF 1.456 -> 1.412
- net +311R -> +254R
- DD 51.92% -> 46.72%

The ~5.2 percentage-point DD improvement is not enough to justify losing the >8/month average and lowering expectancy/PF.

### Light veto: reject only if M5 candle bearish AND EMA9<EMA20

This veto almost never triggers in an H1/H4-aligned Tick breakout. The 5-minute entry delay itself hurts the portfolio:
- 997 trades
- 8.53/month
- +0.284R/trade
- PF 1.418
- +283R
- max DD 58.46%

This is inferior to V3 on expectancy/PF/net R and also has worse drawdown.

## Final research conclusion

M5 confirmation is useful diagnostically for the Tick sleeve, but **not as a portfolio entry rule**. The portfolio benefits more from taking the original M15/H4 momentum event immediately.

No further historical tuning should be performed on 2017–2026. The system is now frozen for forward/paper validation and realistic broker-friction monitoring.
