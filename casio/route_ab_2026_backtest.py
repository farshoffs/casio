from __future__ import annotations

import argparse
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from .structural_frequency_research import setup_frame_mode
from .structural_portfolio_latest import StructuralPortfolioConfig, prepare_features
from .v3_core import load_m5_csv


START_BALANCE_RM = 100.0
RISK_FRACTION = 0.05
START_2026 = pd.Timestamp("2026-01-01", tz="UTC")
END_2026 = pd.Timestamp("2027-01-01", tz="UTC")


def _safe_number(v: float | int | None) -> str:
    if v is None or not np.isfinite(float(v)):
        return "n/a"
    return f"{float(v):.2f}"


def _route_rr(runway_r: float, *, precision: bool, quality_score: int) -> float:
    """Frozen 1:2 to 1:4 target policy based on available structural runway."""
    if precision:
        # Precision keeps 2R as the default and only stretches when the A+ evidence
        # and structural runway are both unusually strong.
        if runway_r >= 4.0 and quality_score >= 6:
            return 4.0
        if runway_r >= 3.0 and quality_score >= 5:
            return 3.0
        return 2.0
    if runway_r >= 4.0 and quality_score >= 4:
        return 4.0
    if runway_r >= 3.0:
        return 3.0
    return 2.0


def _annotate_route_a(setups: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for s in setups.itertuples(index=False):
        i = int(s.signal_i)
        row = features.iloc[i]
        d = int(s.direction)
        fresh_internal = bool(row.internal_sell_sweep_age <= 3 if d == 1 else row.internal_buy_sweep_age <= 3)
        fresh_external = bool(row.external_sell_sweep_age <= 4 if d == 1 else row.external_buy_sweep_age <= 4)
        trend_aligned = bool(row.trend_vote >= 2 if d == 1 else row.trend_vote <= -2)
        m15_aligned = bool(row.m15_structure_bias > 0 if d == 1 else row.m15_structure_bias < 0)
        clean_disp = bool(row.body_fraction >= 0.58 and row.range_atr >= 0.80)
        fvg_entry = str(s.entry_model) == "FVG50"
        quality = int(fresh_internal) + int(fresh_external) + int(trend_aligned) + int(m15_aligned) + int(clean_disp) + int(fvg_entry)
        rr = _route_rr(float(s.external_runway_r), precision=False, quality_score=quality)
        r = s._asdict()
        r.update(
            route="A_STRUCTURAL_ASYMMETRIC",
            quality_score=quality,
            target_r=rr,
            target=float(s.entry) + d * rr * float(s.risk),
            fresh_internal=fresh_internal,
            fresh_external=fresh_external,
            trend_aligned=trend_aligned,
            m15_aligned=m15_aligned,
            clean_displacement=clean_disp,
            fvg_entry=fvg_entry,
        )
        rows.append(r)
    return pd.DataFrame(rows)


def _route_b_from_a(route_a: pd.DataFrame) -> pd.DataFrame:
    if route_a.empty:
        return route_a.copy()
    # Route B is the A+ subset discussed with the user: same structural foundation,
    # but it must have a real FVG retracement, aligned HTF/M15 structure, clean
    # displacement, fresh liquidity, and at least 2R of external runway.
    x = route_a[
        route_a.fvg_entry
        & route_a.trend_aligned
        & route_a.m15_aligned
        & route_a.clean_displacement
        & (route_a.fresh_internal | route_a.fresh_external)
        & route_a.external_runway_r.ge(2.0)
        & route_a.quality_score.ge(5)
    ].copy()
    if x.empty:
        return x
    x["route"] = "B_PRECISION_A_PLUS"
    x["target_r"] = [
        _route_rr(float(runway), precision=True, quality_score=int(score))
        for runway, score in zip(x.external_runway_r, x.quality_score)
    ]
    x["target"] = x.entry + x.direction * x.target_r * x.risk
    return x


def _replay_variable_targets(m5: pd.DataFrame, setups: pd.DataFrame, cfg: StructuralPortfolioConfig) -> pd.DataFrame:
    if setups.empty:
        return pd.DataFrame()
    events: list[dict] = []
    next_free = -1
    for s in setups.sort_values("signal_i").itertuples(index=False):
        sig = int(s.signal_i)
        if sig < next_free:
            continue
        d = int(s.direction)
        entry = float(s.entry)
        stop = float(s.stop)
        risk = float(s.risk)
        target_r = float(s.target_r)
        target = entry + d * target_r * risk

        fill = None
        for j in range(sig + 1, min(len(m5), sig + 1 + cfg.retrace_fill_bars)):
            lo, hi = float(m5.low.iat[j]), float(m5.high.iat[j])
            # If the structural stop is invalidated before retracement entry, cancel.
            if (lo <= stop if d == 1 else hi >= stop):
                break
            if lo <= entry <= hi:
                fill = j
                break
        if fill is None:
            continue

        end = min(len(m5), fill + 1 + cfg.max_hold_bars)
        gross_r = reason = exit_i = None
        exit_price = np.nan
        for j in range(fill + 1, end):
            lo, hi, close = float(m5.low.iat[j]), float(m5.high.iat[j]), float(m5.close.iat[j])
            hit_stop = lo <= stop if d == 1 else hi >= stop
            hit_target = hi >= target if d == 1 else lo <= target
            if hit_stop and hit_target:
                gross_r, reason, exit_price = -1.0, "stop_same_bar", stop
            elif hit_stop:
                gross_r, reason, exit_price = -1.0, "stop", stop
            elif hit_target:
                gross_r, reason, exit_price = target_r, "target", target
            elif j == end - 1:
                gross_r, reason, exit_price = (close - entry) / risk * d, "time_exit", close
            else:
                continue
            exit_i = j
            break
        if gross_r is None or exit_i is None:
            continue

        cost_r = (entry * cfg.round_trip_cost_bps / 10000.0) / risk
        rec = s._asdict()
        rec.update(
            entry_time=m5.index[fill] + pd.Timedelta(minutes=5),
            exit_time=m5.index[exit_i] + pd.Timedelta(minutes=5),
            exit_price=float(exit_price),
            gross_r=float(gross_r),
            cost_r=float(cost_r),
            net_r=float(gross_r - cost_r),
            reason=reason,
        )
        events.append(rec)
        next_free = exit_i + 1
    return pd.DataFrame(events)


def _compound_rm(trades: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    x = trades.sort_values("entry_time").copy()
    balance = START_BALANCE_RM
    peak = balance
    max_dd_rm = 0.0
    max_dd_pct = 0.0
    before, risk_rm, pnl_rm, after = [], [], [], []
    for r in x.net_r.astype(float):
        b0 = balance
        stake = b0 * RISK_FRACTION
        pnl = stake * r
        balance = b0 + pnl
        peak = max(peak, balance)
        dd_rm = peak - balance
        dd_pct = dd_rm / peak * 100.0 if peak > 0 else 0.0
        max_dd_rm = max(max_dd_rm, dd_rm)
        max_dd_pct = max(max_dd_pct, dd_pct)
        before.append(b0)
        risk_rm.append(stake)
        pnl_rm.append(pnl)
        after.append(balance)
    if not x.empty:
        x["balance_before_rm"] = before
        x["risk_rm"] = risk_rm
        x["pnl_rm"] = pnl_rm
        x["balance_after_rm"] = after
    summary = {
        "start_balance_rm": START_BALANCE_RM,
        "ending_balance_rm": balance,
        "return_pct": (balance / START_BALANCE_RM - 1.0) * 100.0,
        "max_drawdown_rm": max_dd_rm,
        "max_drawdown_pct": max_dd_pct,
    }
    return x, summary


def _route_metrics(trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    days = max((end - start).total_seconds() / 86400.0, 1e-9)
    if trades.empty:
        return {
            "trades": 0, "trades_per_30d": 0.0, "win_rate": 0.0,
            "avg_win_r": None, "avg_loss_r": None, "expectancy_r": 0.0,
            "profit_factor": None, "net_r": 0.0,
        }
    r = trades.net_r.astype(float)
    wins = r[r > 0.05]
    losses = r[r < -0.05]
    return {
        "trades": int(len(r)),
        "trades_per_30d": float(len(r) * 30.0 / days),
        "win_rate": float((r > 0.05).mean() * 100.0),
        "avg_win_r": float(wins.mean()) if len(wins) else None,
        "avg_loss_r": float(-losses.mean()) if len(losses) else None,
        "expectancy_r": float(r.mean()),
        "profit_factor": float(wins.sum() / (-losses.sum())) if len(losses) else (math.inf if len(wins) else None),
        "net_r": float(r.sum()),
    }


def _monthly_table(trades: pd.DataFrame) -> pd.DataFrame:
    months = pd.period_range("2026-01", "2026-12", freq="M")
    rows = []
    for month in months:
        a = pd.Timestamp(month.start_time, tz="UTC")
        b = pd.Timestamp((month + 1).start_time, tz="UTC")
        t = trades[(pd.to_datetime(trades.entry_time, utc=True) >= a) & (pd.to_datetime(trades.entry_time, utc=True) < b)].copy() if not trades.empty else trades.copy()
        if t.empty:
            rows.append({"month": str(month), "trades": 0, "win_rate": None, "net_r": 0.0, "pnl_rm": 0.0, "ending_balance_rm": None})
        else:
            r = t.net_r.astype(float)
            rows.append({
                "month": str(month),
                "trades": len(t),
                "win_rate": float((r > 0.05).mean() * 100.0),
                "net_r": float(r.sum()),
                "pnl_rm": float(t.pnl_rm.sum()),
                "ending_balance_rm": float(t.balance_after_rm.iloc[-1]),
            })
    return pd.DataFrame(rows)


def _md_table(df: pd.DataFrame, columns: list[str]) -> str:
    if df.empty:
        return "_No trades._"
    rows = ["| " + " | ".join(columns) + " |", "|" + "|".join(["---"] * len(columns)) + "|"]
    for _, r in df[columns].iterrows():
        vals = []
        for c in columns:
            v = r[c]
            if pd.isna(v):
                vals.append("—")
            elif isinstance(v, (float, np.floating)):
                vals.append(f"{float(v):.2f}")
            else:
                vals.append(str(v))
        rows.append("| " + " | ".join(vals) + " |")
    return "\n".join(rows)


def run(data_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    m5 = load_m5_csv(data_path)
    observed_end = min(END_2026, m5.index.max() + pd.Timedelta(minutes=5))
    if observed_end <= START_2026:
        raise ValueError("Dukascopy research CSV has no 2026 data")

    # Use pre-2026 rows only as causal indicator/structure warm-up. Entries are
    # strictly restricted to 2026.
    cfg = replace(
        StructuralPortfolioConfig(),
        min_external_runway_r=2.0,
        target_r=2.0,
        round_trip_cost_bps=1.0,
    )
    features = prepare_features(m5, cfg)
    base_setups = setup_frame_mode(features, cfg, "DISPLACEMENT_RETRACE")
    base_setups = base_setups[
        (pd.to_datetime(base_setups.signal_time, utc=True) >= START_2026)
        & (pd.to_datetime(base_setups.signal_time, utc=True) < observed_end)
    ].copy()

    route_a_setups = _annotate_route_a(base_setups, features)
    route_b_setups = _route_b_from_a(route_a_setups)

    route_a = _replay_variable_targets(m5, route_a_setups, cfg)
    route_b = _replay_variable_targets(m5, route_b_setups, cfg)
    if not route_a.empty:
        route_a = route_a[(pd.to_datetime(route_a.entry_time, utc=True) >= START_2026) & (pd.to_datetime(route_a.entry_time, utc=True) < observed_end)].copy()
    if not route_b.empty:
        route_b = route_b[(pd.to_datetime(route_b.entry_time, utc=True) >= START_2026) & (pd.to_datetime(route_b.entry_time, utc=True) < observed_end)].copy()

    route_a, a_equity = _compound_rm(route_a)
    route_b, b_equity = _compound_rm(route_b)
    a_metrics = _route_metrics(route_a, START_2026, observed_end)
    b_metrics = _route_metrics(route_b, START_2026, observed_end)
    a_month = _monthly_table(route_a)
    b_month = _monthly_table(route_b)

    route_a.to_csv(output_dir / "route_a_trades.csv", index=False)
    route_b.to_csv(output_dir / "route_b_trades.csv", index=False)
    a_month.to_csv(output_dir / "route_a_monthly.csv", index=False)
    b_month.to_csv(output_dir / "route_b_monthly.csv", index=False)

    comparison = pd.DataFrame([
        {
            "route": "A Structural Asymmetric",
            **a_metrics,
            **a_equity,
        },
        {
            "route": "B Precision A+",
            **b_metrics,
            **b_equity,
        },
    ])

    def objective(m: dict) -> str:
        freq_ok = 6.0 <= float(m["trades_per_30d"]) <= 10.0
        wr_ok = float(m["win_rate"]) >= 70.0
        exp_ok = float(m["expectancy_r"]) > 0
        pf = m["profit_factor"]
        pf_ok = pf is not None and (math.isinf(float(pf)) or float(pf) > 1.0)
        return "YES" if freq_ok and wr_ok and exp_ok and pf_ok else "NO"

    report = [
        "# CASIO 2026 Dukascopy — Route A vs Route B Backtest",
        "",
        f"Generated from `{data_path}`. Entry period: **2026-01-01 UTC → {observed_end.isoformat()}** (dataset is currently YTD, not a complete 2026 calendar year).",
        "",
        "## Frozen test assumptions",
        "",
        "- Starting balance: **RM100** for each route independently.",
        "- Risk: **5% of current equity per filled trade**, compounded trade by trade.",
        "- RR: **1:2 to 1:4**, selected before replay from structural runway and setup quality.",
        "- Execution: M5 retracement fill model; stop-first if both stop and target are touched in the same M5 candle.",
        f"- Cost model: **{cfg.round_trip_cost_bps:.1f} bps round trip** converted to R. No separate broker-specific spread/slippage model beyond that cost assumption.",
        "- No 2026 parameter optimization/grid search is performed in this job; the two route definitions are frozen before results are calculated.",
        "- Pre-2026 bars are used only for causal indicator/market-structure warm-up. All counted entries are in 2026.",
        "",
        "## Route definitions",
        "",
        "**Route A — Structural Asymmetric:** CASIO `DISPLACEMENT_RETRACE` structural engine. London/NY structural setup, liquidity/structure context, displacement, retracement entry (FVG50 when available, otherwise displacement-body 50%), structural stop, and 2R/3R/4R target chosen from available external-liquidity runway.",
        "",
        "**Route B — Precision A+:** premium subset of Route A. Requires FVG retracement, HTF trend alignment, M15 structure alignment, clean displacement, fresh internal/external liquidity, quality score >=5/6, and >=2R structural runway. Defaults to 2R and only stretches to 3R/4R on stronger A+ evidence.",
        "",
        "## Headline comparison",
        "",
        "| Route | Trades | Trades/30d | Win rate | Avg win R | Avg loss R | Expectancy R | PF | Net R | End balance RM | Return % | Max DD % | 8/mo + 70% objective |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for label, m, e in [("A Structural Asymmetric", a_metrics, a_equity), ("B Precision A+", b_metrics, b_equity)]:
        pf = "∞" if m["profit_factor"] is not None and math.isinf(float(m["profit_factor"])) else _safe_number(m["profit_factor"])
        report.append(
            f"| {label} | {m['trades']} | {m['trades_per_30d']:.2f} | {m['win_rate']:.2f}% | "
            f"{_safe_number(m['avg_win_r'])} | {_safe_number(m['avg_loss_r'])} | {m['expectancy_r']:.3f} | {pf} | "
            f"{m['net_r']:.2f} | {e['ending_balance_rm']:.2f} | {e['return_pct']:.2f}% | {e['max_drawdown_pct']:.2f}% | {objective(m)} |"
        )

    report += [
        "",
        "## Route A — month by month",
        "",
        _md_table(a_month, ["month", "trades", "win_rate", "net_r", "pnl_rm", "ending_balance_rm"]),
        "",
        "## Route B — month by month",
        "",
        _md_table(b_month, ["month", "trades", "win_rate", "net_r", "pnl_rm", "ending_balance_rm"]),
        "",
        "## Target distribution",
        "",
    ]
    for label, t in [("Route A", route_a), ("Route B", route_b)]:
        if t.empty:
            report.append(f"- **{label}:** no filled trades.")
        else:
            counts = t.target_r.value_counts().sort_index()
            desc = ", ".join(f"{float(rr):.0f}R: {int(n)}" for rr, n in counts.items())
            report.append(f"- **{label}:** {desc}")

    report += [
        "",
        "## Notes",
        "",
        "This report is a research backtest, not a profitability guarantee. The useful comparison is whether either frozen route can hold frequency, hit rate, expectancy, PF, and drawdown together on the same 2026 Dukascopy sample.",
        "",
        "Raw filled trades and monthly summaries are saved beside this report for audit/replay.",
    ]
    (output_dir / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(comparison.to_string(index=False))
    print(f"Report: {output_dir / 'REPORT.md'}")


def main() -> None:
    p = argparse.ArgumentParser(description="Backtest CASIO Route A vs Route B on 2026 Dukascopy M5")
    p.add_argument("--data", type=Path, default=Path("data/xauusd_m5_dukascopy_research.csv"))
    p.add_argument("--output", type=Path, default=Path("reports/route-ab-2026"))
    args = p.parse_args()
    run(args.data, args.output)


if __name__ == "__main__":
    main()
