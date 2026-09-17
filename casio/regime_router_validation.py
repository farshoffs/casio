from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import math

import pandas as pd

from .v3_core import load_m5_csv
from .m15_all_families_2026 import prepare
from .multi_technique_2026 import _build_streams, route_regime, PRIORITY

START_RM = 100.0
RISK_FRACTION = 0.05


def _signals(streams: dict[str, pd.DataFrame], start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    parts = []
    for name, t in streams.items():
        if t.empty:
            continue
        x = t.copy()
        x["entry_time"] = pd.to_datetime(x.entry_time, utc=True)
        x["exit_time"] = pd.to_datetime(x.exit_time, utc=True)
        x = x[(x.entry_time >= start) & (x.entry_time < end)].copy()
        if x.empty:
            continue
        x["priority"] = PRIORITY[name]
        parts.append(x)
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True).sort_values(
        ["entry_time", "priority", "technique"]
    ).reset_index(drop=True)


def compound(trades: pd.DataFrame, start_rm: float = START_RM) -> tuple[pd.DataFrame, dict]:
    x = trades.sort_values("entry_time").copy()
    bal = float(start_rm)
    low = bal
    peak = bal
    max_dd = 0.0
    befores, afters, pnls = [], [], []
    for r in pd.to_numeric(x.get("net_r", pd.Series(dtype=float)), errors="coerce").fillna(0.0):
        before = bal
        pnl = bal * RISK_FRACTION * float(r)
        bal = max(0.0, bal + pnl)
        peak = max(peak, bal)
        low = min(low, bal)
        max_dd = max(max_dd, (peak - bal) / peak * 100.0 if peak > 0 else 0.0)
        befores.append(before)
        afters.append(bal)
        pnls.append(pnl)
    if len(x):
        x["balance_before_rm"] = befores
        x["pnl_rm"] = pnls
        x["balance_after_rm"] = afters
    return x, {
        "ending_balance_rm": float(bal),
        "lowest_balance_rm": float(low),
        "max_drawdown_pct": float(max_dd),
    }


def monthly(trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, start_rm: float = START_RM) -> pd.DataFrame:
    x = trades.copy()
    x["entry_time"] = pd.to_datetime(x.entry_time, utc=True)
    x = x[(x.entry_time >= start) & (x.entry_time < end)].copy()
    x, _ = compound(x, start_rm)
    periods = pd.period_range(
        start=start.tz_localize(None).to_period("M"),
        end=(end - pd.Timedelta(seconds=1)).tz_localize(None).to_period("M"),
        freq="M",
    )
    rows = []
    prev = float(start_rm)
    for p in periods:
        a = pd.Timestamp(p.start_time, tz="UTC")
        b = pd.Timestamp((p + 1).start_time, tz="UTC")
        z = x[(x.entry_time >= a) & (x.entry_time < b)] if not x.empty else x
        ending = float(z.balance_after_rm.iloc[-1]) if len(z) else prev
        rows.append({
            "month": str(p),
            "trades": int(len(z)),
            "pnl_rm": ending - prev,
            "ending_balance_rm": ending,
        })
        prev = ending
    return pd.DataFrame(rows)


def summarize(trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, start_rm: float = START_RM) -> dict:
    x = trades.copy()
    if x.empty:
        mon = monthly(x, start, end, start_rm)
        return {
            "trades": 0,
            "trades_per_30d": 0.0,
            "min_completed_month_trades": 0,
            "ending_balance_rm": start_rm,
            "lowest_balance_rm": start_rm,
            "max_drawdown_pct": 0.0,
            "passes_frequency": False,
            "passes_growth": False,
            "requested_fit": False,
        }
    x["entry_time"] = pd.to_datetime(x.entry_time, utc=True)
    x = x[(x.entry_time >= start) & (x.entry_time < end)].copy()
    _, eq = compound(x, start_rm)
    mon = monthly(x, start, end, start_rm)
    min_month = int(mon.trades.min()) if len(mon) else 0
    days = max((end - start).total_seconds() / 86400.0, 1e-9)
    pass_freq = min_month >= 8
    pass_growth = eq["ending_balance_rm"] > start_rm
    return {
        "trades": int(len(x)),
        "trades_per_30d": float(len(x) * 30.0 / days),
        "min_completed_month_trades": min_month,
        **eq,
        "passes_frequency": bool(pass_freq),
        "passes_growth": bool(pass_growth),
        "requested_fit": bool(pass_freq and pass_growth),
    }


def run_validation(data: Path, start: pd.Timestamp, end: pd.Timestamp, out: Path, warmup_days: int = 120) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    m5 = load_m5_csv(data)
    warmup = start - pd.Timedelta(days=warmup_days)
    m5 = m5[(m5.index >= warmup) & (m5.index < end)].copy()
    if m5.empty or m5.index.min() > start - pd.Timedelta(days=30) or m5.index.max() < end - pd.Timedelta(days=3):
        raise RuntimeError(
            f"Insufficient data coverage for {start.date()}->{end.date()}: "
            f"min={m5.index.min() if len(m5) else None}, max={m5.index.max() if len(m5) else None}"
        )

    m15, f = prepare(m5)
    streams = _build_streams(m15, f)
    sig = _signals(streams, start, end)
    routed = route_regime(sig, f)
    routed["entry_time"] = pd.to_datetime(routed.entry_time, utc=True)
    routed["exit_time"] = pd.to_datetime(routed.exit_time, utc=True)
    routed = routed[(routed.entry_time >= start) & (routed.entry_time < end)].copy()

    s = summarize(routed, start, end)
    routed_eq, _ = compound(routed)
    mon = monthly(routed, start, end)
    contrib = (
        routed.technique.value_counts().rename_axis("technique").reset_index(name="trades")
        if not routed.empty else pd.DataFrame(columns=["technique", "trades"])
    )

    routed_eq.to_csv(out / "trades.csv", index=False)
    mon.to_csv(out / "monthly.csv", index=False)
    contrib.to_csv(out / "contributions.csv", index=False)

    lines = [
        f"# Frozen CASIO Regime Router — {start.date()} to {end.date()}",
        "",
        "## Method",
        "",
        f"- Source file: `{data}`.",
        "- Exact frozen Regime Router architecture from the 2026 ensemble research; no parameter tuning in this run.",
        f"- Test window: **{start.isoformat()} through {end.isoformat()}**.",
        "- Start **RM100**, risk **5% of current balance** on each accepted trade.",
        "- One shared position at a time; source techniques keep their frozen 2R/3R/4R logic.",
        "- Same research replay assumptions and 1 bp round-trip cost embedded in the source trade streams.",
        "- Requirement: ending balance > RM100 and at least 8 trades in every tested calendar month.",
        "",
        "## Result",
        "",
        pd.DataFrame([s]).to_markdown(index=False),
        "",
        "## Monthly equity",
        "",
        mon.to_markdown(index=False) if len(mon) else "No trades.",
        "",
        "## Technique contribution",
        "",
        contrib.to_markdown(index=False) if len(contrib) else "No trades.",
        "",
    ]
    (out / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    return s


def _ts(value: str) -> pd.Timestamp:
    x = pd.Timestamp(value)
    return x.tz_localize("UTC") if x.tzinfo is None else x.tz_convert("UTC")


def main() -> None:
    ap = ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--warmup-days", type=int, default=120)
    args = ap.parse_args()

    s = run_validation(Path(args.data), _ts(args.start), _ts(args.end), Path(args.out), args.warmup_days)
    print(s)


if __name__ == "__main__":
    main()
