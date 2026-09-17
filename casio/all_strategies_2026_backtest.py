from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from .backtest import run_backtest as legacy_run_backtest
from .outcome_first_structural_research import build_variants as outcome_build_variants
from .route_ab_2026_backtest import (
    _annotate_route_a,
    _replay_variable_targets,
    _route_b_from_a,
)
from .structural_frequency_research import MODES as STRUCTURAL_MODES, setup_frame_mode
from .structural_portfolio_latest import (
    StructuralPortfolioConfig,
    prepare_features as structural_prepare_features,
    replay as structural_replay,
    setup_frame as structural_portfolio_setup,
)
from .structural_regime_router_research import ROUTERS, _router_setups
from .v3_aplus_hybrid_research import replay as hybrid_replay
from .v3_aplus_research import replay_profile as aplus_replay
from .v3_aplus_v2_research import add_regime_features, replay as aplus_v2_replay
from .v3_asymmetry_challenger import (
    asymmetry_signals,
    prepare_asymmetry_features,
    variants as asymmetry_variants,
)
from .v3_core import load_m5_csv
from .v3_edge_map import candidate_frame
from .v3_m5_engine import (
    V3M5Config,
    prepare_m5_features,
    replay_execution,
    signals_for_m5_features,
)
from .v3_structural_aplus_research import (
    StructuralAPlusConfig,
    prepare_structural_features,
    replay as structural_aplus_replay,
    setup_frame as structural_aplus_setup,
)
from .v4_confluence_research import Candidate as V4Candidate
from .v4_confluence_research import load_features as v4_load_features
from .v4_confluence_research import replay as v4_replay
from .v4_edge_diagnose import core as v4_core


DATA = Path("data/xauusd_m5_dukascopy_research.csv")
OUTPUT = Path("reports/all-strategies-2026")
START = pd.Timestamp("2026-01-01T00:00:00Z")
END = pd.Timestamp("2027-01-01T00:00:00Z")
WARMUP = pd.Timestamp("2025-10-01T00:00:00Z")
START_RM = 100.0
RISK_FRACTION = 0.05


results: list[dict] = []
all_trade_frames: list[pd.DataFrame] = []


def _fmt(v: float | None, digits: int = 2) -> str:
    if v is None or not np.isfinite(float(v)):
        return "—"
    return f"{float(v):.{digits}f}"


def _standardize(
    name: str,
    family: str,
    trades: pd.DataFrame,
    observed_end: pd.Timestamp,
    *,
    r_col: str = "net_r",
    cost_model: str = "1.0 bps round trip",
) -> pd.DataFrame:
    if trades is None or trades.empty or "entry_time" not in trades.columns or r_col not in trades.columns:
        x = pd.DataFrame(columns=["strategy", "family", "entry_time", "exit_time", "net_r", "balance_before_rm", "risk_rm", "pnl_rm", "balance_after_rm"])
        _register_summary(name, family, x, observed_end, cost_model)
        return x

    x = trades.copy()
    x["entry_time"] = pd.to_datetime(x["entry_time"], utc=True, errors="coerce")
    if "exit_time" in x.columns:
        x["exit_time"] = pd.to_datetime(x["exit_time"], utc=True, errors="coerce")
    else:
        x["exit_time"] = pd.NaT
    x["net_r"] = pd.to_numeric(x[r_col], errors="coerce")
    x = x[(x.entry_time >= START) & (x.entry_time < observed_end)].dropna(subset=["entry_time", "net_r"]).sort_values("entry_time").copy()

    balance = START_RM
    peak = balance
    before: list[float] = []
    risk_rm: list[float] = []
    pnl_rm: list[float] = []
    after: list[float] = []
    for r in x.net_r.astype(float):
        b0 = balance
        stake = b0 * RISK_FRACTION
        pnl = stake * r
        balance = b0 + pnl
        before.append(b0)
        risk_rm.append(stake)
        pnl_rm.append(pnl)
        after.append(balance)
        peak = max(peak, balance)
    x["strategy"] = name
    x["family"] = family
    x["balance_before_rm"] = before
    x["risk_rm"] = risk_rm
    x["pnl_rm"] = pnl_rm
    x["balance_after_rm"] = after
    compact = x[["strategy", "family", "entry_time", "exit_time", "net_r", "balance_before_rm", "risk_rm", "pnl_rm", "balance_after_rm"]].copy()
    all_trade_frames.append(compact)
    _register_summary(name, family, compact, observed_end, cost_model)
    return compact


