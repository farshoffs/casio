# CASIO market data

The current product is **CASIO v3**. Normal live TradingView use gets market data directly from TradingView and does **not** require a CSV file.

Historical CSV files are used by the independent Python research engines.

## CASIO v3 research dataset

The current automated MTF research engine requires:

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

This allows one dataset to support the full current MTF rule family.

## Why GitHub needs its own data

TradingView supplies the live chart and Pine strategy with its own historical/feed data, but GitHub Actions/Python cannot automatically query the user's TradingView chart history as if it were a public database.

Therefore:

```text
TradingView live v3 FAST -> no CSV needed
Python v3 research       -> data/xauusd_m5.csv needed
```

If `data/xauusd_m5.csv` is absent, `.github/workflows/v3-research.yml` reports that research was skipped. It does not invent performance numbers.

## Run v3 research

```bash
pip install -r requirements.txt
python -m casio.research_cli \
  --data data/xauusd_m5.csv \
  --output reports/v3-research \
  --max-candidates 64 \
  --cost-bps 1.0
```

See `docs/RESEARCH_V3.md` for the methodology and generated reports.

## Legacy Python dataset

The older single-timeframe Python research engine still accepts:

```text
data/xauusd.csv
```

with the same basic OHLC schema. M15 was the original recommended timeframe for that engine.

It is run by:

```text
.github/workflows/strategy-audit.yml
```

and produces the legacy reports:

```text
reports/trades.csv
reports/backtest-100.json
reports/audit.json
```

That workflow is retained for historical comparison. New MTF strategy research should use the v3 M5 engine.

## Parity caveat

The Python v3 engine is designed to reproduce the current **v3 product using the v2 regime-first MTF rule baseline**, but exact TradingView/Python parity is not yet assumed.

Possible differences include:

- source-feed OHLC differences,
- higher-timeframe bar mapping,
- Pine `request.security()` behavior,
- execution assumptions,
- live broker spread/slippage.

Before promoting a research candidate to live Pine, compare the same historical period in TradingView and Python.
