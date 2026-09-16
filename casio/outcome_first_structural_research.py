from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

from .v3_core import _bars_since, load_m5_csv
from .structural_portfolio_latest import (
    StructuralPortfolioConfig,
    _safe,
    _session,
    _target,
    metrics,
    prepare_features,
    replay,
)


# Research principle:
# Do not tune ADX/RSI and do not optimize dozens of thresholds to a target score.
# Start with current market behaviour, express a small number of structural
# techniques, freeze them, then walk backwards and across the independent feed.
#
# Target remains an acceptance standard, not an optimizer objective:
# ~8 trades/30d, 42-50% WR, ~3.5R avg winner, <=~1R avg loss,
# >=+0.70R expectancy, PF>=2.

PLAYBOOK_PRIORITY = {
    "EXTERNAL_SWEEP": 0,
    "TREND_PULLBACK": 1,
    "ACCEPTED_BREAK_RETEST": 2,
}


def _accepted_break_retest(f: pd.DataFrame, direction: int) -> pd.Series:
    """Causal breakout -> acceptance -> retest -> displacement context.

    This deliberately replaces the old loose session-retest memory. A breakout
    must close through a meaningful external level, price must show acceptance
    with two consecutive closes beyond it, then revisit the level without
    closing back through it. The actual entry still waits for fresh M5
    displacement and then a retracement.
    """
    out = pd.Series(False, index=f.index)
    levels = ["asia_high", "prev_day_high", "h1_last_ph", "h4_last_ph"] if direction == 1 else [
        "asia_low", "prev_day_low", "h1_last_pl", "h4_last_pl"
    ]
    for col in levels:
        level = f[col]
        if direction == 1:
            broke = level.notna() & (f.close > level + 0.05 * f.m5_atr) & (f.close.shift(1) <= level)
            age_break = _bars_since(broke)
            accepted = age_break.between(1, 6) & (f.close > level) & (f.close.shift(1) > level)
            age_accept = _bars_since(accepted)
            retest = (
                age_accept.between(1, 10)
                & (f.low <= level + 0.20 * f.m5_atr)
                & (f.close >= level)
            )
        else:
            broke = level.notna() & (f.close < level - 0.05 * f.m5_atr) & (f.close.shift(1) >= level)
            age_break = _bars_since(broke)
            accepted = age_break.between(1, 6) & (f.close < level) & (f.close.shift(1) < level)
            age_accept = _bars_since(accepted)
            retest = (
                age_accept.between(1, 10)
                & (f.high >= level - 0.20 * f.m5_atr)
                & (f.close <= level)
            )
        out |= _bars_since(retest).le(4)
    return out


def _entry(row: pd.Series, direction: int, model: str) -> float:
    if model == "FVG50":
        if direction == 1:
            if not bool(row.bull_fvg):
                return np.nan
            return (float(row.bull_fvg_low) + float(row.bull_fvg_high)) / 2.0
        if not bool(row.bear_fvg):
            return np.nan
        return (float(row.bear_fvg_low) + float(row.bear_fvg_high)) / 2.0
    # Displacement-body retracement. We use the impulse as proof of intent but
    # refuse to chase its close.
    return (float(row.open) + float(row.close)) / 2.0


