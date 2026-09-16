from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json

import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .structural_portfolio_latest import StructuralPortfolioConfig, _safe, metrics, prepare_features, replay
from .structural_frequency_research import setup_frame_mode


# Research-only causal routers. No year/date is used as a trading rule.
# Secondary-feed 2024/2025 results are discovery data, not untouched OOS.
ROUTERS = (
    "QUALITY_CORE",
    "LONDON_CORE",
    "ROBUST_CORE",
)

TARGET = {
    "trades_per_30d": 8.0,
    "win_rate_low": 42.0,
    "win_rate_high": 50.0,
    "avg_win_r": 3.5,
    "avg_loss_r_max": 1.0,
    "expectancy_r_min": 0.70,
    "profit_factor_min": 2.0,
}


def _meets_quality(m: dict) -> bool:
    return bool(
        (m.get("win_rate") or 0) >= 42.0
        and (m.get("avg_win_r") or 0) >= 3.0
        and (m.get("avg_loss_r") or 99) <= 1.15
        and (m.get("expectancy_r") or -99) >= 0.70
        and (m.get("profit_factor") or 0) >= 2.0
    )


def _combine(parts: list[pd.DataFrame], cooldown_bars: int) -> pd.DataFrame:
    nonempty = [x.copy() for x in parts if not x.empty]
    if not nonempty:
        return pd.DataFrame()
    x = pd.concat(nonempty, ignore_index=True)
    priority = {"EXTERNAL_SWEEP": 0, "TREND_PULLBACK": 1, "SESSION_EXPANSION_RETEST": 2}
    x["_priority"] = x.playbook.map(priority).fillna(9)
    x = x.sort_values(["signal_i", "_priority"]).drop_duplicates(
        ["signal_i", "direction", "playbook"], keep="first"
    )
    keep: list[int] = []
    last = {1: -10**9, -1: -10**9}
    for idx, row in x.iterrows():
        d = int(row.direction)
        i = int(row.signal_i)
        if i - last[d] < cooldown_bars:
            continue
        keep.append(idx)
        last[d] = i
    return x.loc[keep].drop(columns=["_priority"]).sort_values("signal_i").reset_index(drop=True)


def _router_setups(
    displacement: pd.DataFrame,
    strict: pd.DataFrame,
    cfg: StructuralPortfolioConfig,
    router: str,
) -> pd.DataFrame:
    # External-sweep discovery was materially more robust when a real M5 FVG was
    # required, especially in London. Body-only sweep entries remain excluded.
    strict_london_sweep = strict[
        strict.playbook.eq("EXTERNAL_SWEEP") & strict.session.eq("LONDON")
    ].copy()

    pullbacks = displacement[displacement.playbook.eq("TREND_PULLBACK")].copy()

    if router == "ROBUST_CORE":
        # Broadest causal core: displacement-retrace pullbacks in either primary
        # session + strict-FVG London sweeps.
        pb = pullbacks
    elif router == "LONDON_CORE":
        # Same techniques, but London only.
        pb = pullbacks[pullbacks.session.eq("LONDON")].copy()
    elif router == "QUALITY_CORE":
        # High-quality pullback branch: a real FVG, or H4 expansion in the
        # moderate 0.7-0.9 normalized-range band. This is a discovery hypothesis,
        # not a production threshold.
        pb = pullbacks[
            pullbacks.entry_model.eq("FVG50")
            | pullbacks.h4_range_ratio12.between(0.70, 0.90, inclusive="left")
        ].copy()
    else:
        raise ValueError(f"Unknown router: {router}")

    # Session-expansion retest is intentionally OFF: the current implementation
    # did not show an independent edge on the secondary feed. It must earn its
    # place through a redesigned causal retest study rather than being forced in
    # to manufacture frequency.
    return _combine([pb, strict_london_sweep], cfg.cooldown_bars)


