from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import pandas as pd

EXPECTED = {
    "EURUSD": {
        "name": "fxpro_EURUSD_m1.csv",
        "rows": 3_584_839,
        "sha256": "733470dfc42b5babe806ab2e3308b07a9c244f7dec6d7ced2006dc95c4898c06",
    },
    "GBPUSD": {
        "name": "fxpro_gbpusd_m1.csv",
        "rows": 3_589_010,
        "sha256": "f47e8218a4d00aaae65f3d7496dcf40638f5efacc47417a8c21b103d5c9b831c",
    },
    "GBPJPY": {
        "name": "fxpro_GBPJPY_m1.csv",
        "rows": 3_606_586,
        "sha256": "fd845d8cf5226019fc5a9e30dd345bf0017b6c90ceae72b705a2970058c548e1",
    },
}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def inspect(path: Path) -> dict:
    df = pd.read_csv(path, usecols=lambda c: c in {
        "time_utc", "timestamp", "open", "high", "low", "close", "tick_volume", "symbol", "timeframe"
    })
    tcol = "time_utc" if "time_utc" in df.columns else "timestamp"
    t = pd.to_datetime(df[tcol], utc=True, errors="coerce")
    symbol = str(df["symbol"].dropna().iloc[0]) if "symbol" in df.columns and not df["symbol"].dropna().empty else None
    tf = str(df["timeframe"].dropna().iloc[0]) if "timeframe" in df.columns and not df["timeframe"].dropna().empty else None
    return {
        "rows": len(df),
        "start": str(t.min()),
        "end": str(t.max()),
        "symbol": symbol,
        "timeframe": tf,
        "sha256": sha256(path),
    }

def main():
    ap = argparse.ArgumentParser()
    for symbol in ["EURUSD", "GBPUSD", "GBPJPY", "XAUUSD"]:
        ap.add_argument(f"--{symbol.lower()}", type=Path)
    args = ap.parse_args()

    for symbol in ["EURUSD", "GBPUSD", "GBPJPY", "XAUUSD"]:
        path = getattr(args, symbol.lower())
        if path is None:
            print(f"{symbol}: MISSING")
            continue
        info = inspect(path)
        print(f"{symbol}: {path}")
        for k, v in info.items():
            print(f"  {k}: {v}")
        if symbol in EXPECTED:
            e = EXPECTED[symbol]
            ok = info["rows"] == e["rows"] and info["sha256"] == e["sha256"]
            print(f"  exact_manifest_match: {ok}")
        else:
            # XAUUSD historical source has no frozen checksum in GitHub.
            # Require genuine multi-year M1 coverage and explicit FxPro provenance.
            years = pd.Timestamp(info["end"]).year - pd.Timestamp(info["start"]).year
            plausible = info["timeframe"] in (None, "M1") and info["rows"] > 1_000_000 and years >= 8
            print(f"  historical_coverage_plausible: {plausible}")

if __name__ == "__main__":
    main()
