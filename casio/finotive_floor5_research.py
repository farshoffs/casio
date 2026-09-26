from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import itertools
import json
import math

import numpy as np
import pandas as pd

from .v3_core import _atr, _resample, load_m5_csv
from .regime_router_engine import RegimeRouterConfig, load_price_csv, replay_engine


START_BALANCE = 2500.0
MONTHLY_FLOOR_PCT = 5.0
MPD_PCT_INITIAL = 0.5
DAILY_DD_PCT = 3.0
MAX_DD_PCT = 6.0
RISKS = (0.005, 0.006)


@dataclass(frozen=True)
class Config:
    cost_bps: float = 1.0
    max_hold_bars: int = 144
    min_risk_atr: float = 0.25
    max_risk_atr: float = 2.8


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def _align_closed(ctx: pd.DataFrame, index: pd.DatetimeIndex, delta: pd.Timedelta) -> pd.DataFrame:
    x = ctx.copy()
    x.index = x.index + delta
    return x.reindex(index, method="ffill")


def _bars_since(event: pd.Series, cap: int = 10000) -> pd.Series:
    arr = event.fillna(False).to_numpy(bool)
    out = np.full(len(arr), cap, dtype=int)
    age = cap
    for i, yes in enumerate(arr):
        age = 0 if yes else min(cap, age + 1)
        out[i] = age
    return pd.Series(out, index=event.index)


