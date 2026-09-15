from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class V3Config:
    """CASIO v3 config: v2 regime-first MTF core plus v3 session-aware execution."""

    mode: str = "AUTO"

    # Intraday core
    intraday_min_score: int = 80
    intraday_target_rr: float = 3.0
    intraday_min_rr: float = 2.5
    h1_value_atr: float = 0.65
    sweep_fresh_bars: int = 3

    # Session-aware execution. Primary London/NY keeps the original threshold.
    # Asia and transition hours can still trade, but only through stricter
    # trend-exception gates. AUTO continues to prefer Scalping in range regimes.
    session_policy: str = "adaptive_24h"  # adaptive_24h | primary_only
    asia_start: str = "00:00"
    asia_end: str = "06:00"
    london_start: str = "07:00"
    london_end: str = "11:00"
    new_york_start: str = "12:30"
    new_york_end: str = "16:30"
    asia_intraday_min_score: int = 90
    asia_intraday_min_rr: float = 3.0
    transition_intraday_min_score: int = 90
    transition_intraday_min_rr: float = 3.0
    transition_min_adx: float = 25.0

    # Range / Scalping core
    scalp_min_score: int = 85
    scalp_min_rr: float = 1.3
    h1_compression_atr: float = 0.40
    h1_max_range_atr: float = 8.0
    m15_max_adx: float = 22.0
    m15_max_range_atr: float = 5.5

    # Research toggles
    h4_veto: bool = True
    h1_value_model: str = "ema_atr"  # ema_atr | pivot
    use_m5_confirmation: bool = True
    round_trip_cost_bps: float = 1.0


SESSION_PROFILES = {
    "baseline": ("07:00", "11:00", "12:30", "16:30"),
    "early": ("06:00", "10:00", "12:00", "16:00"),
    "late": ("08:00", "12:00", "13:00", "17:00"),
    "wide": ("06:00", "12:00", "12:00", "17:00"),
}

SESSION_POLICIES = ("adaptive_24h", "primary_only")


def load_m5_csv(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"timestamp", "open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"missing columns: {', '.join(sorted(missing))}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="raise")
    df = df.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="raise")
    if "volume" not in df.columns:
        df["volume"] = 0.0
    df = df.set_index("timestamp")
    if len(df) < 500:
        raise ValueError("v3 research needs at least 500 M5 bars")
    return df[["open", "high", "low", "close", "volume"]]


def _resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    out = df.resample(rule, label="left", closed="left", origin="epoch").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    return out.dropna(subset=["open", "high", "low", "close"])


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=1).mean()


def _rma(s: pd.Series, n: int) -> pd.Series:
    x = s.astype(float).to_numpy()
    out = np.full(len(x), np.nan)
    valid = np.flatnonzero(~np.isnan(x))
    if len(valid) < n:
        return pd.Series(out, index=s.index)
    start = valid[0]
    end = start + n
    seed = x[start:end]
    if len(seed) < n or np.isnan(seed).any():
        return s.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    out[end - 1] = seed.mean()
    alpha = 1 / n
    for i in range(end, len(x)):
        out[i] = out[i - 1] if np.isnan(x[i]) else alpha * x[i] + (1 - alpha) * out[i - 1]
    return pd.Series(out, index=s.index)


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat(
        [df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()],
        axis=1,
    ).max(axis=1)
    return _rma(tr, n)


def _adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    up, down = df["high"].diff(), -df["low"].diff()
    plus = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    atr = _atr(df, n)
    pdi = 100 * _rma(plus, n) / atr.replace(0, np.nan)
    mdi = 100 * _rma(minus, n) / atr.replace(0, np.nan)
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return _rma(dx, n)


def _bars_since(flag: pd.Series) -> pd.Series:
    out, age = [], None
    for val in flag.fillna(False).to_numpy(dtype=bool):
        age = 0 if val else (None if age is None else age + 1)
        out.append(np.nan if age is None else age)
    return pd.Series(out, index=flag.index, dtype=float)


def _align_htf(x: pd.DataFrame, m15_index: pd.DatetimeIndex, period: pd.Timedelta) -> pd.DataFrame:
    x = x.copy()
    x.index = x.index + period
    eval_time = pd.DatetimeIndex(m15_index + pd.Timedelta(minutes=15))
    out = x.reindex(eval_time, method="ffill")
    out.index = m15_index
    return out


