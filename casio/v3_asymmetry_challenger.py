from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

from .v3_core import _atr, _bars_since, _resample, load_m5_csv
from .v3_m5_engine import V3M5Config, _align_completed, prepare_m5_features, replay_execution, signals_for_m5_features


@dataclass(frozen=True)
class AsymmetryConfig:
    name: str = "balanced_3r"
    min_rr: float = 3.0
    max_rr: float = 5.0
    efficiency_min: float = 0.28
    max_extension_atr: float = 1.10
    displacement_body_min: float = 0.58
    displacement_range_atr_min: float = 0.85
    pullback_fresh_bars: int = 6
    sweep_fresh_bars: int = 3
    min_stop_atr: float = 0.55
    stop_buffer_atr: float = 0.10
    target_buffer_atr: float = 0.05
    enable_pullback: bool = True
    enable_liquidity_sweep: bool = True
    cooldown_m5_bars: int = 6
    round_trip_cost_bps: float = 1.0


def _safe(obj):
    if isinstance(obj, dict):
        return {str(k): _safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe(v) for v in obj]
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        return v if math.isfinite(v) else None
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return obj


def _nearest_above(entry: pd.Series, levels: list[pd.Series]) -> pd.Series:
    a = np.column_stack([pd.to_numeric(x, errors="coerce").to_numpy(float) for x in levels])
    e = entry.to_numpy(float)[:, None]
    a = np.where(a > e, a, np.nan)
    result = np.full(len(entry), np.nan)
    ok = np.isfinite(a).any(axis=1)
    result[ok] = np.nanmin(a[ok], axis=1)
    return pd.Series(result, index=entry.index)


def _nearest_below(entry: pd.Series, levels: list[pd.Series]) -> pd.Series:
    a = np.column_stack([pd.to_numeric(x, errors="coerce").to_numpy(float) for x in levels])
    e = entry.to_numpy(float)[:, None]
    a = np.where(a < e, a, np.nan)
    result = np.full(len(entry), np.nan)
    ok = np.isfinite(a).any(axis=1)
    result[ok] = np.nanmax(a[ok], axis=1)
    return pd.Series(result, index=entry.index)


def prepare_asymmetry_features(m5: pd.DataFrame) -> pd.DataFrame:
    """Add location/liquidity/efficiency features to the canonical non-repainting frame."""
    f = prepare_m5_features(m5).copy()
    f["m5_atr"] = _atr(m5, 14)
    candle_range = (m5.high - m5.low).replace(0, np.nan)
    f["m5_body_fraction"] = (m5.close - m5.open).abs() / candle_range
    f["m5_close_location"] = (m5.close - m5.low) / candle_range
    f["m5_range_atr"] = candle_range / f.m5_atr.replace(0, np.nan)
    travel = m5.close.diff().abs().rolling(12, min_periods=12).sum()
    f["m5_efficiency12"] = (m5.close - m5.close.shift(12)).abs() / travel.replace(0, np.nan)
    f["m5_extension_atr"] = (m5.close - f.m5_ema20).abs() / f.m5_atr.replace(0, np.nan)

    f["m5_prior_high8"] = m5.high.shift(1).rolling(8, min_periods=8).max()
    f["m5_prior_low8"] = m5.low.shift(1).rolling(8, min_periods=8).min()
    f["m5_prior_high48"] = m5.high.shift(1).rolling(48, min_periods=48).max()
    f["m5_prior_low48"] = m5.low.shift(1).rolling(48, min_periods=48).min()

    local_sell_sweep = (m5.low < f.m5_prior_low8) & (m5.close > f.m5_prior_low8)
    local_buy_sweep = (m5.high > f.m5_prior_high8) & (m5.close < f.m5_prior_high8)
    f["m5_sell_sweep_age"] = _bars_since(local_sell_sweep)
    f["m5_buy_sweep_age"] = _bars_since(local_buy_sweep)

    long_pullback = (m5.low <= f.m5_ema20 + f.m5_atr * 0.15) & (m5.close >= f.m5_ema20 - f.m5_atr * 0.20)
    short_pullback = (m5.high >= f.m5_ema20 - f.m5_atr * 0.15) & (m5.close <= f.m5_ema20 + f.m5_atr * 0.20)
    f["m5_long_pullback_age"] = _bars_since(long_pullback)
    f["m5_short_pullback_age"] = _bars_since(short_pullback)

    daily = _resample(m5, "1D")
    d = pd.DataFrame(index=daily.index)
    d["prev_day_high"] = daily.high
    d["prev_day_low"] = daily.low
    aligned_daily = _align_completed(d, m5.index, pd.Timedelta(days=1))
    f = f.join(aligned_daily)

    # Previous closed M15 swing levels are already causal in prepare_m5_features.
    # Combine several independent liquidity references instead of forcing one target type.
    f["next_liq_long"] = _nearest_above(
        m5.close,
        [f.prev_day_high, f.h1_high20, f.m15_range_high30, f.m5_prior_high48],
    )
    f["next_liq_short"] = _nearest_below(
        m5.close,
        [f.prev_day_low, f.h1_low20, f.m15_range_low30, f.m5_prior_low48],
    )

    f["recent_low6"] = m5.low.rolling(6, min_periods=6).min()
    f["recent_high6"] = m5.high.rolling(6, min_periods=6).max()
    f["recent_low4"] = m5.low.rolling(4, min_periods=4).min()
    f["recent_high4"] = m5.high.rolling(4, min_periods=4).max()
    return f