def _register_summary(name: str, family: str, x: pd.DataFrame, observed_end: pd.Timestamp, cost_model: str) -> None:
    days = max((observed_end - START).total_seconds() / 86400.0, 1e-9)
    if x.empty:
        results.append({
            "strategy": name, "family": family, "trades": 0, "trades_per_30d": 0.0,
            "win_rate": 0.0, "avg_win_r": np.nan, "avg_loss_r": np.nan,
            "expectancy_r": 0.0, "profit_factor": np.nan, "net_r": 0.0,
            "ending_balance_rm": START_RM, "return_pct": 0.0, "max_drawdown_pct": 0.0,
            "target_8mo_70": "NO", "cost_model": cost_model,
        })
        return

    r = x.net_r.astype(float)
    wins = r[r > 0.05]
    losses = r[r < -0.05]
    pf = float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() < 0 else (math.inf if len(wins) else np.nan)
    end_rm = float(x.balance_after_rm.iloc[-1])
    equity = pd.Series([START_RM, *x.balance_after_rm.astype(float).tolist()])
    peak = equity.cummax()
    dd_pct = ((peak - equity) / peak.replace(0, np.nan) * 100.0).max()
    tpm = len(x) * 30.0 / days
    wr = len(wins) * 100.0 / len(x)
    objective = "YES" if 6.0 <= tpm <= 10.0 and wr >= 70.0 and float(r.mean()) > 0 and (math.isinf(pf) or pf > 1.0) else "NO"
    results.append({
        "strategy": name,
        "family": family,
        "trades": int(len(x)),
        "trades_per_30d": float(tpm),
        "win_rate": float(wr),
        "avg_win_r": float(wins.mean()) if len(wins) else np.nan,
        "avg_loss_r": float(-losses.mean()) if len(losses) else np.nan,
        "expectancy_r": float(r.mean()),
        "profit_factor": pf,
        "net_r": float(r.sum()),
        "ending_balance_rm": end_rm,
        "return_pct": (end_rm / START_RM - 1.0) * 100.0,
        "max_drawdown_pct": float(dd_pct) if np.isfinite(dd_pct) else 0.0,
        "target_8mo_70": objective,
        "cost_model": cost_model,
    })


def _run_v3_family(m5: pd.DataFrame, observed_end: pd.Timestamp) -> None:
    print("[all-strategies] V3 M5 family")
    f = prepare_m5_features(m5)
    configs = {
        "V3 M5 Combined": V3M5Config(),
        "V3 Classic M15 Only": replace(V3M5Config(), enable_m5_trend=False, enable_m5_range=False),
        "V3 M5 Trend Only": replace(V3M5Config(), enable_classic=False, enable_m5_range=False),
        "V3 M5 Range Only": replace(V3M5Config(), enable_classic=False, enable_m5_trend=False),
    }
    for name, cfg in configs.items():
        tr = replay_execution(m5, signals_for_m5_features(f, cfg), cfg)
        _standardize(name, "V3 M5", tr, observed_end)


def _run_asymmetry(m5: pd.DataFrame, observed_end: pd.Timestamp) -> None:
    print("[all-strategies] V3 asymmetry variants")
    f = prepare_asymmetry_features(m5)
    for cfg in asymmetry_variants():
        sig = asymmetry_signals(f, cfg)
        exec_cfg = V3M5Config(cooldown_m5_bars=cfg.cooldown_m5_bars, round_trip_cost_bps=cfg.round_trip_cost_bps)
        tr = replay_execution(m5, sig, exec_cfg)
        _standardize(f"V3 Asymmetry {cfg.name}", "V3 Asymmetry", tr, observed_end)


