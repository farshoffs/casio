from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .v3_core import V3Config, load_m5_csv, prepare_features
from .v3_strategy import signals_for_config


def _bias(value: int) -> str:
    return "bullish" if value == 1 else "bearish" if value == -1 else "neutral"


def latest_signal(
    data_path: str | Path,
    max_age_minutes: int = 35,
    now: pd.Timestamp | None = None,
) -> dict | None:
    m5 = load_m5_csv(data_path)
    features = prepare_features(m5)
    cfg = V3Config()
    signals = signals_for_config(features, cfg)
    if signals.empty:
        return None

    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    if now.tzinfo is None:
        now = now.tz_localize("UTC")
    else:
        now = now.tz_convert("UTC")

    eligible = signals[signals["entry_time"] <= now].copy()
    if eligible.empty:
        return None

    row = eligible.iloc[-1]
    bar_open = eligible.index[-1]
    entry_time = pd.Timestamp(row["entry_time"])
    age_minutes = (now - entry_time).total_seconds() / 60.0

    if not bool(row["valid"]) or age_minutes < 0 or age_minutes > max_age_minutes:
        return None

    direction = int(row["direction"])
    mode = str(row["mode"])
    if mode == "SCALPING":
        required_score = cfg.scalp_min_score
        required_rr = cfg.scalp_min_rr
    else:
        required_score = int(round(float(row["required_score"])))
        required_rr = round(float(row["required_rr"]), 2)

    payload = {
        "schema": "casio.tv.v3",
        "event": "signal",
        "symbol": "DUKASCOPY:XAUUSD",
        "ticker": "XAUUSD",
        "timeframe": "15",
        "bar_time": int(pd.Timestamp(bar_open).timestamp() * 1000),
        "mode": mode.lower(),
        "regime": str(row["regime"]),
        "session": str(row["session"]),
        "playbook": str(row["playbook"]),
        "session_policy": cfg.session_policy,
        "required_score": required_score,
        "required_rr": required_rr,
        "direction": "long" if direction == 1 else "short",
        "score": int(round(float(row["score"]))),
        "entry": round(float(row["entry"]), 4),
        "stop": round(float(row["stop"]), 4),
        "target": round(float(row["target"]), 4),
        "rr": round(float(row["rr"]), 4),
        "h4_bias": _bias(int(row["h4_bias"])),
        "h1_bias": _bias(int(row["h1_bias"])),
        "m15_adx": round(float(row["m15_adx"]), 4),
        "source": "casio-v3-python-dukascopy",
        "entry_time_utc": entry_time.isoformat(),
    }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the latest closed CASIO v3 M15 setup from M5 data"
    )
    parser.add_argument("--data", default="data/xauusd_m5.csv")
    parser.add_argument("--output", default="tmp/casio_live_signal.json")
    parser.add_argument("--max-age-minutes", type=int, default=35)
    args = parser.parse_args()

    payload = latest_signal(args.data, max_age_minutes=args.max_age_minutes)
    output = Path(args.output)
    if output.exists():
        output.unlink()

    if payload is None:
        print("CASIO live: no fresh valid signal")
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
