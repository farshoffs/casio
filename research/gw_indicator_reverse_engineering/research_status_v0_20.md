# GW/MPL reverse engineering — status v0.20

## Major forensic breakthrough: lower oscillator fingerprint

The lower-panel legend in the supplied screenshot reads approximately:

`indikator GW free 1 12 26 close 9 EMA EMA 3 2 5 5`

The sequence after the MACD settings matches the public/community **CM MACD Custom Indicator - Multiple Time Frame V2.x** family extremely closely.

Core fingerprint:
- Fast Length = 12
- Slow Length = 26
- Source = close
- Signal Smoothing = 9
- Oscillator MA Type = EMA
- Signal Line MA Type = EMA

The same public script family uses:
- MACD Width = 3
- Signal Width = 2
- Histogram Width = 5
- Dot Width = 5

Therefore the trailing `3 2 5 5` are very likely **plot-width settings**, not hidden proprietary oscillator parameters.

The public script also plots dots exactly on MACD/signal crosses:

`cross_UP = signal[1] >= macd[1] and signal < macd`

`cross_DN = signal[1] <= macd[1] and signal > macd`

This substantially changes the research direction: the lower panel is probably a renamed/forked standard MACD-MTF display rather than the source of a secret 3/2/5/5 trading formula.

The leading `1` before `12` remains unresolved. It may be an indicator-timeframe input in a fork, but this is not yet confirmed.

## Screenshot date/value forensic match

The 30m GW-free screenshot around the Sep 5/7 date labels strongly matches FxPro XAUUSD on 2025-09-05.

Standard 30m MACD(12,26,9) around the matching late-session candle reconstructs approximately:
- MACD ~= 8.85
- signal ~= 10.14
- histogram ~= -1.30

That is visually consistent with the supplied screenshot's two lines, red cross-dot region and negative histogram near -1.2.

This supports:
- standard MACD core;
- chart-timeframe MACD behavior;
- dot = MACD/signal crossover.

## Exact Bjorgum correction

The upper-overlay screenshot legend:

`20 SMA close 2 Bj Reversal close 0.7 Fast Slow H...`

matches public Bjorgum SuperScript settings very closely.

Exact Bj Reversal defaults are:
- fast T3 length = 5
- slow T3 length = 8
- T3 alpha = 0.7.

The previous v0.15 proxy used fast T3 length 6. v0.19 corrects this to 5/8.

The preceding `20 SMA close 2` is consistent with a standard Bollinger Band:
- basis SMA20;
- source close;
- multiplier 2.

This also makes the **SMA20 Bollinger basis** a stronger candidate for the classroom's purple "breakout moving average" than the earlier EMA50 hypothesis.

## v0.19 — exact visible-component reconstruction

Tested:
- BB basis SMA20;
- Bj Reversal T3 5/8, alpha 0.7;
- standard MACD 12/26/9 cross-dots;
- blue RMA10 candidate;
- dot/break sequencing;
- M15/H1 filters;
- supplied Malaysia initial-entry windows;
- strict real SL $4 and TP $12 = 1:3.

Best frequency-valid candidate:

`M3 | age3 dot_sma_bluex | M15 blue | supplied timing`

Results:
- 2024: 211 trades, 30.81% WR, +49R, minimum month 12.
- 2025: 216 trades, 31.48% WR, +56R, minimum month 11.
- 2026 YTD: 187 trades, 33.69% WR, +65R, minimum month 18.

Correcting Bjorgum and using SMA20 instead of EMA50 does not reproduce a 60–80% WR edge.

## v0.20 — live/current HTF reconstruction

Telegram wording repeatedly refers to `candle semasa` (current candle), so v0.20 reconstructs current partial M15/H1 candles rather than using only completed HTF bars.

The current HTF RMA value is reconstructed from:
- previous completed HTF RMA;
- current live close.

Best frequency-valid candidate:

`M3 | age3 dot_sma_blue | M15 live alignment | candle direction | timing`

Results:
- 2024: 235 trades, 30.21% WR, +49R, minimum month 15.
- 2025: 253 trades, 30.83% WR, +59R, minimum month 17.
- 2026 YTD: 211 trades, 30.33% WR, +45R, minimum month 17.

Using live partial M15/H1 alignment does not unlock the claimed hit rate.

## Revised interpretation

Visible/public-looking components are now substantially identified:

1. Lower panel: likely CM-MACD-MTF-style standard MACD 12/26/9 with cross dots.
2. Upper overlay: likely Bollinger SMA20/2 plus Bjorgum SuperScript-style Bj Reversal.
3. Purple breakout line: SMA20 basis is now a stronger candidate than EMA50.
4. MACD trailing values `3 2 5 5` are likely visual widths, not strategy parameters.

The unexplained selection edge is therefore concentrated elsewhere:

- **Momentum Power Line / blue direction engine**;
- grey confirmation line/color state;
- dynamic timetable generation;
- HTF forecast-zone rejection/break-and-hold selection;
- discretionary publication/filtering;
- layering + BE execution rather than raw fixed-1:3 single-entry statistics.

## Next forensic target

Focus exclusively on the supplied title:

`MOMENTUM POWER LINE - V1 A close 10 1 2`

The visual behavior is asymmetric/trailing:
- above price in bearish regimes;
- below price in bullish regimes;
- tends to flatten/trail rather than behave like an ordinary centered MA.

This now deserves a direct formula shootout:
- RMA/SMMA10;
- EMA10;
- ATR trailing stop;
- UT-Bot style ATR stop;
- Supertrend families;
- Chandelier-style trailing line;
- recursive trend-stop variants.

Known screenshot anchors around 2026-09-14, 2026-09-16 and 2026-09-25 should be matched numerically before any further strategy optimization.
