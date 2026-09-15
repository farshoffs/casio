# Market data

Place XAUUSD OHLC data at `data/xauusd.csv`.

Required columns:

```csv
timestamp,open,high,low,close,volume
2026-01-02T00:00:00Z,2624.10,2626.40,2621.70,2625.80,0
```

- `timestamp` must be parseable as a date/time.
- `open`, `high`, `low`, and `close` are required.
- `volume` is optional in v0.1.
- Keep one consistent timeframe per file. M15 is the recommended first dataset for the combined Intraday/Scalping engine.

The GitHub Action automatically detects this file and runs the rolling backtest/audit.
