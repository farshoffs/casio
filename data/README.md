# CASIO market data

The current product is **CASIO v3**. Normal live TradingView use gets market data directly from TradingView and does **not** require a CSV file.

Historical CSV files are used by the independent Python research engine.

## Automatic M5 collection

CASIO can now build the research CSV automatically from new TradingView bars.

```text
TradingView XAUUSD M5
        |
        | every newly closed 5-minute bar
        v
pine/CASIO_XAUUSD_M5_FEED.pine
        |
        v
Vercel /api/tradingview
        |
        v
Google Apps Script
        |
        v
CASIO XAUUSD M5 Google Sheet
        |
        v
Vercel CSV export
        |
        v
.github/workflows/market-data-sync.yml
        |
        v
data/xauusd_m5.csv
        |
        v
CASIO v3 Research & Robustness
```

The GitHub sync runs daily at 21:20 UTC and commits new bars into `data/xauusd_m5.csv`. A data commit then triggers the v3 research workflow automatically.

### Important limitation

TradingView Pine alerts only produce events on realtime bars after an alert has been created. Therefore the automatic collector can maintain the dataset **from the moment it is activated forward**, but it cannot retrospectively send several years of old TradingView bars through alerts.

For robust multi-year testing, a one-time historical backfill is still useful. A manually exported TradingView M5 CSV can be merged into `data/xauusd_m5.csv`; the automatic sync preserves existing historical rows and appends/deduplicates the new realtime feed.

## One-time collector setup

1. Update/deploy the latest `apps-script/Code.gs`, then run `setupCasio()` once. It creates a Google Sheet named **CASIO XAUUSD M5 Data** in addition to the existing email setup.
2. In TradingView open the same XAUUSD feed used by CASIO on **5 minutes**.
3. Paste `pine/CASIO_XAUUSD_M5_FEED.pine`, save it and add it to the chart.
4. Create one alert using **Any alert() function call** and the existing CASIO Vercel webhook URL.
5. Leave the alert running. TradingView runs alerts on its servers; the browser/chart does not need to stay open.

After that, M5 collection is automatic.

## CASIO v3 research dataset

The current automated MTF research engine uses:

```text
data/xauusd_m5.csv
```

Required columns:

```csv
timestamp,open,high,low,close,volume
2026-01-02T00:00:00Z,2624.10,2625.00,2623.80,2624.70,0
```

Requirements:

- one row per M5 bar,
- `timestamp` is UTC **bar-open** time,
- `open`, `high`, `low`, `close` are required,
- `volume` is optional,
- rows should be chronological,
- multi-year history is strongly preferred for robustness testing.

The v3 research engine uses the M5 source to rebuild:

```text
M15 -> execution features and primary setup logic
H1  -> structure, value and range context
H4  -> directional context
M5  -> finer stop/target resolution and Scalping confirmation
```

## Automatic CSV endpoint

Once Apps Script is updated and the Vercel environment variables remain configured, CASIO exposes public **market data only** at:

```text
https://casio-farhan-shoffis-projects.vercel.app/api/tradingview?export=m5
```

The private Apps Script token remains server-side in Vercel; the public endpoint does not expose the token or email configuration.

`casio/sync_market_data.py` downloads this feed and merges it with any existing local history while deduplicating timestamps.

## Run v3 research manually

```bash
pip install -r requirements.txt
python -m casio.research_cli \
  --data data/xauusd_m5.csv \
  --output reports/v3-research \
  --max-candidates 64 \
  --cost-bps 1.0
```

See `docs/RESEARCH_V3.md` for methodology and reports.

## Legacy Python dataset

The older single-timeframe engine still accepts `data/xauusd.csv` and is retained only for historical comparison.

## Parity caveat

The Python v3 engine is designed to reproduce the current **v3 product using the v2 regime-first MTF rule baseline**, but exact TradingView/Python parity is not yet assumed. Feed OHLC, higher-timeframe mapping, Pine behavior and execution assumptions can still differ. Validate parity before promoting a research candidate to live Pine.
