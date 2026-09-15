# CASIO

CASIO is an experimental **XAUUSD AI-assisted strategy lab** with two deterministic trading modes plus automated backtest/audit agents and a TradingView live-signal adapter.

> Research software only. Historical performance is not a guarantee of future results.

## TradingView integration

CASIO now includes:

```text
pine/CASIO_XAUUSD_v1.pine   TradingView strategy + live JSON alerts
api/tradingview.py          secure webhook receiver for live alerts
docs/TRADINGVIEW.md         setup guide
```

Recommended first chart: **XAUUSD M15**, with strategy mode set to `AUTO`.

The live flow is:

```text
TradingView XAUUSD
       |
       +--> CASIO Pine strategy
                |
                +--> Intraday / Scalping regime selection
                +--> Strategy Tester
                +--> confirmed-bar JSON alert
                            |
                            v
                    /api/tradingview
```

See [`docs/TRADINGVIEW.md`](docs/TRADINGVIEW.md) for the full setup.

## Strategy modes

### 1. Intraday mode
Designed for directional XAUUSD conditions.

Core idea:

1. Trend alignment using EMA20/EMA50.
2. Detect previous 20-bar liquidity highs/lows.
3. Look for liquidity sweep + reclaim/rejection.
4. Require confirmation candle and acceptable volatility.
5. Enter only when the weighted score reaches the configured threshold.
6. Initial research target is **1:3 R:R**.

The intended production evolution is H4 bias -> H1 supply/demand -> M15 liquidity sweep/structure confirmation. The current engine provides a deterministic first version that can be backtested immediately from OHLC data.

### 2. Scalping mode
Designed especially for sideways/ranging XAUUSD.

The engine classifies a sideways regime using:

- ADX <= configured limit (default 22)
- 30-bar range compression relative to ATR

It then trades **range-edge mean reversion** rather than trend continuation:

- lower edge + sell-side sweep/reclaim -> long candidate
- upper edge + buy-side sweep/rejection -> short candidate
- reversal candle confirmation
- initial research target **1:1.5 R:R**

## Automatic regime selection

CASIO calculates features for each bar and routes the setup automatically:

```text
low ADX + compressed range -> SCALPING
otherwise                  -> INTRADAY
```

This keeps the sideways playbook separate from the directional playbook instead of forcing one strategy into every market condition.

## Backtest agent

`casio/backtest.py` simulates trades deterministically from OHLC data.

Important behaviors:

- no overlapping positions in the initial engine
- conservative same-candle handling: if stop and target are both touched, stop is counted first
- configurable maximum holding bars
- trade results expressed in **R multiples**
- continuously reports the **latest 100 completed trades**
- statistics are also split into Intraday and Scalping modes

Statistics include:

- trades / wins / losses
- win rate
- average R / expectancy
- profit factor
- maximum drawdown in R

## Audit agent

`casio/audit.py` compares the latest rolling sample with the previous sample.

It checks for:

- falling win rate
- falling expectancy
- profit factor below 1.0
- non-positive rolling expectancy
- degradation separately in Intraday and Scalping

Audit state:

```text
HEALTHY
WARNING
CRITICAL
INSUFFICIENT_DATA
```

The audit agent **does not automatically rewrite or deploy strategy parameters**. It reports degradation and recommends review. This is intentional to prevent last-100-trade overfitting and keeps every strategy change reviewable through Git history.

## Automated GitHub agent

`.github/workflows/strategy-audit.yml` runs:

- on strategy/data pushes
- manually with `workflow_dispatch`
- once every hour

When `data/xauusd.csv` exists it produces:

```text
reports/trades.csv
reports/backtest-100.json
reports/audit.json
```

The reports are published into the GitHub Actions summary and uploaded as a workflow artifact.

## Market data

Add XAUUSD OHLC data here:

```text
data/xauusd.csv
```

Required schema:

```csv
timestamp,open,high,low,close,volume
2026-01-02T00:00:00Z,2624.10,2626.40,2621.70,2625.80,0
```

M15 is the recommended starting timeframe for the combined engine.

## Run locally

```bash
pip install -r requirements.txt
python -m casio.cli --data data/xauusd.csv --output reports
```

## Project structure

```text
casio/
  config.py       strategy thresholds and audit limits
  strategy.py     regime detection + Intraday/Scalping signals
  backtest.py     deterministic trade simulator + rolling metrics
  audit.py        strategy health / degradation audit
  cli.py          report runner
pine/
  CASIO_XAUUSD_v1.pine
api/
  tradingview.py
docs/
  TRADINGVIEW.md
data/
  README.md
.github/workflows/
  strategy-audit.yml
```

## Next planned layer

The live TradingView adapter and deterministic research layer now share the same initial thresholds. The next layer is persistent live-signal storage plus a dashboard that shows the current CASIO signal beside rolling last-100 performance and audit health.
