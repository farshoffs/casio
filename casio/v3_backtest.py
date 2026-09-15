from __future__ import annotations

import math
import numpy as np
import pandas as pd

from .v3_core import V3Config


def backtest_signals(m5: pd.DataFrame, signals: pd.DataFrame, cfg: V3Config,
                     start: pd.Timestamp | None = None, end: pd.Timestamp | None = None) -> pd.DataFrame:
    sig = signals[signals.valid].copy()
    if start is not None:
        sig = sig[sig.entry_time >= start]
    if end is not None:
        sig = sig[sig.entry_time < end]
    cols = [
        "signal_bar", "entry_time", "exit_time", "mode", "direction", "score", "entry", "stop", "target",
        "planned_rr", "gross_r", "cost_r", "net_r", "exit_reason", "regime", "session", "playbook",
        "required_score", "required_rr",
    ]
    if sig.empty:
        return pd.DataFrame(columns=cols)

    idx, rows, busy_until = m5.index, [], None
    for bar_time, s in sig.iterrows():
        entry_time = pd.Timestamp(s["entry_time"])
        if busy_until is not None and entry_time <= busy_until:
            continue
        pos = idx.searchsorted(entry_time, side="left")
        if pos >= len(idx):
            continue
        direction, stop, target, risk = int(s["direction"]), float(s["stop"]), float(s["target"]), float(s["risk_distance"])
        if not np.isfinite(risk) or risk <= 0:
            continue
        exit_price = exit_time = reason = None
        for j in range(pos, len(idx)):
            t = idx[j]
            if end is not None and t >= end:
                break
            lo, hi = float(m5.iloc[j].low), float(m5.iloc[j].high)
            if direction == 1:
                hit_stop, hit_target = lo <= stop, hi >= target
            else:
                hit_stop, hit_target = hi >= stop, lo <= target
            if hit_stop and hit_target:
                exit_price, reason = stop, "stop_same_bar"
            elif hit_stop:
                exit_price, reason = stop, "stop"
            elif hit_target:
                exit_price, reason = target, "target"
            if exit_price is not None:
                exit_time = t + pd.Timedelta(minutes=5)
                break
        if exit_price is None:
            continue
        gross_r = (exit_price - float(s["entry"])) / risk if direction == 1 else (float(s["entry"]) - exit_price) / risk
        cost_r = (float(s["entry"]) * cfg.round_trip_cost_bps / 10000.0) / risk
        rows.append({
            "signal_bar": bar_time,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "mode": s["mode"],
            "direction": direction,
            "score": float(s["score"]),
            "entry": float(s["entry"]),
            "stop": stop,
            "target": target,
            "planned_rr": float(s["rr"]),
            "gross_r": gross_r,
            "cost_r": cost_r,
            "net_r": gross_r - cost_r,
            "exit_reason": reason,
            "regime": s["regime"],
            "session": s["session"],
            "playbook": s.get("playbook", "UNKNOWN"),
            "required_score": float(s.get("required_score", np.nan)),
            "required_rr": float(s.get("required_rr", np.nan)),
        })
        busy_until = exit_time
    return pd.DataFrame(rows, columns=cols)


def metrics(trades: pd.DataFrame, r_col: str = "net_r") -> dict:
    if trades.empty:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": None,
            "expectancy_r": None,
            "profit_factor": None,
            "max_drawdown_r": None,
        }
    r = pd.to_numeric(trades[r_col], errors="coerce").dropna()
    if r.empty:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": None,
            "expectancy_r": None,
            "profit_factor": None,
            "max_drawdown_r": None,
        }
    wins, losses = int((r > 0).sum()), int((r < 0).sum())
    gw, gl = float(r[r > 0].sum()), float(-r[r < 0].sum())
    pf = gw / gl if gl > 0 else (999.0 if gw > 0 else None)
    curve = r.cumsum()
    dd = curve.cummax() - curve
    return {
        "trades": int(len(r)),
        "wins": wins,
        "losses": losses,
        "win_rate": float(wins * 100 / len(r)),
        "expectancy_r": float(r.mean()),
        "profit_factor": float(pf) if pf is not None else None,
        "max_drawdown_r": float(dd.max()) if len(dd) else 0.0,
    }


def year_stability(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {"years": 0, "positive_year_ratio": None, "yearly": {}}
    x = trades.copy()
    x["year"] = pd.to_datetime(x.entry_time, utc=True).dt.year
    yearly = {str(int(y)): metrics(g) for y, g in x.groupby("year")}
    exps = [m["expectancy_r"] for m in yearly.values() if m["expectancy_r"] is not None]
    return {
        "years": len(exps),
        "positive_year_ratio": sum(v > 0 for v in exps) / len(exps) if exps else None,
        "yearly": yearly,
    }


def mode_stability(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {"positive_mode_ratio": None, "modes": {}}
    modes = {str(k): metrics(g) for k, g in trades.groupby("mode")}
    exps = [m["expectancy_r"] for m in modes.values() if m["expectancy_r"] is not None]
    return {
        "positive_mode_ratio": sum(v > 0 for v in exps) / len(exps) if exps else None,
        "modes": modes,
    }
