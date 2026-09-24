# Regime Router FxPro M1 Integrity Re-Backtest

Date: 2026-09-24

## Scope

This audit re-tests the five source techniques that formed the original profitable Regime Router ensemble using the user's complete FxPro XAUUSD M1 dataset.

Source techniques:

1. M15-0591 MTF
2. V1 Legacy M15
3. Outcome First M15
4. Structural Portfolio MTF
5. Structural Frequency M15

The strategy definitions, M15/H1/H4 causal context, source 2R/3R/4R targets, structural stops, 1 bp research friction, one-position portfolio rule, and Regime Router ordering are taken from the frozen `feature/regime-router-dashboard-research` implementation.

Data:
- FxPro XAUUSD M1
- 3,439,763 rows
- 2017-01-02 23:00 UTC through 2026-09-24 00:21 UTC
- 0 duplicate timestamps
- 0 invalid OHLC rows
- M1 is resampled causally to M15/H1/H4

Research account convention:
- RM100 starting balance
- 5% current-equity risk
- 1 bp round-trip cost sensitivity retained from the old research

## Audit result

### 1. No higher-timeframe lookahead found

The H1 and H4 data are shifted to their completed-candle time before being mapped to M15. The router uses the previous completed M15 feature row at the entry open. The audit did not find evidence that unfinished H1/H4 bars were used to make historical entries.

### 2. M15 same-bar TP/SL ordering did not inflate the old results

Across 19,491 raw source candidates there were only 46 M15 candles where both stop and target were inside the same M15 bar.

M1 chronological resolution found:
- 19: stop first
- 14: stop and target inside the same M1 candle -> still resolved stop-first
- 13: target first

Therefore the old M15 rule `stop first when both are touched` was conservative, not optimistic.

For the legacy Regime Router, M1 chronological resolution changes the full-history result from +39.27R to +47.27R after the same 1 bp cost: **+8R**, not a deterioration.

### 3. Entry-price parity is good, with a small timestamp-label issue

Whenever an M1 candle exists exactly at the nominal M15 entry time, the M15 entry price equals the M1 open exactly.

There are 19 raw candidates where the exact quarter-hour M1 candle is absent and the M15 resampler uses the first available minute's open while retaining the nominal quarter-hour label. Five of those trades were selected by the legacy router. Their actual first available M1 bars were 1-9 minutes later.

This does not change their fill price, but the historical entry timestamp should be recorded as the actual first available M1 timestamp in a future cleaned engine.

### 4. Major architecture dependency: source-stream position preblocking

The original ensemble does not route every valid source-technique signal. Each technique is first replayed as its own hypothetical standalone trade stream. While that hypothetical source trade is open, later signals from that technique are removed before the Regime Router sees them.

| Technique | Raw valid candidates | Signals seen by old router | Suppressed before routing |
|---|---:|---:|---:|
| M15-0591 MTF | 4,066 | 3,313 | 18.5% |
| Structural Portfolio MTF | 2,067 | 1,620 | 21.6% |
| Outcome First M15 | 2,073 | 1,681 | 18.9% |
| V1 Legacy M15 | 9,371 | 4,471 | **52.3%** |
| Structural Frequency M15 | 1,914 | 1,373 | 28.3% |

This is causal, so it is **not lookahead**, but it is a hidden state assumption: the router is affected by hypothetical source positions it may never have taken.

Sensitivity result:
- old serialized-source router: 3,908 trades, **+47.27R net** after 1 bp
- router allowed to see every raw valid source candidate: 4,315 trades, **+5.42R net** after 1 bp

The raw-signal version can over-count persistent multi-bar conditions, so it is not automatically the replacement engine. But the 42R collapse proves the historical result depends heavily on the source preblocking design. A clean router needs explicit signal de-duplication rules independent of hypothetical standalone positions.

## Standalone technique results — 2017-2026 YTD

These preserve the old source-stream position logic, but resolve execution on M1.

| Technique | Trades | WR | Gross R | 1bp cost R | Net R | Net expectancy | PF |
|---|---:|---:|---:|---:|---:|---:|---:|
| M15-0591 MTF | 3,313 | 31.7% | +128.11 | -185.83 | **-57.71** | -0.017R | 0.975 |
| Structural Portfolio MTF | 1,620 | 31.9% | +77.61 | -83.19 | **-5.58** | -0.003R | 0.995 |
| Outcome First M15 | 1,681 | 34.0% | +51.32 | -75.32 | **-24.00** | -0.014R | 0.978 |
| V1 Legacy M15 | 4,471 | 35.4% | +104.56 | -205.49 | **-100.93** | -0.023R | 0.965 |
| Structural Frequency M15 | 1,373 | 36.9% | +90.20 | -59.28 | **+30.92** | +0.023R | 1.036 |

All five are gross-positive before the 1 bp research cost. After that cost, **only Structural Frequency M15 remains profitable as a standalone technique over the complete history**.

This makes execution cost one of the most important unresolved variables. The FxPro M1 file contains one OHLC stream, not historical bid/ask spread, so the 1 bp number remains a sensitivity assumption rather than measured broker cost.

