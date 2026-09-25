# GW/MPL reverse engineering — status v0.18

## v0.16 — MACD/dot reconstruction

The lower-panel title strongly supports a standard MACD core:
- 12 / 26 / close / 9 / EMA / EMA.

A broad dot-state search was tested with:
- MACD line/signal crosses;
- zero-line crosses;
- curl states;
- H1/M15 current-candle alignment;
- Bjorgum/BB overlay states;
- supplied initial-entry timing windows;
- real $4 SL and fixed $12 TP (1:3).

Best frequency-valid candidate across 2024/2025/2026:
- M3, line-cross/zero-cross family;
- H1+M15 current-candle alignment;
- Bj+BB top-state;
- initial timing window.

Results:
- 2024: 168 trades, 29.76% WR, +32R, min month 10.
- 2025: 175 trades, 36.00% WR, +77R, min month 11.
- 2026 YTD: 153 trades, 30.72% WR, +35R, min month 11.

Conclusion: plain MACD-derived dot logic is not sufficient.

## v0.17 — SOP order / sequence testing

Evidence says the SOP is ordered:
- dot,
- label,
- breakout,
- confirmation.

So the backtest tested temporal sequencing rather than requiring all states on the same bar:
- dot then break;
- break then dot;
- sequence ages 1/2/3/5/8 bars;
- M15 alignment;
- Bj label;
- candle direction;
- initial timing.

Best stable frequency-valid result:
- M3, break_then_dot, age 3, M15 align, Bj label, candle direction, initial timing.

Results:
- 2024: 185 trades, 32.43% WR, +55R, min month 11.
- 2025: 174 trades, 32.76% WR, +54R, min month 10.
- 2026 YTD: 141 trades, 33.33% WR, +47R, min month 11.

A dot_then_break age-2 candidate reached 36.22% WR in 2026, but only 31.48%/33.33% in 2024/2025.

Conclusion: sequence matters, but the reconstructed components are still not the true proprietary filter.

## v0.18 — H1 structure / break-and-hold reconstruction

Weekly forecast evidence repeatedly uses:
- reject upper zone => sell;
- break & hold above pivot => buy;
- break & hold below support => continuation sell.

Tested H1 pivot/break-state families with:
- recent swing/pivot structures;
- hold for 1 or 2 candles;
- pivot-trend and break-state modes;
- M3/M5 execution;
- optional Bj label;
- candle direction;
- supplied timing.

Best frequency-valid candidate:
- M3, p3_hold2 breakState, no label, candle direction, initial timing.

Results:
- 2024: 202 trades, 27.72% WR, +22R, min month 13.
- 2025: 213 trades, 30.05% WR, +43R, min month 12.
- 2026 YTD: 148 trades, 30.41% WR, +32R, min month 9.

Conclusion: generic H1 pivot/break-and-hold logic also does not reproduce MPL's apparent signal quality.

## Current conclusion

Across v0.15-v0.18, every visible/public-looking component tested so far remains profitable only because 1:3 has a 25% breakeven WR, but none approaches the required 60–80% WR while preserving >=8 trades/month.

The strongest surviving clues remain:
1. Blue line ≈ RMA/SMMA(close,10).
2. The lower panel definitely looks like MACD 12/26/9 with extra proprietary inputs.
3. The chart overlay likely contains Bjorgum SuperScript-like components and Bollinger structure.
4. The missing edge is likely in the extra oscillator parameters / dynamic timetable / discretionary HTF-zone filter / selective publication logic rather than the visible MA layer alone.

Next step: reverse-engineer the remaining lower-panel parameters `1 ... 3 2 5 5` and test whether they define a second oscillator / stochastic-style smoothing / volume-pressure regime that gates MACD dots.
