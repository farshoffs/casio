from __future__ import annotations

import numpy as np
import pandas as pd

from .v4_core import V4Config


def _minute(value: str) -> int:
    h, m = value.split(":")
    return int(h) * 60 + int(m)


def _in_window(index: pd.DatetimeIndex, start: str, end: str) -> pd.Series:
    x = index.hour * 60 + index.minute
    a, b = _minute(start), _minute(end)
    mask = ((x >= a) & (x < b)) if a <= b else ((x >= a) | (x < b))
    return pd.Series(mask, index=index)


def _bars_since(flag: pd.Series) -> pd.Series:
    out: list[float] = []
    age: int | None = None
    for value in flag.fillna(False).to_numpy(dtype=bool):
        age = 0 if value else (None if age is None else age + 1)
        out.append(np.nan if age is None else float(age))
    return pd.Series(out, index=flag.index, dtype=float)


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False, min_periods=1).mean()


def _session_context(f: pd.DataFrame, cfg: V4Config) -> tuple[pd.Series, pd.Series]:
    asia = _in_window(f.index, cfg.asia_start, cfg.asia_end)
    london = _in_window(f.index, cfg.london_start, cfg.london_end)
    ny = _in_window(f.index, cfg.new_york_start, cfg.new_york_end)
    primary = london | ny
    names = pd.Series(
        np.select(
            [asia.to_numpy(), london.to_numpy(), ny.to_numpy()],
            ["ASIA", "LONDON", "NEW YORK"],
            default="TRANSITION",
        ),
        index=f.index,
    )
    bonus = pd.Series(
        np.where(primary, cfg.session_bonus_primary, np.where(asia, cfg.session_bonus_asia, 0)),
        index=f.index,
        dtype=float,
    )
    return names, bonus


def _htf_score(direction: int, f: pd.DataFrame, cfg: V4Config) -> pd.Series:
    aligned_h4 = f.h4_bias.eq(direction)
    aligned_h1 = f.h1_bias.eq(direction)
    neutral_h4 = f.h4_bias.eq(0)
    neutral_h1 = f.h1_bias.eq(0)
    return (
        aligned_h4.astype(int) * cfg.htf_alignment_bonus
        + aligned_h1.astype(int) * cfg.htf_alignment_bonus
        + neutral_h4.astype(int) * cfg.htf_neutral_bonus
        + neutral_h1.astype(int) * cfg.htf_neutral_bonus
    ).astype(float)


def _strong_conflict(direction: int, f: pd.DataFrame) -> pd.Series:
    return f.h4_bias.eq(-direction) & f.h1_bias.eq(-direction)


