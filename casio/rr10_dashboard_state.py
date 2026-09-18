from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .regime_router_engine import (
    ENGINE_ID,
    RegimeRouterConfig,
    _bias,
    _indicators,
    _last_closed,
    _resample,
    load_price_csv,
    replay_engine,
)

STATE_SCHEMA = "casio.regime-router.rr10.state.v1"
RISK_PCT = 5.0


def latest_dashboard_state(
    data_path: str | Path,
    now: pd.Timestamp | None = None,
) -> dict:
    m15, source_tf = load_price_csv(data_path)
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    now = now.tz_localize("UTC") if now.tzinfo is None else now.tz_convert("UTC")

    m15 = m15[m15.index + pd.Timedelta(minutes=15) <= now]
    if len(m15) < 500:
        raise ValueError("RR10 dashboard state needs at least 500 completed M15 bars")

    cfg = RegimeRouterConfig()
    _, active = replay_engine(m15, cfg)

    h1 = _resample(m15, "1h")
    h4 = _resample(m15, "4h")
    h1i = _indicators(h1)
    h4i = _indicators(h4)

    close_time = m15.index[-1] + pd.Timedelta(minutes=15)
    close_ms = int(close_time.value // 1_000_000)
    h1_close = h1.index.view("int64") // 1_000_000 + 3_600_000
    h4_close = h4.index.view("int64") // 1_000_000 + 14_400_000
    hi1 = _last_closed(h1_close, close_ms)
    hi4 = _last_closed(h4_close, close_ms)
    if hi1 < 0 or hi4 < 0:
        raise ValueError("RR10 dashboard state could not resolve completed H1/H4 context")

    h1_bias = _bias(
        float(h1.iloc[hi1].close),
        float(h1i["e20"][hi1]),
        float(h1i["e50"][hi1]),
    )
    h4_bias = _bias(
        float(h4.iloc[hi4].close),
        float(h4i["e20"][hi4]),
        float(h4i["e50"][hi4]),
    )
    h4_adx = float(h4i["adx"][hi4])
    strong_trend = h1_bias != 0 and h1_bias == h4_bias and np.isfinite(h4_adx) and h4_adx >= 18.0

    age_minutes = max(0.0, (now - close_time).total_seconds() / 60.0)
    stale = age_minutes > 35.0

    active_payload = None
    portfolio = "WAIT"
    if active is not None:
        direction = int(active["direction"])
        portfolio = "LONG" if direction == 1 else "SHORT"
        active_payload = {
            "signal_id": str(active["signal_id"]),
            "direction": portfolio,
            "entry_time_utc": str(active["entry_time_utc"]),
            "signal_bar_open_utc": str(active["signal_bar_open_utc"]),
            "entry": float(active["entry"]),
            "stop": float(active["stop"]),
            "target": float(active["target"]),
            "rr": float(active["rr"]),
            "support": int(active["support"]),
            "align_count": int(active["align_count"]),
            "router_mode": str(active["router_mode"]),
        }

    return {
        "schema": STATE_SCHEMA,
        "engine": ENGINE_ID,
        "build": "RR10-XD1",
        "generated_at_utc": now.isoformat(),
        "symbol": "XAUUSD",
        "timeframe": "M15",
        "portfolio": portfolio,
        "router_mode": "TREND" if strong_trend else "MIXED",
        "h1_bias": int(h1_bias),
        "h4_bias": int(h4_bias),
        "h4_adx": h4_adx if np.isfinite(h4_adx) else None,
        "target_r": float(cfg.target_r),
        "risk_pct": RISK_PCT,
        "active_signal": active_payload,
        "last_m15_open_utc": m15.index[-1].isoformat(),
        "last_m15_close_utc": close_time.isoformat(),
        "data_age_minutes": round(age_minutes, 2),
        "stale": stale,
        "feed_adapter": f"{source_tf}->M15" if source_tf != "M15" else "M15",
        "data_source": "Dukascopy XAUUSD bid feed -> canonical RR10",
        "execution_source": "FxPro/cTrader live quote overlay when available",
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Build cross-device RR10 dashboard state")
    p.add_argument("--data", default="data/xauusd_m5.csv")
    p.add_argument("--output", default="tmp/rr10-state.json")
    args = p.parse_args()

    state = latest_dashboard_state(args.data)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(state, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    print(json.dumps(state, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
