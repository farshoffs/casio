# CASIO market data

CASIO v3 uses TradingView for visual charting, but the **automated research/live-signal data source is Dukascopy**, not TradingView alerts.

This keeps CASIO usable with a TradingView Free account.

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

The first successful sync backfills from:

```text
2020-01-09T00:00:00Z
```

Later daily runs start a few days before the newest stored timestamp. The overlap is intentional: the merger sorts and deduplicates by timestamp so recent data can be refreshed safely.

No TradingView CSV download is required.

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
M15 -> primary setup/execution features
H1  -> structure, value and range context
H4  -> directional context
M5  -> Scalping confirmation + finer execution simulation
```

## Source and pricing

The automatic downloader currently requests:

```text
instrument: XAUUSD
timeframe: M5
price side: bid
UTC offset: 0
```

Bid candles are used as a consistent research source. The separate CASIO cost model is still required because a bid-only OHLC history does not reproduce the live bid/ask spread, commissions or slippage by itself.

Dukascopy and the broker/feed shown in TradingView can have different XAUUSD candles. The research engine therefore does not claim tick-for-tick TradingView parity.

## Rate limiting and reliability

Long historical backfills are split into chunks. The downloader includes pacing and exponential-style cooldown/retry behavior for provider rate limiting. Daily incremental runs are much smaller than the initial backfill.

If a data-sync workflow fails, it must not commit a partial invalid dataset. The workflow validates row count, timestamp order and duplicate timestamps before committing.

## Free-plan live signal data

`.github/workflows/live-signal.yml` also fetches recent Dukascopy M5 data shortly after each M15 close. It combines that recent data with the stored dataset, runs `casio/live_signal.py`, and only emits a fresh valid CASIO setup.

The live job does **not** modify `data/xauusd_m5.csv` every 15 minutes; the persistent research dataset remains on the slower daily sync.

## Run research manually

```bash
pip install -r requirements.txt
python -m casio.research_cli \
  --data data/xauusd_m5.csv \
  --output reports/v3-research \
  --max-candidates 64 \
  --cost-bps 1.0
```

## Optional TradingView collector

`pine/CASIO_XAUUSD_M5_FEED.pine` is retained only for TradingView accounts that support alerts/webhooks. It is not required and is not the primary data source for the current Free-plan setup.

## Legacy dataset

The older single-timeframe research engine still accepts:

```text
data/xauusd.csv
```

That path is retained only for historical comparison. New CASIO v3 MTF work should use `data/xauusd_m5.csv`.
