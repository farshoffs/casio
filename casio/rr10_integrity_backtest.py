from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .regime_router_engine import RegimeRouterConfig, load_price_csv, replay_engine

START_EQUITY_RM = 100.0
RISK_FRACTION = 0.05
DEFAULT_RRS = (2.0, 3.0, 4.0, 5.0)


def _ts(value: str | None) -> pd.Timestamp | None:
    if not value:
        return None
    x = pd.Timestamp(value)
    return x.tz_localize("UTC") if x.tzinfo is None else x.tz_convert("UTC")


def _equity_curve(trades: pd.DataFrame, start_rm: float = START_EQUITY_RM) -> tuple[pd.DataFrame, dict]:
    x = trades.copy()
    bal = float(start_rm)
    peak = bal
    max_dd = 0.0
    before, pnl, after = [], [], []

    for r in pd.to_numeric(x.get("result_r", pd.Series(dtype=float)), errors="coerce").fillna(0.0):
        b = bal
        p = b * RISK_FRACTION * float(r)
        bal = max(0.0, b + p)
        peak = max(peak, bal)
        max_dd = max(max_dd, ((peak - bal) / peak * 100.0) if peak > 0 else 0.0)
        before.append(b)
        pnl.append(p)
        after.append(bal)

    if len(x):
        x["balance_before_rm"] = before
        x["pnl_rm"] = pnl
        x["balance_after_rm"] = after

    return x, {
        "ending_balance_rm": bal,
        "net_profit_rm": bal - start_rm,
        "max_drawdown_pct": max_dd,
    }


def _profit_factor(r: pd.Series) -> float:
    vals = pd.to_numeric(r, errors="coerce").dropna()
    gross_win = float(vals[vals > 0].sum())
    gross_loss = float(-vals[vals < 0].sum())
    return gross_win / gross_loss if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)


def _monthly(trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    periods = pd.period_range(
        start=start.tz_localize(None).to_period("M"),
        end=(end - pd.Timedelta(seconds=1)).tz_localize(None).to_period("M"),
        freq="M",
    )
    rows = []
    prev = START_EQUITY_RM
    for p in periods:
        a = pd.Timestamp(p.start_time, tz="UTC")
        b = pd.Timestamp((p + 1).start_time, tz="UTC")
        z = trades[(trades["entry_time"] >= a) & (trades["entry_time"] < b)].copy()
        z, eq = _equity_curve(z, prev)
        ending = eq["ending_balance_rm"]
        wins = int((pd.to_numeric(z.get("result_r"), errors="coerce") > 0).sum()) if len(z) else 0
        rows.append({
            "month": str(p),
            "trades": int(len(z)),
            "wins": wins,
            "win_rate_pct": (wins / len(z) * 100.0) if len(z) else 0.0,
            "pnl_rm": ending - prev,
            "ending_balance_rm": ending,
        })
        prev = ending
    return pd.DataFrame(rows)


def run_one(m15: pd.DataFrame, rr: float, start: pd.Timestamp, end: pd.Timestamp, out: Path) -> dict:
    events, active = replay_engine(m15, RegimeRouterConfig(target_r=float(rr)))

    if events.empty:
        trades = events.copy()
        trades["entry_time"] = pd.Series(dtype="datetime64[ns, UTC]")
    else:
        trades = events.copy()
        trades["entry_time"] = pd.to_datetime(trades["entry_time_utc"], utc=True)
        trades = trades[(trades["entry_time"] >= start) & (trades["entry_time"] < end)].copy()
        trades = trades.sort_values("entry_time").reset_index(drop=True)

    trades_eq, eq = _equity_curve(trades)
    result_r = pd.to_numeric(trades_eq.get("result_r", pd.Series(dtype=float)), errors="coerce")
    wins = int((result_r > 0).sum()) if len(trades_eq) else 0
    losses = int((result_r < 0).sum()) if len(trades_eq) else 0
    days = max((end - start).total_seconds() / 86400.0, 1e-9)
    monthly = _monthly(trades_eq, start, end)

    summary = {
        "engine": "RR10",
        "rr": float(rr),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "start_equity_rm": START_EQUITY_RM,
        "risk_pct": RISK_FRACTION * 100.0,
        "closed_trades": int(len(trades_eq)),
        "wins": wins,
        "losses": losses,
        "win_rate_pct": (wins / len(trades_eq) * 100.0) if len(trades_eq) else 0.0,
        "expectancy_r": float(result_r.mean()) if len(trades_eq) else 0.0,
        "profit_factor": _profit_factor(result_r),
        "trades_per_30d": float(len(trades_eq) * 30.0 / days),
        "min_month_trades": int(monthly["trades"].min()) if len(monthly) else 0,
        **eq,
        "open_trade_at_data_end": bool(active is not None),
    }

    tag = f"rr{int(rr) if float(rr).is_integer() else str(rr).replace('.', 'p')}"
    trades_eq.to_csv(out / f"{tag}_trades.csv", index=False)
    monthly.to_csv(out / f"{tag}_monthly.csv", index=False)
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description="Integrity backtest for the canonical CASIO RR10 engine")
    p.add_argument("--data", required=True)
    p.add_argument("--start", default="2026-01-01T00:00:00Z")
    p.add_argument("--end", default="")
    p.add_argument("--rr", nargs="+", type=float, default=list(DEFAULT_RRS))
    p.add_argument("--out", default="reports/regime-router-canonical/fxpro-integrity")
    args = p.parse_args()

    m15, source_tf = load_price_csv(args.data)
    if source_tf != "M15":
        raise SystemExit(f"Integrity test requires the supplied FxPro M15 file; detected {source_tf}")

    start = _ts(args.start)
    if start is None:
        raise SystemExit("--start is required")
    end = _ts(args.end)
    if end is None:
        end = m15.index.max() + pd.Timedelta(minutes=15)

    if m15.index.min() > start - pd.Timedelta(days=60):
        raise SystemExit(
            f"Need at least ~60 days of pre-start warmup. data starts {m15.index.min()}, test starts {start}"
        )
    if m15.index.max() + pd.Timedelta(minutes=15) < end:
        raise SystemExit(
            f"Data ends before requested test end: {m15.index.max() + pd.Timedelta(minutes=15)} < {end}"
        )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = [run_one(m15, rr, start, end, out) for rr in args.rr]
    summary = pd.DataFrame(rows)
    summary.to_csv(out / "summary.csv", index=False)
    (out / "summary.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

    lines = [
        "# RR10 FxPro M15 Integrity Backtest",
        "",
        f"- Source: {args.data}",
        f"- Detected timeframe: **{source_tf}**",
        f"- Window: **{start.isoformat()} -> {end.isoformat()}**",
        "- Start equity: **RM100**",
        "- Risk: **5% of current equity per closed trade**",
        "- Engine: **RR10 canonical**, one active trade at a time, stop-first on same-bar SL+TP.",
        "- R targets tested: **" + ", ".join(f"{x:g}R" for x in args.rr) + "**",
        "",
        "## Summary",
        "",
        summary.to_markdown(index=False),
        "",
    ]
    (out / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