def run(data_path: str | Path, output_dir: str | Path = "reports/structural-regime-router") -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    m5 = load_m5_csv(data_path)
    cfg = replace(StructuralPortfolioConfig(), target_r=3.5, min_external_runway_r=3.5)
    f = prepare_features(m5, cfg)

    displacement = setup_frame_mode(f, cfg, "DISPLACEMENT_RETRACE")
    strict = setup_frame_mode(f, cfg, "STRICT_FVG")

    end = m5.index.max() + pd.Timedelta(minutes=5)
    latest60 = (end - pd.Timedelta(days=60), end)
    periods = [("LATEST_60D", *latest60)]
    for year in (2026, 2025, 2024):
        a = pd.Timestamp(f"{year}-01-01", tz="UTC")
        b = min(pd.Timestamp(f"{year + 1}-01-01", tz="UTC"), end)
        if b > a:
            periods.append((str(year), a, b))

    rows: list[dict] = []
    caches: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}
    for router in ROUTERS:
        setups = _router_setups(displacement, strict, cfg, router)
        trades = replay(m5, setups, cfg)
        caches[router] = (setups, trades)
        for label, a, b in periods:
            m = metrics(trades, a, b)
            rows.append({
                "router": router,
                "period": label,
                **m,
                "quality_floor_met": _meets_quality(m),
            })

    history = pd.DataFrame(rows)
    history.to_csv(out / "router_history.csv", index=False)

    # Latest-first selection is recorded, but not auto-deployed. The secondary
    # archive ends Jan-2026, so this selection is not a substitute for current
    # Sep-2026 Dukascopy validation.
    latest = history[history.period.eq("LATEST_60D")].copy()
    latest["distance"] = (
        (latest.trades_per_30d.fillna(0) - 8.0).abs() / 8.0
        + (42.0 - latest.win_rate.fillna(0)).clip(lower=0) / 20.0
        + (0.70 - latest.expectancy_r.fillna(-9)).clip(lower=0) / 0.70
        + (2.0 - latest.profit_factor.fillna(0)).clip(lower=0) / 2.0
    )
    latest = latest.sort_values(
        ["quality_floor_met", "distance", "expectancy_r", "profit_factor"],
        ascending=[False, True, False, False],
        na_position="last",
    )
    selected = str(latest.iloc[0].router)
    setups, trades = caches[selected]
    setups.to_csv(out / "selected_setups.csv", index=False)
    trades.to_csv(out / "selected_trades.csv", index=False)

    summary = {
        "feed": "secondary_octafx_mt4_utc_normalized",
        "coverage": {"rows": len(m5), "start": m5.index.min(), "end": m5.index.max()},
        "target": TARGET,
        "routers": list(ROUTERS),
        "selected_latest_first": selected,
        "history": history.to_dict(orient="records"),
        "auto_deploy": False,
        "production_changed": False,
        "notes": [
            "No ADX/RSI routing.",
            "Trend pullback uses displacement/retracement.",
            "External sweep requires strict FVG and London session.",
            "Current session-expansion retest implementation is disabled until it proves independent edge.",
            "2024/2025/Jan-2026 secondary data are discovery/robustness data, not untouched OOS.",
        ],
    }
    (out / "summary.json").write_text(json.dumps(_safe(summary), indent=2), encoding="utf-8")

    report = [
        "# CASIO Structural Regime Router Research",
        "",
        "Research-only. No production or TradingView promotion.",
        "",
        "Core causal routing:",
        "- TREND_PULLBACK -> displacement + retracement",
        "- EXTERNAL_SWEEP -> strict M5 FVG + London",
        "- SESSION_EXPANSION_RETEST -> disabled pending redesign",
        "",
        "## Latest -> backwards",
        "",
        "```text",
        history.to_string(index=False),
        "```",
        "",
        f"Latest-first research selection: `{selected}`",
        "",
        "The secondary archive ends 2026-01-30. Current Sep-2026 decisions must still be validated on current Dukascopy data.",
    ]
    (out / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    return summary


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output", default="reports/structural-regime-router")
    a = p.parse_args()
    print(json.dumps(_safe(run(a.data, a.output)), indent=2))


if __name__ == "__main__":
    main()