def _setup_rows(
    f: pd.DataFrame,
    cfg: StructuralPortfolioConfig,
    long_mask: pd.Series,
    short_mask: pd.Series,
    playbook: str,
    entry_model: str,
) -> pd.DataFrame:
    sessions = _session(f.index)
    rows: list[dict] = []
    last = {1: -10**9, -1: -10**9}
    mask = long_mask.fillna(False) | short_mask.fillna(False)
    for i in np.flatnonzero(mask.to_numpy()):
        d = 1 if bool(long_mask.iat[i]) else -1
        if i - last[d] < cfg.cooldown_bars:
            continue
        row = f.iloc[i]
        entry = _entry(row, d, entry_model)
        if not np.isfinite(entry):
            continue
        if d == 1:
            stop = float(row.recent_low8) - cfg.stop_buffer_atr * float(row.m5_atr)
            risk = entry - stop
            day_aligned = entry > float(row.day_open)
        else:
            stop = float(row.recent_high8) + cfg.stop_buffer_atr * float(row.m5_atr)
            risk = stop - entry
            day_aligned = entry < float(row.day_open)
        if not np.isfinite(risk) or risk <= 0 or not np.isfinite(row.m5_atr):
            continue
        risk_atr = risk / float(row.m5_atr)
        if not cfg.min_risk_atr <= risk_atr <= cfg.max_risk_atr:
            continue
        # Continuation trades should agree with the current daily auction.
        if playbook == "TREND_PULLBACK" and not day_aligned:
            continue
        liq, liq_type, runway = _target(row, d, entry, risk, cfg)
        if not np.isfinite(runway):
            continue
        rows.append({
            "signal_i": i,
            "signal_time": f.index[i],
            "direction": d,
            "playbook": playbook,
            "session": sessions[i],
            "entry_model": entry_model,
            "entry": entry,
            "stop": stop,
            "risk": risk,
            "risk_atr": risk_atr,
            "target": entry + d * cfg.target_r * risk,
            "target_r": cfg.target_r,
            "external_liquidity": liq,
            "external_liquidity_type": liq_type,
            "external_runway_r": runway,
            "trend_vote": int(row.trend_vote) if np.isfinite(row.trend_vote) else 0,
            "day_open_aligned": bool(day_aligned),
            "body_fraction": float(row.body_fraction),
            "range_atr": float(row.range_atr),
            "d1_efficiency20": float(row.d1_efficiency20) if np.isfinite(row.d1_efficiency20) else np.nan,
            "d1_range_ratio20": float(row.d1_range_ratio20) if np.isfinite(row.d1_range_ratio20) else np.nan,
            "h4_range_ratio12": float(row.h4_range_ratio12) if np.isfinite(row.h4_range_ratio12) else np.nan,
        })
        last[d] = i
    return pd.DataFrame(rows)


def _combine(parts: list[pd.DataFrame], cooldown_bars: int) -> pd.DataFrame:
    xs = [x.copy() for x in parts if not x.empty]
    if not xs:
        return pd.DataFrame()
    x = pd.concat(xs, ignore_index=True)
    x["_p"] = x.playbook.map(PLAYBOOK_PRIORITY).fillna(9)
    x = x.sort_values(["signal_i", "_p"])
    # A single market event can satisfy more than one description. Preserve the
    # highest-priority structural interpretation instead of counting duplicates.
    x = x.drop_duplicates(["signal_i", "direction"], keep="first")
    keep: list[int] = []
    last = {1: -10**9, -1: -10**9}
    for ix, r in x.iterrows():
        d = int(r.direction); i = int(r.signal_i)
        if i - last[d] < cooldown_bars:
            continue
        keep.append(ix); last[d] = i
    return x.loc[keep].drop(columns=["_p"]).sort_values("signal_i").reset_index(drop=True)


