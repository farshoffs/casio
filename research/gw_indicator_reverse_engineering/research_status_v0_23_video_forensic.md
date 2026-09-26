# GW/MPL reverse engineering — v0.23 video forensic pass

Source: user-supplied MPL/GW indicator video, analyzed frame-by-frame against the local FxPro XAUUSD M1 history.

## 1. MPL V1 B is now numerically identified

The lower pane legend in the video reads:

`MPL V1 B 12 26 close 9 EMA EMA`

At the visible M3 cursor timestamp:
- 2026-03-30 15:27 MYT
- 2026-03-30 07:27 UTC

the video shows approximately:
- histogram: -2.094
- MACD: 0.254
- signal: 2.348

FxPro M3 reconstructed standard MACD(12,26,9), EMA/EMA:
- MACD: ~0.2754
- signal: ~2.3563
- histogram: ~-2.0809

The small deviations are consistent with broker/feed differences.

**Conclusion:** the core of MPL V1 B is standard chart-timeframe MACD(12,26,9), EMA/EMA.

Two additional plotted values visible in the pane (~4.833 and ~-5.273 at this timestamp) remain unresolved. They must not yet be treated as standard MACD outputs.

## 2. Blue MPL line = SMA20(close), independently confirmed again

At the video section around 2026-03-30 15:57 MYT on M3:

Video:
- O ~4527.840
- H ~4528.265
- L ~4525.085
- C ~4527.585
- blue MPL value ~4525.715

FxPro M3:
- O ~4527.61
- H ~4528.06
- L ~4524.89
- C ~4527.42
- SMA20(close) ~4525.4855

The blue-line difference is only about 0.23, consistent with the simultaneous broker/feed price offset.

**Conclusion:** the blue line should be treated as `SMA(close, 20)`.

This independently confirms the Sep-16 side-by-side evidence.

## 3. Strong new candidate for MPL V1 A red/green ribbon

The upper indicator legend is:

`MOMENTUM POWER LINE - V1 A close 10 1 2`

This exact four-parameter signature is highly compatible with:

`ALMA(source, length, offset, sigma)`

which maps naturally to:

`ALMA(close, 10, 1, 2)`

The video says the M3 buy SOP only appears around 15:57 MYT, at the point where the upper red ribbon changes to green.

On FxPro M3:
- ALMA(close,10,1,2) compared with ALMA[2] flips bullish on the 15:54 close;
- therefore the confirmed state becomes available on the 15:57 bar.

That timing matches the spoken/video transition unusually well.

Candidate state logic:

```
mplA = ALMA(close, 10, 1, 2)
bull = mplA > mplA[2]
bear = mplA < mplA[2]
```

The ribbon can be reproduced as the filled area between `mplA` and `mplA[2]`.

**Status:** strongest current hypothesis, but not yet promoted to confirmed. It still needs multiple independent transition matches from the video/screenshots.

## 4. Candidates weakened/rejected by the video

- RMA10/HMA10/EMA10 delayed-copy hypotheses: no longer primary; they do not explain the exact `close 10 1 2` signature.
- AlphaTrend(10,1): state timing does not match the observed transition.
- classic OTT/VAR with 1%: visual gap is far too large around $4,500 gold.
- simple EMA10/SMA20 cross: transition is too late.
- generic range filter: too many state changes and poor visual match.

Supertrend-like formulas remain a fallback because some can flip near the same event, but they do not explain the input signature nearly as cleanly as ALMA.

## 5. Current reconstructed architecture

Upper module:
- blue line: SMA20(close) — high confidence / numerically matched.
- red/green MPL-A ribbon: ALMA(close,10,1,2) vs ALMA[2] — strongest current candidate.

Lower module:
- MACD 12/26/9 EMA/EMA — numerically confirmed.
- red/green dots/arrows likely tied to MACD/signal cross events — needs bar-by-bar validation.
- extra upper/lower plotted values remain unknown.

## Next validation

1. Extract every clearly visible red->green / green->red MPL-A transition in the video.
2. Compare exact transition bars against ALMA(close,10,1,2) vs ALMA[2].
3. Validate MACD cross marker timestamps against the lower-pane arrows/dots.
4. Reverse-engineer the two extra MPL-B values (~4.833 / -5.273).
5. Only after repeated visual matches, rerun the 2024-2026 backtest with the corrected components.
