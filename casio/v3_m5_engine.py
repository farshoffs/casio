from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

from .v3_core import _adx, _atr, _bars_since, _ema, _resample, _rma


@dataclass(frozen=True)
class V3M5Config:
    # Classic v3 branch
    enable_classic: bool = True
    intraday_min_score: int = 80
    intraday_target_rr: float = 3.0
    intraday_min_rr: float = 2.5
    h1_value_atr: float = 0.65
    sweep_fresh_bars: int = 3

    # M5 execution branches
    enable_m5_trend: bool = True
    enable_m5_range: bool = True
    m5_trend_target_rr: float = 2.2
    m5_trend_min_score_primary: int = 65
    m5_trend_min_score_other: int = 75
    m5_trend_min_adx: float = 16.0
    m5_rsi_long: float = 52.0
    m5_rsi_short: float = 48.0
    m5_range_min_rr: float = 1.2
    range_edge_fraction: float = 0.30

    # Sessions UTC
    asia_start: str = "00:00"
    asia_end: str = "06:00"
    london_start: str = "07:00"
    london_end: str = "11:00"
    new_york_start: str = "12:30"
    new_york_end: str = "16:30"
    asia_classic_score: int = 90
    asia_classic_rr: float = 3.0
    transition_classic_score: int = 90
    transition_classic_rr: float = 3.0
    transition_min_adx: float = 25.0

    # Range classifier
    h1_compression_atr: float = 0.65
    h1_max_range_atr: float = 9.0
    m15_max_adx: float = 25.0
    m15_max_range_atr: float = 6.5

    # Execution
    cooldown_m5_bars: int = 6
    round_trip_cost_bps: float = 1.0


def _rsi(s: pd.Series, n: int = 14) -> pd.Series:
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = (-delta.clip(upper=0))
    avg_gain = _rma(gain, n)
    avg_loss = _rma(loss, n)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    out = out.where(avg_loss.ne(0), 100.0)
    both_zero = avg_gain.eq(0) & avg_loss.eq(0)
    out = out.where(~both_zero, 50.0)
    return out


def _align_completed(frame: pd.DataFrame, base_index: pd.DatetimeIndex, period: pd.Timedelta) -> pd.DataFrame:
    x = frame.copy()
    x.index = x.index + period
    out = x.reindex(base_index, method="ffill")
    out.index = base_index
    return out


def _minute(value: str) -> int:
    h, m = value.split(":")
    return int(h) * 60 + int(m)


def _in_window(index: pd.DatetimeIndex, start: str, end: str) -> pd.Series:
    x = index.hour * 60 + index.minute
    a, b = _minute(start), _minute(end)
    mask = ((x >= a) & (x < b)) if a <= b else ((x >= a) | (x < b))
    return pd.Series(mask, index=index)