def signals_for_config(f: pd.DataFrame, cfg: V4Config | None = None) -> pd.DataFrame:
    """Return CASIO v4 setup-first signals.

    Three independent playbooks are evaluated on every closed M15 bar:
    TREND_PULLBACK, RANGE_ROTATION and BREAKOUT_RETEST. Context contributes to
    quality instead of acting as a long chain of mandatory gates. The valid
    candidate with the highest quality score wins that bar.
    """

    cfg = cfg or V4Config()
    x = f.copy()
    idx = x.index
    atr = x.m15_atr.replace(0, np.nan)
    m15_ema20 = _ema(x.close, 20)
    m15_ema50 = _ema(x.close, 50)

    candle_range = (x.high - x.low).replace(0, np.nan)
    body = (x.close - x.open).abs()
    lower_wick = np.minimum(x.open, x.close) - x.low
    upper_wick = x.high - np.maximum(x.open, x.close)
    bull_reject = (x.close > x.open) & (
        (lower_wick >= body * 0.50) | (x.close >= x.low + candle_range * 0.65)
    )
    bear_reject = (x.close < x.open) & (
        (upper_wick >= body * 0.50) | (x.close <= x.high - candle_range * 0.65)
    )
    abnormal = candle_range > atr * cfg.abnormal_candle_atr

    session, session_bonus = _session_context(x, cfg)
    recent_sell_sweep = x.sell_sweep_age.le(3)
    recent_buy_sweep = x.buy_sweep_age.le(3)

    # ------------------------------------------------------------------
    # 1) TREND PULLBACK
    # ------------------------------------------------------------------
    long_context = x.h4_bias.eq(1) | x.h1_bias.eq(1)
    short_context = x.h4_bias.eq(-1) | x.h1_bias.eq(-1)
    long_pullback = (
        x.low <= m15_ema20 + atr * cfg.trend_pullback_atr
    ) & (x.close >= m15_ema20 - atr * 0.15) & (x.close >= m15_ema50 - atr * 0.20)
    short_pullback = (
        x.high >= m15_ema20 - atr * cfg.trend_pullback_atr
    ) & (x.close <= m15_ema20 + atr * 0.15) & (x.close <= m15_ema50 + atr * 0.20)

    trend_long_setup = long_context & long_pullback & bull_reject & ~abnormal
    trend_short_setup = short_context & short_pullback & bear_reject & ~abnormal
    if cfg.strong_conflict_veto:
        trend_long_setup &= ~_strong_conflict(1, x)
        trend_short_setup &= ~_strong_conflict(-1, x)

    trend_long_stop_dist = np.maximum(
        x.close - (np.minimum(x.low, x.prior_low5) - atr * 0.10), atr * 0.75
    )
    trend_short_stop_dist = np.maximum(
        (np.maximum(x.high, x.prior_high5) + atr * 0.10) - x.close, atr * 0.75
    )
    trend_long_target = x.close + trend_long_stop_dist * cfg.trend_target_rr
    trend_short_target = x.close - trend_short_stop_dist * cfg.trend_target_rr

    trend_long_score = (
        40
        + _htf_score(1, x, cfg)
        + recent_sell_sweep.astype(int) * cfg.sweep_bonus
        + x.m15_bos_long.astype(int) * cfg.bos_bonus
        + x.m5_bull_confirm.astype(int) * cfg.m5_bonus
        + session_bonus
        + (cfg.trend_target_rr >= 2.0) * cfg.rr_bonus
    )
    trend_short_score = (
        40
        + _htf_score(-1, x, cfg)
        + recent_buy_sweep.astype(int) * cfg.sweep_bonus
        + x.m15_bos_short.astype(int) * cfg.bos_bonus
        + x.m5_bear_confirm.astype(int) * cfg.m5_bonus
        + session_bonus
        + (cfg.trend_target_rr >= 2.0) * cfg.rr_bonus
    )
    trend_long_valid = trend_long_setup & (cfg.trend_target_rr >= cfg.trend_min_rr) & trend_long_score.ge(cfg.trend_min_score)
    trend_short_valid = trend_short_setup & (cfg.trend_target_rr >= cfg.trend_min_rr) & trend_short_score.ge(cfg.trend_min_score)

    # ------------------------------------------------------------------
    # 2) RANGE ROTATION
    # ------------------------------------------------------------------
    h1_range_atr = (x.h1_high20 - x.h1_low20) / x.h1_atr.replace(0, np.nan)
    h1_compression = (x.h1_ema20 - x.h1_ema50).abs() / x.h1_atr.replace(0, np.nan)
    range_points = (
        (h1_compression <= cfg.range_h1_compression_atr).astype(int)
        + (h1_range_atr <= cfg.range_h1_max_range_atr).astype(int)
        + (x.m15_adx <= cfg.range_m15_max_adx).astype(int)
        + (x.range_atr30 <= cfg.range_m15_max_range_atr).astype(int)
    )
    range_env = range_points >= 3
    width = (x.range_high30 - x.range_low30).replace(0, np.nan)
    lower_zone = x.range_low30 + width * cfg.range_edge_fraction
    upper_zone = x.range_high30 - width * cfg.range_edge_fraction

    range_long_setup = range_env & (x.low <= lower_zone) & (x.close < x.range_mean30) & bull_reject & ~abnormal
    range_short_setup = range_env & (x.high >= upper_zone) & (x.close > x.range_mean30) & bear_reject & ~abnormal
    if cfg.range_require_m5:
        range_long_setup &= x.m5_bull_confirm
        range_short_setup &= x.m5_bear_confirm

    range_long_stop_dist = np.maximum(
        x.close - (np.minimum(x.low, x.range_low30) - atr * 0.10), atr * 0.55
    )
    range_short_stop_dist = np.maximum(
        (np.maximum(x.high, x.range_high30) + atr * 0.10) - x.close, atr * 0.55
    )
    range_long_target = x.range_mean30
    range_short_target = x.range_mean30
    range_long_rr = (range_long_target - x.close) / range_long_stop_dist
    range_short_rr = (x.close - range_short_target) / range_short_stop_dist

    range_long_score = (
        38
        + range_points * 5
        + x.m5_bull_confirm.astype(int) * cfg.m5_bonus
        + recent_sell_sweep.astype(int) * cfg.sweep_bonus
        + session_bonus
        + range_long_rr.ge(1.5).astype(int) * cfg.rr_bonus
    )
    range_short_score = (
        38
        + range_points * 5
        + x.m5_bear_confirm.astype(int) * cfg.m5_bonus
        + recent_buy_sweep.astype(int) * cfg.sweep_bonus
        + session_bonus
        + range_short_rr.ge(1.5).astype(int) * cfg.rr_bonus
    )
    range_long_valid = range_long_setup & range_long_rr.ge(cfg.range_min_rr) & range_long_score.ge(cfg.range_min_score)
    range_short_valid = range_short_setup & range_short_rr.ge(cfg.range_min_rr) & range_short_score.ge(cfg.range_min_score)

    # ------------------------------------------------------------------
    # 3) BREAKOUT -> RETEST
    # ------------------------------------------------------------------
    prev_inside_up = x.close.shift(1) <= x.range_high30.shift(1)
    prev_inside_dn = x.close.shift(1) >= x.range_low30.shift(1)
    breakout_up = (
        prev_inside_up
        & (x.close > x.range_high30)
        & (x.close > x.open)
        & (candle_range >= atr * cfg.breakout_expansion_atr)
    )
    breakout_dn = (
        prev_inside_dn
        & (x.close < x.range_low30)
        & (x.close < x.open)
        & (candle_range >= atr * cfg.breakout_expansion_atr)
    )
    up_age, dn_age = _bars_since(breakout_up), _bars_since(breakout_dn)
    up_level = x.range_high30.where(breakout_up).ffill()
    dn_level = x.range_low30.where(breakout_dn).ffill()
    up_age_ok = up_age.between(cfg.breakout_retest_min_bars, cfg.breakout_retest_max_bars)
    dn_age_ok = dn_age.between(cfg.breakout_retest_min_bars, cfg.breakout_retest_max_bars)

    breakout_long_setup = (
        up_age_ok
        & (x.low <= up_level + atr * cfg.breakout_retest_atr)
        & (x.close > up_level)
        & bull_reject
        & ~abnormal
    )
    breakout_short_setup = (
        dn_age_ok
        & (x.high >= dn_level - atr * cfg.breakout_retest_atr)
        & (x.close < dn_level)
        & bear_reject
        & ~abnormal
    )
    if cfg.strong_conflict_veto:
        breakout_long_setup &= ~_strong_conflict(1, x)
        breakout_short_setup &= ~_strong_conflict(-1, x)

    breakout_long_stop_dist = np.maximum(x.close - (x.low - atr * 0.10), atr * 0.70)
    breakout_short_stop_dist = np.maximum((x.high + atr * 0.10) - x.close, atr * 0.70)
    breakout_long_target = x.close + breakout_long_stop_dist * cfg.breakout_target_rr
    breakout_short_target = x.close - breakout_short_stop_dist * cfg.breakout_target_rr

    breakout_long_score = (
        45
        + _htf_score(1, x, cfg)
        + x.m5_bull_confirm.astype(int) * cfg.m5_bonus
        + session_bonus
        + cfg.rr_bonus
    )
    breakout_short_score = (
        45
        + _htf_score(-1, x, cfg)
        + x.m5_bear_confirm.astype(int) * cfg.m5_bonus
        + session_bonus
        + cfg.rr_bonus
    )
    breakout_long_valid = breakout_long_setup & (cfg.breakout_target_rr >= cfg.breakout_min_rr) & breakout_long_score.ge(cfg.breakout_min_score)
    breakout_short_valid = breakout_short_setup & (cfg.breakout_target_rr >= cfg.breakout_min_rr) & breakout_short_score.ge(cfg.breakout_min_score)

    candidates = [
        ("TREND_PULLBACK", 1, trend_long_valid, trend_long_score, trend_long_stop_dist, trend_long_target, cfg.trend_target_rr, cfg.trend_min_score, cfg.trend_min_rr),
        ("TREND_PULLBACK", -1, trend_short_valid, trend_short_score, trend_short_stop_dist, trend_short_target, cfg.trend_target_rr, cfg.trend_min_score, cfg.trend_min_rr),
        ("RANGE_ROTATION", 1, range_long_valid, range_long_score, range_long_stop_dist, range_long_target, range_long_rr, cfg.range_min_score, cfg.range_min_rr),
        ("RANGE_ROTATION", -1, range_short_valid, range_short_score, range_short_stop_dist, range_short_target, range_short_rr, cfg.range_min_score, cfg.range_min_rr),
        ("BREAKOUT_RETEST", 1, breakout_long_valid, breakout_long_score, breakout_long_stop_dist, breakout_long_target, cfg.breakout_target_rr, cfg.breakout_min_score, cfg.breakout_min_rr),
        ("BREAKOUT_RETEST", -1, breakout_short_valid, breakout_short_score, breakout_short_stop_dist, breakout_short_target, cfg.breakout_target_rr, cfg.breakout_min_score, cfg.breakout_min_rr),
    ]

    score_matrix = np.column_stack([
        np.where(valid.to_numpy(dtype=bool), np.asarray(score, dtype=float), -np.inf)
        for _, _, valid, score, *_ in candidates
    ])
    winner = np.argmax(score_matrix, axis=1)
    best_score = score_matrix[np.arange(len(x)), winner]
    any_valid = np.isfinite(best_score) & (best_score >= cfg.min_score)

    out = pd.DataFrame(index=idx)
    out["entry_time"] = out.index + pd.Timedelta(minutes=15)
    out["valid"] = any_valid
    out["direction"] = 0
    out["mode"] = "NONE"
    out["playbook"] = "NONE"
    out["score"] = np.where(any_valid, best_score, np.nan)
    out["entry"] = np.where(any_valid, x.close, np.nan)
    out["stop"] = np.nan
    out["target"] = np.nan
    out["risk_distance"] = np.nan
    out["rr"] = np.nan
    out["required_score"] = np.nan
    out["required_rr"] = np.nan

    for k, (name, direction, valid, score, stop_dist, target, rr_value, min_score, min_rr) in enumerate(candidates):
        mask = any_valid & (winner == k)
        if not np.any(mask):
            continue
        stop_arr = np.asarray(stop_dist, dtype=float)
        target_arr = np.asarray(target, dtype=float)
        rr_arr = np.full(len(x), float(rr_value)) if np.isscalar(rr_value) else np.asarray(rr_value, dtype=float)
        entry_arr = x.close.to_numpy(dtype=float)
        out.loc[mask, "direction"] = direction
        out.loc[mask, "mode"] = name
        out.loc[mask, "playbook"] = name
        out.loc[mask, "risk_distance"] = stop_arr[mask]
        out.loc[mask, "target"] = target_arr[mask]
        out.loc[mask, "stop"] = np.where(direction == 1, entry_arr - stop_arr, entry_arr + stop_arr)[mask]
        out.loc[mask, "rr"] = rr_arr[mask]
        out.loc[mask, "required_score"] = float(min_score)
        out.loc[mask, "required_rr"] = float(min_rr)

    out["regime"] = np.where(range_env, "range", "directional_or_transition")
    out["session"] = session
    out["h4_bias"] = x.h4_bias
    out["h1_bias"] = x.h1_bias
    out["m15_adx"] = x.m15_adx
    return out