def asymmetry_signals(f: pd.DataFrame, cfg: AsymmetryConfig) -> pd.DataFrame:
    idx = f.index
    entry = f.close.astype(float)

    long_displacement = (
        (f.close > f.open)
        & f.m5_body_fraction.ge(cfg.displacement_body_min)
        & f.m5_close_location.ge(0.72)
        & f.m5_range_atr.ge(cfg.displacement_range_atr_min)
        & (f.close > f.m5_prior_high3)
    )
    short_displacement = (
        (f.close < f.open)
        & f.m5_body_fraction.ge(cfg.displacement_body_min)
        & f.m5_close_location.le(0.28)
        & f.m5_range_atr.ge(cfg.displacement_range_atr_min)
        & (f.close < f.m5_prior_low3)
    )

    clean_long = f.m5_efficiency12.ge(cfg.efficiency_min) & f.m5_extension_atr.le(cfg.max_extension_atr)
    clean_short = f.m5_efficiency12.ge(cfg.efficiency_min) & f.m5_extension_atr.le(cfg.max_extension_atr)

    # Continuation playbook: both higher timeframes agree, M15 is directional,
    # M5 has recently returned to value, then displaces back with structure.
    pb_long_context = (
        f.h4_bias.eq(1)
        & f.h1_bias.eq(1)
        & f.m15_trend_long.fillna(False)
        & f.m5_long_pullback_age.le(cfg.pullback_fresh_bars)
        & clean_long
    )
    pb_short_context = (
        f.h4_bias.eq(-1)
        & f.h1_bias.eq(-1)
        & f.m15_trend_short.fillna(False)
        & f.m5_short_pullback_age.le(cfg.pullback_fresh_bars)
        & clean_short
    )

    # Liquidity playbook: local stop run, no strong HTF conflict, then decisive displacement.
    # This is deliberately trend-compatible rather than a blind counter-trend reversal.
    sweep_long_context = (
        f.m5_sell_sweep_age.le(cfg.sweep_fresh_bars)
        & ~((f.h4_bias.eq(-1)) & (f.h1_bias.eq(-1)))
        & (f.h1_bias.eq(1) | f.h4_bias.eq(1) | f.m15_trend_long.fillna(False))
        & clean_long
    )
    sweep_short_context = (
        f.m5_buy_sweep_age.le(cfg.sweep_fresh_bars)
        & ~((f.h4_bias.eq(1)) & (f.h1_bias.eq(1)))
        & (f.h1_bias.eq(-1) | f.h4_bias.eq(-1) | f.m15_trend_short.fillna(False))
        & clean_short
    )

    pb_long_risk = np.maximum(entry - (f.recent_low6 - f.m5_atr * cfg.stop_buffer_atr), f.m5_atr * cfg.min_stop_atr)
    pb_short_risk = np.maximum((f.recent_high6 + f.m5_atr * cfg.stop_buffer_atr) - entry, f.m5_atr * cfg.min_stop_atr)
    sw_long_risk = np.maximum(entry - (f.recent_low4 - f.m5_atr * cfg.stop_buffer_atr), f.m5_atr * cfg.min_stop_atr)
    sw_short_risk = np.maximum((f.recent_high4 + f.m5_atr * cfg.stop_buffer_atr) - entry, f.m5_atr * cfg.min_stop_atr)

    long_liq_target = f.next_liq_long - f.m5_atr * cfg.target_buffer_atr
    short_liq_target = f.next_liq_short + f.m5_atr * cfg.target_buffer_atr

    pb_long_avail = (long_liq_target - entry) / pb_long_risk
    pb_short_avail = (entry - short_liq_target) / pb_short_risk
    sw_long_avail = (long_liq_target - entry) / sw_long_risk
    sw_short_avail = (entry - short_liq_target) / sw_short_risk

    pb_long = cfg.enable_pullback & pb_long_context & long_displacement & pb_long_avail.ge(cfg.min_rr)
    pb_short = cfg.enable_pullback & pb_short_context & short_displacement & pb_short_avail.ge(cfg.min_rr)
    sweep_long = cfg.enable_liquidity_sweep & sweep_long_context & long_displacement & sw_long_avail.ge(cfg.min_rr)
    sweep_short = cfg.enable_liquidity_sweep & sweep_short_context & short_displacement & sw_short_avail.ge(cfg.min_rr)

    # Prefer explicit liquidity-sweep entries when both playbooks fire on the same bar.
    direction = np.select([sweep_long, sweep_short, pb_long, pb_short], [1, -1, 1, -1], default=0)
    playbook = np.select(
        [sweep_long | sweep_short, pb_long | pb_short],
        ["LIQUIDITY_SWEEP", "PULLBACK_CONTINUATION"],
        default="NONE",
    )
    risk = np.select(
        [sweep_long, sweep_short, pb_long, pb_short],
        [sw_long_risk, sw_short_risk, pb_long_risk, pb_short_risk],
        default=np.nan,
    ).astype(float)
    avail = np.select(
        [sweep_long, sweep_short, pb_long, pb_short],
        [sw_long_avail, sw_short_avail, pb_long_avail, pb_short_avail],
        default=np.nan,
    ).astype(float)
    target_rr = np.minimum(avail, cfg.max_rr)
    stop = np.where(direction == 1, entry - risk, np.where(direction == -1, entry + risk, np.nan))
    target = np.where(direction == 1, entry + risk * target_rr, np.where(direction == -1, entry - risk * target_rr, np.nan))

    quality = (
        20
        + np.where((f.h4_bias == direction) & (direction != 0), 15, 0)
        + np.where((f.h1_bias == direction) & (direction != 0), 15, 0)
        + np.where(f.m5_efficiency12.ge(0.40), 15, np.where(f.m5_efficiency12.ge(cfg.efficiency_min), 8, 0))
        + np.where(f.m5_body_fraction.ge(0.70), 15, 8)
        + np.where(f.m5_extension_atr.le(0.70), 10, 4)
        + np.where(target_rr >= 4.0, 10, np.where(target_rr >= 3.5, 7, 4))
    ).astype(float)

    valid = (direction != 0) & np.isfinite(risk) & np.isfinite(target_rr) & target_rr.ge(cfg.min_rr)
    out = pd.DataFrame(index=idx)
    out["entry_time"] = idx + pd.Timedelta(minutes=5)
    out["valid"] = valid
    out["direction"] = direction
    out["mode"] = "INTRADAY"
    out["score"] = np.where(valid, quality, 0.0)
    out["entry"] = np.where(valid, entry, np.nan)
    out["stop"] = np.where(valid, stop, np.nan)
    out["target"] = np.where(valid, target, np.nan)
    out["risk_distance"] = np.where(valid, risk, np.nan)
    out["rr"] = np.where(valid, target_rr, np.nan)
    out["regime"] = np.where(valid, "asymmetry", "none")
    out["session"] = np.select(
        [idx.hour < 6, (idx.hour >= 7) & (idx.hour < 11), ((idx.hour > 12) | ((idx.hour == 12) & (idx.minute >= 30))) & ((idx.hour < 16) | ((idx.hour == 16) & (idx.minute < 30)))],
        ["ASIA", "LONDON", "NEW YORK"],
        default="TRANSITION",
    )
    out["playbook"] = playbook
    out["required_score"] = 0.0
    out["required_rr"] = cfg.min_rr
    out["h4_bias"] = f.h4_bias
    out["h1_bias"] = f.h1_bias
    out["m15_adx"] = f.m15_adx
    out["m5_bias"] = np.select(
        [(f.m5_ema20 > f.m5_ema50) & (f.close > f.m5_ema20), (f.m5_ema20 < f.m5_ema50) & (f.close < f.m5_ema20)],
        [1, -1], default=0,
    )
    out["m5_rsi"] = f.m5_rsi
    out["efficiency"] = f.m5_efficiency12
    out["extension_atr"] = f.m5_extension_atr
    out["available_rr"] = avail
    return out