def _run_aplus(m5: pd.DataFrame, observed_end: pd.Timestamp) -> None:
    print("[all-strategies] V3 A+ variants")
    c = add_regime_features(m5, candidate_frame(m5))

    for profile in ["APLUS_CORE", "FREQUENCY"]:
        for mgmt in ["FULL_3R", "SCALE_2R_RUN4R"]:
            tr = aplus_replay(m5, c, profile, mgmt)
            _standardize(f"A+ {profile} {mgmt}", "V3 A+ v1", tr, observed_end)

    for profile in ["ROBUST", "ROBUST_EFF20", "FREQ16", "ADAPTIVE03", "ADAPTIVE05", "ADAPTIVE07"]:
        for target in [3.0, 3.5, 4.0]:
            tr = aplus_v2_replay(m5, c, profile, target)
            _standardize(f"A+ v2 {profile} {target:.1f}R", "V3 A+ v2", tr, observed_end)

    for name, spread, slope in [("HYBRID03", .30, .10), ("HYBRID05", .50, .15), ("HYBRID07", .70, .15), ("HYBRID10", 1.0, .20)]:
        tr = hybrid_replay(m5, c, spread, slope)
        _standardize(f"A+ Hybrid {name}", "V3 A+ Hybrid", tr, observed_end)


def _run_structural_aplus(m5: pd.DataFrame, observed_end: pd.Timestamp) -> None:
    print("[all-strategies] Structural A+ grid")
    f = prepare_structural_features(m5)
    for runway in [3.0, 3.5, 4.0]:
        for retrace_bars in [4, 6, 8]:
            for mgmt in ["FULL_3_5R", "SCALE_25_2R_RUN4R"]:
                cfg = StructuralAPlusConfig(min_runway_r=runway, retrace_bars=retrace_bars, management=mgmt)
                setups = structural_aplus_setup(f, cfg)
                tr = structural_aplus_replay(m5, setups, cfg)
                _standardize(f"Structural A+ R{runway:.1f} RB{retrace_bars} {mgmt}", "Structural A+", tr, observed_end)


def _run_structural_portfolios(m5: pd.DataFrame, observed_end: pd.Timestamp) -> None:
    print("[all-strategies] Structural portfolio / frequency / routers / outcome-first")
    cfg = replace(StructuralPortfolioConfig(), target_r=3.5, min_external_runway_r=3.5)
    f = structural_prepare_features(m5, cfg)

    setups = structural_portfolio_setup(f, cfg)
    _standardize("Structural Portfolio 3.5R", "Structural Portfolio", structural_replay(m5, setups, cfg), observed_end)

    mode_setups: dict[str, pd.DataFrame] = {}
    for mode in STRUCTURAL_MODES:
        s = setup_frame_mode(f, cfg, mode)
        mode_setups[mode] = s
        _standardize(f"Structural Frequency {mode}", "Structural Frequency", structural_replay(m5, s, cfg), observed_end)

    displacement = mode_setups["DISPLACEMENT_RETRACE"]
    strict = mode_setups["STRICT_FVG"]
    for router in ROUTERS:
        s = _router_setups(displacement, strict, cfg, router)
        _standardize(f"Structural Router {router}", "Structural Router", structural_replay(m5, s, cfg), observed_end)

    _, variants = outcome_build_variants(m5, cfg)
    for name, s in variants.items():
        _standardize(f"Outcome First {name}", "Outcome First", structural_replay(m5, s, cfg), observed_end)


def _run_routes(m5: pd.DataFrame, observed_end: pd.Timestamp) -> None:
    print("[all-strategies] Route A / B")
    cfg = replace(StructuralPortfolioConfig(), min_external_runway_r=2.0, target_r=2.0, round_trip_cost_bps=1.0)
    f = structural_prepare_features(m5, cfg)
    s = setup_frame_mode(f, cfg, "DISPLACEMENT_RETRACE")
    a = _annotate_route_a(s, f)
    b = _route_b_from_a(a)
    _standardize("Route A Structural Asymmetric", "Route A/B", _replay_variable_targets(m5, a, cfg), observed_end)
    _standardize("Route B Precision A+", "Route A/B", _replay_variable_targets(m5, b, cfg), observed_end)