def prepare_m5_features(m5: pd.DataFrame) -> pd.DataFrame:
    """Build a non-repainting M5-native feature frame.

    Every H4/H1/M15 value is aligned only after that higher-timeframe candle has
    closed. The current row is the native M5 candle that can trigger execution.
    """
    f = m5.copy()
    f["m5_ema20"] = _ema(m5.close, 20)
    f["m5_ema50"] = _ema(m5.close, 50)
    f["m5_rsi"] = _rsi(m5.close, 14)
    f["m5_prior_high3"] = m5.high.shift(1).rolling(3, min_periods=3).max()
    f["m5_prior_low3"] = m5.low.shift(1).rolling(3, min_periods=3).min()

    m15 = _resample(m5, "15min")
    m15f = pd.DataFrame(index=m15.index)
    m15f["m15_bar_time"] = m15.index
    m15f["m15_open"] = m15.open
    m15f["m15_high"] = m15.high
    m15f["m15_low"] = m15.low
    m15f["m15_close"] = m15.close
    m15f["m15_ema20"] = _ema(m15.close, 20)
    m15f["m15_ema50"] = _ema(m15.close, 50)
    m15f["m15_atr"] = _atr(m15, 14)
    m15f["m15_adx"] = _adx(m15, 14)
    m15f["m15_hh20"] = m15.high.shift(1).rolling(20, min_periods=20).max()
    m15f["m15_ll20"] = m15.low.shift(1).rolling(20, min_periods=20).min()
    m15f["m15_prior_high5"] = m15.high.shift(1).rolling(5, min_periods=5).max()
    m15f["m15_prior_low5"] = m15.low.shift(1).rolling(5, min_periods=5).min()
    m15f["m15_range_high30"] = m15.high.shift(1).rolling(30, min_periods=30).max()
    m15f["m15_range_low30"] = m15.low.shift(1).rolling(30, min_periods=30).min()
    m15f["m15_range_size30"] = m15f.m15_range_high30 - m15f.m15_range_low30
    m15f["m15_range_mean30"] = (m15f.m15_range_high30 + m15f.m15_range_low30) / 2
    m15f["m15_range_atr30"] = m15f.m15_range_size30 / m15f.m15_atr.replace(0, np.nan)
    sell_sweep = (m15.low < m15f.m15_ll20) & (m15.close > m15f.m15_ll20)
    buy_sweep = (m15.high > m15f.m15_hh20) & (m15.close < m15f.m15_hh20)
    m15f["m15_sell_sweep_age"] = _bars_since(sell_sweep)
    m15f["m15_buy_sweep_age"] = _bars_since(buy_sweep)
    m15f["m15_bos_long"] = (m15.close > m15f.m15_prior_high5) & (m15.close > m15.open)
    m15f["m15_bos_short"] = (m15.close < m15f.m15_prior_low5) & (m15.close < m15.open)
    m15f["m15_trend_long"] = (m15f.m15_ema20 > m15f.m15_ema50) & (m15.close > m15f.m15_ema50)
    m15f["m15_trend_short"] = (m15f.m15_ema20 < m15f.m15_ema50) & (m15.close < m15f.m15_ema50)
    m15f["m15_pullback_long"] = (
        m15f.m15_trend_long
        & (m15.low <= m15f.m15_ema20 + m15f.m15_atr * 0.25)
        & (m15.close >= m15f.m15_ema50)
    )
    m15f["m15_pullback_short"] = (
        m15f.m15_trend_short
        & (m15.high >= m15f.m15_ema20 - m15f.m15_atr * 0.25)
        & (m15.close <= m15f.m15_ema50)
    )
    aligned_m15 = _align_completed(m15f, m5.index, pd.Timedelta(minutes=15))
    f = f.join(aligned_m15)
    f["new_m15"] = f.m15_bar_time.notna() & f.m15_bar_time.ne(f.m15_bar_time.shift(1))

    h1 = _resample(m5, "1h")
    h1f = pd.DataFrame(index=h1.index)
    h1f["h1_close"] = h1.close
    h1f["h1_ema20"] = _ema(h1.close, 20)
    h1f["h1_ema50"] = _ema(h1.close, 50)
    h1f["h1_atr"] = _atr(h1, 14)
    h1f["h1_high20"] = h1.high.shift(1).rolling(20, min_periods=20).max()
    h1f["h1_low20"] = h1.low.shift(1).rolling(20, min_periods=20).min()
    h1f["h1_bias"] = np.select(
        [
            (h1f.h1_ema20 > h1f.h1_ema50) & (h1.close > h1f.h1_ema20),
            (h1f.h1_ema20 < h1f.h1_ema50) & (h1.close < h1f.h1_ema20),
        ],
        [1, -1],
        default=0,
    )
    f = f.join(_align_completed(h1f, m5.index, pd.Timedelta(hours=1)))

    h4 = _resample(m5, "4h")
    h4f = pd.DataFrame(index=h4.index)
    h4f["h4_close"] = h4.close
    h4f["h4_ema20"] = _ema(h4.close, 20)
    h4f["h4_ema50"] = _ema(h4.close, 50)
    h4f["h4_bias"] = np.select(
        [
            (h4f.h4_ema20 > h4f.h4_ema50) & (h4.close > h4f.h4_ema20),
            (h4f.h4_ema20 < h4f.h4_ema50) & (h4.close < h4f.h4_ema20),
        ],
        [1, -1],
        default=0,
    )
    f = f.join(_align_completed(h4f, m5.index, pd.Timedelta(hours=4)))
    return f


