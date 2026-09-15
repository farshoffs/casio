# CASIO market data

CASIO v3 uses TradingView for visual charting, while the **automated research/live-signal data source is Dukascopy**. This keeps the system usable with TradingView Free.

The current strategy is:

```text
v2 regime-first MTF core
+
v3 adaptive 24h session overlay
```

The same M5 source is used to reconstruct the session-aware Python context.

## Automatic XAUUSD M5 dataset

Primary dataset:

```text
data/xauusd_m5.csv
```

Automatic workflow:

```text
.github/workflows/market-data-sync.yml
```

Pipeline:

```text
Dukascopy XAUUSD bid M5
        |
        v
scripts/fetch_dukascopy.mjs
        |
        v
casio/sync_market_data.py
        |
        v
data/xauusd_m5.csv
        |
        v
CASIO v3 Research & Robustness
```

The sync is configured to backfill from:

```text
2020-01-09T00:00:00Z
```

Later runs overlap recent stored data, then sort and deduplicate timestamps. No TradingView CSV download is required.

## Data format

```csv
timestamp,open,high,low,close,volume
2026-01-02T00:00:00Z,2624.10,2625.00,2623.80,2624.70,0
```

Requirements:

- M5 bars,
- UTC bar-open timestamps,
- OHLC required,
- volume optional,
- chronological unique timestamps.

The v3 engine rebuilds:

```text
M15 -> primary setup/execution features + session classification
H1  -> bias, value and range context
H4  -> directional context
M5  -> Scalping confirmation + finer execution simulation
```

UTC timestamps matter because the current session buckets are evaluated as:

```text
ASIA        00:00-06:00 UTC
LONDON      07:00-11:00 UTC
NEW YORK    12:30-16:30 UTC
TRANSITION  all remaining times
```

## Source and pricing

The automatic downloader requests:

```text
instrument: XAUUSD
timeframe: M5
price side: bid
UTC offset: 0
```

Bid candles provide a consistent research source, but the separate CASIO cost model is still required because bid-only OHLC does not reproduce live bid/ask spread, commissions or slippage.

Dukascopy and the provider shown in TradingView can have different XAUUSD candles. CASIO therefore does not claim tick-for-tick TradingView parity.

## Rate limiting and reliability

Long historical backfills are split into chunks and paced because public data providers can rate-limit aggressive requests. Incremental updates are much smaller.

A failed sync should not commit a partial invalid dataset. The workflow validates row count, timestamp order and duplicate timestamps before committing.

## Free-plan live signal data

`.github/workflows/live-signal.yml` fetches recent Dukascopy M5 shortly after each M15 close, rebuilds H4/H1/M15/M5 context, classifies the current session and applies the active session playbook.

It can therefore evaluate:

```text
London / New York normal Intraday
Asia stricter trend exception
Transition stricter trend exception
Scalping range playbook across sessions
```

The live job does **not** rewrite `data/xauusd_m5.csv` every 15 minutes; the persistent research dataset remains on the slower sync.

## Run research manually

```bash
pip install -r requirements.txt
python -m casio.research_cli \
  --data data/xauusd_m5.csv \
  --output reports/v3-research \
  --max-candidates 64 \
  --cost-bps 1.0
```

Session-specific research output is written to:

```text
reports/v3-research/session_performance.csv
```

## Optional TradingView collector

`pine/CASIO_XAUUSD_M5_FEED.pine` is retained only for TradingView accounts that support alerts/webhooks. It is not required for the current Free-plan setup.

## Legacy dataset

The older single-timeframe engine still accepts:

```text
data/xauusd.csv
```

That path is for historical comparison only. Current CASIO v3 MTF work should use `data/xauusd_m5.csv`.
