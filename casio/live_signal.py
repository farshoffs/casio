from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .v3_core import load_m5_csv
from .v3_m5_engine import V3M5Config, prepare_m5_features, replay_execution, signals_for_m5_features


def _bias(value: int) -> str:
    return "bullish" if value == 1 else "bearish" if value == -1 else "neutral"


def latest_signal(
    data_path: str | Path,
    max_age_minutes: int = 35,
    now: pd.Timestamp | None = None,
) -> dict | None:
    """Return the newest executable CASIO v3 M5 entry that is still fresh.

    This replays the same one-position-at-a-time + cooldown policy used by the
    canonical Pine FAST/BACKTEST scripts, so email signals follow the same entry
    stream rather than every raw setup candidate.
    """
    m5 = load_m5_csv(data_path)
    features = prepare_m5_features(m5)
    cfg = V3M5Config()
    raw = signals_for_m5_features(features, cfg)
    executed = replay_execution(m5, raw, cfg)
    if executed.empty:
        return None

    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    if now.tzinfo is None:
        now = now.tz_localize("UTC")
    else:
        now = now.tz_convert("UTC")

    eligible = executed[pd.to_datetime(executed["entry_time"], utc=True) <= now].copy()
    if eligible.empty:
        return None

    row = eligible.iloc[-1]
    entry_time = pd.Timestamp(row["entry_time"])
    if entry_time.tzinfo is None:
        entry_time = entry_time.tz_localize("UTC")
    else:
        entry_time = entry_time.tz_convert("UTC")
    age_minutes = (now - entry_time).total_seconds() / 60.0
    if age_minutes < 0 or age_minutes > max_age_minutes:
        return None

    bar_open = pd.Timestamp(row["signal_bar"])
    direction = int(row["direction"])
    mode = str(row["mode"])
    required_score = int(round(float(row["required_score"]))) if pd.notna(row["required_score"]) else 0
    required_rr = round(float(row["required_rr"]), 2) if pd.notna(row["required_rr"]) else 0.0

    payload = {
        "schema": "casio.tv.v3",
        "event": "signal",
        "symbol": "DUKASCOPY:XAUUSD",
        "ticker": "XAUUSD",
        "timeframe": "5",
        "bar_time": int(bar_open.timestamp() * 1000),
        "mode": mode.lower(),
        "regime": str(row["regime"]),
        "session": str(row["session"]),
        "playbook": str(row["playbook"]),
        "session_policy": "m5_canonical",
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
        "m5_bias": _bias(int(row["m5_bias"])),
        "m5_rsi": round(float(row["m5_rsi"]), 2),
        "source": "casio-v3-m5-canonical-python-dukascopy",
        "entry_time_utc": entry_time.isoformat(),
    }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the latest executable CASIO v3 M5-native entry from Dukascopy M5 data"
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
        print("CASIO live: no fresh executable M5 signal")
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
