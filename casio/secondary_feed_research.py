from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json

import pandas as pd

from .v3_core import load_m5_csv
from .structural_portfolio_latest import StructuralPortfolioConfig, _safe, metrics, prepare_features, replay
from .structural_frequency_research import MODES, setup_frame_mode


PLAYBOOK_SETS = {
    "ALL": ("TREND_PULLBACK", "EXTERNAL_SWEEP", "SESSION_EXPANSION_RETEST"),
    "PULLBACK_SWEEP": ("TREND_PULLBACK", "EXTERNAL_SWEEP"),
    "PULLBACK_RETEST": ("TREND_PULLBACK", "SESSION_EXPANSION_RETEST"),
    "SWEEP_RETEST": ("EXTERNAL_SWEEP", "SESSION_EXPANSION_RETEST"),
    "PULLBACK": ("TREND_PULLBACK",),
    "SWEEP": ("EXTERNAL_SWEEP",),
    "RETEST": ("SESSION_EXPANSION_RETEST",),
}


def _distance(m: dict) -> float:
    freq = float(m.get("trades_per_30d", 0) or 0)
    wr = float(m.get("win_rate", 0) or 0)
    aw = float(m.get("avg_win_r", 0) or 0)
    al = float(m.get("avg_loss_r", 9) or 9)
    exp = float(m.get("expectancy_r", -9) if m.get("expectancy_r") is not None else -9)
    pf = float(m.get("profit_factor", 0) or 0)
    return float(
        abs(freq - 8.0) / 8.0
        + max(0.0, 42.0 - wr) / 20.0
        + max(0.0, 3.30 - aw) / 3.30
        + max(0.0, aw - 3.80) / 3.80
        + max(0.0, al - 1.15)
        + max(0.0, 0.70 - exp) / 0.70
        + max(0.0, 2.0 - pf) / 2.0
    )


def _meets(m: dict) -> bool:
    return bool(
        6.0 <= (m.get("trades_per_30d") or 0) <= 10.5
        and (m.get("win_rate") or 0) >= 42.0
        and (m.get("avg_win_r") or 0) >= 3.30
        and (m.get("avg_loss_r") or 99) <= 1.15
        and (m.get("expectancy_r") or -99) >= 0.70
        and (m.get("profit_factor") or 0) >= 2.0
    )


