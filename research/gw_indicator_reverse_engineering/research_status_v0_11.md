# GW/MPL reverse engineering — v0.9 to v0.11

Branch: `research/gw-indicator-reverse-engineering`

## Major forensic breakthrough

A supplied screenshot visibly contains the parameter string `Bj Reversal close 0.7 Fast Slow...`. Public Bjorgum source confirms that **Bj Reversal** uses two Tilson T3 averages and a selectable T3 alpha. The public implementation uses:
- T3 fast = 5 in the current SuperScript; an older published Gold/BJ implementation uses fast = 6.
- T3 slow = 8.
- T3 alpha = 0.7.
- bullish state when fast T3 >= slow T3 and price is above slow T3.
- bearish state when fast T3 <= slow T3 and price is below slow T3.
- yellow/reversal state when price and T3 ordering disagree.

This maps very closely to the candle/line behavior visible in the supplied GW screenshots.

A second public Gold scalping script combines:
- Chandelier Exit direction/labels,
- Bjorgum Reversal T3 confirmation,
- a trend MA,
- momentum filters.

That does **not** prove MPL/GW copied this script, but it gives a credible open-source component family that visually resembles the supplied indicator.

## Updated working architecture

The strongest evidence-backed mapping is now:

1. **Label / direction** -> Chandelier Exit / ATR trailing-state family.
2. **Dot / momentum** -> MACD 12/26/9 cross or side (the supplied oscillator input string exposes 12, 26, close, 9, EMA, EMA and the dot appears at the line crossover).
3. **Breakout MA / purple line** -> a moving-average breakout; SMA20 is now a stronger candidate than the previously tested EMA50.
4. **Colour / confirmation** -> Bjorgum Reversal / Tilson T3 state, alpha 0.7.
5. **MTF SOP** -> H1/M15/M5/M3 alignment applied on top.
6. **Timing Power** -> observed Malaysia-time entry windows.

## v0.9 — Bjorgum/T3 test

An initial v0.9 run appeared to produce very high WR on selective variants (including 75%+ in 2026), but audit found a higher-timeframe state-mapping bug: the script used the final close/state of the still-forming H1/M15 candle. That is future leakage.

**All v0.9 high-WR results are rejected.**

A corrected real-time/partial-state reconstruction was then run. Once the lookahead was removed, the apparent edge collapsed. This confirms that the earlier high WR was not valid.

## v0.10 — public-component reconstruction

Tested, without HTF future leakage:
- Chandelier Exit direction, ATR period 1 / multiplier 2.3 candidate.
- Bjorgum T3 (fast 6, slow 8, alpha 0.7).
- SMA20 breakout/side state.
- MACD 12/26/9 side and recent cross.
- M3 and M5.
- supplied entry windows.
- real SL, fixed 1:3.
- fixed $4 SL and ATR-normalized SL variants.
- one position at a time.

The best **frequency-compliant** family remained only around 28–31% WR across 2024–2026. Example:
- M3, SMA20 fresh break within 3 bars, MACD cross within 3 bars, CE direction, fixed $4:
  - 2024: 372 trades, 28.23% WR, +48R, min month 22.
  - 2025: 490 trades, 31.22% WR, +122R, min month 28.
  - 2026 YTD: 488 trades, 28.07% WR, +60R, min month 41.

Adding the Bjorgum confirmation to that family did not materially improve the hit rate:
- 2024: 27.92%.
- 2025: 28.21%.
- 2026 YTD: 28.03%.

ATR-normalized real stops also failed to move the system anywhere near the 60–80% WR target at 1:3.

## v0.11 — "first complete SOP state" trigger

To better mimic a signal indicator, the engine was changed so it does not enter on every bar while conditions remain aligned. It enters only when the complete component state changes from false -> true.

Best stable frequency-compliant example:
- M15 Chandelier Exit + MACD + SMA state.
- Trigger only on first full alignment.
- candle direction required.
- ATR10 x 1.5 real stop.
- fixed TP = 3R.

Results:
- 2024: 423 trades, 31.21% WR, +105R, minimum month 29.
- 2025: 409 trades, 29.58% WR, +75R, minimum month 27.
- 2026 YTD: 279 trades, 32.62% WR, +85R, minimum month 27.

Removing candle direction improved 2024/2026 slightly but 2025 stayed below 30%.

## Known-event forensic check: 14 Sep 2026

The public-component reconstruction lines up surprisingly well with the supplied large SELL example:
- Around 14:45 MYT on M5, Chandelier direction, Bjorgum state and MACD are simultaneously bearish.
- Around the later 19:45–20:00 MYT layering window, Chandelier and Bjorgum remain bearish and MACD turns bearish during the continuation.
- The reconstructed RMA10/SMA20 areas sit near the supplied layer prices.

This supports the component-family hypothesis, but historical backtests show that **raw component alignment is far too common**. MPL/GW is almost certainly applying an additional selector before publishing a signal.

## Current conclusion

We now have a much more credible reconstruction of what the visible components may be, but we still do not have the missing high-quality selector.

Do **not** optimize CE/T3/MACD/SMA parameters blindly. The next work should focus on the selection layer:

1. Reconstruct the exact daily timetable / "Timing Power" rule rather than treating all supplied windows as active every day.
2. Reconstruct the weekly/H1 forecast zone engine: reject zone vs break-and-hold.
3. Determine whether the Telegram channel publishes only a discretionary subset of raw indicator signals.
4. Match the known 14 Sep, 16 Sep and 25 Sep screenshots candle-by-candle and identify which raw signals were ignored.
5. Infer the grey-line confirmation state and exact Up/Down label source.
6. Only after the published-signal selector can be reproduced should we rerun the RM100 / 5% / real-SL / fixed-1:3 report.
