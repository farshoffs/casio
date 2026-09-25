# GW/MPL reverse engineering — v0.15 SuperScript forensic pass

## New forensic identification

A supplied TradingView screenshot shows the overlay title fragment:

`20 SMA close 2 Bj Reversal close 0.7 Fast Slow H`

Public source material for **Bjorgum SuperScript** documents:
- Bj Reversal uses Tilson/T3 moving averages.
- transition bars turn yellow when price crosses the Tilson moving averages;
- confirmed trend bars become blue/red when the two Tilson averages themselves align/cross;
- default T3 alpha is 0.7;
- the script also contains Fast/Slow TSI/RSI selections, PSAR, HEMA and arrow/curl options.

This is a very strong visual/settings match to the supplied GW-free screenshot. The preceding `20 SMA close 2` is also consistent with a standard Bollinger Band basis of SMA(20), source close, multiplier 2.

Therefore v0.15 tests the visible/public components directly instead of proxying them with arbitrary indicators.

## Components reconstructed

- Bollinger basis: SMA(close,20), stdev x2.
- Bjorgum Reversal exact candidate:
  - fast T3 length 6;
  - slow T3 length 8;
  - alpha 0.7.
- Bj TSI Fast:
  - short 5;
  - long 25;
  - signal EMA 14.
- RSI Slow: RSI 14.
- HEMA candidate: HA-open EMA 5/9/21 alignment.
- PSAR: standard 0.02 / 0.02 / 0.20 candidate.
- Trigger candidates:
  - state;
  - fresh Bj confirmation;
  - fresh BB basis cross;
  - BB retest;
  - TSI curl;
  - yellow-transition -> confirmed Bj state.
- MTF candidates on M15/H1.
- Supplied Malaysia timing windows.
- Real fixed SL $4, TP $12 = strict 1:3.
- One active trade at a time; M1 resolves exits conservatively.

## 2024–2026 result

No reconstructed SuperScript combination reaches the requested 60–80% WR while preserving >=8 trades in every month.

Best stable frequency-valid candidate in this pass:

`M3 | Bj + BB + TRM | yellow->confirm | candle direction | supplied timing`

- 2024: 297 trades, 28.96% WR, +47R, minimum month 17.
- 2025: 372 trades, 29.30% WR, +64R, minimum month 20.
- 2026 YTD: 314 trades, 28.66% WR, +46R, minimum month 31.

A more selective M5 candidate:

`M5 | Bj + BB + HEMA | M15/H1 Bj direction | supplied timing`

- 2024: 244 trades, 28.28% WR, +32R.
- 2025: 387 trades, 29.46% WR, +69R.
- 2026 YTD: 417 trades, 30.94% WR, +99R.

This is positive expectancy at 1:3 because breakeven before costs is 25%, but it is nowhere near MPL's apparent signal-selection quality.

## What v0.15 changes

The visual overlay in the supplied screenshot is now much less mysterious. A substantial part is likely based on, or visually derived from, public components in the Bjorgum SuperScript family plus a Bollinger Band.

However, reproducing those visible components does **not** reproduce the claimed high hit rate. Therefore the missing edge is much more likely to live in:

1. the lower `indikator GW free` oscillator/dot logic;
2. exact dynamic timetable selection;
3. discretionary HTF zones / reject vs break-and-hold filtering;
4. selective signal publication;
5. or a proprietary layer added on top of the public-looking chart overlay.

## Important oscillator observation

The lower panel title reads:

`indikator GW free 1 12 26 close 9 EMA EMA 3 2 5 5`

The `12 26 close 9 EMA EMA` segment exactly matches TradingView's standard MACD input signature. The visible panel itself also has:
- two MACD-like lines;
- zero-centered histogram;
- histogram fading as momentum contracts;
- red/green dots around momentum transitions.

The remaining `1 ... 3 2 5 5` parameters are therefore the next forensic target. v0.16 should identify what these extra inputs control rather than treating the bottom panel as a plain MACD.
