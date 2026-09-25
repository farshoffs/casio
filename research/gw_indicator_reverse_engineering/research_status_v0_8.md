# GW/MPL reverse engineering — research status v0.8

Branch: `research/gw-indicator-reverse-engineering`

Dataset:
- FxPro XAUUSD M1.
- Historical validation used 2024, 2025 and 2026 YTD (through 2026-09-24).
- Malaysia timing windows taken only from supplied MPL evidence.

## Strong forensic findings

### Blue line candidate
The strongest match remains RMA/SMMA(close, 10).

On the supplied 2026-09-14 M15 screenshot the blue Momentum Power Line is about 4296.403. FxPro M15 RMA10 around the corresponding period reconstructs about 4296.5, and an earlier point matched within about 0.03. This is substantially closer than ordinary EMA candidates and remains the primary blue-line hypothesis.

### Telegram zone geometry
Repeated signal geometry supports:
- blue-line-side edge of entry zone ~= anchor;
- zone width ~= $4;
- stop ~= $4 outside anchor;
- TP1 ~= 2R;
- TP2 ~= 3R;
- TP3 ~= 4R.

Therefore research that must obey fixed 1:3 uses the blue-line anchor as entry, $4 real SL and $12 TP (Telegram TP2 equivalent). Using the far edge of the zone increases apparent WR but reduces the *actual* R multiple, so those runs are explicitly rejected as incompatible with the fixed 1:3 rule.

## v0.2/v0.3 — MTF + current candle + momentum candidates

Evidence-backed live/current-candle logic was tested:
- H1 current candle direction + price vs RMA10.
- M15 current candle direction + price vs RMA10.
- M3 current candle direction + price vs RMA10.
- observed timing windows.
- MACD 12/26/9 candidate.
- signed tick-volume pressure proxy.
- EMA50 side candidate.

Best raw 2026 WR with fixed $4 / 1:3 remained below 40%. Fresh M3 cross + MACD produced roughly 38.6% WR but frequency was not sufficient.

## v0.4 — retest/limit execution

A pending-limit model was tested because the supplied material repeatedly says "sell on retest" and the Telegram entry zone hugs the blue line.

When entries were moved deep into the 4-dollar zone, WR rose above 50%, but the actual reward:risk fell to about 1.29R because the stop stayed outside the blue-line anchor. This is not valid under the fixed 1:3 research rule.

The only compatible 1:3 version is exact-anchor entry:
- entry = M15 RMA10;
- SL = 4 dollars;
- TP = 12 dollars.

That exact-anchor version did not reach the 60–80% WR target.

## v0.5 — "Timing Power" out-of-sample test

The three supplied initial-entry windows were treated as a timetable selection problem:
- 08:50–09:30 MYT
- 10:30–11:15 MYT
- 13:30–14:30 MYT

A weekday-to-window timetable was optimized only on 2024–2025 and then validated on 2026 YTD.

Best validation results remained around:
- Base: 32.5% WR, +25R.
- MACD: 33.3% WR, +24R.
- MTF volume: 33.3% WR, +22R.
- combined candidate: 34.8% WR, +27R.

Conclusion: timetable selection by itself does not explain MPL's claimed hit rate.

## v0.6 — H1 structural breakout state

Tested HTF regime states based on confirmed H1 breaks of prior 6/12/24/48-hour ranges, then forward-filled until an opposite break.

The filters increased 2026 selectivity/frequency profiles in some cases but were not stable across 2024–2026. No candidate sustained >=35% WR across all three years at fixed 1:3.

## v0.7 — add M5 confirmation

Because supplied SOP examples explicitly mention combinations including M5, completed M5 RMA10/MACD confirmation was added.

Best 2026 candidate:
- M5 + fresh M3 cross + MACD: 40.0% WR, +12R.
- only 20 trades YTD; minimum month = 1.

This improved quality but destroyed required frequency and was not stable in 2024–2025.

## v0.8 — purple "breakout moving average" candidate

The `50` visible in the V2 Advance title and classroom text "Breakout Moving Average" motivated a direct EMA50-breakout test:
- fresh M3 EMA50 cross;
- cross within last 1/2/3/5 M3 bars;
- MACD / volume combinations;
- M15 EMA50 side confirmation.

Result: fresh EMA50 breakout generally made historical performance worse. No variant was stable across 2024–2026. Therefore "purple line = simple EMA50 breakout" is currently a weak hypothesis and should be deprioritized.

## Current best interpretation

The supplied system cannot yet be reproduced by:
- RMA10 direction,
- MTF candle alignment,
- the observed timetable,
- ordinary MACD,
- a simple tick-volume proxy,
- simple EMA50 breakout,
- or generic H1 breakout-state filters.

The evidence strongly suggests one or more still-missing proprietary/discretionary pieces are doing most of the selection:
1. exact dot/momentum formula;
2. exact buyer/seller pressure formula;
3. exact purple/grey confirmation formula;
4. daily timetable generation rather than a fixed clock schedule;
5. HTF forecast zones / rejection-vs-break-and-hold logic;
6. possible selective publication / discretionary rejection of otherwise-valid raw signals.

## Next research direction

Do not parameter-optimize the failed proxies. Continue forensic reconstruction:
- match the supplied screenshots candle-by-candle;
- identify the exact blue-line formula first (RMA10 remains primary);
- reconstruct dot state transitions from screenshot timestamps;
- infer whether the oscillator uses MACD, MACD + stochastic-style smoothing, or a transformed volume oscillator;
- reconstruct HTF support/resistance zones from H1 swing clusters on the supplied dates;
- backtest only after each component can reproduce known screenshots.
