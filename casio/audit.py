from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .backtest import metrics
from .config import AuditConfig


def _delta(current: dict, previous: dict) -> dict:
    return {
        "win_rate_pct": round(current["win_rate_pct"] - previous["win_rate_pct"], 2),
        "expectancy_r": round(current["expectancy_r"] - previous["expectancy_r"], 4),
        "profit_factor": round(current["profit_factor"] - previous["profit_factor"], 3)
        if current["profit_factor"] != float("inf") and previous["profit_factor"] != float("inf")
        else None,
    }


def audit_trades(trades: pd.DataFrame, cfg: AuditConfig = AuditConfig()) -> dict:
    n = cfg.rolling_trades
    current = trades.tail(n).copy()
    previous = trades.iloc[max(0, len(trades) - 2 * n): max(0, len(trades) - n)].copy()

    report = {
        "window_size": n,
        "current": metrics(current),
        "previous": metrics(previous),
        "delta": {},
        "status": "INSUFFICIENT_DATA",
        "findings": [],
        "recommendation": "Collect more closed trades before changing strategy parameters.",
        "modes": {},
    }

    if len(current) < cfg.min_trades_for_audit:
        return report

    report["delta"] = _delta(report["current"], report["previous"]) if len(previous) >= cfg.min_trades_for_audit else {}
    findings: list[str] = []
    status = "HEALTHY"

    if report["current"]["profit_factor"] < cfg.critical_profit_factor:
        status = "CRITICAL"
        findings.append(f"Profit factor below {cfg.critical_profit_factor:.2f}.")
    if report["current"]["expectancy_r"] <= cfg.critical_expectancy_r:
        status = "CRITICAL"
        findings.append("Rolling expectancy is non-positive.")

    if report["delta"]:
        if report["delta"]["win_rate_pct"] <= -cfg.warn_win_rate_drop_pct:
            if status != "CRITICAL":
                status = "WARNING"
            findings.append(f"Win rate dropped {abs(report['delta']['win_rate_pct']):.2f} percentage points versus the previous window.")
        if report["delta"]["expectancy_r"] <= -cfg.warn_expectancy_drop_r:
            if status != "CRITICAL":
                status = "WARNING"
            findings.append(f"Expectancy dropped {abs(report['delta']['expectancy_r']):.3f}R versus the previous window.")

    for mode in ["intraday", "scalping"]:
        mode_current = current[current["mode"] == mode]
        mode_previous = previous[previous["mode"] == mode]
        mode_metrics = metrics(mode_current)
        mode_prev_metrics = metrics(mode_previous)
        report["modes"][mode] = {
            "current": mode_metrics,
            "previous": mode_prev_metrics,
            "delta": _delta(mode_metrics, mode_prev_metrics) if len(mode_current) and len(mode_previous) else {},
        }

    report["status"] = status
    report["findings"] = findings or ["No material degradation detected in the rolling sample."]
    if status == "HEALTHY":
        report["recommendation"] = "Keep parameters unchanged; continue collecting forward results."
    elif status == "WARNING":
        report["recommendation"] = "Review the weaker mode and market regime before proposing parameter changes; do not auto-deploy changes."
    else:
        report["recommendation"] = "Pause strategy promotion and investigate regime/logic degradation before any live use."
    return report


def write_audit(report: dict, path: str = "reports/audit.json") -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
