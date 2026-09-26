# GW/MPL reverse engineering — v0.21 correction

## Major correction from direct visual match

A new side-by-side screenshot supplied by the user overlays the MPL chart with a TradingView chart using **SMA 20 close**.

At the same XAUUSD M15 location (2026-09-16 around 09:15 MYT), the blue line shape and level visually match the MPL blue line.

FxPro M1 reconstruction gives:
- MPL screenshot blue-line label: about **4289.614**
- M15 SMA20(close): about **4289.566**
- absolute difference: about **0.049**
- M15 RMA10(close): about **4288.263**
- RMA10 error: about **1.35**

The tiny SMA20 difference is consistent with broker/feed differences.

### Revised conclusion

The earlier primary hypothesis **RMA/SMMA(close,10)** is rejected for the blue Momentum Power Line.

The blue line should now be treated as:

`SMA(close, 20)`

on the chart timeframe, unless later evidence contradicts this.

This also explains why earlier RMA10-based backtests were systematically off.

## Research reset

All future GW/MPL reconstruction runs should replace the blue-line engine with SMA20 and rerun:
1. M3/M5/M15/H1 direction alignment.
2. candle direction filter.
3. MACD 12/26/9 cross-dot logic.
4. Bjorgum / Bollinger overlay logic.
5. supplied timing windows.
6. Telegram zone anchoring around the blue line.
7. strict real SL and fixed 1:3 tests.

The user's side-by-side evidence is currently the strongest direct identification of the blue line in the entire project.
