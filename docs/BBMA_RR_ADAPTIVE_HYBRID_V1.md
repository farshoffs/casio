# CASIO BBMA–RR Adaptive Hybrid v1

Branch: `feature/bbma-rr-adaptive-hybrid-v1`

TradingView script:

```text
pine/CASIO_BBMA_RR_ADAPTIVE_HYBRID_V1.pine
```

## Purpose

This branch freezes the first BBMA–RR Adaptive Hybrid implementation for live visual use and TradingView Strategy Tester work.

The router is deliberately asymmetric:

```text
BBMA Cleaner Core = default engine
RR10              = exceptional-regime engine
```

RR10 does not replace an open BBMA position. The portfolio remains one-position-at-a-time.

## TradingView setup

Use:

```text
Symbol: XAUUSD
Chart: 5 minutes
Mode: LIVE + BACKTEST
Backtest start: 2017-01-01 UTC
Initial capital: RM100
Risk per accepted entry: 5%
Pyramiding: 0
```

The script is a Pine `strategy()`, so it serves both purposes:

- **live dashboard / indicator** — BUY and SELL labels plus active Entry, SL, TP1 and TP2;
- **Strategy Tester** — the same accepted signals place strategy orders when Mode is `LIVE + BACKTEST`.

Set Mode to `LIVE SIGNALS ONLY` to suppress Strategy Tester orders while retaining the live trade plan, labels, levels, dashboard and alerts.

## BBMA Cleaner Core

The deterministic BBMA implementation uses:

- Bollinger Bands 20, 2;
- LWMA 5 High / Low;
- LWMA 10 High / Low;
- EMA50 major-trend context;
- H4 -> H1 -> M15 -> M5 multi-timeframe structure.

The retained entry families are research labels around BBMA sequencing:

```text
RRR_CSM
CSM_CSM_RE
H1_RE_M15_CSM_M5_RE
```

All accepted BBMA entries require H4 major-trend alignment. Short entries also require the H1 Zero-Loss structure.

Default stop filter:

```text
structural swing stop + 0.15 M5 ATR buffer
minimum stop = 1.0 M5 ATR
maximum stop = 1.8 M5 ATR
```

Cadence controls:

```text
maximum 3 entries/day
36 M5-bar cooldown
```

Default management:

```text
initial risk = 1R
+0.50R reached -> protection moves to +0.25R after that bar closes
50% TP at +3R
50% runner at +4R
opposite M5 CSM/CSAK -> close remaining position
```

## RR10 exception

RR10 uses the canonical CASIO 0591 impulse -> pullback -> confirmation state machine and the existing RR10 internal confirmation/router logic.

A canonical RR10 setup is eligible for the Hybrid only when:

```text
RR10 router mode = TREND
support >= 2
rolling shadow sample >= 16 completed qualifying RR10 trades
rolling-16 RR10 shadow expectancy > 0R
```

The qualifying RR10 shadow stream continues to run even when BBMA owns the live position. Shadow results do not place portfolio trades; they only decide whether the RR10 exception gate is open for future entries.

RR10 target:

```text
fixed 3R
```

## Live display

When a hybrid trade is active the dashboard shows:

- direction;
- active engine: BBMA or RR10;
- BBMA setup / RR10 mode;
- RR10 adaptive gate state;
- shadow sample size and expectancy;
- RR10 TREND/MIXED state and confirmation support;
- Entry;
- SL;
- TP1;
- TP2 for BBMA;
- BBMA protection state;
- Strategy Tester closed trades, win rate and net P/L.

Chart plots use separate Entry, SL, TP1 and TP2 lines. BUY and SELL labels are printed on accepted portfolio signals.

## Alerts

Create one TradingView alert with:

```text
Condition: CASIO BBMA–RR Adaptive Hybrid v1
Trigger: Any alert() function call
```

The script sends JSON containing the active engine, setup, direction, entry, stop, TP1, TP2, risk percentage, RR shadow sample, RR shadow expectancy and adaptive-gate state.

## Causality

Higher-timeframe BBMA context uses completed bars only.

RR10 is evaluated at the final M5 child of each M15 bar. The M15 value uses `lookahead_off`, so the RR10 state transition is made only when that M15 bar has completed.

H1/H4 RR10 context uses completed higher-timeframe bars.

The RR10 adaptive gate for a new candidate uses only the **previously completed** shadow trades. The current candidate is added to the shadow stream only after its gate decision is made.

## Backtest notes

The script uses TradingView's broker emulator and enables Bar Magnifier. Results can differ from the Python research replay because of:

- broker/feed candle differences;
- TradingView intrabar reconstruction;
- contract/point-value sizing;
- spread, slippage, swap and commission assumptions.

Commission is intentionally zero in v1 so the baseline matches the existing gross research method. Cost stress should be performed separately before deployment.

The RM risk calculation uses:

```text
risk cash = current Strategy Tester equity × risk %
quantity  = symbol-converted risk cash / (stop distance × syminfo.pointvalue)
```

## Status

This branch is a **research/live-visual candidate**, not a production promotion.

Before production promotion:

1. compile in TradingView Pine v6;
2. run Strategy Tester from 2017 on the intended XAUUSD feed;
3. compare overlapping trades against the Python RR10 engine;
4. run independent-feed robustness;
5. run spread/slippage stress;
6. confirm live alert payloads and lot-size behavior with the intended broker.
