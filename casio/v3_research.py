from __future__ import annotations

from dataclasses import asdict, replace
from itertools import product
from pathlib import Path
import json
import math
import random

import numpy as np
import pandas as pd

from .v3_backtest import backtest_signals, metrics, mode_stability, year_stability
from .v3_core import SESSION_POLICIES, SESSION_PROFILES, V3Config, prepare_features
from .v3_strategy import signals_for_config


def _profile(base: V3Config, name: str) -> V3Config:
    a, b, c, d = SESSION_PROFILES[name]
    return replace(base, london_start=a, london_end=b, new_york_start=c, new_york_end=d)


def _config_id(cfg: V3Config) -> str:
    session = next(
        (
            k
            for k, v in SESSION_PROFILES.items()
            if v == (cfg.london_start, cfg.london_end, cfg.new_york_start, cfg.new_york_end)
        ),
        "custom",
    )
    return (
        f"h4={int(cfg.h4_veto)}|value={cfg.h1_value_model}|sweep={cfg.sweep_fresh_bars}"
        f"|m5={int(cfg.use_m5_confirmation)}|rr={cfg.intraday_min_rr:.2f}"
        f"|policy={cfg.session_policy}|session={session}"
    )


def _safe(obj):
    if isinstance(obj, dict):
        return {str(k): _safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        return v if math.isfinite(v) else None
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return obj


def _clip(v):
    if v is None or not math.isfinite(v):
        return 0.0
    return max(0.0, min(1.0, v))


def session_stability(trades: pd.DataFrame) -> dict:
    if trades.empty or "session" not in trades:
        return {"positive_session_ratio": None, "sessions": {}}
    sessions = {str(k): metrics(g) for k, g in trades.groupby("session")}
    exps = [m["expectancy_r"] for m in sessions.values() if m["expectancy_r"] is not None]
    return {
        "positive_session_ratio": sum(v > 0 for v in exps) / len(exps) if exps else None,
        "sessions": sessions,
    }


def robustness_score(m: dict, folds: list[dict], ys: dict, ms: dict, ss: dict) -> float:
    exp = m.get("expectancy_r")
    pf = m.get("profit_factor")
    dd = m.get("max_drawdown_r")
    n = m.get("trades", 0)
    fexp = [x["expectancy_r"] for x in folds if x.get("expectancy_r") is not None]
    favg = float(np.mean(fexp)) if fexp else None
    fpos = sum(v > 0 for v in fexp) / len(fexp) if fexp else 0.0
    score = (
        25 * _clip(((exp if exp is not None else -.05) + .05) / .55)
        + 15 * _clip(((pf or 0) - 1) / 1)
        + 15 * _clip(1 - ((dd if dd is not None else 99) / 15))
        + 20 * _clip(((favg if favg is not None else -.05) + .05) / .55)
        + 10 * fpos
        + 5 * min(1, n / 250)
        + 5 * (ys.get("positive_year_ratio") or 0)
        + 3 * (ms.get("positive_mode_ratio") or 0)
        + 2 * (ss.get("positive_session_ratio") or 0)
    )
    return round(float(score), 2)


def monte_carlo_bootstrap(
    trades: pd.DataFrame, simulations: int = 1000, seed: int = 42
) -> tuple[pd.DataFrame, dict]:
    """Bootstrap the selected trade-R distribution to stress sequence/drawdown risk.

    This is a robustness diagnostic, not a forecast or probability calibration.
    """
    if trades.empty or "net_r" not in trades:
        empty = pd.DataFrame(columns=["simulation", "total_r", "max_drawdown_r", "min_equity_r"])
        return empty, {
            "simulations": 0,
            "trades_per_simulation": 0,
            "probability_positive_total": None,
            "total_r_p05": None,
            "total_r_p50": None,
            "total_r_p95": None,
            "max_drawdown_r_p50": None,
            "max_drawdown_r_p90": None,
            "max_drawdown_r_p95": None,
        }

    r = pd.to_numeric(trades["net_r"], errors="coerce").dropna().to_numpy(dtype=float)
    if len(r) == 0:
        return monte_carlo_bootstrap(pd.DataFrame(), simulations, seed)

    rng = np.random.default_rng(seed)
    rows = []
    for i in range(simulations):
        sample = rng.choice(r, size=len(r), replace=True)
        equity = np.concatenate(([0.0], np.cumsum(sample)))
        peak = np.maximum.accumulate(equity)
        drawdown = peak - equity
        rows.append(
            {
                "simulation": i + 1,
                "total_r": float(equity[-1]),
                "max_drawdown_r": float(drawdown.max()),
                "min_equity_r": float(equity.min()),
            }
        )

    frame = pd.DataFrame(rows)
    q = frame.quantile([.05, .50, .90, .95], numeric_only=True)
    summary = {
        "simulations": simulations,
        "trades_per_simulation": int(len(r)),
        "probability_positive_total": float((frame.total_r > 0).mean()),
        "total_r_p05": float(q.loc[.05, "total_r"]),
        "total_r_p50": float(q.loc[.50, "total_r"]),
        "total_r_p95": float(q.loc[.95, "total_r"]),
        "max_drawdown_r_p50": float(q.loc[.50, "max_drawdown_r"]),
        "max_drawdown_r_p90": float(q.loc[.90, "max_drawdown_r"]),
        "max_drawdown_r_p95": float(q.loc[.95, "max_drawdown_r"]),
        "note": "Bootstrap diagnostic from historical net-R trades; not a calibrated forecast.",
    }
    return frame, summary


def _session_rows(label: str, trades: pd.DataFrame) -> list[dict]:
    if trades.empty or "session" not in trades:
        return []
    rows = []
    for session, group in trades.groupby("session"):
        rows.append({"sample": label, "session": session, **metrics(group)})
    return rows


def run_research(
    m5: pd.DataFrame,
    output_dir: str | Path,
    max_candidates: int = 64,
    cost_bps: float = 1.0,
    seed: int = 42,
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Current live baseline: adaptive 24h session overlay on the v2 MTF core.
    base = V3Config(round_trip_cost_bps=cost_bps)
    features = prepare_features(m5)
    start = features.index.min() + pd.Timedelta(days=30)
    finish = features.index.max() + pd.Timedelta(minutes=15)
    cutoff = start + (finish - start) * .80
    span = cutoff - start
    wf_windows = [
        (start + span * a, start + span * b)
        for a, b in [(0.40, 0.60), (0.60, 0.80), (0.80, 1.00)]
    ]
    cache = {}

    def evaluate(cfg: V3Config, a=start, b=cutoff):
        if cfg not in cache:
            sig = signals_for_config(features, cfg)
            cache[cfg] = (sig, backtest_signals(m5, sig, cfg))
        sig, all_trades = cache[cfg]
        t = (
            all_trades[(all_trades["entry_time"] >= a) & (all_trades["entry_time"] < b)].copy()
            if not all_trades.empty
            else all_trades
        )
        return sig, t, metrics(t)

    # Direct ablations answer one question at a time before the combination search.
    ablations = [
        ("baseline", "adaptive_24h", base),
        ("session_policy", "primary_only", replace(base, session_policy="primary_only")),
        ("h4_veto", "off", replace(base, h4_veto=False)),
        ("h1_value_model", "pivot", replace(base, h1_value_model="pivot")),
        ("m5_confirmation", "off", replace(base, use_m5_confirmation=False)),
    ]
    ablations += [
        ("sweep_fresh_bars", str(v), replace(base, sweep_fresh_bars=v))
        for v in [1, 2, 4, 5]
    ]
    ablations += [
        ("intraday_min_rr", str(v), replace(base, intraday_min_rr=v))
        for v in [2.0, 2.25, 2.75, 3.0]
    ]
    ablations += [("sessions", p, _profile(base, p)) for p in ["early", "late", "wide"]]

    rows = []
    for qname, variant, cfg in ablations:
        _, t, m = evaluate(cfg)
        intra = metrics(t[t["mode"] == "INTRADAY"]) if not t.empty else metrics(t)
        scalp = metrics(t[t["mode"] == "SCALPING"]) if not t.empty else metrics(t)
        ss = session_stability(t)
        rows.append(
            {
                "question": qname,
                "variant": variant,
                "config_id": _config_id(cfg),
                **m,
                "intraday_expectancy_r": intra["expectancy_r"],
                "scalp_expectancy_r": scalp["expectancy_r"],
                "scalp_trades": scalp["trades"],
                "positive_session_ratio": ss["positive_session_ratio"],
            }
        )
    abl = pd.DataFrame(rows)
    abl.to_csv(out / "ablations.csv", index=False)

    # Bounded combination search. Session policy is now itself a research dimension.
    grid = []
    for h4, value, sweep, m5c, rr, policy, session in product(
        [True, False],
        ["ema_atr", "pivot"],
        [1, 2, 3, 4, 5],
        [True, False],
        [2.0, 2.25, 2.5, 2.75, 3.0],
        SESSION_POLICIES,
        SESSION_PROFILES,
    ):
        grid.append(
            _profile(
                replace(
                    base,
                    h4_veto=h4,
                    h1_value_model=value,
                    sweep_fresh_bars=sweep,
                    use_m5_confirmation=m5c,
                    intraday_min_rr=rr,
                    session_policy=policy,
                ),
                session,
            )
        )

    rng = random.Random(seed)
    rng.shuffle(grid)
    chosen = [base]
    for cfg in grid:
        if cfg not in chosen:
            chosen.append(cfg)
        if len(chosen) >= max_candidates:
            break

    cand, wf_rows = [], []
    for cfg in chosen:
        _, t, m = evaluate(cfg)
        folds = []
        for i, (a, b) in enumerate(wf_windows, 1):
            _, _, fm = evaluate(cfg, a, b)
            folds.append(fm)
            wf_rows.append(
                {
                    "config_id": _config_id(cfg),
                    "fold": i,
                    "start": a.isoformat(),
                    "end": b.isoformat(),
                    **fm,
                }
            )
        ys, ms, ss = year_stability(t), mode_stability(t), session_stability(t)
        cand.append(
            {
                "config_id": _config_id(cfg),
                "robustness_score": robustness_score(m, folds, ys, ms, ss),
                **asdict(cfg),
                **m,
                "positive_year_ratio": ys["positive_year_ratio"],
                "positive_mode_ratio": ms["positive_mode_ratio"],
                "positive_session_ratio": ss["positive_session_ratio"],
                "positive_wf_ratio": sum(
                    (x.get("expectancy_r") if x.get("expectancy_r") is not None else -999) > 0
                    for x in folds
                )
                / len(folds),
            }
        )

    candidates = pd.DataFrame(cand).sort_values(
        ["robustness_score", "expectancy_r", "trades"],
        ascending=[False, False, False],
    )
    candidates.to_csv(out / "candidates.csv", index=False)
    pd.DataFrame(wf_rows).to_csv(out / "walk_forward.csv", index=False)

    best_row = candidates.iloc[0].to_dict()
    best = next(c for c in chosen if _config_id(c) == best_row["config_id"])
    _, best_dev_t, best_dev = evaluate(best)
    _, base_dev_t, base_dev = evaluate(base)
    _, best_oos_t, best_oos = evaluate(best, cutoff, finish)
    _, base_oos_t, base_oos = evaluate(base, cutoff, finish)
    oos_intra = metrics(best_oos_t[best_oos_t["mode"] == "INTRADAY"]) if not best_oos_t.empty else metrics(best_oos_t)
    oos_scalp = metrics(best_oos_t[best_oos_t["mode"] == "SCALPING"]) if not best_oos_t.empty else metrics(best_oos_t)

    ok = (
        best_oos["trades"] >= 30
        and (best_oos["expectancy_r"] or -999) > 0
        and (best_oos["profit_factor"] or 0) > 1
        and best_row["positive_wf_ratio"] >= 2 / 3
    )
    better = ok and (
        (best_oos["expectancy_r"] or -999) > (base_oos["expectancy_r"] or -999) + .05
        or (best_oos["max_drawdown_r"] or 999) < (base_oos["max_drawdown_r"] or 999) * .85
    )
    verdict = "CANDIDATE_FOR_REVIEW" if better else (
        "ROBUST_BUT_NOT_MATERIALLY_BETTER" if ok else "REJECT_OR_INSUFFICIENT"
    )

    best_dev_t.to_csv(out / "best_candidate_dev_trades.csv", index=False)
    best_oos_t.to_csv(out / "best_candidate_oos_trades.csv", index=False)

    session_rows = (
        _session_rows("baseline_dev", base_dev_t)
        + _session_rows("baseline_oos", base_oos_t)
        + _session_rows("selected_dev", best_dev_t)
        + _session_rows("selected_oos", best_oos_t)
    )
    pd.DataFrame(session_rows).to_csv(out / "session_performance.csv", index=False)

    mc_frame, mc_summary = monte_carlo_bootstrap(best_dev_t, simulations=1000, seed=seed)
    mc_frame.to_csv(out / "monte_carlo.csv", index=False)
    (out / "monte_carlo_summary.json").write_text(
        json.dumps(_safe(mc_summary), indent=2), encoding="utf-8"
    )

    base_sig = signals_for_config(features, base)
    costs = []
    for mult in [0, .5, 1, 1.5, 2]:
        c = replace(base, round_trip_cost_bps=cost_bps * mult)
        t = backtest_signals(m5, base_sig, c, start, finish)
        scalp = t[t["mode"] == "SCALPING"] if not t.empty else t
        costs.append(
            {
                "cost_multiplier": mult,
                "round_trip_cost_bps": c.round_trip_cost_bps,
                **metrics(scalp),
            }
        )
    cost_df = pd.DataFrame(costs)
    cost_df.to_csv(out / "scalping_cost_sensitivity.csv", index=False)

    baseline = abl[abl["question"] == "baseline"].iloc[0].to_dict()

    def best_tested(question, baseline_variant):
        x = abl[abl["question"] == question].copy()
        b = dict(baseline)
        b.update(question=question, variant=baseline_variant)
        x = pd.concat([pd.DataFrame([b]), x], ignore_index=True)
        x["sort"] = pd.to_numeric(x["expectancy_r"], errors="coerce").fillna(-999)
        r = x.sort_values(
            ["sort", "profit_factor", "trades"], ascending=[False, False, False]
        ).iloc[0].to_dict()
        r.pop("sort", None)
        return _safe(r)

    priority = {
        "1_h4_veto": {"best_tested": best_tested("h4_veto", "on")},
        "2_h1_value_model": {
            "best_tested": best_tested("h1_value_model", "ema_atr"),
            "note": "pivot is a causal 2-left/2-right pivot-zone proxy",
        },
        "3_sessions": {
            "session_policy": {
                "best_tested": best_tested("session_policy", "adaptive_24h"),
                "tested": list(SESSION_POLICIES),
                "note": "adaptive_24h keeps normal London/NY rules but uses stricter trend exceptions in Asia/transition hours; Scalping remains regime-driven 24h",
            },
            "primary_windows": {
                "best_tested": best_tested("sessions", "baseline"),
                "tested_profiles": SESSION_PROFILES,
            },
            "selected_dev_by_session": session_stability(best_dev_t),
            "selected_oos_by_session": session_stability(best_oos_t),
        },
        "4_sweep_fresh_bars": {
            "best_tested": best_tested("sweep_fresh_bars", "3"),
            "tested": [1, 2, 3, 4, 5],
        },
        "5_m5_confirmation": {"best_tested": best_tested("m5_confirmation", "on")},
        "6_intraday_min_rr": {
            "best_tested": best_tested("intraday_min_rr", "2.5"),
            "tested": [2.0, 2.25, 2.5, 2.75, 3.0],
            "note": "adaptive Asia/transition exceptions use their own stricter 3.0R defaults",
        },
        "7_scalping_after_costs": {
            "sensitivity": _safe(cost_df.to_dict(orient="records"))
        },
        "8_multi_year_regime_stability": {
            "years": year_stability(best_dev_t),
            "modes": mode_stability(best_dev_t),
            "sessions": session_stability(best_dev_t),
            "monte_carlo": mc_summary,
        },
    }
    (out / "priority_questions.json").write_text(
        json.dumps(_safe(priority), indent=2), encoding="utf-8"
    )

    summary = {
        "product_version": "CASIO v3",
        "baseline_rule_set": "v2 regime-first MTF core + v3 adaptive 24h session overlay",
        "data_requirement": "M5 OHLC with UTC bar-open timestamps; M15/H1/H4 rebuilt causally",
        "cost_model": {
            "round_trip_cost_bps": cost_bps,
            "note": "configurable research assumption, not broker-identical",
        },
        "development_window": {"start": start, "end": cutoff},
        "final_oos_window": {"start": cutoff, "end": finish},
        "baseline_dev": base_dev,
        "baseline_oos": base_oos,
        "baseline_dev_sessions": session_stability(base_dev_t),
        "baseline_oos_sessions": session_stability(base_oos_t),
        "selected_config": asdict(best),
        "selected_config_id": _config_id(best),
        "selected_robustness_score": best_row["robustness_score"],
        "selected_dev": metrics(best_dev_t),
        "selected_oos": best_oos,
        "selected_oos_intraday": oos_intra,
        "selected_oos_scalping": oos_scalp,
        "selected_dev_sessions": session_stability(best_dev_t),
        "selected_oos_sessions": session_stability(best_oos_t),
        "monte_carlo": mc_summary,
        "verdict": verdict,
        "auto_deploy": False,
        "guardrail": "Research ranks candidates; it never rewrites or deploys live Pine automatically.",
    }
    (out / "research_summary.json").write_text(
        json.dumps(_safe(summary), indent=2), encoding="utf-8"
    )
    (out / "best_candidate.json").write_text(
        json.dumps(
            _safe({"config": asdict(best), "config_id": _config_id(best), "verdict": verdict}),
            indent=2,
        ),
        encoding="utf-8",
    )

    report = [
        "# CASIO v3 Research Report",
        "",
        "> v3 product; v2 regime-first MTF core with adaptive 24h session handling.",
        "",
        f"- Verdict: **{verdict}**",
        f"- Candidate: `{_config_id(best)}`",
        f"- Robustness score: **{best_row['robustness_score']} / 100**",
        f"- Final OOS trades: **{best_oos['trades']}**",
        f"- Final OOS expectancy: **{best_oos['expectancy_r']} R**",
        f"- Monte Carlo median max DD: **{mc_summary.get('max_drawdown_r_p50')} R**",
        f"- Monte Carlo 95th percentile max DD: **{mc_summary.get('max_drawdown_r_p95')} R**",
        "",
        "Session-specific results are written to session_performance.csv. The final OOS segment is not used to rank candidates. Monte Carlo is a bootstrap diagnostic, not a forecast. No candidate is auto-deployed.",
    ]
    (out / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    return _safe(summary)
