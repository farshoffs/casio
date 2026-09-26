# v0.25 INVALIDATED — execution model mismatch

The previous 2026 backtest v0.25 must not be used for conclusions.

Reason: the implementation introduced rules that were not faithful to the actual indicator usage:
- recent MACD cross within 3 bars;
- ATR-based "near SMA20" thresholds;
- ATR pullback thresholds;
- structural 3-bar SL + ATR buffer;
- arbitrary +30 minute timetable grace;
- immediate market entry after trigger close.

## Forensic correction from the 11 Sep 2026 M5 signal

Published signal:
- SELL M5
- Entry zone 4324–4328
- SL 4332
- TP1 4320
- TP2 4316
- TP3 4312
- post time 10:50 MYT

FxPro M5 completed bar immediately before the signal:
- 02:45 UTC / 10:45 MYT
- SMA20(close) = 4327.5675

Rounded SMA20 anchor = 4328.

The entire signal geometry is then reproduced exactly:
- SELL zone = anchor-4 .. anchor = 4324..4328
- SL = anchor+4 = 4332
- TP1 = anchor-8 = 4320
- TP2 = anchor-12 = 4316
- TP3 = anchor-16 = 4312

This is a direct numerical match.

A second supplied signal also supports the same formula:
- blue line shown ≈ 4296.403
- SELL zone 4292–4296
- SL 4300
- TP1/2/3 4288/4284/4280

Rounded blue line anchor = 4296, producing the signal levels exactly.

## Revised usage model

The system is a retest-zone engine, not a "MACD crossed recently -> enter next bar" engine.

Working model:
1. Use HTF direction/bias.
2. Use the signal timeframe's SMA20 as the live/recent reference.
3. MACD is a momentum STATE/confirmation, not necessarily a fresh cross.
4. When price retests the SMA20 area during a timetable monitoring window, form a 4-dollar zone around the rounded SMA20 anchor.
5. SELL:
   - zone = anchor-4 .. anchor
   - SL = anchor+4
   - TP1/2/3 = anchor-8/-12/-16
6. BUY:
   - zone = anchor .. anchor+4
   - SL = anchor-4
   - TP1/2/3 = anchor+8/+12/+16
7. Published entry-zone execution allows fills inside the zone, so actual RR depends on fill price. It must not be silently treated as fixed 1:3.

Next backtest must model zone fills/layering explicitly and keep the fixed-1:3 research variant separate from the published-usage variant.