## Legacy Regime Router — full-history result

M1-resolved, same 1 bp research cost:

- trades: 3,908
- wins: 1,331
- losses: 2,577
- WR: 34.06% on net-R sign / 34.26% on gross target outcomes
- gross R: +234.91R
- friction: -187.64R
- net R: **+47.27R**
- expectancy: **+0.012R/trade**
- PF: **1.018**
- longest losing streak: 20

The additive R is positive, but the edge is extremely thin compared with the number of trades and assumed cost.

### Year by year

| Year | Trades | Net R | PF | Result |
|---:|---:|---:|---:|---|
| 2017 | 393 | -3.02 | 0.989 | loss |
| 2018 | 380 | -17.96 | 0.931 | loss |
| 2019 | 370 | -17.00 | 0.933 | loss |
| 2020 | 394 | -11.42 | 0.957 | loss |
| 2021 | 406 | -34.89 | 0.874 | loss |
| 2022 | 403 | -10.14 | 0.962 | loss |
| 2023 | 419 | +13.99 | 1.049 | profit |
| 2024 | 427 | -10.67 | 0.962 | loss |
| 2025 | 411 | +96.30 | 1.380 | profit |
| 2026 YTD | 305 | +42.08 | 1.217 | profit |

Only **3 of 10 year rows** are positive after the same 1 bp cost. The spectacular 2025-2026 period is not representative of the previous history.

## Which techniques actually contribute profit inside the legacy router?

Full-history selected-trade contribution after 1 bp:

| Technique selected by router | Selected trades | Net R |
|---|---:|---:|
| V1 Legacy M15 | 929 | **+56.03R** |
| Structural Frequency M15 | 577 | **+11.30R** |
| M15-0591 MTF | 637 | +0.26R |
| Outcome First M15 | 638 | -2.65R |
| Structural Portfolio MTF | 1,127 | **-17.68R** |

The long-history router profit is therefore concentrated mainly in **V1 Legacy M15 when filtered by router context** plus **Structural Frequency M15**. Structural Portfolio is a net drag in the complete FxPro history despite being given the highest mixed-regime priority.

## Continuous RM100 / 5% risk reality check

Using the complete 2017->2026 trade sequence continuously, without annual resets:

- after 1 bp cost: **RM100 -> RM0.0148**
- max compounded-equity drawdown: essentially **100%**

Even gross before the 1 bp cost:
- RM100 -> about **RM183.51**
- max drawdown: about **99.9%**

The reason is geometric volatility drag: +47R spread over 3,908 trades is too small an edge for 5% current-equity risk, and the strategy suffers long multi-year losing regimes.

Net-cost risk sensitivity for the same trade sequence:
- 0.5% risk: RM100 -> RM112.67, max DD ~52.9%
- 1% risk: RM100 -> RM100.72, max DD ~80.9%
- 2% risk: RM100 -> RM40.78, max DD ~98.0%
- 5% risk: RM100 -> RM0.0148, max DD ~100%

## Same-window 2026 feed check

The old Dukascopy 2026 Regime Router report through about 2026-09-16 showed 284 trades and RM842.28 from RM100.

Using FxPro M1 through 2026-09-16 13:30 UTC with the same source-family router architecture:
- 299 trades
- +48.18R after the 1 bp cost
- RM100 -> **RM409.99**
- gross/no-cost RM100 -> RM588.36

The difference is large enough to classify the system as **feed-sensitive**. It does not prove either feed is wrong; it means the historical edge is not sufficiently invariant across data sources.

## Verdict

The audit does **not** find a hidden future-data / HTF-lookahead error, and M15 same-bar handling was conservative.

However, the old Regime Router should **not be accepted as verified** in its current form because:

1. full 2017-2026 FxPro history is weak and highly regime-dependent;
2. four of five standalone techniques become negative after the research 1 bp cost;
3. the router's profitability depends heavily on source-technique position preblocking before routing;
4. Structural Portfolio is a long-run drag despite its high mixed-regime priority;
5. continuous RM100 / 5% compounding is effectively catastrophic;
6. 2026 performance is materially feed-sensitive between Dukascopy and FxPro.

## Recommended rebuild

Do not tune targets yet. Rebuild the Regime Router audit architecture first:

- source modules emit explicit **setup events**, not pre-replayed hypothetical trades;
- define deterministic de-duplication / cooldown per technique;
- route those events first;
- only the chosen portfolio trade gets an active-position lifecycle;
- execute SL/TP on M1;
- keep completed H1/H4 context only;
- report gross and several realistic cost sensitivities separately;
- validate year-by-year from 2017, continuously compounded without annual reset;
- re-rank source techniques using full-history router contribution, not 2025/2026 performance.

The strongest candidates to preserve for the rebuild are **V1 Legacy M15 under router filtering** and **Structural Frequency M15**. M15-0591 should remain research-only until its cost sensitivity improves. Outcome First and Structural Portfolio should not automatically retain their old priority.