def prepare_features(m5: pd.DataFrame) -> pd.DataFrame:
    """Build causal M15/H1/H4 features and the last M5 intrabar confirmation."""
    m15, h1, h4 = _resample(m5, "15min"), _resample(m5, "1h"), _resample(m5, "4h")
    f = m15.copy()
    f["m15_atr"], f["m15_adx"] = _atr(m15), _adx(m15)
    f["hh20"] = m15.high.shift(1).rolling(20, min_periods=20).max()
    f["ll20"] = m15.low.shift(1).rolling(20, min_periods=20).min()
    f["prior_high5"] = m15.high.shift(1).rolling(5, min_periods=5).max()
    f["prior_low5"] = m15.low.shift(1).rolling(5, min_periods=5).min()
    f["range_high30"] = m15.high.shift(1).rolling(30, min_periods=30).max()
    f["range_low30"] = m15.low.shift(1).rolling(30, min_periods=30).min()
    f["range_size30"] = f.range_high30 - f.range_low30
    f["range_atr30"] = f.range_size30 / f.m15_atr.replace(0, np.nan)
    f["range_mean30"] = (f.range_high30 + f.range_low30) / 2
    sell = (m15.low < f.ll20) & (m15.close > f.ll20)
    buy = (m15.high > f.hh20) & (m15.close < f.hh20)
    f["sell_sweep_age"], f["buy_sweep_age"] = _bars_since(sell), _bars_since(buy)
    f["m15_bos_long"] = (m15.close > f.prior_high5) & (m15.close > m15.open)
    f["m15_bos_short"] = (m15.close < f.prior_low5) & (m15.close < m15.open)

    h4f = pd.DataFrame(
        {"h4_close": h4.close, "h4_ema20": _ema(h4.close, 20), "h4_ema50": _ema(h4.close, 50)}
    )
    f = f.join(_align_htf(h4f, m15.index, pd.Timedelta(hours=4)))
    f["h4_bias"] = np.select(
        [
            (f.h4_ema20 > f.h4_ema50) & (f.h4_close > f.h4_ema20),
            (f.h4_ema20 < f.h4_ema50) & (f.h4_close < f.h4_ema20),
        ],
        [1, -1],
        default=0,
    )

    h1f = pd.DataFrame(index=h1.index)
    h1f["h1_close"], h1f["h1_ema20"], h1f["h1_ema50"], h1f["h1_atr"] = (
        h1.close,
        _ema(h1.close, 20),
        _ema(h1.close, 50),
        _atr(h1),
    )
    h1f["h1_high20"] = h1.high.shift(1).rolling(20, min_periods=20).max()
    h1f["h1_low20"] = h1.low.shift(1).rolling(20, min_periods=20).min()
    lo5, hi5 = h1.low.rolling(5, min_periods=5).min(), h1.high.rolling(5, min_periods=5).max()
    pl = h1.low.shift(2).where(h1.low.shift(2).eq(lo5))
    ph = h1.high.shift(2).where(h1.high.shift(2).eq(hi5))
    h1f["pivot_low"], h1f["pivot_high"] = pl.ffill(), ph.ffill()
    h1f["pivot_low_atr"] = h1f.h1_atr.shift(2).where(pl.notna()).ffill()
    h1f["pivot_high_atr"] = h1f.h1_atr.shift(2).where(ph.notna()).ffill()
    f = f.join(_align_htf(h1f, m15.index, pd.Timedelta(hours=1)))
    f["h1_bias"] = np.select(
        [
            (f.h1_ema20 > f.h1_ema50) & (f.h1_close > f.h1_ema20),
            (f.h1_ema20 < f.h1_ema50) & (f.h1_close < f.h1_ema20),
        ],
        [1, -1],
        default=0,
    )

    m5x = m5.copy()
    m5x["m5_ema20"] = _ema(m5.close, 20)
    last = m5x[["open", "close", "m5_ema20"]].resample(
        "15min", label="left", closed="left", origin="epoch"
    ).last()
    last = last.rename(columns={"open": "m5_open", "close": "m5_close"})
    f = f.join(last)
    f["m5_bull_confirm"] = (f.m5_close > f.m5_open) & (f.m5_close > f.m5_ema20)
    f["m5_bear_confirm"] = (f.m5_close < f.m5_open) & (f.m5_close < f.m5_ema20)
    return f
