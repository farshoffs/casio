from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .audit import audit_trades
from .backtest import rolling_report, run_backtest


def load_ohlc(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"timestamp", "open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").drop_duplicates("timestamp").set_index("timestamp")
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["open", "high", "low", "close"])


def safe_json(obj: dict) -> str:
    def clean(v):
        if isinstance(v, dict):
            return {k: clean(x) for k, x in v.items()}
        if isinstance(v, list):
            return [clean(x) for x in v]
        if isinstance(v, float) and (v == float("inf") or v == float("-inf")):
            return None
        return v
    return json.dumps(clean(obj), indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="CASIO XAUUSD research engine")
    parser.add_argument("--data", default="data/xauusd.csv", help="OHLC CSV input")
    parser.add_argument("--max-bars", type=int, default=48, help="Maximum bars allowed per simulated trade")
    parser.add_argument("--output", default="reports", help="Output directory")
    args = parser.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    df = load_ohlc(args.data)
    trades = run_backtest(df, max_bars_per_trade=args.max_bars)
    trades.to_csv(out / "trades.csv", index=False)

    rolling = rolling_report(trades, 100)
    audit = audit_trades(trades)
    (out / "backtest-100.json").write_text(safe_json(rolling), encoding="utf-8")
    (out / "audit.json").write_text(safe_json(audit), encoding="utf-8")

    print("CASIO backtest complete")
    print(safe_json({"backtest": rolling, "audit": audit}))


if __name__ == "__main__":
    main()
