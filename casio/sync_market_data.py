from __future__ import annotations

import argparse
import io
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

REQUIRED = ["timestamp", "open", "high", "low", "close"]
OUTPUT_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def _normalise(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    missing = [c for c in REQUIRED if c not in frame.columns]
    if missing:
        raise ValueError(f"market CSV missing columns: {', '.join(missing)}")

    if "volume" not in frame.columns:
        frame["volume"] = 0.0

    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    for col in ["open", "high", "low", "close", "volume"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")

    frame = frame.dropna(subset=["timestamp", "open", "high", "low", "close"])
    frame["volume"] = frame["volume"].fillna(0.0)
    frame = frame[OUTPUT_COLUMNS]
    frame = frame.sort_values("timestamp").drop_duplicates("timestamp", keep="last")

    bad = (frame["high"] < frame[["open", "close", "low"]].max(axis=1)) | (
        frame["low"] > frame[["open", "close", "high"]].min(axis=1)
    )
    if bad.any():
        raise ValueError(f"market CSV contains {int(bad.sum())} invalid OHLC rows")
    return frame


def fetch_csv(url: str) -> pd.DataFrame:
    request = Request(url, headers={"User-Agent": "CASIO-GitHub-Sync/2"})
    with urlopen(request, timeout=30) as response:
        raw = response.read()
        content_type = response.headers.get("Content-Type", "")
        if response.status != 200:
            raise RuntimeError(f"market endpoint returned HTTP {response.status}")
        if b"\"ok\":false" in raw[:500] or "application/json" in content_type.lower():
            raise RuntimeError("market endpoint did not return CSV: " + raw[:500].decode("utf-8", errors="replace"))
    if not raw.strip():
        raise RuntimeError("market endpoint returned an empty body")
    return _normalise(pd.read_csv(io.BytesIO(raw)))


def load_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(f"market file missing or empty: {path}")
    return _normalise(pd.read_csv(path))


def merge_frame(remote: pd.DataFrame, output: str | Path) -> tuple[int, int, int]:
    output = Path(output)
    old_count = 0

    if output.exists() and output.stat().st_size > 0:
        local = _normalise(pd.read_csv(output))
        old_count = len(local)
        merged = _normalise(pd.concat([local, remote], ignore_index=True))
    else:
        merged = remote

    output.parent.mkdir(parents=True, exist_ok=True)
    serial = merged.copy()
    serial["timestamp"] = serial["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    serial.to_csv(output, index=False)
    return old_count, len(remote), len(merged)


def sync_url(url: str, output: str | Path) -> tuple[int, int, int]:
    return merge_frame(fetch_csv(url), output)


def sync_file(source: str | Path, output: str | Path) -> tuple[int, int, int]:
    return merge_frame(load_csv(source), output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge XAUUSD M5 market data into data/xauusd_m5.csv")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="Remote market CSV endpoint")
    source.add_argument("--file", help="Local market CSV file, e.g. Dukascopy download")
    parser.add_argument("--output", default="data/xauusd_m5.csv")
    args = parser.parse_args()

    if args.url:
        before, received, after = sync_url(args.url, args.output)
        source_name = args.url
    else:
        before, received, after = sync_file(args.file, args.output)
        source_name = args.file

    print(
        f"CASIO M5 sync: source={source_name} local_before={before} "
        f"received={received} merged={after} added={max(0, after-before)}"
    )


if __name__ == "__main__":
    main()