def build_variants(m5: pd.DataFrame, cfg: StructuralPortfolioConfig) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    f = prepare_features(m5, cfg)
    session = pd.Series(_session(f.index), index=f.index)
    primary = session.isin(["LONDON", "NEW_YORK"])
    london = session.eq("LONDON")
    vote = f.trend_vote.fillna(0)
    trend_long = (vote >= 2) & (f.m15_structure_bias.fillna(0) >= 0)
    trend_short = (vote <= -2) & (f.m15_structure_bias.fillna(0) <= 0)

    pb_l = primary & trend_long & f.internal_sell_sweep_age.le(cfg.internal_sweep_fresh) & f.disp_long
    pb_s = primary & trend_short & f.internal_buy_sweep_age.le(cfg.internal_sweep_fresh) & f.disp_short

    # External sweep is deliberately stricter: a genuine M5 imbalance is needed.
    sw_l = london & f.external_sell_sweep_age.le(cfg.external_sweep_fresh) & (vote >= 0) & f.bull_fvg
    sw_s = london & f.external_buy_sweep_age.le(cfg.external_sweep_fresh) & (vote <= 0) & f.bear_fvg

    ar_l_ctx = _accepted_break_retest(f, 1)
    ar_s_ctx = _accepted_break_retest(f, -1)
    ar_l = primary & trend_long & ar_l_ctx & f.disp_long
    ar_s = primary & trend_short & ar_s_ctx & f.disp_short

    pb_body = _setup_rows(f, cfg, pb_l, pb_s, "TREND_PULLBACK", "BODY50")
    pb_fvg = _setup_rows(f, cfg, pb_l & f.bull_fvg, pb_s & f.bear_fvg, "TREND_PULLBACK", "FVG50")
    sw_fvg = _setup_rows(f, cfg, sw_l, sw_s, "EXTERNAL_SWEEP", "FVG50")
    ar_body = _setup_rows(f, cfg, ar_l, ar_s, "ACCEPTED_BREAK_RETEST", "BODY50")
    ar_fvg = _setup_rows(f, cfg, ar_l & f.bull_fvg, ar_s & f.bear_fvg, "ACCEPTED_BREAK_RETEST", "FVG50")

    variants = {
        "PB_BODY": pb_body,
        "PB_FVG": pb_fvg,
        "SWEEP_FVG_LONDON": sw_fvg,
        "RETEST_BODY": ar_body,
        "RETEST_FVG": ar_fvg,
        "CORE_PB_SWEEP": _combine([pb_body, sw_fvg], cfg.cooldown_bars),
        "PORTFOLIO_BODY": _combine([pb_body, sw_fvg, ar_body], cfg.cooldown_bars),
        "PORTFOLIO_FVG_RETEST": _combine([pb_body, sw_fvg, ar_fvg], cfg.cooldown_bars),
    }
    return f, variants


def _scorecard(m: dict) -> float:
    # Distance is only for sorting research cards. It is not used as a trading
    # feature and does not mutate rules to force the desired result.
    freq = float(m.get("trades_per_30d") or 0)
    wr = float(m.get("win_rate") or 0)
    aw = float(m.get("avg_win_r") or 0)
    al = float(m.get("avg_loss_r") or 9)
    ex = float(m.get("expectancy_r") if m.get("expectancy_r") is not None else -9)
    pf = float(m.get("profit_factor") or 0)
    return (
        abs(freq - 8.0) / 8.0
        + max(0.0, 42.0 - wr) / 20.0
        + max(0.0, 3.30 - aw) / 3.30
        + max(0.0, al - 1.15)
        + max(0.0, 0.70 - ex) / 0.70
        + max(0.0, 2.0 - pf) / 2.0
    )


def _periods(m5: pd.DataFrame, feed: str) -> list[tuple[str, pd.Timestamp, pd.Timestamp]]:
    end = m5.index.max() + pd.Timedelta(minutes=5)
    if feed == "dukascopy":
        return [
            ("LATEST_60D", end - pd.Timedelta(days=60), end),
            ("PREVIOUS_60D", end - pd.Timedelta(days=120), end - pd.Timedelta(days=60)),
            ("EARLIER_60D", end - pd.Timedelta(days=180), end - pd.Timedelta(days=120)),
        ]
    out = [("LATEST_60D", end - pd.Timedelta(days=60), end)]
    for y in (2025, 2024):
        a = pd.Timestamp(f"{y}-01-01", tz="UTC")
        b = pd.Timestamp(f"{y+1}-01-01", tz="UTC")
        if a < end and b > m5.index.min():
            out.append((str(y), a, min(b, end)))
    return out