def _metrics(trades: pd.DataFrame, a: pd.Timestamp, b: pd.Timestamp) -> dict:
    if trades.empty:
        x = trades.copy()
    else:
        tt = pd.to_datetime(trades.entry_time, utc=True)
        x = trades[(tt >= a) & (tt < b)].copy()
    r = pd.to_numeric(x.get("net_r", pd.Series(dtype=float)), errors="coerce").dropna()
    if r.empty:
        return {"trades": 0, "wins": 0, "losses": 0, "win_rate": None, "expectancy_r": None,
                "profit_factor": None, "avg_win_r": None, "median_win_r": None, "avg_loss_r": None,
                "max_drawdown_r": None, "trades_per_30d": 0.0, "pct_winners_ge_3r": None,
                "pct_winners_ge_3_5r": None, "pct_winners_ge_4r": None}
    wins, losses = r[r > 0], r[r < 0]
    gw, gl = float(wins.sum()), float(-losses.sum())
    curve = r.cumsum(); dd = curve.cummax() - curve
    days = max((b-a).total_seconds()/86400, 1e-9)
    return {
        "trades": int(len(r)), "wins": int(len(wins)), "losses": int(len(losses)),
        "win_rate": float(len(wins)*100/len(r)), "expectancy_r": float(r.mean()),
        "profit_factor": float(gw/gl) if gl > 0 else (999.0 if gw > 0 else None),
        "avg_win_r": float(wins.mean()) if len(wins) else None,
        "median_win_r": float(wins.median()) if len(wins) else None,
        "avg_loss_r": float(-losses.mean()) if len(losses) else None,
        "max_drawdown_r": float(dd.max()) if len(dd) else 0.0,
        "trades_per_30d": float(len(r)*30/days),
        "pct_winners_ge_3r": float((wins >= 3).mean()*100) if len(wins) else None,
        "pct_winners_ge_3_5r": float((wins >= 3.5).mean()*100) if len(wins) else None,
        "pct_winners_ge_4r": float((wins >= 4).mean()*100) if len(wins) else None,
    }


