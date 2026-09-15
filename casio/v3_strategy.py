from __future__ import annotations

import numpy as np
import pandas as pd

from .v3_core import V3Config


def _minute(value: str) -> int:
    h, m = value.split(":")
    return int(h) * 60 + int(m)


def _in_window(index: pd.DatetimeIndex, start: str, end: str) -> pd.Series:
    x = index.hour * 60 + index.minute
    a, b = _minute(start), _minute(end)
    mask = ((x >= a) & (x < b)) if a <= b else ((x >= a) | (x < b))
    return pd.Series(mask, index=index)


def signals_for_config(f: pd.DataFrame, cfg: V3Config) -> pd.DataFrame:
    recent_sell = f.sell_sweep_age.le(cfg.sweep_fresh_bars)
    recent_buy = f.buy_sweep_age.le(cfg.sweep_fresh_bars)

    h1_range_atr = (f.h1_high20 - f.h1_low20) / f.h1_atr.replace(0, np.nan)
    h1_compression = (f.h1_ema20 - f.h1_ema50).abs() / f.h1_atr.replace(0, np.nan)
    h1_range = (h1_compression <= cfg.h1_compression_atr) & (h1_range_atr <= cfg.h1_max_range_atr)
    m15_range = (f.m15_adx <= cfg.m15_max_adx) & (f.range_atr30 <= cfg.m15_max_range_atr)
    scalp_regime = h1_range & m15_range

    if cfg.h1_value_model == "ema_atr":
        long_value = (f.close <= f.h1_ema20 + f.h1_atr * cfg.h1_value_atr) & (f.close > f.h1_low20 - f.h1_atr * .20)
        short_value = (f.close >= f.h1_ema20 - f.h1_atr * cfg.h1_value_atr) & (f.close < f.h1_high20 + f.h1_atr * .20)
    elif cfg.h1_value_model == "pivot":
        long_value = (f.close >= f.pivot_low - f.pivot_low_atr * .20) & (f.close <= f.pivot_low + f.pivot_low_atr * cfg.h1_value_atr)
        short_value = (f.close <= f.pivot_high + f.pivot_high_atr * .20) & (f.close >= f.pivot_high - f.pivot_high_atr * cfg.h1_value_atr)
    else:
        raise ValueError(f"unknown h1_value_model: {cfg.h1_value_model}")

    london = _in_window(f.index, cfg.london_start, cfg.london_end)
    ny = _in_window(f.index, cfg.new_york_start, cfg.new_york_end)
    in_session = london | ny
    session = np.where(london, "LONDON", np.where(ny, "NEW YORK", "OFF-SESSION"))
    active_mode = pd.Series(np.where(scalp_regime, "SCALPING", "INTRADAY") if cfg.mode == "AUTO" else cfg.mode, index=f.index)

    long_sd = np.maximum(f.close - (f.ll20 - f.m15_atr * .20), f.m15_atr)
    short_sd = np.maximum((f.hh20 + f.m15_atr * .20) - f.close, f.m15_atr)
    long_liq_rr = (f.h1_high20 - f.close) / long_sd
    short_liq_rr = (f.close - f.h1_low20) / short_sd
    long_rr_ok, short_rr_ok = long_liq_rr.ge(cfg.intraday_min_rr), short_liq_rr.ge(cfg.intraday_min_rr)

    long_score = (
        (f.h4_bias == 1).astype(int) * 20
        + np.where(f.h1_bias == 1, 15, np.where(f.h1_bias == 0, 8, 0))
        + long_value.astype(int) * 15 + recent_sell.astype(int) * 20
        + f.m15_bos_long.astype(int) * 15 + in_session.astype(int) * 10 + long_rr_ok.astype(int) * 5
    )
    short_score = (
        (f.h4_bias == -1).astype(int) * 20
        + np.where(f.h1_bias == -1, 15, np.where(f.h1_bias == 0, 8, 0))
        + short_value.astype(int) * 15 + recent_buy.astype(int) * 20
        + f.m15_bos_short.astype(int) * 15 + in_session.astype(int) * 10 + short_rr_ok.astype(int) * 5
    )
    h4_long = (f.h4_bias == 1) if cfg.h4_veto else pd.Series(True, index=f.index)
    h4_short = (f.h4_bias == -1) if cfg.h4_veto else pd.Series(True, index=f.index)
    intraday_long = (
        active_mode.eq("INTRADAY") & h4_long & (f.h1_bias != -1) & long_value & recent_sell & f.m15_bos_long
        & in_session & long_rr_ok & pd.Series(long_score, index=f.index).ge(cfg.intraday_min_score)
    )
    intraday_short = (
        active_mode.eq("INTRADAY") & h4_short & (f.h1_bias != 1) & short_value & recent_buy & f.m15_bos_short
        & in_session & short_rr_ok & pd.Series(short_score, index=f.index).ge(cfg.intraday_min_score)
    )

    scalp_long_sweep = (f.low < f.range_low30) & (f.close > f.range_low30)
    scalp_short_sweep = (f.high > f.range_high30) & (f.close < f.range_high30)
    scalp_long_sd = np.maximum(f.close - (f.low - f.m15_atr * .10), f.m15_atr * .65)
    scalp_short_sd = np.maximum((f.high + f.m15_atr * .10) - f.close, f.m15_atr * .65)
    scalp_long_rr = (f.range_mean30 - f.close) / scalp_long_sd
    scalp_short_rr = (f.close - f.range_mean30) / scalp_short_sd
    scalp_long_rr_ok, scalp_short_rr_ok = scalp_long_rr.ge(cfg.scalp_min_rr), scalp_short_rr.ge(cfg.scalp_min_rr)
    m5_long = f.m5_bull_confirm if cfg.use_m5_confirmation else pd.Series(True, index=f.index)
    m5_short = f.m5_bear_confirm if cfg.use_m5_confirmation else pd.Series(True, index=f.index)
    scalp_long_score = h1_range.astype(int) * 25 + m15_range.astype(int) * 20 + scalp_long_sweep.astype(int) * 25 + m5_long.astype(int) * 15 + scalp_long_rr_ok.astype(int) * 15
    scalp_short_score = h1_range.astype(int) * 25 + m15_range.astype(int) * 20 + scalp_short_sweep.astype(int) * 25 + m5_short.astype(int) * 15 + scalp_short_rr_ok.astype(int) * 15
    scalp_long = active_mode.eq("SCALPING") & scalp_regime & scalp_long_sweep & m5_long & scalp_long_rr_ok & pd.Series(scalp_long_score, index=f.index).ge(cfg.scalp_min_score)
    scalp_short = active_mode.eq("SCALPING") & scalp_regime & scalp_short_sweep & m5_short & scalp_short_rr_ok & pd.Series(scalp_short_score, index=f.index).ge(cfg.scalp_min_score)

    direction = np.select([intraday_long, intraday_short, scalp_long, scalp_short], [1, -1, 1, -1], default=0)
    mode = np.select([intraday_long | intraday_short, scalp_long | scalp_short], ["INTRADAY", "SCALPING"], default="NONE")
    score = np.select([intraday_long, intraday_short, scalp_long, scalp_short], [long_score, short_score, scalp_long_score, scalp_short_score], default=np.maximum(np.asarray(long_score), np.asarray(short_score))).astype(float)

    intra_sd = np.where(direction == 1, long_sd, short_sd)
    liq_target = np.where(direction == 1, f.h1_high20, f.h1_low20)
    preferred = np.where(direction == 1, f.close + intra_sd * cfg.intraday_target_rr, f.close - intra_sd * cfg.intraday_target_rr)
    intra_target = np.where(direction == 1, np.minimum(preferred, liq_target), np.maximum(preferred, liq_target))
    is_intra = np.asarray(mode) == "INTRADAY"
    stop_dist = np.where(is_intra, intra_sd, np.where(direction == 1, scalp_long_sd, scalp_short_sd))
    target = np.where(is_intra, intra_target, f.range_mean30)
    entry = f.close.to_numpy()
    stop = np.where(direction == 1, entry - stop_dist, np.where(direction == -1, entry + stop_dist, np.nan))
    rr = np.where(direction == 1, (target - entry) / stop_dist, np.where(direction == -1, (entry - target) / stop_dist, np.nan))

    out = pd.DataFrame(index=f.index)
    out["entry_time"] = out.index + pd.Timedelta(minutes=15)
    out["valid"], out["direction"], out["mode"], out["score"] = direction != 0, direction, mode, score
    out["entry"] = np.where(direction != 0, entry, np.nan)
    out["stop"], out["target"] = stop, np.where(direction != 0, target, np.nan)
    out["risk_distance"], out["rr"] = np.where(direction != 0, stop_dist, np.nan), np.where(direction != 0, rr, np.nan)
    out["regime"], out["session"] = np.where(scalp_regime, "range", "directional"), session
    out["h4_bias"], out["h1_bias"], out["m15_adx"] = f.h4_bias, f.h1_bias, f.m15_adx
    return out