def _safe(v):
    if isinstance(v, dict):
        return {str(k): _safe(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_safe(x) for x in v]
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        x = float(v)
        return x if math.isfinite(x) else None
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    return v


def features(m5: pd.DataFrame) -> pd.DataFrame:
    f = m5.copy()
    f["atr"] = _atr(m5, 14)
    rng = (f.high - f.low).replace(0, np.nan)
    f["body_frac"] = (f.close - f.open).abs() / rng
    f["close_loc"] = (f.close - f.low) / rng
    f["range_atr"] = rng / f.atr.replace(0, np.nan)
    f["e20"] = _ema(f.close, 20)
    f["prior_hi5"] = f.high.shift(1).rolling(5, min_periods=5).max()
    f["prior_lo5"] = f.low.shift(1).rolling(5, min_periods=5).min()
    f["recent_hi8"] = f.high.rolling(8, min_periods=8).max()
    f["recent_lo8"] = f.low.rolling(8, min_periods=8).min()

    h1 = _resample(m5, "1h")
    h1c = pd.DataFrame(index=h1.index)
    h1c["h1_e20"] = _ema(h1.close, 20)
    h1c["h1_e50"] = _ema(h1.close, 50)
    h1c["h1_close"] = h1.close
    h1c["h1_atr"] = _atr(h1, 14)
    h1c["h1_sep"] = (h1c.h1_e20 - h1c.h1_e50).abs() / h1c.h1_atr.replace(0, np.nan)
    f = f.join(_align_closed(h1c, f.index, pd.Timedelta(hours=1)))

    h4 = _resample(m5, "4h")
    h4c = pd.DataFrame(index=h4.index)
    h4c["h4_e20"] = _ema(h4.close, 20)
    h4c["h4_e50"] = _ema(h4.close, 50)
    h4c["h4_close"] = h4.close
    h4c["h4_atr"] = _atr(h4, 14)
    h4c["h4_sep"] = (h4c.h4_e20 - h4c.h4_e50).abs() / h4c.h4_atr.replace(0, np.nan)
    f = f.join(_align_closed(h4c, f.index, pd.Timedelta(hours=4)))

    d = _resample(m5, "1D")
    dr = d.high - d.low
    dc = pd.DataFrame(index=d.index)
    dc["prev_day_high"] = d.high
    dc["prev_day_low"] = d.low
    dc["adr20"] = dr.rolling(20, min_periods=20).mean()
    f = f.join(_align_closed(dc, f.index, pd.Timedelta(days=1)))

    day = f.index.floor("D")
    day_series = pd.Series(day, index=f.index)
    f["day_high_sofar"] = f.groupby(day).high.cummax()
    f["day_low_sofar"] = f.groupby(day).low.cummin()
    f["day_range_util"] = (f.day_high_sofar - f.day_low_sofar) / f.adr20.replace(0, np.nan)

    asia_mask = f.index.hour < 6
    asia = f[asia_mask].groupby(f[asia_mask].index.floor("D")).agg(
        asia_high=("high", "max"), asia_low=("low", "min")
    )
    asia["asia_range"] = asia.asia_high - asia.asia_low
    asia["asia_med20"] = asia.asia_range.shift(1).rolling(20, min_periods=15).median()
    asia["asia_comp"] = asia.asia_range / asia.asia_med20.replace(0, np.nan)
    f["asia_high"] = day_series.map(asia.asia_high)
    f["asia_low"] = day_series.map(asia.asia_low)
    f["asia_comp"] = day_series.map(asia.asia_comp)
    f.loc[asia_mask, ["asia_high", "asia_low", "asia_comp"]] = np.nan

    lon = f.index.tz_convert("Europe/London")
    ny = f.index.tz_convert("America/New_York")
    lon_min = lon.hour * 60 + lon.minute
    ny_min = ny.hour * 60 + ny.minute
    f["london"] = (lon_min >= 8 * 60) & (lon_min < 12 * 60)
    f["ny"] = (ny_min >= 8 * 60 + 30) & (ny_min < 12 * 60 + 30)
    f["primary"] = f.london | f.ny

    lon_date = pd.Series(lon.date, index=f.index)
    lo30_mask = (lon_min >= 8 * 60) & (lon_min < 8 * 60 + 30)
    lo30 = f[lo30_mask].groupby(lon_date[lo30_mask]).agg(
        lo30_open=("open", "first"), lo30_close=("close", "last"),
        lo30_high=("high", "max"), lo30_low=("low", "min")
    )
    f["lo30_open"] = lon_date.map(lo30.lo30_open)
    f["lo30_close"] = lon_date.map(lo30.lo30_close)
    f["lo30_high"] = lon_date.map(lo30.lo30_high)
    f["lo30_low"] = lon_date.map(lo30.lo30_low)
    f["lo30_move_h1atr"] = (f.lo30_close - f.lo30_open) / f.h1_atr.replace(0, np.nan)
    f.loc[lon_min < 8 * 60 + 30, ["lo30_open", "lo30_close", "lo30_high", "lo30_low", "lo30_move_h1atr"]] = np.nan

    london_am_mask = (lon_min >= 8 * 60) & (lon_min < 12 * 60)
    lrange = f[london_am_mask].groupby(lon_date[london_am_mask]).agg(
        london_high=("high", "max"), london_low=("low", "min")
    )
    f["london_high"] = lon_date.map(lrange.london_high)
    f["london_low"] = lon_date.map(lrange.london_low)

    f["h1_long"] = (f.h1_e20 > f.h1_e50) & (f.h1_close > f.h1_e20)
    f["h1_short"] = (f.h1_e20 < f.h1_e50) & (f.h1_close < f.h1_e20)
    f["h4_long"] = (f.h4_e20 > f.h4_e50) & (f.h4_close > f.h4_e20)
    f["h4_short"] = (f.h4_e20 < f.h4_e50) & (f.h4_close < f.h4_e20)
    return f


def _rows(
    f: pd.DataFrame,
    long_mask: pd.Series,
    short_mask: pd.Series,
    name: str,
    target_r: float,
    symbol: str,
    stop_mode: str = "recent8",
) -> pd.DataFrame:
    rows = []
    last_day = {1: None, -1: None}
    for i in np.flatnonzero((long_mask.fillna(False) | short_mask.fillna(False)).to_numpy()):
        if i + 1 >= len(f):
            continue
        d = 1 if bool(long_mask.iat[i]) and not bool(short_mask.iat[i]) else -1 if bool(short_mask.iat[i]) and not bool(long_mask.iat[i]) else 0
        if d == 0:
            continue
        ts = f.index[i]
        day_key = ts.floor("D")
        if last_day[d] == day_key and name in {"LO30_REVERSE", "ASIA_FALSE_BREAK"}:
            continue
        row = f.iloc[i]
        atr = float(row.atr)
        if not np.isfinite(atr) or atr <= 0:
            continue
        if stop_mode == "lo30":
            stop = float(row.lo30_low) - .08 * atr if d == 1 else float(row.lo30_high) + .08 * atr
        else:
            stop = float(row.recent_lo8) - .10 * atr if d == 1 else float(row.recent_hi8) + .10 * atr
        if not np.isfinite(stop):
            continue
        rows.append({
            "signal_i": i,
            "signal_time": ts,
            "direction": d,
            "engine": name,
            "symbol": symbol,
            "stop_ref": stop,
            "target_r": target_r,
        })
        last_day[d] = day_key
    return pd.DataFrame(rows)


def engine_set(f: pd.DataFrame, symbol: str) -> dict[str, pd.DataFrame]:
    bull = f.close > f.open
    bear = f.close < f.open

    strong_bull = f.h1_long & f.h4_long & ((f.h1_sep >= .45) | (f.h4_sep >= .45))
    strong_bear = f.h1_short & f.h4_short & ((f.h1_sep >= .45) | (f.h4_sep >= .45))

    # A: Daily-range exhaustion at previous-day external liquidity.
    dre_l = (
        f.primary & f.prev_day_low.notna() & f.day_range_util.ge(.85)
        & (f.low < f.prev_day_low) & (f.close > f.prev_day_low)
        & (~strong_bear) & bull & f.body_frac.ge(.35) & f.close_loc.ge(.58)
    )
    dre_s = (
        f.primary & f.prev_day_high.notna() & f.day_range_util.ge(.85)
        & (f.high > f.prev_day_high) & (f.close < f.prev_day_high)
        & (~strong_bull) & bear & f.body_frac.ge(.35) & f.close_loc.le(.42)
    )

    # B: Asia false-break fade, retained as a known GBP complement and cross-checked on XAU.
    asia_l = (
        f.london & f.asia_low.notna() & (f.low < f.asia_low) & (f.close > f.asia_low)
        & (~strong_bear) & bull & f.body_frac.ge(.30)
    )
    asia_s = (
        f.london & f.asia_high.notna() & (f.high > f.asia_high) & (f.close < f.asia_high)
        & (~strong_bull) & bear & f.body_frac.ge(.30)
    )

    # C: compression -> expansion -> first pullback to the Asian boundary.
    break_l = (
        f.london & f.asia_high.notna() & f.asia_comp.le(.85)
        & f.h1_long & (f.close > f.asia_high) & (f.close.shift(1) <= f.asia_high.shift(1))
        & bull & f.body_frac.ge(.52) & f.range_atr.ge(.70)
    )
    break_s = (
        f.london & f.asia_low.notna() & f.asia_comp.le(.85)
        & f.h1_short & (f.close < f.asia_low) & (f.close.shift(1) >= f.asia_low.shift(1))
        & bear & f.body_frac.ge(.52) & f.range_atr.ge(.70)
    )
    age_bl = _bars_since(break_l)
    age_bs = _bars_since(break_s)
    cep_l = (
        age_bl.between(1, 12) & f.asia_high.notna()
        & (f.low <= f.asia_high + .12 * f.atr) & (f.close >= f.asia_high)
        & bull & f.body_frac.ge(.32) & (f.close > f.e20)
    )
    cep_s = (
        age_bs.between(1, 12) & f.asia_low.notna()
        & (f.high >= f.asia_low - .12 * f.atr) & (f.close <= f.asia_low)
        & bear & f.body_frac.ge(.32) & (f.close < f.e20)
    )

    # D: accepted external break -> retest -> continuation.
    acc_l0 = (
        f.primary & f.prev_day_high.notna() & (f.close > f.prev_day_high + .05 * f.atr)
        & (f.close.shift(1) <= f.prev_day_high.shift(1)) & (~f.h1_short)
        & bull & f.body_frac.ge(.48)
    )
    acc_s0 = (
        f.primary & f.prev_day_low.notna() & (f.close < f.prev_day_low - .05 * f.atr)
        & (f.close.shift(1) >= f.prev_day_low.shift(1)) & (~f.h1_long)
        & bear & f.body_frac.ge(.48)
    )
    age_al = _bars_since(acc_l0)
    age_as = _bars_since(acc_s0)
    acc_l = (
        age_al.between(1, 12) & (f.low <= f.prev_day_high + .12 * f.atr)
        & (f.close > f.prev_day_high) & bull & f.body_frac.ge(.30)
    )
    acc_s = (
        age_as.between(1, 12) & (f.high >= f.prev_day_low - .12 * f.atr)
        & (f.close < f.prev_day_low) & bear & f.body_frac.ge(.30)
    )

    # E: failed breakout second-entry fade. Requires a second rejection 2-12 bars after the first.
    second_l = pd.Series(False, index=f.index)
    second_s = pd.Series(False, index=f.index)
    for low_col, high_col in [("prev_day_low", "prev_day_high"), ("asia_low", "asia_high")]:
        first_l = f[low_col].notna() & (f.low < f[low_col]) & (f.close > f[low_col]) & bull
        first_s = f[high_col].notna() & (f.high > f[high_col]) & (f.close < f[high_col]) & bear
        age_l = _bars_since(first_l)
        age_s = _bars_since(first_s)
        second_l |= (
            age_l.between(2, 12) & f[low_col].notna()
            & (f.low <= f[low_col] + .10 * f.atr) & (f.close > f[low_col])
            & bull & f.body_frac.ge(.32)
        )
        second_s |= (
            age_s.between(2, 12) & f[high_col].notna()
            & (f.high >= f[high_col] - .10 * f.atr) & (f.close < f[high_col])
            & bear & f.body_frac.ge(.32)
        )
    second_l &= f.primary & (~strong_bear)
    second_s &= f.primary & (~strong_bull)

    out = {
        "DRE_FADE": _rows(f, dre_l, dre_s, "DRE_FADE", 2.5, symbol),
        "ASIA_FALSE_BREAK": _rows(f, asia_l, asia_s, "ASIA_FALSE_BREAK", 3.0, symbol),
        "COMP_EXP_PULLBACK": _rows(f, cep_l, cep_s, "COMP_EXP_PULLBACK", 3.0, symbol),
        "ACCEPTED_BREAK_RETEST": _rows(f, acc_l, acc_s, "ACCEPTED_BREAK_RETEST", 3.0, symbol),
        "SECOND_ENTRY_FADE": _rows(f, second_l, second_s, "SECOND_ENTRY_FADE", 2.5, symbol),
    }

    if symbol == "GBPUSD":
        lon = f.index.tz_convert("Europe/London")
        lon_min = lon.hour * 60 + lon.minute
        trade_window = (lon_min >= 8 * 60 + 30) & (lon_min < 10 * 60 + 30)
        lo_s = (
            trade_window & f.lo30_move_h1atr.ge(.22)
            & bear & (f.close < f.e20) & f.body_frac.ge(.32)
        )
        lo_l = (
            trade_window & f.lo30_move_h1atr.le(-.22)
            & bull & (f.close > f.e20) & f.body_frac.ge(.32)
        )
        out["LO30_REVERSE"] = _rows(f, lo_l, lo_s, "LO30_REVERSE", 2.5, symbol, stop_mode="lo30")

    if symbol == "XAUUSD":
        # Gold's price discovery is especially active in New York. Test a first pullback
        # after NY accepts a break of the completed London morning range.
        ny = f.index.tz_convert("America/New_York")
        ny_min = ny.hour * 60 + ny.minute
        ny_window = (ny_min >= 8 * 60 + 30) & (ny_min < 11 * 60 + 30)
        xb_l0 = (
            ny_window & f.london_high.notna() & (f.close > f.london_high)
            & (f.close.shift(1) <= f.london_high.shift(1)) & (~f.h1_short)
            & bull & f.body_frac.ge(.50) & f.range_atr.ge(.70)
        )
        xb_s0 = (
            ny_window & f.london_low.notna() & (f.close < f.london_low)
            & (f.close.shift(1) >= f.london_low.shift(1)) & (~f.h1_long)
            & bear & f.body_frac.ge(.50) & f.range_atr.ge(.70)
        )
        age_xl = _bars_since(xb_l0)
        age_xs = _bars_since(xb_s0)
        xb_l = (
            age_xl.between(1, 12) & (f.low <= f.london_high + .12 * f.atr)
            & (f.close >= f.london_high) & bull & f.body_frac.ge(.30)
        )
        xb_s = (
            age_xs.between(1, 12) & (f.high >= f.london_low - .12 * f.atr)
            & (f.close <= f.london_low) & bear & f.body_frac.ge(.30)
        )
        out["NY_LONDON_RANGE_RETEST"] = _rows(f, xb_l, xb_s, "NY_LONDON_RANGE_RETEST", 3.0, symbol)

    return out


def replay(f: pd.DataFrame, setups: pd.DataFrame, cfg: Config | None = None) -> pd.DataFrame:
    cfg = cfg or Config()
    if setups is None or setups.empty:
        return pd.DataFrame(columns=["symbol", "engine", "entry_time", "exit_time", "net_r"])
    events = []
    next_free = -1
    for s in setups.sort_values("signal_i").itertuples(index=False):
        sig = int(s.signal_i)
        fill = sig + 1
        if fill < next_free or fill >= len(f):
            continue
        d = int(s.direction)
        entry = float(f.open.iat[fill])
        stop = float(s.stop_ref)
        if (d == 1 and entry <= stop) or (d == -1 and entry >= stop):
            continue
        risk = abs(entry - stop)
        atr = float(f.atr.iat[sig])
        ratr = risk / atr if atr > 0 else np.nan
        if not np.isfinite(ratr) or not (cfg.min_risk_atr <= ratr <= cfg.max_risk_atr):
            continue
        target_r = float(s.target_r)
        target = entry + d * target_r * risk
        end = min(len(f), fill + cfg.max_hold_bars + 1)
        result = None
        exit_i = None
        reason = None
        for j in range(fill, end):
            lo = float(f.low.iat[j]); hi = float(f.high.iat[j]); close = float(f.close.iat[j])
            hs = lo <= stop if d == 1 else hi >= stop
            ht = hi >= target if d == 1 else lo <= target
            if hs and ht:
                result, reason = -1.0, "stop_same_bar"
            elif hs:
                result, reason = -1.0, "stop"
            elif ht:
                result, reason = target_r, "target"
            elif j == end - 1:
                result, reason = (close - entry) / risk * d, "time_exit"
            else:
                continue
            exit_i = j
            break
        if result is None:
            continue
        cost_r = (entry * cfg.cost_bps / 10000.0) / risk
        events.append({
            "symbol": s.symbol,
            "engine": s.engine,
            "entry_time": f.index[fill] + pd.Timedelta(minutes=5),
            "exit_time": f.index[exit_i] + pd.Timedelta(minutes=5),
            "direction": d,
            "entry": entry,
            "stop": stop,
            "target": target,
            "gross_r": float(result),
            "net_r": float(result - cost_r),
            "reason": reason,
        })
        next_free = exit_i + 1
    return pd.DataFrame(events)


def rr10_trades(xau_path: str | Path) -> pd.DataFrame:
    m15, _ = load_price_csv(xau_path)
    trades, _ = replay_engine(m15, RegimeRouterConfig(target_r=3.0))
    if trades.empty:
        return pd.DataFrame(columns=["symbol", "engine", "entry_time", "exit_time", "net_r"])
    x = pd.DataFrame({
        "symbol": "XAUUSD",
        "engine": "RR10",
        "entry_time": pd.to_datetime(trades.entry_time_utc, utc=True),
        "exit_time": pd.to_datetime(trades.exit_time_utc, utc=True),
        "net_r": pd.to_numeric(trades.result_r, errors="coerce") - 0.04,
    }).dropna()
    return x.sort_values("entry_time").reset_index(drop=True)


def sleeve_metrics(trades: pd.DataFrame, start: str, end: str) -> dict:
    if trades.empty:
        return {"trades": 0, "expectancy_r": None, "profit_factor": None, "win_rate": None}
    a = pd.Timestamp(start, tz="UTC"); b = pd.Timestamp(end, tz="UTC")
    t = pd.to_datetime(trades.entry_time, utc=True)
    r = pd.to_numeric(trades.loc[(t >= a) & (t < b), "net_r"], errors="coerce").dropna()
    if r.empty:
        return {"trades": 0, "expectancy_r": None, "profit_factor": None, "win_rate": None}
    w = r[r > .05]; l = r[r < -.05]
    return {
        "trades": int(len(r)),
        "expectancy_r": float(r.mean()),
        "profit_factor": float(w.sum() / (-l.sum())) if len(l) else 999.0,
        "win_rate": float((r > .05).mean() * 100.0),
    }


def _trading_day(ts: pd.Timestamp) -> str:
    x = pd.Timestamp(ts).tz_convert("America/New_York")
    shifted = x - pd.Timedelta(hours=17)
    return shifted.strftime("%Y-%m-%d")


def simulate_month(trades: pd.DataFrame, month: pd.Timestamp, risk_frac: float) -> dict:
    end = month + pd.offsets.MonthBegin(1)
    if trades.empty:
        x = trades.copy()
    else:
        t = pd.to_datetime(trades.entry_time, utc=True)
        x = trades[(t >= month) & (t < end)].sort_values(["entry_time", "symbol", "engine"]).copy()

    # Portfolio rule: one active position at a time.
    selected = []
    free_at = pd.Timestamp.min.tz_localize("UTC")
    for r in x.itertuples(index=False):
        et = pd.Timestamp(r.entry_time)
        xt = pd.Timestamp(r.exit_time)
        if et < free_at:
            continue
        selected.append(r)
        free_at = xt

    equity = START_BALANCE
    peak = equity
    max_dd = 0.0
    worst_day = 0.0
    profitable_days = 0
    hard_breach = False
    used = 0
    losses_total = 0

    current_day = None
    day_start = equity
    day_pnl = 0.0
    day_losses = 0

    def finish_day():
        nonlocal profitable_days, worst_day
        if current_day is None:
            return
        pct_initial = day_pnl / START_BALANCE * 100.0
        pct_start = day_pnl / day_start * 100.0 if day_start else 0.0
        worst_day = min(worst_day, pct_start)
        if pct_initial >= MPD_PCT_INITIAL:
            profitable_days += 1

    for r in selected:
        td = _trading_day(pd.Timestamp(r.entry_time))
        if current_day is None or td != current_day:
            finish_day()
            if (equity / START_BALANCE - 1.0) * 100.0 >= MONTHLY_FLOOR_PCT and profitable_days >= 5:
                break
            current_day = td
            day_start = equity
            day_pnl = 0.0
            day_losses = 0
        if day_losses >= 2:
            continue

        pnl = equity * risk_frac * float(r.net_r)
        equity += pnl
        day_pnl += pnl
        used += 1
        if float(r.net_r) < 0:
            day_losses += 1
            losses_total += 1

        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak * 100.0)
        daily_dd = (day_start - equity) / day_start * 100.0 if day_start else 0.0
        static_dd = (START_BALANCE - equity) / START_BALANCE * 100.0
        if daily_dd >= DAILY_DD_PCT or static_dd >= MAX_DD_PCT:
            hard_breach = True
            break

    finish_day()
    ret = (equity / START_BALANCE - 1.0) * 100.0
    payout_ready = ret >= MONTHLY_FLOOR_PCT and profitable_days >= 5 and not hard_breach
    return {
        "month": month.strftime("%Y-%m"),
        "risk_pct": risk_frac * 100.0,
        "trades_used": int(used),
        "return_pct": float(ret),
        "profitable_days_0_5": int(profitable_days),
        "max_dd_pct": float(max_dd),
        "worst_daily_pct": float(worst_day),
        "hard_breach": bool(hard_breach),
        "payout_ready_5pct": bool(payout_ready),
        "losses": int(losses_total),
    }