def signals_for_m5_features(f: pd.DataFrame, cfg: V3M5Config | None = None) -> pd.DataFrame:
    cfg = cfg or V3M5Config()
    idx = f.index
    entry = f.close.astype(float)

    asia = _in_window(idx, cfg.asia_start, cfg.asia_end)
    london = _in_window(idx, cfg.london_start, cfg.london_end)
    new_york = _in_window(idx, cfg.new_york_start, cfg.new_york_end)
    primary = london | new_york
    transition = ~(asia | primary)
    session = np.select(
        [asia.to_numpy(), london.to_numpy(), new_york.to_numpy()],
        ["ASIA", "LONDON", "NEW YORK"],
        default="TRANSITION",
    )

    h1_long_value = (entry <= f.h1_ema20 + f.h1_atr * cfg.h1_value_atr) & (
        entry > f.h1_low20 - f.h1_atr * 0.20
    )
    h1_short_value = (entry >= f.h1_ema20 - f.h1_atr * cfg.h1_value_atr) & (
        entry < f.h1_high20 + f.h1_atr * 0.20
    )
    h1_range_atr = (f.h1_high20 - f.h1_low20) / f.h1_atr.replace(0, np.nan)
    h1_compression = (f.h1_ema20 - f.h1_ema50).abs() / f.h1_atr.replace(0, np.nan)
    range_points = (
        h1_compression.le(cfg.h1_compression_atr).astype(int)
        + h1_range_atr.le(cfg.h1_max_range_atr).astype(int)
        + f.m15_adx.le(cfg.m15_max_adx).astype(int)
        + f.m15_range_atr30.le(cfg.m15_max_range_atr).astype(int)
    )
    range_regime = range_points.ge(3)

    recent_sell = f.m15_sell_sweep_age.le(cfg.sweep_fresh_bars)
    recent_buy = f.m15_buy_sweep_age.le(cfg.sweep_fresh_bars)

    classic_required_score = pd.Series(
        np.where(primary, cfg.intraday_min_score, np.where(asia, cfg.asia_classic_score, cfg.transition_classic_score)),
        index=idx,
        dtype=float,
    )
    classic_required_rr = pd.Series(
        np.where(primary, cfg.intraday_min_rr, np.where(asia, cfg.asia_classic_rr, cfg.transition_classic_rr)),
        index=idx,
        dtype=float,
    )
    session_bonus = pd.Series(np.where(primary, 10, np.where(asia, 5, 0)), index=idx, dtype=int)
    classic_long_session = primary | (asia & f.h1_bias.eq(1)) | (
        transition & f.h1_bias.eq(1) & f.m15_adx.ge(cfg.transition_min_adx)
    )
    classic_short_session = primary | (asia & f.h1_bias.eq(-1)) | (
        transition & f.h1_bias.eq(-1) & f.m15_adx.ge(cfg.transition_min_adx)
    )

    classic_long_sd = np.maximum(entry - (f.m15_ll20 - f.m15_atr * 0.20), f.m15_atr)
    classic_short_sd = np.maximum((f.m15_hh20 + f.m15_atr * 0.20) - entry, f.m15_atr)
    classic_long_liq_rr = (f.h1_high20 - entry) / classic_long_sd
    classic_short_liq_rr = (entry - f.h1_low20) / classic_short_sd
    classic_long_rr_ok = classic_long_liq_rr.ge(classic_required_rr)
    classic_short_rr_ok = classic_short_liq_rr.ge(classic_required_rr)

    classic_long_score = (
        f.h4_bias.eq(1).astype(int) * 20
        + np.where(f.h1_bias.eq(1), 15, np.where(f.h1_bias.eq(0), 8, 0))
        + h1_long_value.astype(int) * 15
        + recent_sell.astype(int) * 20
        + f.m15_bos_long.fillna(False).astype(int) * 15
        + session_bonus
        + classic_long_rr_ok.astype(int) * 5
    )
    classic_short_score = (
        f.h4_bias.eq(-1).astype(int) * 20
        + np.where(f.h1_bias.eq(-1), 15, np.where(f.h1_bias.eq(0), 8, 0))
        + h1_short_value.astype(int) * 15
        + recent_buy.astype(int) * 20
        + f.m15_bos_short.fillna(False).astype(int) * 15
        + session_bonus
        + classic_short_rr_ok.astype(int) * 5
    )

    classic_long = (
        cfg.enable_classic
        & f.new_m15.fillna(False)
        & ~range_regime
        & f.h4_bias.eq(1)
        & ~f.h1_bias.eq(-1)
        & h1_long_value
        & recent_sell
        & f.m15_bos_long.fillna(False)
        & classic_long_session
        & classic_long_rr_ok
        & pd.Series(classic_long_score, index=idx).ge(classic_required_score)
    )
    classic_short = (
        cfg.enable_classic
        & f.new_m15.fillna(False)
        & ~range_regime
        & f.h4_bias.eq(-1)
        & ~f.h1_bias.eq(1)
        & h1_short_value
        & recent_buy
        & f.m15_bos_short.fillna(False)
        & classic_short_session
        & classic_short_rr_ok
        & pd.Series(classic_short_score, index=idx).ge(classic_required_score)
    )
    classic_long_target = np.minimum(entry + classic_long_sd * cfg.intraday_target_rr, f.h1_high20)
    classic_short_target = np.maximum(entry - classic_short_sd * cfg.intraday_target_rr, f.h1_low20)

    m5_long_trigger = (
        (f.close > f.open)
        & (f.close > f.m5_prior_high3)
        & (f.close > f.m5_ema20)
        & (f.m5_ema20 > f.m5_ema50)
        & f.m5_rsi.ge(cfg.m5_rsi_long)
    )
    m5_short_trigger = (
        (f.close < f.open)
        & (f.close < f.m5_prior_low3)
        & (f.close < f.m5_ema20)
        & (f.m5_ema20 < f.m5_ema50)
        & f.m5_rsi.le(cfg.m5_rsi_short)
    )
    m5_bias = pd.Series(
        np.select(
            [
                (f.m5_ema20 > f.m5_ema50) & (f.close > f.m5_ema20),
                (f.m5_ema20 < f.m5_ema50) & (f.close < f.m5_ema20),
            ],
            [1, -1],
            default=0,
        ),
        index=idx,
    )

    long_htf_support = f.h4_bias.eq(1) | f.h1_bias.eq(1)
    short_htf_support = f.h4_bias.eq(-1) | f.h1_bias.eq(-1)
    strong_long_conflict = f.h4_bias.eq(-1) & f.h1_bias.eq(-1)
    strong_short_conflict = f.h4_bias.eq(1) & f.h1_bias.eq(1)
    trend_required_score = pd.Series(
        np.where(primary, cfg.m5_trend_min_score_primary, cfg.m5_trend_min_score_other),
        index=idx,
        dtype=float,
    )

    m5_trend_long_score = (
        25
        + np.where(f.h4_bias.eq(1), 15, np.where(f.h4_bias.eq(0), 5, 0))
        + np.where(f.h1_bias.eq(1), 15, np.where(f.h1_bias.eq(0), 5, 0))
        + f.m15_trend_long.fillna(False).astype(int) * 10
        + h1_long_value.astype(int) * 10
        + f.m15_pullback_long.fillna(False).astype(int) * 10
        + recent_sell.astype(int) * 5
        + np.where(primary, 5, np.where(asia, 2, 0))
    )
    m5_trend_short_score = (
        25
        + np.where(f.h4_bias.eq(-1), 15, np.where(f.h4_bias.eq(0), 5, 0))
        + np.where(f.h1_bias.eq(-1), 15, np.where(f.h1_bias.eq(0), 5, 0))
        + f.m15_trend_short.fillna(False).astype(int) * 10
        + h1_short_value.astype(int) * 10
        + f.m15_pullback_short.fillna(False).astype(int) * 10
        + recent_buy.astype(int) * 5
        + np.where(primary, 5, np.where(asia, 2, 0))
    )

    m5_trend_long_context = (
        ~range_regime
        & long_htf_support
        & ~strong_long_conflict
        & f.m15_trend_long.fillna(False)
        & f.m15_adx.ge(cfg.m5_trend_min_adx)
        & (h1_long_value | f.m15_pullback_long.fillna(False) | recent_sell)
    )
    m5_trend_short_context = (
        ~range_regime
        & short_htf_support
        & ~strong_short_conflict
        & f.m15_trend_short.fillna(False)
        & f.m15_adx.ge(cfg.m5_trend_min_adx)
        & (h1_short_value | f.m15_pullback_short.fillna(False) | recent_buy)
    )
    m5_trend_long = (
        cfg.enable_m5_trend
        & m5_trend_long_context
        & m5_long_trigger
        & pd.Series(m5_trend_long_score, index=idx).ge(trend_required_score)
    )
    m5_trend_short = (
        cfg.enable_m5_trend
        & m5_trend_short_context
        & m5_short_trigger
        & pd.Series(m5_trend_short_score, index=idx).ge(trend_required_score)
    )
    m5_trend_long_sd = np.maximum(entry - (f.m15_prior_low5 - f.m15_atr * 0.10), f.m15_atr * 0.75)
    m5_trend_short_sd = np.maximum((f.m15_prior_high5 + f.m15_atr * 0.10) - entry, f.m15_atr * 0.75)
    m5_trend_long_target = entry + m5_trend_long_sd * cfg.m5_trend_target_rr
    m5_trend_short_target = entry - m5_trend_short_sd * cfg.m5_trend_target_rr

    lower_edge = f.m15_range_low30 + f.m15_range_size30 * cfg.range_edge_fraction
    upper_edge = f.m15_range_high30 - f.m15_range_size30 * cfg.range_edge_fraction
    m5_range_long_sd = np.maximum(
        entry - (np.minimum(f.low, f.m15_range_low30) - f.m15_atr * 0.10),
        f.m15_atr * 0.55,
    )
    m5_range_short_sd = np.maximum(
        (np.maximum(f.high, f.m15_range_high30) + f.m15_atr * 0.10) - entry,
        f.m15_atr * 0.55,
    )
    m5_range_long_rr = (f.m15_range_mean30 - entry) / m5_range_long_sd
    m5_range_short_rr = (entry - f.m15_range_mean30) / m5_range_short_sd
    m5_range_long = (
        cfg.enable_m5_range
        & range_regime
        & f.low.le(lower_edge)
        & entry.lt(f.m15_range_mean30)
        & m5_long_trigger
        & m5_range_long_rr.ge(cfg.m5_range_min_rr)
    )
    m5_range_short = (
        cfg.enable_m5_range
        & range_regime
        & f.high.ge(upper_edge)
        & entry.gt(f.m15_range_mean30)
        & m5_short_trigger
        & m5_range_short_rr.ge(cfg.m5_range_min_rr)
    )

    direction = np.select(
        [classic_long, classic_short, m5_trend_long, m5_trend_short, m5_range_long, m5_range_short],
        [1, -1, 1, -1, 1, -1],
        default=0,
    )
    source = np.select(
        [classic_long | classic_short, m5_trend_long | m5_trend_short, m5_range_long | m5_range_short],
        ["CLASSIC_M15", "M5_TREND", "M5_RANGE"],
        default="NONE",
    )
    score = np.select(
        [classic_long, classic_short, m5_trend_long, m5_trend_short, m5_range_long | m5_range_short],
        [classic_long_score, classic_short_score, m5_trend_long_score, m5_trend_short_score, range_points * 20],
        default=0,
    ).astype(float)
    stop_dist = np.select(
        [classic_long, classic_short, m5_trend_long, m5_trend_short, m5_range_long, m5_range_short],
        [classic_long_sd, classic_short_sd, m5_trend_long_sd, m5_trend_short_sd, m5_range_long_sd, m5_range_short_sd],
        default=np.nan,
    ).astype(float)
    target = np.select(
        [classic_long, classic_short, m5_trend_long, m5_trend_short, m5_range_long | m5_range_short],
        [classic_long_target, classic_short_target, m5_trend_long_target, m5_trend_short_target, f.m15_range_mean30],
        default=np.nan,
    ).astype(float)
    stop = np.where(direction == 1, entry - stop_dist, np.where(direction == -1, entry + stop_dist, np.nan))
    rr = np.where(
        direction == 1,
        (target - entry) / stop_dist,
        np.where(direction == -1, (entry - target) / stop_dist, np.nan),
    )
    valid = (direction != 0) & np.isfinite(rr) & (rr > 0)

    required_score = np.select(
        [classic_long | classic_short, m5_trend_long | m5_trend_short],
        [classic_required_score, trend_required_score],
        default=0,
    ).astype(float)
    required_rr = np.select(
        [classic_long | classic_short, m5_range_long | m5_range_short],
        [classic_required_rr, cfg.m5_range_min_rr],
        default=cfg.m5_trend_target_rr,
    ).astype(float)

    out = pd.DataFrame(index=idx)
    out["entry_time"] = idx + pd.Timedelta(minutes=5)
    out["valid"] = valid
    out["direction"] = direction
    out["mode"] = np.where(source == "M5_RANGE", "SCALPING", np.where(source == "NONE", "NONE", "INTRADAY"))
    out["score"] = score
    out["entry"] = np.where(valid, entry, np.nan)
    out["stop"] = np.where(valid, stop, np.nan)
    out["target"] = np.where(valid, target, np.nan)
    out["risk_distance"] = np.where(valid, stop_dist, np.nan)
    out["rr"] = np.where(valid, rr, np.nan)
    out["regime"] = np.where(range_regime, "range", "directional")
    out["session"] = session
    out["playbook"] = source
    out["required_score"] = required_score
    out["required_rr"] = required_rr
    out["h4_bias"] = f.h4_bias
    out["h1_bias"] = f.h1_bias
    out["m15_adx"] = f.m15_adx
    out["m5_bias"] = m5_bias
    out["m5_rsi"] = f.m5_rsi
    return out


