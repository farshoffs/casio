from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .regime_router_engine import latest_signal as _latest_signal


def latest_signal(
    data_path: str | Path,
    max_age_minutes: int = 12,
    now: pd.Timestamp | None = None,
) -> dict | None:
    """Return the newest fresh signal from the single canonical RR10 engine."""
    return _latest_signal(data_path, max_age_minutes=max_age_minutes, now=now)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the canonical CASIO RR10 Regime Router")
    parser.add_argument("--data", default="data/xauusd_m5.csv")
    parser.add_argument("--output", default="tmp/casio_live_signal.json")
    parser.add_argument("--max-age-minutes", type=int, default=12)
    args = parser.parse_args()

    payload = latest_signal(args.data, max_age_minutes=args.max_age_minutes)
    output = Path(args.output)
    if output.exists():
        output.unlink()

    if payload is None:
        print("CASIO RR10 live: no fresh canonical M15 signal")
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