def run(data_path: str | Path, output_dir: str | Path = "reports/structural-secondary") -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    m5 = load_m5_csv(data_path)
    cfg = replace(StructuralPortfolioConfig(), target_r=3.5, min_external_runway_r=3.5)
    end = m5.index.max() + pd.Timedelta(minutes=5)
    latest60 = (end - pd.Timedelta(days=60), end)

    # Full history remains available as a robustness base, but the requested
    # review is current-to-backwards: latest 60d first, then 2026, 2025, 2024.
    f = prepare_features(m5, cfg)
    candidates = []
    cache: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}

    for mode in MODES:
        setups_all = setup_frame_mode(f, cfg, mode)
        for set_name, allowed in PLAYBOOK_SETS.items():
            setups = setups_all[setups_all.playbook.isin(allowed)].copy() if not setups_all.empty else setups_all.copy()
            trades = replay(m5, setups, cfg)
            key = f"{mode}__{set_name}"
            cache[key] = (setups, trades)
            a, b = latest60
            m = metrics(trades, a, b)
            candidates.append({
                "variant": key,
                "mode": mode,
                "playbooks": "+".join(allowed),
                **m,
                "target_distance": _distance(m),
                "meets_target": _meets(m),
            })

    current = pd.DataFrame(candidates).sort_values(
        ["meets_target", "target_distance", "expectancy_r", "profit_factor"],
        ascending=[False, True, False, False],
        na_position="last",
    )
    current.to_csv(out / "latest60_candidates.csv", index=False)

    selected = str(current.iloc[0].variant)
    selected_setups, selected_trades = cache[selected]

    # Also keep the exact current TradingView research assistant technique visible.
    assistant_key = "DISPLACEMENT_RETRACE__ALL"
    assistant_setups, assistant_trades = cache[assistant_key]

    periods: list[tuple[str, pd.Timestamp, pd.Timestamp]] = [("LATEST_60D", *latest60)]
    for year in (2026, 2025, 2024):
        a = pd.Timestamp(f"{year}-01-01", tz="UTC")
        b = min(pd.Timestamp(f"{year + 1}-01-01", tz="UTC"), end)
        if b > a:
            periods.append((str(year), a, b))

    rows = []
    for label, a, b in periods:
        rows.append({"portfolio": "LATEST_FIRST_SELECTED", "variant": selected, "period": label, **metrics(selected_trades, a, b)})
        rows.append({"portfolio": "CURRENT_ASSISTANT_REFERENCE", "variant": assistant_key, "period": label, **metrics(assistant_trades, a, b)})
    backwards = pd.DataFrame(rows)
    backwards.to_csv(out / "latest_to_2024.csv", index=False)

    # Technique-level yearly comparison without choosing a winner after seeing old years.
    mode_rows = []
    for mode in MODES:
        setups_all = setup_frame_mode(f, cfg, mode)
        trades_all = replay(m5, setups_all, cfg)
        for label, a, b in periods:
            mode_rows.append({"mode": mode, "period": label, **metrics(trades_all, a, b)})
    pd.DataFrame(mode_rows).to_csv(out / "mode_history.csv", index=False)

    # Playbook contribution for the two decision-relevant portfolios.
    pb_rows = []
    for portfolio, key, trades in [
        ("LATEST_FIRST_SELECTED", selected, selected_trades),
        ("CURRENT_ASSISTANT_REFERENCE", assistant_key, assistant_trades),
    ]:
        for label, a, b in periods:
            for pb in ("TREND_PULLBACK", "EXTERNAL_SWEEP", "SESSION_EXPANSION_RETEST"):
                t = trades[trades.playbook.eq(pb)].copy() if not trades.empty else trades.copy()
                pb_rows.append({"portfolio": portfolio, "variant": key, "period": label, "playbook": pb, **metrics(t, a, b)})
    pd.DataFrame(pb_rows).to_csv(out / "playbook_history.csv", index=False)

    selected_setups.to_csv(out / "selected_setups.csv", index=False)
    selected_trades.to_csv(out / "selected_trades.csv", index=False)
    assistant_setups.to_csv(out / "assistant_reference_setups.csv", index=False)
    assistant_trades.to_csv(out / "assistant_reference_trades.csv", index=False)

    summary = {
        "feed": "secondary_octafx_mt4_utc_normalized",
        "coverage": {"rows": len(m5), "start": m5.index.min(), "end": m5.index.max()},
        "research_order": ["LATEST_60D", "2026", "2025", "2024"],
        "target": {
            "trades_per_30d": 8.0,
            "win_rate": "42-50%",
            "avg_win_r": 3.5,
            "avg_loss_r_max": 1.0,
            "expectancy_r_min": 0.70,
            "profit_factor_min": 2.0,
        },
        "selected_latest_first": selected,
        "assistant_reference": assistant_key,
        "latest60_candidates_top10": current.head(10).to_dict(orient="records"),
        "latest_to_2024": backwards.to_dict(orient="records"),
        "auto_deploy": False,
        "note": "Secondary broker feed only. Never merge into canonical Dukascopy CSV. Latest data ends 2026-01-30, so 2026 is partial and is not today's Sep-2026 market.",
    }
    (out / "summary.json").write_text(json.dumps(_safe(summary), indent=2), encoding="utf-8")

    report = [
        "# CASIO secondary-feed structural research — latest first",
        "",
        f"Coverage: {m5.index.min().isoformat()} -> {m5.index.max().isoformat()} ({len(m5):,} M5 bars)",
        "",
        "This is the separate OctaFX/Octa Markets MT4 robustness base. It is not merged with canonical Dukascopy data.",
        "",
        f"Latest-first selected candidate: `{selected}`",
        "",
        "## Latest -> 2024 frozen comparison",
        "",
        "```text",
        backwards.to_string(index=False),
        "```",
        "",
        "The secondary feed ends on 2026-01-30. The 2026 row is therefore partial and must not be described as current Sep-2026 performance.",
        "",
        "No live/TradingView model is auto-promoted from this report.",
    ]
    (out / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    return summary


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output", default="reports/structural-secondary")
    a = p.parse_args()
    print(json.dumps(_safe(run(a.data, a.output)), indent=2))


if __name__ == "__main__":
    main()
