from __future__ import annotations

from pathlib import Path
import pandas as pd

from .v3_core import load_m5_csv
from . import m15_all_families_2026 as base
from . import multi_technique_2026 as ensemble

DATA = Path("data/xauusd_m5_secondary_octafx_mt4.csv")
OUT = Path("reports/regime-router-2024-2025")
WARMUP = pd.Timestamp("2023-10-01", tz="UTC")
DATA_END = pd.Timestamp("2026-01-30T23:59:59Z")


def set_window(start: pd.Timestamp, end: pd.Timestamp) -> None:
    # Rebind only the period boundaries used by the frozen 2026 research code.
    # Strategy logic, router ordering, thresholds, targets, costs and risk stay unchanged.
    base.START = start
    base.END = end
    ensemble.START = start
    ensemble.END = end


def run_window(m15: pd.DataFrame, f: pd.DataFrame, streams: dict[str, pd.DataFrame], start: pd.Timestamp, end: pd.Timestamp, label: str):
    set_window(start, end)
    signals = ensemble._all_signals(streams, end)
    trades = ensemble.route_regime(signals, f)
    summary = ensemble._compound_summary(trades, end)
    monthly = base._monthly(trades, end)
    if not monthly.empty:
        monthly.insert(0, "window", label)
    z = base._slice(trades, start, end)
    if not z.empty:
        z, _, _ = base._compound(z)
        z.insert(0, "window", label)
    return summary, monthly, z


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    m5 = load_m5_csv(DATA)
    m5 = m5[(m5.index >= WARMUP) & (m5.index <= DATA_END)].copy()
    if m5.empty or m5.index.min() > pd.Timestamp("2023-12-01", tz="UTC") or m5.index.max() < pd.Timestamp("2025-12-29", tz="UTC"):
        raise RuntimeError("Secondary feed lacks enough 2024-2025 coverage")

    # Build all source techniques once over the full warmup+test data.
    m15, f = base.prepare(m5)
    streams = ensemble._build_streams(m15, f)

    windows = [
        ("2024", pd.Timestamp("2024-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC")),
        ("2025", pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-01-01", tz="UTC")),
        ("2024-2025 continuous", pd.Timestamp("2024-01-01", tz="UTC"), pd.Timestamp("2026-01-01", tz="UTC")),
    ]

    rows = []
    monthly_parts = []
    trade_parts = []
    for label, start, end in windows:
        s, mo, tr = run_window(m15, f, streams, start, end, label)
        rows.append({"window": label, **s})
        if not mo.empty:
            monthly_parts.append(mo)
        if not tr.empty:
            trade_parts.append(tr)

    result = pd.DataFrame(rows)
    result.to_csv(OUT / "comparison.csv", index=False)
    if monthly_parts:
        pd.concat(monthly_parts, ignore_index=True).to_csv(OUT / "monthly.csv", index=False)
    if trade_parts:
        pd.concat(trade_parts, ignore_index=True).to_csv(OUT / "trades.csv", index=False)

    lines = [
        "# Frozen CASIO Regime Router — 2024 & 2025",
        "",
        "## Method",
        "",
        "- Frozen exact Regime Router architecture from the 2026 ensemble test; no tuning on 2024/2025.",
        "- Source: independent secondary XAUUSD M5 feed, resampled/processed identically to the 2026 research engine.",
        "- Each annual test starts at **RM100** independently.",
        "- Risk **5% of current account balance** per accepted trade.",
        "- One shared portfolio position at a time.",
        "- Same **1 bp round-trip cost**, stop-first same-bar handling, source-technique 2R/3R/4R target logic.",
        "- Requirement: **at least 8 filled trades in every completed month** and ending balance above RM100.",
        "- The continuous 2024->2025 row is an additional path test starting RM100 on 2024-01-01 without resetting in 2025.",
        "",
        "## Results",
        "",
        result.to_markdown(index=False),
        "",
        "## Monthly equity",
        "",
    ]
    if monthly_parts:
        lines.append(pd.concat(monthly_parts, ignore_index=True).to_markdown(index=False))
    else:
        lines.append("No monthly rows.")
    lines += [
        "",
        "## Interpretation",
        "",
        "The router passes a window only when RM100 grows and every completed month contains at least 8 accepted trades. These are frozen-rule validation replays, not a new parameter search.",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