def replay_execution(m5: pd.DataFrame, signals: pd.DataFrame, cfg: V3M5Config | None = None) -> pd.DataFrame:
    """Replay the one-position-at-a-time policy used by Pine FAST/BACKTEST.

    A position can only be stopped/targeted starting on the M5 bar after its
    signal bar because the entry is the signal bar close. If stop and target are
    both touched in one M5 candle, stop wins conservatively. No same-bar re-entry
    is allowed after an exit.
    """
    cfg = cfg or V3M5Config()
    columns = list(signals.columns) + [
        "signal_bar",
        "exit_time",
        "exit_price",
        "exit_reason",
        "gross_r",
        "cost_r",
        "net_r",
    ]
    if signals.empty:
        return pd.DataFrame(columns=columns)

    events: list[dict] = []
    active: dict | None = None
    last_entry_pos: int | None = None

    sig = signals.reindex(m5.index)
    for pos, (t, bar) in enumerate(m5.iterrows()):
        exited_this_bar = False
        if active is not None and pos > active["_entry_pos"]:
            direction = int(active["direction"])
            stop = float(active["stop"])
            target = float(active["target"])
            lo, hi = float(bar.low), float(bar.high)
            hit_stop = lo <= stop if direction == 1 else hi >= stop
            hit_target = hi >= target if direction == 1 else lo <= target
            exit_price = None
            reason = None
            if hit_stop and hit_target:
                exit_price, reason = stop, "stop_same_bar"
            elif hit_stop:
                exit_price, reason = stop, "stop"
            elif hit_target:
                exit_price, reason = target, "target"
            if exit_price is not None:
                risk = float(active["risk_distance"])
                ent = float(active["entry"])
                gross_r = (exit_price - ent) / risk if direction == 1 else (ent - exit_price) / risk
                cost_r = (ent * cfg.round_trip_cost_bps / 10000.0) / risk
                active["exit_time"] = t + pd.Timedelta(minutes=5)
                active["exit_price"] = exit_price
                active["exit_reason"] = reason
                active["gross_r"] = gross_r
                active["cost_r"] = cost_r
                active["net_r"] = gross_r - cost_r
                active = None
                exited_this_bar = True

        s = sig.loc[t]
        if exited_this_bar or not bool(s.get("valid", False)):
            continue
        cooldown_ready = last_entry_pos is None or pos - last_entry_pos >= cfg.cooldown_m5_bars
        if active is not None or not cooldown_ready:
            continue

        event = s.to_dict()
        event["signal_bar"] = t
        event["exit_time"] = pd.NaT
        event["exit_price"] = np.nan
        event["exit_reason"] = None
        event["gross_r"] = np.nan
        event["cost_r"] = np.nan
        event["net_r"] = np.nan
        event["_entry_pos"] = pos
        events.append(event)
        active = event
        last_entry_pos = pos

    for event in events:
        event.pop("_entry_pos", None)
    return pd.DataFrame(events)
