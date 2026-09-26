from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json

import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .structural_portfolio_latest import StructuralPortfolioConfig, prepare_features, replay
from .structural_frequency_research import MODES, setup_frame_mode
from .outcome_first_structural_research import build_variants
from .regime_router_engine import RegimeRouterConfig, load_price_csv, replay_engine


START_BALANCE = 2500.0
RISKS = (0.004, 0.005)
TARGET_R = 3.0
MONTHLY_TARGET_PCT = 8.0
DAILY_HARD_DD_PCT = 3.0
MAX_HARD_DD_PCT = 6.0


def _common(trades: pd.DataFrame, time_col: str, r_col: str, label: str) -> pd.DataFrame:
    if trades is None or trades.empty:
        return pd.DataFrame(columns=["entry_time", "net_r", "candidate"])
    out = pd.DataFrame({
        "entry_time": pd.to_datetime(trades[time_col], utc=True, errors="coerce"),
        "net_r": pd.to_numeric(trades[r_col], errors="coerce"),
    }).dropna()
    out["candidate"] = label
    return out.sort_values("entry_time").reset_index(drop=True)


def _simulate_month(trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, risk_frac: float) -> dict:
    x = trades[(trades.entry_time >= start) & (trades.entry_time < end)].copy().sort_values("entry_time")
    equity = START_BALANCE
    peak = equity
    max_dd_pct = 0.0
    max_loss_streak = 0
    loss_streak = 0
    wins = 0
    losses = 0
    daily = {}

    for row in x.itertuples(index=False):
        t = pd.Timestamp(row.entry_time)
        day = t.floor("D")
        if day not in daily:
            daily[day] = {"start_equity": equity, "pnl": 0.0}
        r = float(row.net_r)
        pnl = equity * risk_frac * r
        equity += pnl
        daily[day]["pnl"] += pnl
        peak = max(peak, equity)
        if peak > 0:
            max_dd_pct = max(max_dd_pct, (peak - equity) / peak * 100.0)
        if r > 0:
            wins += 1
            loss_streak = 0
        elif r < 0:
            losses += 1
            loss_streak += 1
            max_loss_streak = max(max_loss_streak, loss_streak)

    daily_returns = []
    profitable_days = 0
    for d in sorted(daily):
        ds = daily[d]["start_equity"]
        pnl = daily[d]["pnl"]
        pct_initial = pnl / START_BALANCE * 100.0
        pct_day_start = pnl / ds * 100.0 if ds else 0.0
        daily_returns.append(pct_day_start)
        if pct_initial >= 0.5:
            profitable_days += 1

    ret = (equity / START_BALANCE - 1.0) * 100.0
    worst_daily = min(daily_returns) if daily_returns else 0.0
    hard_breach = max_dd_pct >= MAX_HARD_DD_PCT or worst_daily <= -DAILY_HARD_DD_PCT
    return {
        "month": start.strftime("%Y-%m"),
        "trades": int(len(x)),
        "wins": wins,
        "losses": losses,
        "win_rate": (wins / len(x) * 100.0) if len(x) else 0.0,
        "return_pct": ret,
        "end_balance": equity,
        "max_dd_pct": max_dd_pct,
        "worst_daily_pct": worst_daily,
        "max_loss_streak": max_loss_streak,
        "profitable_days_0_5": profitable_days,
        "hard_breach": bool(hard_breach),
        "passes_8pct": bool(ret >= MONTHLY_TARGET_PCT and not hard_breach),
    }


def _profiles() -> dict[str, StructuralPortfolioConfig]:
    base = StructuralPortfolioConfig(
        target_r=TARGET_R,
        min_external_runway_r=TARGET_R,
        round_trip_cost_bps=1.0,
    )
    return {
        "BALANCED": base,
        "FREQUENCY": replace(
            base,
            body_min=0.48,
            range_atr_min=0.55,
            internal_sweep_fresh=9,
            external_sweep_fresh=6,
            retrace_fill_bars=10,
            cooldown_bars=3,
        ),
        "QUALITY": replace(
            base,
            body_min=0.58,
            range_atr_min=0.80,
            internal_sweep_fresh=4,
            external_sweep_fresh=3,
            retrace_fill_bars=8,
            cooldown_bars=6,
        ),
    }