def _run_v4(observed_end: pd.Timestamp) -> None:
    print("[all-strategies] V4 Python parity variants")
    f = v4_load_features(DATA)
    f = f[f.index >= WARMUP].copy()
    base_candidate = V4Candidate(55, 0.60, 0.35, 6)
    variants = {
        "V4 CORE": v4_core(f),
        "V4 CORE SD SCORE60": v4_core(f, sd_score=60),
        "V4 CORE SD SCORE65": v4_core(f, sd_score=65),
        "V4 CORE SD M15": v4_core(f, sd_m15=True),
        "V4 CORE SD M15 SCORE60": v4_core(f, sd_score=60, sd_m15=True),
        "V4 CORE SD M15 SCORE65": v4_core(f, sd_score=65, sd_m15=True),
    }
    for name, frame in variants.items():
        _standardize(name, "V4 Confluence", v4_replay(frame, base_candidate), observed_end, r_col="r", cost_model="no explicit transaction cost in v4 Python replay")

    quality = v4_core(f)
    quality["in_asia"] = False
    quality_candidate = V4Candidate(65, 0.60, 0.35, 9, max_trades_per_day=2)
    _standardize("V4 QUALITY65 London/NY proxy", "V4 Confluence", v4_replay(quality, quality_candidate), observed_end, r_col="r", cost_model="no explicit transaction cost in v4 Python replay")


def _run_legacy(m5: pd.DataFrame, observed_end: pd.Timestamp) -> None:
    print("[all-strategies] Legacy Python regime strategy")
    tr = legacy_run_backtest(m5)
    _standardize("Legacy Python Regime Router", "Legacy", tr, observed_end, r_col="r_multiple", cost_model="no explicit transaction cost in legacy replay")


def _monthly(all_trades: pd.DataFrame, observed_end: pd.Timestamp) -> pd.DataFrame:
    rows: list[dict] = []
    names = [r["strategy"] for r in results]
    last_month = observed_end.to_period("M")
    months = pd.period_range("2026-01", last_month, freq="M")
    for name in names:
        t = all_trades[all_trades.strategy.eq(name)].sort_values("entry_time").copy() if not all_trades.empty else pd.DataFrame()
        for month in months:
            a = pd.Timestamp(month.start_time, tz="UTC")
            b = min(pd.Timestamp((month + 1).start_time, tz="UTC"), observed_end)
            x = t[(t.entry_time >= a) & (t.entry_time < b)] if not t.empty else t
            if x.empty:
                rows.append({"strategy": name, "month": str(month), "trades": 0, "win_rate": np.nan, "net_r": 0.0, "pnl_rm": 0.0, "ending_balance_rm": np.nan})
            else:
                r = x.net_r.astype(float)
                rows.append({
                    "strategy": name,
                    "month": str(month),
                    "trades": int(len(x)),
                    "win_rate": float((r > 0.05).mean() * 100.0),
                    "net_r": float(r.sum()),
                    "pnl_rm": float(x.pnl_rm.sum()),
                    "ending_balance_rm": float(x.balance_after_rm.iloc[-1]),
                })
    return pd.DataFrame(rows)