def run(primary_path: str | Path, secondary_path: str | Path | None, output_dir: str | Path) -> dict:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    cfg = replace(StructuralPortfolioConfig(), target_r=3.5, min_external_runway_r=3.5)

    feeds: list[tuple[str, pd.DataFrame]] = []
    p = load_m5_csv(primary_path)
    feeds.append(("dukascopy", p))
    if secondary_path and Path(secondary_path).exists():
        s = load_m5_csv(secondary_path)
        # Research scope requested: latest/current relevance first, then 2025/2024.
        s = s[s.index >= pd.Timestamp("2024-01-01", tz="UTC")]
        feeds.append(("secondary", s))

    all_rows: list[dict] = []
    trade_cache: dict[tuple[str, str], pd.DataFrame] = {}
    setup_cache: dict[tuple[str, str], pd.DataFrame] = {}

    for feed_name, m5 in feeds:
        _, variants = build_variants(m5, cfg)
        for name, setups in variants.items():
            trades = replay(m5, setups, cfg)
            setup_cache[(feed_name, name)] = setups
            trade_cache[(feed_name, name)] = trades
            for label, a, b in _periods(m5, feed_name):
                mm = metrics(trades, a, b)
                all_rows.append({"feed": feed_name, "variant": name, "period": label, **mm})

    history = pd.DataFrame(all_rows)
    history.to_csv(out / "strategy_history.csv", index=False)

    latest = history[(history.feed == "dukascopy") & (history.period == "LATEST_60D")].copy()
    latest["target_distance"] = latest.apply(lambda r: _scorecard(r.to_dict()), axis=1)
    latest = latest.sort_values(["target_distance", "expectancy_r", "profit_factor"], ascending=[True, False, False], na_position="last")
    latest.to_csv(out / "latest_ranked.csv", index=False)
    selected = str(latest.iloc[0].variant) if not latest.empty else "NONE"

    if selected != "NONE":
        for feed_name, _ in feeds:
            setup_cache[(feed_name, selected)].to_csv(out / f"{feed_name}_selected_setups.csv", index=False)
            trade_cache[(feed_name, selected)].to_csv(out / f"{feed_name}_selected_trades.csv", index=False)

    summary = {
        "objective": "Find a structural XAUUSD portfolio with ~8 trades/30d, 42-50% WR, ~3.5R avg winner, <=~1R avg loss, >=+0.70R expectancy, PF>=2 without curve-fitting.",
        "method": "latest-first, fixed structural technique cards; no ADX/RSI; no automatic deployment",
        "selected_latest_first": selected,
        "primary_coverage": {"rows": len(p), "start": p.index.min(), "end": p.index.max()},
        "latest_ranked": latest.to_dict(orient="records"),
        "history": history.to_dict(orient="records"),
        "production_changed": False,
        "tradingview_changed": False,
    }
    (out / "summary.json").write_text(json.dumps(_safe(summary), indent=2), encoding="utf-8")

    lines = [
        "# CASIO outcome-first structural research",
        "",
        "This research deliberately stops pretending that a pretty recent result is already a good strategy.",
        "",
        "Rules are fixed structural technique cards, not ADX/RSI threshold grids. Latest Dukascopy is evaluated first; the same frozen cards are then checked backwards and on the independent secondary feed.",
        "",
        "## Latest Dukascopy ranking",
        "",
        "```text",
        latest.to_string(index=False),
        "```",
        "",
        f"Latest-first selected research card: `{selected}`",
        "",
        "## Full fixed-card history",
        "",
        "```text",
        history.to_string(index=False),
        "```",
        "",
        "No live, email, or TradingView strategy is promoted by this workflow.",
    ]
    (out / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    return summary


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--primary", default="data/xauusd_m5_dukascopy_research.csv")
    ap.add_argument("--secondary", default="data/xauusd_m5_secondary_octafx_mt4.csv")
    ap.add_argument("--output", default="reports/outcome-first-structural")
    a = ap.parse_args()
    print(json.dumps(_safe(run(a.primary, a.secondary, a.output)), indent=2))


if __name__ == "__main__":
    main()
