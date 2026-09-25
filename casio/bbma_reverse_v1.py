from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from casio import bbma_cleaner_robustness as base


# BBMA Reverse v1
# Research invariant: the frozen BBMA Cleaner Core is reused unchanged.
# The ONLY strategy-logic change is direction inversion at the accepted
# signal boundary:
#   original LONG  -> reversed SHORT
#   original SHORT -> reversed LONG
# Stop construction, risk filters, cadence, trade management, costs,
# entry timing, and all feature/context calculations remain unchanged.

_ORIGINAL_SIGNALS = base.signals


def reversed_signals(x, p):
    original_long, original_short, family = _ORIGINAL_SIGNALS(x, p)
    return original_short, original_long, family


def longest_streak(values):
    best = cur = 0
    for v in values:
        if v:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)


def add_equity(trades: pd.DataFrame, start_rm: float = 100.0, risk_pct: float = 0.05) -> pd.DataFrame:
    t = trades.sort_values("entry_time").copy()
    eq = float(start_rm)
    peak = eq
    befores, afters, dds = [], [], []
    for rr in t["r"].astype(float):
        befores.append(eq)
        eq *= 1.0 + risk_pct * rr
        afters.append(eq)
        peak = max(peak, eq)
        dds.append((peak - eq) / peak * 100.0 if peak > 0 else np.nan)
    t["equity_before_rm"] = befores
    t["equity_after_rm"] = afters
    t["drawdown_pct"] = dds
    return t


def monthly_report(t: pd.DataFrame, start: str | None, end: str | None, start_rm: float = 100.0):
    if t.empty:
        return pd.DataFrame()

    tt = t.copy()
    tt["month"] = tt["entry_time"].dt.to_period("M").astype(str)

    if start:
        first = pd.Timestamp(start, tz="UTC").to_period("M")
    else:
        first = tt["entry_time"].min().to_period("M")
    if end:
        end_ts = pd.Timestamp(end, tz="UTC") - pd.Timedelta(microseconds=1)
        last = end_ts.to_period("M")
    else:
        last = tt["entry_time"].max().to_period("M")

    months = pd.period_range(first, last, freq="M")
    rows = []
    running_eq = float(start_rm)

    for m in months:
        ms = str(m)
        g = tt[tt["month"] == ms].sort_values("entry_time")
        opening = running_eq
        peak = opening
        mdd = 0.0

        for rr in g["r"].astype(float):
            running_eq *= 1.0 + 0.05 * rr
            peak = max(peak, running_eq)
            if peak > 0:
                mdd = max(mdd, (peak - running_eq) / peak * 100.0)

        if g.empty:
            rows.append(dict(
                month=ms, trades=0, wins=0, losses=0, positive_rate=0.0,
                avg_r=0.0, net_r=0.0, pf=0.0, stop=0, tp2=0, reverse_exit=0,
                longs=0, shorts=0, max_win_streak=0, max_loss_streak=0,
                opening_rm=opening, ending_rm=running_eq, return_pct=0.0,
                max_dd_pct=0.0
            ))
            continue

        r = g["r"].astype(float)
        wins = r > 0
        losses = r <= 0
        gp = r[r > 0].sum()
        gl = -r[r < 0].sum()
        pf = float(gp / gl) if gl > 0 else float("inf")
        reasons = g["exit_reason"].value_counts()

        rows.append(dict(
            month=ms,
            trades=int(len(g)),
            wins=int(wins.sum()),
            losses=int(losses.sum()),
            positive_rate=float(wins.mean() * 100.0),
            avg_r=float(r.mean()),
            net_r=float(r.sum()),
            pf=pf,
            stop=int(reasons.get("STOP", 0)),
            tp2=int(reasons.get("TP2", 0)),
            reverse_exit=int(reasons.get("REVERSE", 0)),
            longs=int((g["side"] == 1).sum()),
            shorts=int((g["side"] == -1).sum()),
            max_win_streak=longest_streak(wins.tolist()),
            max_loss_streak=longest_streak(losses.tolist()),
            opening_rm=opening,
            ending_rm=running_eq,
            return_pct=(running_eq / opening - 1.0) * 100.0 if opening else np.nan,
            max_dd_pct=mdd,
        ))
    return pd.DataFrame(rows)