def _slice(trades: pd.DataFrame, a: pd.Timestamp, b: pd.Timestamp) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    tt = pd.to_datetime(trades.entry_time, utc=True)
    return trades[(tt >= a) & (tt < b)].copy()


def variants() -> list[AsymmetryConfig]:
    base = AsymmetryConfig()
    return [
        base,
        replace(base, name="balanced_3_5r", min_rr=3.5, max_rr=5.5),
        replace(base, name="strict_4r", min_rr=4.0, max_rr=6.0, efficiency_min=0.32, max_extension_atr=1.0),
        replace(base, name="quality_location", min_rr=3.0, efficiency_min=0.35, max_extension_atr=0.85, displacement_body_min=0.62),
        replace(base, name="pullback_only", enable_liquidity_sweep=False, min_rr=3.0),
        replace(base, name="sweep_only", enable_pullback=False, min_rr=3.0),
        replace(base, name="high_frequency_quality", min_rr=2.75, max_rr=5.0, efficiency_min=0.25, max_extension_atr=1.2, displacement_body_min=0.55),
    ]


def run_research(data_path: str | Path = "data/xauusd_m5.csv", output_dir: str | Path = "reports/v3-asymmetry") -> dict:
    outdir = Path(output_dir); outdir.mkdir(parents=True, exist_ok=True)
    m5 = load_m5_csv(data_path)
    f = prepare_asymmetry_features(m5)
    start = f.index.min() + pd.Timedelta(days=30)
    finish = f.index.max() + pd.Timedelta(minutes=5)
    cutoff = start + (finish-start)*0.75

    # Canonical baseline for an apples-to-apples holdout comparison.
    canonical_cfg = V3M5Config()
    canonical = replay_execution(m5, signals_for_m5_features(f, canonical_cfg), canonical_cfg)
    baseline_dev = _metrics(canonical, start, cutoff)
    baseline_oos = _metrics(canonical, cutoff, finish)

    rows = []
    trade_cache: dict[str, pd.DataFrame] = {}
    for cfg in variants():
        sig = asymmetry_signals(f, cfg)
        exec_cfg = V3M5Config(cooldown_m5_bars=cfg.cooldown_m5_bars, round_trip_cost_bps=cfg.round_trip_cost_bps)
        trades = replay_execution(m5, sig, exec_cfg)
        trade_cache[cfg.name] = trades
        dev = _metrics(trades, start, cutoff)
        # Rank on robust economics, not win-rate alone. Frequency is rewarded only up to 15/month.
        wr = (dev["win_rate"] or 0)/100
        exp = dev["expectancy_r"] or -99
        pf = min(dev["profit_factor"] or 0, 10)
        aw = dev["avg_win_r"] or 0
        freq = min(dev["trades_per_30d"] or 0, 15)/15
        dd = dev["max_drawdown_r"] or 99
        objective = exp*2.0 + wr*0.8 + min(aw, 5)/5*0.5 + freq*0.5 + min(pf, 5)/5*0.4 - dd*0.015
        rows.append({"variant": cfg.name, **dev, "objective": objective})

    frame = pd.DataFrame(rows)
    eligible = frame[
        frame.trades.ge(20)
        & frame.expectancy_r.fillna(-99).gt(0)
        & frame.profit_factor.fillna(0).ge(1.20)
        & frame.trades_per_30d.ge(3.0)
    ].copy()
    selected = str(eligible.sort_values("objective", ascending=False).iloc[0].variant) if len(eligible) else "NONE"

    if selected != "NONE":
        selected_trades = trade_cache[selected]
        selected_dev = _metrics(selected_trades, start, cutoff)
        selected_oos = _metrics(selected_trades, cutoff, finish)
        sel_oos_trades = _slice(selected_trades, cutoff, finish)
    else:
        selected_dev = selected_oos = _metrics(pd.DataFrame(), start, cutoff)
        sel_oos_trades = pd.DataFrame()

    # Aspirational target from user request, reported rather than optimized directly.
    stretch = {
        "trades_per_30d": 15.0,
        "win_rate": 70.0,
        "avg_win_r": 3.5,
        "mathematically_consistent_expectancy_at_minus_1r_losses": 2.15,
        "expectancy_r_requested": 3.0,
        "avg_win_needed_for_3r_expectancy_at_70pct_and_minus_1r_losses": 4.7142857143,
        "profit_factor_implied_by_70pct_wr_and_3_5r_winner_minus_1r_loser": 8.1666666667,
    }

    verdict = "KEEP_CANONICAL"
    if selected != "NONE":
        so, bo = selected_oos, baseline_oos
        if (
            so["trades"] >= 10
            and (so["expectancy_r"] or -99) > max(0, bo["expectancy_r"] or -99)
            and (so["profit_factor"] or 0) >= 1.5
            and (so["avg_win_r"] or 0) >= 2.5
        ):
            verdict = "CHALLENGER_PROMISING_NOT_DEPLOYED"

    frame.sort_values("objective", ascending=False).to_csv(outdir/"development_variants.csv", index=False)
    _slice(canonical, cutoff, finish).to_csv(outdir/"canonical_holdout_trades.csv", index=False)
    sel_oos_trades.to_csv(outdir/"challenger_holdout_trades.csv", index=False)

    group_rows = []
    if selected != "NONE" and not sel_oos_trades.empty:
        for keys, g in sel_oos_trades.groupby(["playbook", "session"], dropna=False):
            a, b = keys
            gm = _metrics(g, cutoff, finish)
            group_rows.append({"playbook": a, "session": b, **gm})
    pd.DataFrame(group_rows).to_csv(outdir/"holdout_playbook_session.csv", index=False)

    summary = {
        "data": {"rows": len(m5), "start": m5.index.min(), "end": m5.index.max(), "dev_end": cutoff, "holdout_end": finish},
        "canonical_dev": baseline_dev,
        "canonical_holdout": baseline_oos,
        "selected_challenger": selected,
        "challenger_dev": selected_dev,
        "challenger_holdout": selected_oos,
        "stretch_objective": stretch,
        "verdict": verdict,
        "auto_deploy": False,
        "note": "Research-only. Live CASIO v3 remains frozen. Current CSV covers 2020 only; later years are required before promotion.",
    }
    (outdir/"summary.json").write_text(json.dumps(_safe(summary), indent=2), encoding="utf-8")
    (outdir/"REPORT.md").write_text(
        "# CASIO Asymmetry Challenger\n\n"
        f"Coverage: {m5.index.min().isoformat()} -> {m5.index.max().isoformat()} ({len(m5):,} M5 rows)\n\n"
        f"Selected on development only: **{selected}**\n\n"
        f"Verdict: **{verdict}**\n\n"
        f"Canonical holdout: `{baseline_oos}`\n\n"
        f"Challenger holdout: `{selected_oos}`\n\n"
        "Live parameters were not modified.\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Research high-asymmetry XAUUSD liquidity/pullback challenger")
    p.add_argument("--data", default="data/xauusd_m5.csv")
    p.add_argument("--output", default="reports/v3-asymmetry")
    a = p.parse_args()
    print(json.dumps(_safe(run_research(a.data, a.output)), indent=2))


if __name__ == "__main__":
    main()