def combine_sleeves(cache: dict[str, pd.DataFrame], names: list[str]) -> pd.DataFrame:
    xs = [cache[n].copy() for n in names if n in cache and not cache[n].empty]
    if not xs:
        return pd.DataFrame(columns=["symbol", "engine", "entry_time", "exit_time", "net_r"])
    return pd.concat(xs, ignore_index=True).sort_values(["entry_time", "symbol", "engine"]).reset_index(drop=True)


def run(xau_path: str | Path, gbp_path: str | Path, output_dir: str | Path) -> dict:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    xau = load_m5_csv(xau_path)
    gbp = load_m5_csv(gbp_path)

    # Common research window; earlier data are used only when both feeds have them.
    earliest = max(xau.index.min(), gbp.index.min(), pd.Timestamp("2017-01-01", tz="UTC"))
    xau = xau[xau.index >= earliest].copy()
    gbp = gbp[gbp.index >= earliest].copy()

    cache: dict[str, pd.DataFrame] = {"XAU_RR10": rr10_trades(xau_path)}
    for symbol, data in [("XAUUSD", xau), ("GBPUSD", gbp)]:
        f = features(data)
        for name, setups in engine_set(f, symbol).items():
            label = f"{symbol}_{name}"
            tr = replay(f, setups)
            if not tr.empty:
                tr["engine"] = label
            cache[label] = tr

    rows = []
    validated = []
    for name, tr in cache.items():
        disc = sleeve_metrics(tr, "2017-01-01", "2023-01-01")
        val = sleeve_metrics(tr, "2023-01-01", "2026-01-01")
        is_valid = (
            (disc["trades"] or 0) >= 20 and (val["trades"] or 0) >= 15
            and (disc["expectancy_r"] or -99) > 0.05
            and (val["expectancy_r"] or -99) > 0.05
            and (disc["profit_factor"] or 0) > 1.05
            and (val["profit_factor"] or 0) > 1.05
        )
        rows.append({"sleeve": name, "validated_pre2026": is_valid, **{f"disc_{k}":v for k,v in disc.items()}, **{f"val_{k}":v for k,v in val.items()}})
        if is_valid:
            validated.append(name)

    sleeve_table = pd.DataFrame(rows).sort_values(
        ["validated_pre2026", "val_expectancy_r", "disc_expectancy_r"],
        ascending=[False, False, False], na_position="last"
    )
    sleeve_table.to_csv(out / "sleeve_validation.csv", index=False)

    # Frozen portfolio definitions rely only on pre-2026 validation status.
    meanrev = [n for n in validated if any(k in n for k in ("DRE_FADE", "ASIA_FALSE_BREAK", "SECOND_ENTRY_FADE", "LO30_REVERSE"))]
    trend = [n for n in validated if any(k in n for k in ("RR10", "COMP_EXP_PULLBACK", "ACCEPTED_BREAK_RETEST", "NY_LONDON_RANGE_RETEST"))]
    quality = []
    if not sleeve_table.empty:
        q = sleeve_table[sleeve_table.validated_pre2026].copy()
        q["robust_exp"] = q[["disc_expectancy_r", "val_expectancy_r"]].min(axis=1)
        quality = q.sort_values("robust_exp", ascending=False).sleeve.head(6).tolist()

    portfolios = {
        "ALL_VALIDATED": validated,
        "MEANREV_VALIDATED": meanrev,
        "TREND_VALIDATED": trend,
        "TOP6_ROBUST": quality,
    }
    if "XAU_RR10" in cache:
        portfolios["RR10_PLUS_VALIDATED"] = list(dict.fromkeys(["XAU_RR10"] + [n for n in validated if n != "XAU_RR10"]))

    data_end = min(xau.index.max(), gbp.index.max()) + pd.Timedelta(minutes=5)
    current_month = data_end.floor("D").replace(day=1)
    starts = list(pd.date_range(
        pd.Timestamp("2026-01-01", tz="UTC"),
        current_month,
        freq="MS",
        inclusive="left",
    ))
    monthly_rows = []
    rank_rows = []

    for pname, names in portfolios.items():
        pt = combine_sleeves(cache, names)
        pt.to_csv(out / f"portfolio_{pname}.csv", index=False)
        for risk in RISKS:
            ms = [simulate_month(pt, m, risk) for m in starts]
            for z in ms:
                monthly_rows.append({"portfolio": pname, "sleeves": "|".join(names), **z})
            rets = [z["return_pct"] for z in ms]
            passes = sum(int(z["payout_ready_5pct"]) for z in ms)
            rank_rows.append({
                "portfolio": pname,
                "risk_pct": risk * 100.0,
                "sleeve_count": len(names),
                "sleeves": "|".join(names),
                "months_tested": len(ms),
                "months_payout_ready_5pct": passes,
                "all_months_pass": passes == len(ms),
                "worst_month_pct": min(rets) if rets else None,
                "avg_month_pct": float(np.mean(rets)) if rets else None,
                "median_month_pct": float(np.median(rets)) if rets else None,
                "max_month_dd_pct": max(z["max_dd_pct"] for z in ms) if ms else None,
                "hard_breach_months": sum(int(z["hard_breach"]) for z in ms),
                "min_profitable_days": min(z["profitable_days_0_5"] for z in ms) if ms else 0,
            })

    monthly = pd.DataFrame(monthly_rows)
    ranking = pd.DataFrame(rank_rows).sort_values(
        ["all_months_pass", "months_payout_ready_5pct", "hard_breach_months", "worst_month_pct", "avg_month_pct"],
        ascending=[False, False, True, False, False], na_position="last"
    )
    monthly.to_csv(out / "monthly_2026.csv", index=False)
    ranking.to_csv(out / "portfolio_ranking.csv", index=False)

    best = ranking.iloc[0].to_dict() if len(ranking) else None
    summary = {
        "objective": ">=5% realized return every completed month plus >=5 Finotive-style profitable days, while respecting 3% daily and 6% static DD.",
        "research_policy": "Sleeves are accepted into portfolios from 2017-2022 discovery + 2023-2025 validation only. 2026 is not used to select sleeve membership.",
        "xau_coverage": {"start": xau.index.min(), "end": xau.index.max(), "rows": len(xau)},
        "gbp_coverage": {"start": gbp.index.min(), "end": gbp.index.max(), "rows": len(gbp)},
        "validated_sleeves": validated,
        "best_2026_portfolio": best,
        "risks_tested_pct": [r * 100 for r in RISKS],
    }
    (out / "summary.json").write_text(json.dumps(_safe(summary), indent=2), encoding="utf-8")

    lines = [
        "# CASIO Finotive 5% Monthly-Floor Research",
        "",
        "Hard target: every completed 2026 month >= +5% AND at least five +0.5%-of-initial profitable days, with zero 3% daily / 6% static DD breaches.",
        "",
        "Important: this workflow is a Dukascopy cross-feed discovery/robustness run. The user's FxPro M1 files remain the final broker-feed acceptance source.",
        "",
        "## Pre-2026 sleeve validation",
        "",
        "~~~text",
        sleeve_table.to_string(index=False),
        "~~~",
        "",
        "## 2026 portfolio ranking",
        "",
        "~~~text",
        ranking.to_string(index=False),
        "~~~",
        "",
    ]
    if best:
        b = monthly[(monthly.portfolio == best["portfolio"]) & (monthly.risk_pct == best["risk_pct"])].copy()
        lines += [
            f"## Best: {best['portfolio']} @ {best['risk_pct']:.1f}% risk",
            "",
            "~~~text",
            b[["month","trades_used","return_pct","profitable_days_0_5","max_dd_pct","worst_daily_pct","hard_breach","payout_ready_5pct"]].to_string(index=False),
            "~~~",
            "",
        ]
    accepted = ranking[ranking.all_months_pass.eq(True)] if len(ranking) else ranking
    lines += [
        "## Verdict",
        "",
        (f"Accepted portfolio count: {len(accepted)}." if len(accepted) else "No frozen pre-2026-selected portfolio cleared +5% and five profitable days in every completed Jan-Aug 2026 month on this cross-feed run."),
        "",
        "No live strategy is changed automatically by this research.",
    ]
    (out / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return summary


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--xau", required=True)
    p.add_argument("--gbp", required=True)
    p.add_argument("--output", default="reports/finotive-floor5")
    a = p.parse_args()
    run(a.xau, a.gbp, a.output)


if __name__ == "__main__":
    main()