def build_candidates(m5: pd.DataFrame, data_path: str | Path) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}

    m15, _ = load_price_csv(data_path)
    rr10, _ = replay_engine(m15, RegimeRouterConfig(target_r=TARGET_R))
    out["RR10_CANONICAL"] = _common(rr10, "entry_time_utc", "result_r", "RR10_CANONICAL")

    for profile_name, cfg in _profiles().items():
        f = prepare_features(m5, cfg)
        for mode in MODES:
            setups = setup_frame_mode(f, cfg, mode)
            trades = replay(m5, setups, cfg)
            name = f"SF_{profile_name}_{mode}"
            out[name] = _common(trades, "entry_time", "net_r", name)

    for profile_name in ("BALANCED", "FREQUENCY"):
        cfg = _profiles()[profile_name]
        _, variants = build_variants(m5, cfg)
        for variant, setups in variants.items():
            trades = replay(m5, setups, cfg)
            name = f"OF_{profile_name}_{variant}"
            out[name] = _common(trades, "entry_time", "net_r", name)

    return out


def run(data_path: str | Path, output_dir: str | Path) -> dict:
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    m5 = load_m5_csv(data_path)
    data_end = m5.index.max() + pd.Timedelta(minutes=5)
    current_month = data_end.floor("D").replace(day=1)
    completed_starts = list(pd.date_range(
        pd.Timestamp("2026-01-01", tz="UTC"),
        current_month,
        freq="MS",
        inclusive="left",
    ))
    current_start = current_month
    current_end = data_end

    candidates = build_candidates(m5, data_path)
    monthly_rows = []
    ranking_rows = []

    for name, trades in candidates.items():
        trades_2026 = trades[trades.entry_time >= pd.Timestamp("2026-01-01", tz="UTC")].copy()
        for risk in RISKS:
            rows = []
            for a in completed_starts:
                b = a + pd.offsets.MonthBegin(1)
                m = _simulate_month(trades_2026, a, b, risk)
                m.update({"candidate": name, "risk_pct": risk * 100.0, "complete_month": True})
                monthly_rows.append(m)
                rows.append(m)

            partial = _simulate_month(trades_2026, current_start, current_end, risk)
            partial.update({"candidate": name, "risk_pct": risk * 100.0, "complete_month": False})
            monthly_rows.append(partial)

            if rows:
                rets = [r["return_pct"] for r in rows]
                pass_months = sum(int(r["passes_8pct"]) for r in rows)
                breach_months = sum(int(r["hard_breach"]) for r in rows)
                total_trades = sum(r["trades"] for r in rows)
                total_wins = sum(r["wins"] for r in rows)
                total_losses = sum(r["losses"] for r in rows)
                ranking_rows.append({
                    "candidate": name,
                    "risk_pct": risk * 100.0,
                    "months_tested": len(rows),
                    "months_ge_8pct": pass_months,
                    "breach_months": breach_months,
                    "worst_month_pct": min(rets),
                    "avg_month_pct": float(np.mean(rets)),
                    "median_month_pct": float(np.median(rets)),
                    "best_month_pct": max(rets),
                    "avg_trades_month": total_trades / len(rows),
                    "aggregate_win_rate": total_wins / max(1, total_wins + total_losses) * 100.0,
                    "worst_month_max_dd_pct": max(r["max_dd_pct"] for r in rows),
                    "worst_daily_pct": min(r["worst_daily_pct"] for r in rows),
                    "max_loss_streak": max(r["max_loss_streak"] for r in rows),
                    "all_months_pass": pass_months == len(rows) and breach_months == 0,
                    "current_partial_return_pct": partial["return_pct"],
                    "current_partial_trades": partial["trades"],
                })

    monthly = pd.DataFrame(monthly_rows)
    ranking = pd.DataFrame(ranking_rows).sort_values(
        ["all_months_pass", "months_ge_8pct", "breach_months", "worst_month_pct", "avg_month_pct", "worst_month_max_dd_pct"],
        ascending=[False, False, True, False, False, True],
    ).reset_index(drop=True)

    monthly.to_csv(outdir / "monthly_results.csv", index=False)
    ranking.to_csv(outdir / "ranking.csv", index=False)

    top = ranking.head(12).copy()
    winner = top.iloc[0].to_dict() if len(top) else None
    accepted = ranking[ranking.all_months_pass.eq(True)].copy() if len(ranking) else ranking.copy()

    summary = {
        "data_start": m5.index.min().isoformat(),
        "data_end": m5.index.max().isoformat(),
        "completed_months": [x.strftime("%Y-%m") for x in completed_starts],
        "current_partial_month": current_start.strftime("%Y-%m"),
        "rules": {
            "start_balance": START_BALANCE,
            "risk_pct_tested": [x * 100 for x in RISKS],
            "fixed_rr": TARGET_R,
            "real_sl": True,
            "breakeven": False,
            "scale_out": False,
            "monthly_target_pct": MONTHLY_TARGET_PCT,
            "daily_hard_dd_pct": DAILY_HARD_DD_PCT,
            "max_hard_dd_pct": MAX_HARD_DD_PCT,
            "one_active_trade": True,
            "cost_bps_structural": 1.0,
        },
        "candidate_count": len(candidates),
        "accepted_count": int(len(accepted)),
        "best_candidate": winner,
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# Finotive-style Prop Research - 2026",
        "",
        f"Data: {m5.index.min().isoformat()} -> {m5.index.max().isoformat()}",
        f"Completed months tested: {', '.join(summary['completed_months'])}",
        f"Candidates: {len(candidates)}; risk: 0.4% and 0.5%; fixed target: 3R.",
        "",
        "Hard acceptance: every completed month >= +8%, zero simulated 3% daily / 6% max-DD breaches.",
        "Closed-trade equity is used for DD/daily calculations; gap/slippage and intrabar floating equity beyond the modeled hard SL are not reconstructed.",
        "",
        f"Accepted candidates: **{len(accepted)}**",
        "",
        "## Top ranking",
        "",
        "~~~text",
        top.to_string(index=False),
        "~~~",
        "",
    ]

    if winner:
        wname = str(winner["candidate"])
        wrisk = float(winner["risk_pct"])
        wm = monthly[(monthly.candidate == wname) & (monthly.risk_pct == wrisk)].sort_values("month")
        lines += [
            f"## Best candidate: {wname} @ {wrisk:.1f}% risk",
            "",
            "~~~text",
            wm[["month","complete_month","trades","win_rate","return_pct","max_dd_pct","worst_daily_pct","max_loss_streak","profitable_days_0_5","hard_breach","passes_8pct"]].to_string(index=False),
            "~~~",
            "",
        ]

    if len(accepted) == 0:
        lines += [
            "## Verdict",
            "",
            "No tested fixed technique/profile met the hard requirement of >=8% in every completed 2026 month.",
            "The top row is therefore the closest robust candidate, not an accepted prop engine.",
        ]
    else:
        lines += [
            "## Verdict",
            "",
            "At least one fixed technique/profile cleared the hard month-by-month acceptance test on the completed 2026 sample.",
            "It still requires cross-feed and earlier-year validation before deployment.",
        ]

    report = "\n".join(lines)
    (outdir / "REPORT.md").write_text(report, encoding="utf-8")
    print(report)
    return summary


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--output", default="reports/finotive-prop-2026")
    a = p.parse_args()
    run(a.data, a.output)


if __name__ == "__main__":
    main()