def overall_summary(t: pd.DataFrame, stats: dict, start_rm: float = 100.0):
    if t.empty:
        return dict(**stats, start_rm=start_rm, end_rm=start_rm, compounded_return_pct=0.0,
                    max_dd_pct=0.0, max_win_streak=0, max_loss_streak=0)
    te = add_equity(t, start_rm=start_rm)
    wins = te["r"].astype(float) > 0
    losses = ~wins
    end_rm = float(te["equity_after_rm"].iloc[-1])
    return dict(
        **stats,
        start_rm=start_rm,
        end_rm=end_rm,
        compounded_return_pct=(end_rm / start_rm - 1.0) * 100.0,
        max_dd_pct=float(te["drawdown_pct"].max()),
        max_win_streak=longest_streak(wins.tolist()),
        max_loss_streak=longest_streak(losses.tolist()),
        stop_exits=int((te["exit_reason"] == "STOP").sum()),
        tp2_exits=int((te["exit_reason"] == "TP2").sum()),
        reverse_exits=int((te["exit_reason"] == "REVERSE").sum()),
        long_trades=int((te["side"] == 1).sum()),
        short_trades=int((te["side"] == -1).sum()),
    )


def write_report(outdir: Path, source: str, params, feat, trades, stats, yearly, monthly):
    outdir.mkdir(parents=True, exist_ok=True)
    enriched = add_equity(trades) if not trades.empty else trades.copy()
    enriched.to_csv(outdir / "trades.csv", index=False)
    monthly.to_csv(outdir / "monthly.csv", index=False)
    yearly.to_csv(outdir / "yearly.csv", index=False)

    summary = overall_summary(trades, stats)
    payload = {
        "strategy": "BBMA Reverse v1",
        "source_module": "casio.bbma_cleaner_robustness",
        "logic_change": "swap accepted LONG and SHORT signals only",
        "data": source,
        "feature_start": str(feat.index.min()) if len(feat) else None,
        "feature_end": str(feat.index.max()) if len(feat) else None,
        "params": params.__dict__,
        "summary": summary,
    }
    (outdir / "summary.json").write_text(json.dumps(payload, indent=2, default=str))

    lines = [
        "# BBMA Reverse v1 — Backtest Report",
        "",
        "## Research invariant",
        "",
        "The frozen BBMA Cleaner Core is reused unchanged. The only strategy-logic change is:",
        "",
        "- original accepted LONG -> reversed SHORT",
        "- original accepted SHORT -> reversed LONG",
        "",
        "All feature logic, MTF filters, stop construction, risk filters, cooldown, max trades/day,",
        "trade management, opposite-signal exits, fill timing and cost assumptions are inherited unchanged.",
        "",
        "## Overall",
        "",
        f"- Data: {source}",
        f"- Window: {payload['feature_start']} to {payload['feature_end']}",
        f"- Trades: {summary['trades']}",
        f"- Positive rate: {summary['positive_rate']:.2f}%",
        f"- Average R/trade: {summary['avg_r']:+.4f}R",
        f"- Profit factor: {summary['pf']:.3f}",
        f"- Net R: {summary['net_r']:+.2f}R",
        f"- Trades/month: {summary['trades_month']:.2f}",
        f"- RM100 -> RM{summary['end_rm']:.2f}",
        f"- Compounded return: {summary['compounded_return_pct']:+.2f}%",
        f"- Max compounded drawdown: {summary['max_dd_pct']:.2f}%",
        f"- Max win streak: {summary['max_win_streak']}",
        f"- Max loss streak: {summary['max_loss_streak']}",
        f"- STOP exits: {summary['stop_exits']}",
        f"- TP2 exits: {summary['tp2_exits']}",
        f"- Opposite-signal exits: {summary['reverse_exits']}",
        "",
        "## Monthly",
        "",
        monthly.to_markdown(index=False) if not monthly.empty else "_No trades._",
        "",
        "## Yearly (original frozen reporting function)",
        "",
        yearly.to_markdown(index=False) if not yearly.empty else "_No trades._",
        "",
    ]
    (outdir / "REPORT.md").write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--cost", type=float, default=0.0)
    ap.add_argument("--next-open", action="store_true")
    ap.add_argument("--out", default="reports/bbma-reverse-v1")
    args = ap.parse_args()

    base.signals = reversed_signals
    p = base.Params(cost_usd=args.cost, next_open_entry=args.next_open)
    feat, trades, stats, yearly = base.run(args.data, p, args.start, args.end)
    monthly = monthly_report(trades, args.start, args.end)
    write_report(Path(args.out), args.data, p, feat, trades, stats, yearly, monthly)
    print(json.dumps(overall_summary(trades, stats), indent=2, default=str))
    if not monthly.empty:
        print(monthly.to_string(index=False))


if __name__ == "__main__":
    main()
