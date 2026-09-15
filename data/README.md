# CASIO market data

This folder is used by the **Python research/backtest engine**, not by the live TradingView v2 strategy.

TradingView v2 receives its market data directly from TradingView and internally requests H4, H1, M15 and M5 context. You do not need to export CSV data for normal live use.

## Python research dataset

Place XAUUSD OHLC data at:

```text
data/xauusd.csv
```

Required columns:

```csv
timestamp,open,high,low,close,volume
2026-01-02T00:00:00Z,2624.10,2626.40,2621.70,2625.80,0
```

Requirements:

- `timestamp` must be parseable as date/time.
- `open`, `high`, `low`, and `close` are required.
- `volume` is optional.
- Keep one consistent timeframe in a file.
- M15 is the recommended dataset for the existing Python engine.
- Use sufficiently long history to avoid drawing conclusions from a very small number of trades.

## Important v2 limitation

The current Python strategy under `casio/` is the earlier deterministic single-timeframe research engine. It is **not yet a 1:1 implementation of `pine/CASIO_XAUUSD_v2_MTF.pine`**.

Therefore:

```text
TradingView v2 result != Python result by design, for now
```

For CASIO v2 performance, use:

1. TradingView Strategy Tester for the full historical Pine strategy result.
2. The CASIO v2 on-chart rolling audit for recent closed-trade health.

The Python engine remains useful as an independent research framework and will later be upgraded to reproduce the MTF v2 rules.

## GitHub Action

`.github/workflows/strategy-audit.yml` checks for `data/xauusd.csv` and, when present, runs:

```bash
python -m casio.cli --data data/xauusd.csv --output reports
```

It produces:

```text
reports/trades.csv
reports/backtest-100.json
reports/audit.json
```

This scheduled audit applies to the current Python research engine, not directly to the TradingView v2 MTF strategy.