def _md_summary(frame: pd.DataFrame) -> list[str]:
    lines = [
        "| Strategy | Family | Trades | Trades/30d | WR | Avg W | Avg L | Exp R | PF | Net R | End RM | Return | Max DD | 8/mo+70 | Cost |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for _, r in frame.iterrows():
        pf = "∞" if np.isinf(r.profit_factor) else _fmt(r.profit_factor)
        lines.append(
            f"| {r.strategy} | {r.family} | {int(r.trades)} | {r.trades_per_30d:.2f} | {r.win_rate:.2f}% | "
            f"{_fmt(r.avg_win_r)} | {_fmt(r.avg_loss_r)} | {r.expectancy_r:.3f} | {pf} | {r.net_r:.2f} | "
            f"{r.ending_balance_rm:.2f} | {r.return_pct:.2f}% | {r.max_drawdown_pct:.2f}% | {r.target_8mo_70} | {r.cost_model} |"
        )
    return lines


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    full = load_m5_csv(DATA)
    observed_end = min(END, full.index.max() + pd.Timedelta(minutes=5))
    if observed_end <= START:
        raise RuntimeError("No 2026 rows in Dukascopy research CSV")
    m5 = full[full.index >= WARMUP].copy()

    _run_legacy(m5, observed_end)
    _run_v3_family(m5, observed_end)
    _run_asymmetry(m5, observed_end)
    _run_aplus(m5, observed_end)
    _run_structural_aplus(m5, observed_end)
    _run_structural_portfolios(m5, observed_end)
    _run_routes(m5, observed_end)
    _run_v4(observed_end)

    comparison = pd.DataFrame(results)
    comparison = comparison.sort_values(["ending_balance_rm", "profit_factor", "expectancy_r"], ascending=[False, False, False], na_position="last").reset_index(drop=True)
    comparison.to_csv(OUTPUT / "comparison.csv", index=False)

    all_trades = pd.concat(all_trade_frames, ignore_index=True) if all_trade_frames else pd.DataFrame(columns=["strategy", "family", "entry_time", "exit_time", "net_r", "balance_before_rm", "risk_rm", "pnl_rm", "balance_after_rm"])
    all_trades.to_csv(OUTPUT / "all_trades.csv", index=False)
    monthly = _monthly(all_trades, observed_end)
    monthly.to_csv(OUTPUT / "monthly.csv", index=False)

    lines = [
        "# CASIO — All Backtestable Strategies, 2026 Dukascopy RM100",
        "",
        f"Dataset: `{DATA}`. Counted entry window: **2026-01-01 UTC → {observed_end.isoformat()}**. Pre-2026 bars from {WARMUP.date()} are used only for causal warm-up.",
        "",
        "## Common money assumptions",
        "",
        "- Starting balance: **RM100 per strategy**, reset independently for every strategy/variant.",
        "- Risk: **5% of current equity per filled trade**, compounded trade by trade.",
        "- Stop-first handling is retained where the underlying replay defines same-bar stop/target collisions.",
        "- Most v3/structural engines include the repository's **1.0 bps round-trip** cost model. Legacy and v4 Python replays do not explicitly deduct transaction costs; that difference is shown in the Cost column.",
        "- This job does **not** optimize parameters on 2026. It replays the fixed named strategies/profiles already present in CASIO.",
        "",
        f"Backtested fixed strategies/variants: **{len(comparison)}**.",
        "",
        "## 2026 comparison",
        "",
        *_md_summary(comparison),
        "",
        "## Month-by-month",
        "",
        "The full month-by-month matrix is saved as `monthly.csv`. Below are months with at least one trade.",
        "",
        "| Strategy | Month | Trades | WR | Net R | P/L RM | Ending RM |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for _, r in monthly[monthly.trades > 0].iterrows():
        lines.append(
            f"| {r.strategy} | {r.month} | {int(r.trades)} | {_fmt(r.win_rate)}% | {r.net_r:.2f} | {r.pnl_rm:.2f} | {_fmt(r.ending_balance_rm)} |"
        )

    lines += [
        "",
        "## Pine inventory not directly executable in GitHub Actions",
        "",
        "GitHub Actions has no TradingView/Pine broker-emulator runtime. I therefore did **not fabricate Python results** for Pine files that do not have a maintained Python parity engine. Exact Pine-only items still requiring TradingView Strategy Tester are:",
        "",
        "- `pine/CASIO_XAUUSD_v1.pine` — Pine-only legacy implementation.",
        "- `pine/CASIO_XAUUSD_v2_MTF.pine` — Pine-only MTF implementation.",
        "- `pine/CASIO_XAUUSD_v5_MTF.pine` — Pine-only M15-setup/M5-execution challenger; no maintained Python parity engine yet.",
        "- `pine/CASIO_XAUUSD_TRADING_ASSISTANT.pine` and `pine/CASIO_XAUUSD_M5_FEED.pine` are indicators/feed helpers rather than independent Python backtest engines.",
        "",
        "`CASIO_XAUUSD_v3_BACKTEST.pine` / `v3_FAST.pine` are represented by the V3 M5 Python engine family; v4 is represented by the v4 confluence Python replay variants.",
        "",
        "## Audit files",
        "",
        "- `comparison.csv` — one row per strategy/variant.",
        "- `monthly.csv` — month-by-month results.",
        "- `all_trades.csv` — normalized 2026 trade/equity rows used for the RM100/5% calculation.",
        "",
        "This is research evidence, not a guarantee of future profitability. Many variants are closely related, so a high result from one profile is not independent confirmation by itself.",
    ]
    (OUTPUT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(comparison.to_string(index=False))
    print(f"Report written to {OUTPUT / 'REPORT.md'}")


if __name__ == "__main__":
    main()
