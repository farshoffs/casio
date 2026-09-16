from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .structural_portfolio_latest import (
    PORTFOLIO_TARGET,
    StructuralPortfolioConfig,
    _safe,
    metrics,
    prepare_features,
    replay,
    setup_frame,
)


PLAYBOOK_SETS = {
    "ALL": ("TREND_PULLBACK", "EXTERNAL_SWEEP", "SESSION_EXPANSION_RETEST"),
    "PULLBACK_SWEEP": ("TREND_PULLBACK", "EXTERNAL_SWEEP"),
    "PULLBACK_RETEST": ("TREND_PULLBACK", "SESSION_EXPANSION_RETEST"),
    "SWEEP_RETEST": ("EXTERNAL_SWEEP", "SESSION_EXPANSION_RETEST"),
    "PULLBACK": ("TREND_PULLBACK",),
    "SWEEP": ("EXTERNAL_SWEEP",),
    "RETEST": ("SESSION_EXPANSION_RETEST",),
}


# Small, hypothesis-driven grid. We deliberately do not optimize dozens of
# thresholds. The research question is whether the three structural playbooks
# can produce the target portfolio, not which 47th decimal backtests best.
PAYOFF_PROFILES = (
    (3.0, 3.0),
    (3.5, 3.5),
    (4.0, 4.0),
)


