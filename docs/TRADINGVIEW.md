# CASIO + TradingView

TradingView is the **primary CASIO interface**. Vercel stays in the background for webhook ingestion/logging, while the chart itself shows the strategy, signal, performance and rolling audit.

## Add CASIO to TradingView

1. Open an **XAUUSD** chart.
2. Start with **M15**.
3. Open **Pine Editor**.
4. Paste `pine/CASIO_XAUUSD_v1.pine`.
5. Save and choose **Add to chart**.
6. Leave `Strategy mode = AUTO` initially.

Recommended defaults:

```text
Intraday minimum score: 70
Intraday target RR: 3.0
Scalping minimum score: 68
Scalping target RR: 1.5
Maximum ADX: 22
Maximum range / ATR: 5.5
Range-edge fraction: 0.22
Rolling audit: 100 trades
Minimum trades before audit: 30
```

AUTO routing:

```text
ADX <= 22 AND 30-bar range <= 5.5 ATR -> SCALPING
otherwise                                -> INTRADAY
```

## TradingView dashboard

The CASIO panel is rendered directly on the chart and shows:

```text
MODE
REGIME
ADX / SCORE
SIGNAL
ENTRY
STOP
TARGET
LAST 100 CLOSED TRADES
WIN RATE
EXPECTANCY (R)
PROFIT FACTOR
MAX DRAWDOWN (R)
INTRADAY WIN RATE
SCALPING WIN RATE
AUDIT STATUS
```

The latest rolling window is compared against the preceding window. Audit states are:

```text
INSUFFICIENT  fewer than configured minimum closed trades
HEALTHY       positive expectancy/PF and no material degradation
WARNING       win rate or expectancy degraded versus the previous window
CRITICAL      profit factor below threshold or non-positive expectancy
```

CASIO stores up to 200 closed-trade R results inside Pine so the latest 100 can be compared with the preceding 100 without leaving TradingView.

## Strategy Tester

Because the script uses `strategy()`, TradingView's **Strategy Tester** provides its own full performance view from TradingView market data. Use CASIO's on-chart rolling statistics for the most recent strategy health and Strategy Tester for deeper historical inspection.

## Live alerts to Vercel

The existing Vercel webhook remains useful for logging or future external automation.

Create an alert using:

```text
Condition: CASIO XAUUSD v1 — Intraday + Scalping
Trigger: alert() function calls only
```

Enable the webhook URL and use the CASIO Vercel endpoint configured for this project.

The Pine strategy emits JSON only on confirmed bar-close setups, including:

```text
mode
direction
score
entry
stop
target
RR
ADX
ATR
```

## Architecture

```text
TradingView XAUUSD
      |
      |-- CASIO Pine
      |     |-- Intraday / Scalping AUTO routing
      |     |-- BUY / SELL / WAIT
      |     |-- Entry / SL / TP
      |     |-- Strategy Tester
      |     |-- Rolling last-100 audit
      |
      +-- alert() JSON --> Vercel webhook --> CASIO backend logs

GitHub
      +-- versioned Pine + Python research engine
```

TradingView is therefore the day-to-day interface; GitHub is the source of truth for code/versioning; Vercel is the optional backend integration layer.

> Research software only. Historical performance does not guarantee future results.
