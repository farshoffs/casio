from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json

import numpy as np
import pandas as pd

from .v3_core import _bars_since, load_m5_csv
from .structural_portfolio_latest import (
    PORTFOLIO_TARGET,
    StructuralPortfolioConfig,
    _safe,
    _session,
    _target,
    metrics,
    prepare_features,
    replay,
)


# Research question:
# Can we move the structural portfolio from ~2-3 trades/30d toward ~8 without
# using ADX/RSI and without sacrificing the 3.5R asymmetric payoff profile?
#
# This is deliberately a tiny set of price-action hypotheses, not a parameter grid.
MODES = (
    "STRICT_FVG",                 # current assistant baseline
    "DISPLACEMENT_RETRACE",       # BOS/displacement, retrace to 50% body even without a 3-candle FVG
    "M15_LIQUIDITY_RETRACE",      # above + M15 internal-liquidity sweep qualifies a trend pullback
    "FULL_STRUCTURAL_ROUTER",     # above + H1/H4 external break/retest can qualify session expansion
)


def _window_metrics(trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    x = metrics(trades, start, end)
    x["start"] = start
    x["end"] = end
    return x


def _distance(m: dict) -> float:
    """Distance to the portfolio objective. Research ranking only."""
    freq = float(m.get("trades_per_30d", 0) or 0)
    wr = float(m.get("win_rate", 0) or 0)
    aw = float(m.get("avg_win_r", 0) or 0)
    al = float(m.get("avg_loss_r", 9) or 9)
    exp = float(m.get("expectancy_r", -9) if m.get("expectancy_r") is not None else -9)
    pf = float(m.get("profit_factor", 0) or 0)
    return float(
        abs(freq - 8.0) / 8.0
        + max(0.0, 42.0 - wr) / 20.0
        + max(0.0, aw - 3.8) / 3.8
        + max(0.0, 3.3 - aw) / 3.3
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


def _recent_level_retest(f: pd.DataFrame, levels: list[str], direction: int) -> pd.Series:
    """Break an external level, retest it within 12 bars, then keep the retest fresh 4 bars."""
    out = pd.Series(False, index=f.index)
    for col in levels:
        level = f[col]
        if direction == 1:
            broke = (f.close > level) & (f.close.shift(1) <= level) & level.notna()
            age = _bars_since(broke)
            retest = age.between(1, 12) & (f.low <= level + .15 * f.m5_atr) & (f.close >= level)
        else:
            broke = (f.close < level) & (f.close.shift(1) >= level) & level.notna()
            age = _bars_since(broke)
            retest = age.between(1, 12) & (f.high >= level - .15 * f.m5_atr) & (f.close <= level)
        out |= _bars_since(retest).le(4)
    return out


def _entry_for(row: pd.Series, direction: int, mode: str) -> tuple[float, str]:
    has_fvg = bool(row.bull_fvg if direction == 1 else row.bear_fvg)
    if has_fvg:
        if direction == 1:
            return (float(row.bull_fvg_low) + float(row.bull_fvg_high)) / 2.0, "FVG50"
        return (float(row.bear_fvg_low) + float(row.bear_fvg_high)) / 2.0, "FVG50"
    if mode == "STRICT_FVG":
        return np.nan, "NONE"
    # A displacement candle is itself an imbalance event. If it does not leave a
    # literal 3-candle FVG, research a 50% body retracement rather than chasing.
    return (float(row.open) + float(row.close)) / 2.0, "DISP_BODY50"


def setup_frame_mode(f: pd.DataFrame, cfg: StructuralPortfolioConfig, mode: str) -> pd.DataFrame:
    idx = f.index
    sessions = _session(idx)
    primary = pd.Series(sessions != "OTHER", index=idx)
    vote = f.trend_vote.fillna(0)
    trend_long = (vote >= 2) & (f.m15_structure_bias.fillna(0) >= 0)
    trend_short = (vote <= -2) & (f.m15_structure_bias.fillna(0) <= 0)

    strict_fvg = mode == "STRICT_FVG"
    trig_long = f.bull_fvg if strict_fvg else f.disp_long
    trig_short = f.bear_fvg if strict_fvg else f.disp_short

    # Existing M5 internal sweep remains the baseline pullback event.
    pb_event_long = f.internal_sell_sweep_age.le(cfg.internal_sweep_fresh)
    pb_event_short = f.internal_buy_sweep_age.le(cfg.internal_sweep_fresh)

    # Technique 2: treat a confirmed M15 swing as internal liquidity for a trend
    # continuation. This is price structure, not an oscillator filter.
    if mode in ("M15_LIQUIDITY_RETRACE", "FULL_STRUCTURAL_ROUTER"):
        m15_sell = ((f.low < f.m15_last_pl) & (f.close > f.m15_last_pl) & f.m15_last_pl.notna()).fillna(False)
        m15_buy = ((f.high > f.m15_last_ph) & (f.close < f.m15_last_ph) & f.m15_last_ph.notna()).fillna(False)
        pb_event_long |= _bars_since(m15_sell).le(9)
        pb_event_short |= _bars_since(m15_buy).le(9)

    pb_long = primary & trend_long & pb_event_long & trig_long
    pb_short = primary & trend_short & pb_event_short & trig_short

    regime_ok = f.d1_range_ratio20.le(cfg.d1_range_ratio_max) & f.h4_range_ratio12.ge(cfg.h4_range_ratio_min)
    sw_long = primary & regime_ok & f.external_sell_sweep_age.le(cfg.external_sweep_fresh) & (vote >= 0) & trig_long
    sw_short = primary & regime_ok & f.external_buy_sweep_age.le(cfg.external_sweep_fresh) & (vote <= 0) & trig_short

    rt_long_event = f.session_retest_long.copy()
    rt_short_event = f.session_retest_short.copy()
    if mode == "FULL_STRUCTURAL_ROUTER":
        rt_long_event |= _recent_level_retest(f, ["h1_last_ph", "h4_last_ph"], 1)
        rt_short_event |= _recent_level_retest(f, ["h1_last_pl", "h4_last_pl"], -1)

    rt_long = primary & trend_long & rt_long_event & trig_long
    rt_short = primary & trend_short & rt_short_event & trig_short

    rows: list[dict] = []
    last = {1: -999, -1: -999}
    mask = pb_long | pb_short | sw_long | sw_short | rt_long | rt_short
    for i in np.flatnonzero(mask.to_numpy()):
        if sw_long.iat[i]: direction, playbook = 1, "EXTERNAL_SWEEP"
        elif sw_short.iat[i]: direction, playbook = -1, "EXTERNAL_SWEEP"
        elif rt_long.iat[i]: direction, playbook = 1, "SESSION_EXPANSION_RETEST"
        elif rt_short.iat[i]: direction, playbook = -1, "SESSION_EXPANSION_RETEST"
        elif pb_long.iat[i]: direction, playbook = 1, "TREND_PULLBACK"
        elif pb_short.iat[i]: direction, playbook = -1, "TREND_PULLBACK"
        else: continue
        if i - last[direction] < cfg.cooldown_bars:
            continue
        row = f.iloc[i]
        entry, entry_model = _entry_for(row, direction, mode)
        if not np.isfinite(entry):
            continue
        if direction == 1:
            stop = float(row.recent_low8) - cfg.stop_buffer_atr * float(row.m5_atr)
            risk = entry - stop
            day_aligned = entry > float(row.day_open)
        else:
            stop = float(row.recent_high8) + cfg.stop_buffer_atr * float(row.m5_atr)
            risk = stop - entry
            day_aligned = entry < float(row.day_open)
        if not np.isfinite(risk) or not np.isfinite(row.m5_atr):
            continue
        risk_atr = risk / float(row.m5_atr)
        if risk_atr < cfg.min_risk_atr or risk_atr > cfg.max_risk_atr:
            continue
        if playbook == "TREND_PULLBACK" and not day_aligned:
            continue
        liq, liq_type, runway = _target(row, direction, entry, risk, cfg)
        if not np.isfinite(runway):
            continue
        rows.append({
            "signal_i": i, "signal_time": idx[i], "direction": direction,
            "playbook": playbook, "session": sessions[i], "mode": mode,
            "entry_model": entry_model, "entry": entry, "stop": stop, "risk": risk,
            "target": entry + direction * cfg.target_r * risk, "target_r": cfg.target_r,
            "external_liquidity": liq, "external_liquidity_type": liq_type,
            "external_runway_r": runway, "trend_vote": int(vote.iat[i]),
            "day_open_aligned": bool(day_aligned),
            "d1_range_ratio20": float(row.d1_range_ratio20) if np.isfinite(row.d1_range_ratio20) else np.nan,
            "h4_range_ratio12": float(row.h4_range_ratio12) if np.isfinite(row.h4_range_ratio12) else np.nan,
        })
        last[direction] = i
    return pd.DataFrame(rows)


def run(data_path: str | Path, output_dir: str | Path = "reports/structural-frequency") -> dict:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    m5 = load_m5_csv(data_path)
    end = m5.index.max() + pd.Timedelta(minutes=5)
    if end - m5.index.min() < pd.Timedelta(days=190):
        raise ValueError("Need at least ~190 days of current M5 history")
    windows = {
        "CURRENT_60D": (end - pd.Timedelta(days=60), end),
        "PREVIOUS_60D": (end - pd.Timedelta(days=120), end - pd.Timedelta(days=60)),
        "EARLIER_60D": (end - pd.Timedelta(days=180), end - pd.Timedelta(days=120)),
    }

    cfg = replace(StructuralPortfolioConfig(), target_r=3.5, min_external_runway_r=3.5)
    f = prepare_features(m5, cfg)
    current_rows = []
    cache: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}

    for mode in MODES:
        setups = setup_frame_mode(f, cfg, mode)
        trades = replay(m5, setups, cfg)
        cache[mode] = (setups, trades)
        a, b = windows["CURRENT_60D"]
        m = _window_metrics(trades, a, b)
        current_rows.append({"mode": mode, **m, "target_distance": _distance(m), "meets_target_band": _meets(m)})

    current = pd.DataFrame(current_rows).sort_values(
        ["meets_target_band", "target_distance", "expectancy_r", "profit_factor"],
        ascending=[False, True, False, False], na_position="last"
    )
    current.to_csv(out / "current_60d_modes.csv", index=False)
    selected = str(current.iloc[0].mode)
    setups, trades = cache[selected]

    backward_rows = []
    pb_rows = []
    for name, (a, b) in windows.items():
        m = _window_metrics(trades, a, b)
        backward_rows.append({"mode": selected, "window": name, **m, "meets_target_band": _meets(m)})
        for pb in ("TREND_PULLBACK", "EXTERNAL_SWEEP", "SESSION_EXPANSION_RETEST"):
            t = trades[trades.playbook.eq(pb)].copy() if not trades.empty else trades.copy()
            pb_rows.append({"mode": selected, "window": name, "playbook": pb, **_window_metrics(t, a, b)})

    backwards = pd.DataFrame(backward_rows)
    pbs = pd.DataFrame(pb_rows)
    backwards.to_csv(out / "selected_mode_backwards.csv", index=False)
    pbs.to_csv(out / "selected_mode_playbooks.csv", index=False)
    setups.to_csv(out / "selected_setups.csv", index=False)
    trades.to_csv(out / "selected_trades.csv", index=False)

    summary = {
        "coverage": {"rows": len(m5), "start": m5.index.min(), "end": m5.index.max()},
        "target": PORTFOLIO_TARGET,
        "research_question": "Increase structural setup frequency without ADX/RSI or sacrificing 3.5R asymmetry.",
        "modes": list(MODES),
        "selected_latest_first": selected,
        "current_modes": current.to_dict(orient="records"),
        "selected_backwards": backwards.to_dict(orient="records"),
        "selected_playbooks": pbs.to_dict(orient="records"),
        "auto_deploy": False,
    }
    (out / "summary.json").write_text(json.dumps(_safe(summary), indent=2), encoding="utf-8")

    lines = [
        "# CASIO Structural Frequency Research",
        "",
        "Objective: approach 8 trades/30d while preserving structural entries, ~3.5R winners, >=+0.70R expectancy and PF>=2.",
        "",
        "No ADX or RSI is used. Latest 60d is development; earlier windows are backward stability checks.",
        "",
        "## Latest 60d — curated structural techniques",
        "",
        "```text", current.to_string(index=False), "```",
        "",
        f"Selected latest-first mode: `{selected}`",
        "",
        "## Frozen backward check",
        "", "```text", backwards.to_string(index=False), "```",
        "",
        "## Playbook contribution",
        "", "```text", pbs.to_string(index=False), "```",
        "",
        "No production strategy was changed automatically.",
    ]
    (out / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    return summary


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--output", default="reports/structural-frequency")
    a = p.parse_args()
    print(json.dumps(_safe(run(a.data, a.output)), indent=2))


if __name__ == "__main__":
    main()