def _window_metrics(trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    result = metrics(trades, start, end)
    result["start"] = start
    result["end"] = end
    return result


def _target_distance(m: dict) -> float:
    """Lower is better. This is a research ranking, never an auto-deploy score."""
    trades = float(m.get("trades", 0) or 0)
    freq = float(m.get("trades_per_30d", 0) or 0)
    wr = m.get("win_rate")
    aw = m.get("avg_win_r")
    al = m.get("avg_loss_r")
    exp = m.get("expectancy_r")
    pf = m.get("profit_factor")

    score = abs(freq - 8.0) / 8.0
    score += max(0.0, 42.0 - float(wr or 0.0)) / 20.0
    score += max(0.0, 3.5 - float(aw or 0.0)) / 3.5
    score += max(0.0, float(al or 9.0) - 1.0)
    score += max(0.0, 0.70 - float(exp if exp is not None else -2.0)) / 0.70
    score += max(0.0, 2.0 - float(pf or 0.0)) / 2.0
    if trades < 8:
        score += (8.0 - trades) / 8.0
    return float(score)


def _meets_quality(m: dict) -> bool:
    return bool(
        (m.get("trades_per_30d") or 0) >= 6.0
        and (m.get("win_rate") or 0) >= 42.0
        and (m.get("avg_win_r") or 0) >= 3.30
        and (m.get("avg_loss_r") or 99) <= 1.15
        and (m.get("expectancy_r") or -99) >= 0.70
        and (m.get("profit_factor") or 0) >= 2.0
    )


def run(data_path: str | Path, output_dir: str | Path = "reports/structural-current") -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    m5 = load_m5_csv(data_path)
    end = m5.index.max() + pd.Timedelta(minutes=5)
    if end - m5.index.min() < pd.Timedelta(days=190):
        raise ValueError("Current-first research needs at least ~190 days so the earliest 60-day slice has warm-up history")

    windows = {
        "CURRENT_60D": (end - pd.Timedelta(days=60), end),
        "PREVIOUS_60D": (end - pd.Timedelta(days=120), end - pd.Timedelta(days=60)),
        "EARLIER_60D": (end - pd.Timedelta(days=180), end - pd.Timedelta(days=120)),
    }

    base = StructuralPortfolioConfig()
    features = prepare_features(m5, base)
    current_rows: list[dict] = []
    cache: dict[str, tuple[StructuralPortfolioConfig, tuple[str, ...], pd.DataFrame, pd.DataFrame]] = {}

    for target_r, runway_r in PAYOFF_PROFILES:
        cfg = replace(base, target_r=target_r, min_external_runway_r=runway_r)
        setups_all = setup_frame(features, cfg)
        for set_name, allowed in PLAYBOOK_SETS.items():
            setups = setups_all[setups_all.playbook.isin(allowed)].copy() if not setups_all.empty else setups_all.copy()
            trades = replay(m5, setups, cfg)
            key = f"T{target_r:.1f}_R{runway_r:.1f}_{set_name}"
            cache[key] = (cfg, allowed, setups, trades)
            a, b = windows["CURRENT_60D"]
            m = _window_metrics(trades, a, b)
            current_rows.append(
                {
                    "variant": key,
                    "target_r": target_r,
                    "runway_r": runway_r,
                    "playbooks": "+".join(allowed),
                    **m,
                    "target_distance": _target_distance(m),
                    "meets_current_quality": _meets_quality(m),
                }
            )

    current = pd.DataFrame(current_rows).sort_values(
        ["meets_current_quality", "target_distance", "expectancy_r", "profit_factor"],
        ascending=[False, True, False, False],
        na_position="last",
    )
    current.to_csv(out / "current_60d_variants.csv", index=False)

    if current.empty:
        raise RuntimeError("No structural variants were evaluated")

    selected = str(current.iloc[0].variant)
    cfg, allowed, setups, trades = cache[selected]

    frozen_rows = []
    playbook_rows = []
    for window_name, (a, b) in windows.items():
        m = _window_metrics(trades, a, b)
        frozen_rows.append({"variant": selected, "window": window_name, **m, "meets_quality": _meets_quality(m)})
        for playbook in ("TREND_PULLBACK", "EXTERNAL_SWEEP", "SESSION_EXPANSION_RETEST"):
            if trades.empty or "playbook" not in trades.columns:
                x = trades
            else:
                x = trades[trades.playbook.eq(playbook)].copy()
            playbook_rows.append({"variant": selected, "window": window_name, "playbook": playbook, **_window_metrics(x, a, b)})

    frozen = pd.DataFrame(frozen_rows)
    per_playbook = pd.DataFrame(playbook_rows)
    frozen.to_csv(out / "selected_variant_backwards.csv", index=False)
    per_playbook.to_csv(out / "selected_variant_playbooks.csv", index=False)
    setups.to_csv(out / "selected_setups.csv", index=False)
    trades.to_csv(out / "selected_trades.csv", index=False)

    summary = {
        "coverage": {"rows": len(m5), "start": m5.index.min(), "end": m5.index.max()},
        "research_order": ["CURRENT_60D", "PREVIOUS_60D", "EARLIER_60D"],
        "portfolio_target": PORTFOLIO_TARGET,
        "selection_rule": "Rank on latest 60 days only; freeze the selected rules before looking backward. No live auto-deploy.",
        "selected_variant": selected,
        "selected_config": {
            "target_r": cfg.target_r,
            "min_external_runway_r": cfg.min_external_runway_r,
            "playbooks": list(allowed),
        },
        "selected_backwards": frozen.to_dict(orient="records"),
        "selected_playbook_breakdown": per_playbook.to_dict(orient="records"),
        "current_top10": current.head(10).to_dict(orient="records"),
        "auto_deploy": False,
        "note": "Current-first structural research. No ADX/RSI. Latest period is development; earlier windows test backward stability, not forward OOS proof.",
    }
    (out / "summary.json").write_text(json.dumps(_safe(summary), indent=2), encoding="utf-8")

    lines = [
        "# CASIO Structural Portfolio — Current First",
        "",
        f"Coverage: {m5.index.min().isoformat()} -> {m5.index.max().isoformat()} ({len(m5):,} M5 bars)",
        "",
        f"Selected on latest 60d: `{selected}`",
        "",
        "## Frozen backwards check",
        "",
        "```text",
        frozen.to_string(index=False),
        "```",
        "",
        "## Playbook contribution",
        "",
        "```text",
        per_playbook.to_string(index=False),
        "```",
        "",
        "No production/live strategy was changed.",
    ]
    (out / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    return summary


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--output", default="reports/structural-current")
    a = p.parse_args()
    print(json.dumps(_safe(run(a.data, a.output)), indent=2))


if __name__ == "__main__":
    main()
