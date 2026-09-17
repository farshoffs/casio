from __future__ import annotations

from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

from .v3_core import _adx, _atr, _bars_since, _ema, _resample, load_m5_csv

DATA = Path("data/xauusd_m5_dukascopy_research.csv")
OUT = Path("reports/m15-all-families-2026")
START = pd.Timestamp("2026-01-01T00:00:00Z")
END = pd.Timestamp("2027-01-01T00:00:00Z")
START_RM = 100.0
RISK_FRACTION = 0.05
COST_BPS = 1.0


def _rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def _align_completed(x: pd.DataFrame, index: pd.DatetimeIndex, delta: pd.Timedelta) -> pd.DataFrame:
    y = x.copy()
    y.index = y.index + delta
    eval_time = pd.DatetimeIndex(index + pd.Timedelta(minutes=15))
    out = y.reindex(eval_time, method="ffill")
    out.index = index
    return out


def _session(index: pd.DatetimeIndex) -> np.ndarray:
    mins = index.hour * 60 + index.minute
    return np.select(
        [mins < 360, (mins >= 420) & (mins < 720), (mins >= 750) & (mins < 1020)],
        ["ASIA", "LONDON", "NEW_YORK"],
        default="OTHER",
    )


def prepare(m5: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    m15 = _resample(m5, "15min")
    f = m15.copy()
    f["atr"] = _atr(m15, 14)
    f["adx"] = _adx(m15, 14)
    f["ema9"] = _ema(m15.close, 9)
    f["ema20"] = _ema(m15.close, 20)
    f["ema50"] = _ema(m15.close, 50)
    f["ema200"] = _ema(m15.close, 200)
    f["rsi"] = _rsi(m15.close, 14)
    rng = (m15.high - m15.low).replace(0, np.nan)
    f["body_frac"] = (m15.close - m15.open).abs() / rng
    f["close_loc"] = (m15.close - m15.low) / rng
    f["range_atr"] = rng / f.atr.replace(0, np.nan)
    for n in (5, 10, 20, 30):
        f[f"hh{n}"] = m15.high.shift(1).rolling(n, min_periods=n).max()
        f[f"ll{n}"] = m15.low.shift(1).rolling(n, min_periods=n).min()
    for n in (4, 6, 8):
        f[f"recent_low{n}"] = m15.low.rolling(n, min_periods=n).min()
        f[f"recent_high{n}"] = m15.high.rolling(n, min_periods=n).max()
    f["bb_mid"] = m15.close.rolling(20, min_periods=20).mean()
    std = m15.close.rolling(20, min_periods=20).std()
    f["bb_up"] = f.bb_mid + 2 * std
    f["bb_dn"] = f.bb_mid - 2 * std
    f["bull_fvg"] = m15.low > m15.high.shift(2)
    f["bear_fvg"] = m15.high < m15.low.shift(2)
    f["disp_long"] = (
        (m15.close > m15.open)
        & f.body_frac.ge(.55)
        & f.close_loc.ge(.68)
        & f.range_atr.ge(.80)
        & (m15.close > f.hh5)
    )
    f["disp_short"] = (
        (m15.close < m15.open)
        & f.body_frac.ge(.55)
        & f.close_loc.le(.32)
        & f.range_atr.ge(.80)
        & (m15.close < f.ll5)
    )
    sell_sweep = (m15.low < f.ll20) & (m15.close > f.ll20)
    buy_sweep = (m15.high > f.hh20) & (m15.close < f.hh20)
    f["sell_sweep"] = sell_sweep
    f["buy_sweep"] = buy_sweep
    f["sell_sweep_age"] = _bars_since(sell_sweep)
    f["buy_sweep_age"] = _bars_since(buy_sweep)
    f["bos_long"] = (m15.close > f.hh5) & (m15.close > m15.open)
    f["bos_short"] = (m15.close < f.ll5) & (m15.close < m15.open)
    f["session"] = _session(f.index)

    h1 = _resample(m5, "1h")
    h1f = pd.DataFrame(index=h1.index)
    h1f["h1_close"] = h1.close
    h1f["h1_ema20"] = _ema(h1.close, 20)
    h1f["h1_ema50"] = _ema(h1.close, 50)
    h1f["h1_adx"] = _adx(h1, 14)
    h1f["h1_atr"] = _atr(h1, 14)
    f = f.join(_align_completed(h1f, f.index, pd.Timedelta(hours=1)))
    f["h1_bias"] = np.select(
        [(f.h1_ema20 > f.h1_ema50) & (f.h1_close > f.h1_ema20),
         (f.h1_ema20 < f.h1_ema50) & (f.h1_close < f.h1_ema20)],
        [1, -1], default=0,
    )

    h4 = _resample(m5, "4h")
    h4f = pd.DataFrame(index=h4.index)
    h4f["h4_close"] = h4.close
    h4f["h4_ema20"] = _ema(h4.close, 20)
    h4f["h4_ema50"] = _ema(h4.close, 50)
    h4f["h4_adx"] = _adx(h4, 14)
    f = f.join(_align_completed(h4f, f.index, pd.Timedelta(hours=4)))
    f["h4_bias"] = np.select(
        [(f.h4_ema20 > f.h4_ema50) & (f.h4_close > f.h4_ema20),
         (f.h4_ema20 < f.h4_ema50) & (f.h4_close < f.h4_ema20)],
        [1, -1], default=0,
    )

    d = _resample(m5, "1D")
    dctx = pd.DataFrame({"prev_day_high": d.high, "prev_day_low": d.low}, index=d.index)
    f = f.join(_align_completed(dctx, f.index, pd.Timedelta(days=1)))
    day_key = f.index.floor("D")
    day_open = f.groupby(day_key).open.first()
    f["day_open"] = pd.Series(day_key, index=f.index).map(day_open)

    # Completed Asia and London-morning ranges for the v6 family translation.
    day = pd.Series(day_key, index=f.index)
    asia_src = f[f.index.hour < 6]
    asia = asia_src.groupby(asia_src.index.floor("D")).agg(asia_high=("high", "max"), asia_low=("low", "min"))
    f["asia_high"] = day.map(asia.asia_high)
    f["asia_low"] = day.map(asia.asia_low)
    f.loc[f.index.hour < 6, ["asia_high", "asia_low"]] = np.nan
    lon_src = f[(f.index.hour >= 7) & (f.index.hour < 12)]
    lon = lon_src.groupby(lon_src.index.floor("D")).agg(london_high=("high", "max"), london_low=("low", "min"))
    f["london_high"] = day.map(lon.london_high)
    f["london_low"] = day.map(lon.london_low)
    f.loc[f.index.hour < 12, ["london_high", "london_low"]] = np.nan
    return m15, f


def _quality_target(q: pd.Series | np.ndarray | float) -> pd.Series:
    q = pd.Series(q) if not isinstance(q, pd.Series) else q
    return pd.Series(np.select([q >= 4, q >= 2], [4.0, 3.0], default=2.0), index=q.index)


def _mk(name: str, family: str, long: pd.Series, short: pd.Series, q: pd.Series, note: str,
        stop_lookback: int = 6, max_hold: int = 64) -> dict:
    return {
        "name": name, "family": family, "long": long.fillna(False), "short": short.fillna(False),
        "target": _quality_target(q.fillna(0)), "note": note,
        "stop_lookback": stop_lookback, "max_hold": max_hold,
    }


def build_strategies(f: pd.DataFrame) -> list[dict]:
    bull = f.close > f.open
    bear = f.close < f.open
    primary = pd.Series(np.isin(f.session, ["LONDON", "NEW_YORK"]), index=f.index)
    htf_long = (f.h1_bias >= 0) & (f.h4_bias >= 0)
    htf_short = (f.h1_bias <= 0) & (f.h4_bias <= 0)
    strong_long = (f.h1_bias == 1) & (f.h4_bias == 1)
    strong_short = (f.h1_bias == -1) & (f.h4_bias == -1)

    out: list[dict] = []

    # v1 / legacy: simple trend breakout family.
    l = (f.ema20 > f.ema50) & (f.close > f.hh10) & bull & f.body_frac.ge(.45)
    s = (f.ema20 < f.ema50) & (f.close < f.ll10) & bear & f.body_frac.ge(.45)
    q = f.adx.gt(22).astype(int) + strong_long.astype(int) + strong_short.astype(int)
    out.append(_mk("V1 Legacy M15", "Legacy", l, s, q, "EMA trend + M15 10-bar breakout."))

    # v2: MTF regime-first translation.
    l = strong_long & f.adx.gt(18) & (f.low <= f.ema20 + .2 * f.atr) & (f.close > f.ema20) & bull
    s = strong_short & f.adx.gt(18) & (f.high >= f.ema20 - .2 * f.atr) & (f.close < f.ema20) & bear
    q = strong_long.astype(int) + strong_short.astype(int) + f.adx.gt(25).astype(int) + f.range_atr.gt(.8).astype(int)
    out.append(_mk("V2 MTF M15", "V2", l, s, q, "H4/H1 trend regime + M15 EMA20 pullback."))

    # v3 trend.
    l = strong_long & primary & f.sell_sweep_age.le(4) & f.bos_long
    s = strong_short & primary & f.buy_sweep_age.le(4) & f.bos_short
    q = f.disp_long.astype(int) + f.disp_short.astype(int) + f.adx.gt(22).astype(int) + primary.astype(int)
    out.append(_mk("V3 Trend M15", "V3", l, s, q, "HTF trend + recent M15 liquidity sweep + BOS."))

    # v3 range.
    l = (f.adx < 20) & (f.low <= f.bb_dn) & (f.close > f.bb_dn) & bull & (f.rsi < 45)
    s = (f.adx < 20) & (f.high >= f.bb_up) & (f.close < f.bb_up) & bear & (f.rsi > 55)
    q = (f.adx < 17).astype(int) + primary.astype(int) + (f.range_atr < 1.2).astype(int)
    out.append(_mk("V3 Range M15", "V3", l, s, q, "Low-ADX Bollinger rejection / mean reversion."))

    # v3 combined.
    trend_l = strong_long & f.sell_sweep_age.le(4) & f.bos_long
    trend_s = strong_short & f.buy_sweep_age.le(4) & f.bos_short
    range_l = (f.adx < 20) & (f.low <= f.bb_dn) & (f.close > f.bb_dn) & bull
    range_s = (f.adx < 20) & (f.high >= f.bb_up) & (f.close < f.bb_up) & bear
    l, s = trend_l | range_l, trend_s | range_s
    q = primary.astype(int) + (strong_long | strong_short).astype(int) + (f.disp_long | f.disp_short).astype(int)
    out.append(_mk("V3 Combined M15", "V3", l, s, q, "Trend and range engines combined on M15."))

    # asymmetry challenger.
    l = f.sell_sweep & bull & (f.close_loc > .6) & (f.range_atr > .65)
    s = f.buy_sweep & bear & (f.close_loc < .4) & (f.range_atr > .65)
    q = primary.astype(int) + (strong_long | strong_short).astype(int) + (f.bull_fvg | f.bear_fvg).astype(int) + f.range_atr.gt(1).astype(int)
    out.append(_mk("V3 Asymmetry M15", "V3 Asymmetry", l, s, q, "20-bar liquidity sweep reversal with asymmetric 2R-4R target."))

    # A+ scale-out concept translated to a single comparable 2R-4R target.
    l = strong_long & primary & f.sell_sweep_age.le(2) & f.bull_fvg & f.disp_long
    s = strong_short & primary & f.buy_sweep_age.le(2) & f.bear_fvg & f.disp_short
    q = pd.Series(4, index=f.index)
    out.append(_mk("A+ M15", "A+", l, s, q, "Strict HTF alignment + fresh sweep + FVG + displacement."))

    # Structural A+.
    l = htf_long & primary & f.sell_sweep_age.le(3) & f.bull_fvg & f.bos_long & (f.close > f.day_open)
    s = htf_short & primary & f.buy_sweep_age.le(3) & f.bear_fvg & f.bos_short & (f.close < f.day_open)
    q = (f.bull_fvg | f.bear_fvg).astype(int) + (f.disp_long | f.disp_short).astype(int) + strong_long.astype(int) + strong_short.astype(int)
    out.append(_mk("Structural A+ M15", "Structural A+", l, s, q, "Structure + sweep + FVG + daily-auction alignment."))

    # Structural portfolio: three playbooks union.
    pb_l = strong_long & f.sell_sweep_age.le(5) & f.bull_fvg
    pb_s = strong_short & f.buy_sweep_age.le(5) & f.bear_fvg
    sw_l = htf_long & f.sell_sweep_age.le(2) & f.bull_fvg
    sw_s = htf_short & f.buy_sweep_age.le(2) & f.bear_fvg
    rt_l = primary & htf_long & (f.low <= f.prev_day_high + .15*f.atr) & (f.close > f.prev_day_high) & f.bull_fvg
    rt_s = primary & htf_short & (f.high >= f.prev_day_low - .15*f.atr) & (f.close < f.prev_day_low) & f.bear_fvg
    l, s = pb_l | sw_l | rt_l, pb_s | sw_s | rt_s
    q = primary.astype(int) + (strong_long | strong_short).astype(int) + (f.bull_fvg | f.bear_fvg).astype(int) + (f.disp_long | f.disp_short).astype(int)
    out.append(_mk("Structural Portfolio M15", "Structural Portfolio", l, s, q, "Trend pullback + external sweep + expansion/retest playbooks."))

    # Structural frequency: loosen FVG to displacement/body continuation.
    l = primary & htf_long & f.sell_sweep_age.le(6) & (f.disp_long | f.bull_fvg)
    s = primary & htf_short & f.buy_sweep_age.le(6) & (f.disp_short | f.bear_fvg)
    q = (strong_long | strong_short).astype(int) + (f.bull_fvg | f.bear_fvg).astype(int) + f.range_atr.gt(1).astype(int)
    out.append(_mk("Structural Frequency M15", "Structural Frequency", l, s, q, "Looser displacement/retrace structural engine."))

    # Structural regime router.
    trend_regime = f.h4_adx > 22
    l = primary & ((trend_regime & strong_long & f.bos_long) | (~trend_regime & f.sell_sweep & bull))
    s = primary & ((trend_regime & strong_short & f.bos_short) | (~trend_regime & f.buy_sweep & bear))
    q = trend_regime.astype(int) + (f.bull_fvg | f.bear_fvg).astype(int) + (strong_long | strong_short).astype(int)
    out.append(_mk("Structural Router M15", "Structural Router", l, s, q, "H4-ADX routes between trend continuation and sweep reversal."))

    # Outcome-first structural.
    l = primary & ((f.sell_sweep_age.le(2) & f.bull_fvg) | (strong_long & f.disp_long & (f.low <= f.ema20 + .25*f.atr)))
    s = primary & ((f.buy_sweep_age.le(2) & f.bear_fvg) | (strong_short & f.disp_short & (f.high >= f.ema20 - .25*f.atr)))
    q = (f.bull_fvg | f.bear_fvg).astype(int) + (f.disp_long | f.disp_short).astype(int) + (strong_long | strong_short).astype(int)
    out.append(_mk("Outcome First M15", "Outcome First", l, s, q, "FVG sweep or HTF-aligned displacement pullback."))

    # Route A structural asymmetric.
    l = primary & htf_long & (f.sell_sweep_age.le(5) | (f.low <= f.ema20 + .2*f.atr)) & f.bos_long
    s = primary & htf_short & (f.buy_sweep_age.le(5) | (f.high >= f.ema20 - .2*f.atr)) & f.bos_short
    q = primary.astype(int) + (strong_long | strong_short).astype(int) + (f.bull_fvg | f.bear_fvg).astype(int) + (f.disp_long | f.disp_short).astype(int)
    out.append(_mk("Route A M15", "Route A/B", l, s, q, "Structural asymmetric engine; target graded 2R/3R/4R."))

    # Route B precision is a strict subset.
    l = strong_long & primary & f.sell_sweep_age.le(2) & f.bull_fvg & f.disp_long & (f.close > f.day_open)
    s = strong_short & primary & f.buy_sweep_age.le(2) & f.bear_fvg & f.disp_short & (f.close < f.day_open)
    q = pd.Series(4, index=f.index)
    out.append(_mk("Route B Precision M15", "Route A/B", l, s, q, "A+ precision subset: HTF + sweep + FVG + displacement + day-open alignment."))

    # v4 confluence translation: score creates candidate in the original family.
    long_score = (
        (f.ema9 > f.ema20).astype(int) + (f.ema20 > f.ema50).astype(int) + (f.h1_bias >= 0).astype(int)
        + f.bos_long.astype(int) + f.bull_fvg.astype(int) + f.sell_sweep_age.le(4).astype(int) + f.adx.gt(20).astype(int)
    )
    short_score = (
        (f.ema9 < f.ema20).astype(int) + (f.ema20 < f.ema50).astype(int) + (f.h1_bias <= 0).astype(int)
        + f.bos_short.astype(int) + f.bear_fvg.astype(int) + f.buy_sweep_age.le(4).astype(int) + f.adx.gt(20).astype(int)
    )
    l, s = primary & (long_score >= 5) & bull, primary & (short_score >= 5) & bear
    q = pd.concat([long_score, short_score], axis=1).max(axis=1) - 3
    out.append(_mk("V4 Confluence M15", "V4 Confluence", l, s, q, "Native-M15 confluence score: trend/BOS/FVG/sweep/ADX."))

    # v5 M15-setup / M15-execution translation: remove old M5 execution layer.
    l = strong_long & primary & f.sell_sweep_age.le(4) & (f.bos_long | f.bull_fvg) & (f.close > f.ema20)
    s = strong_short & primary & f.buy_sweep_age.le(4) & (f.bos_short | f.bear_fvg) & (f.close < f.ema20)
    q = (f.bull_fvg | f.bear_fvg).astype(int) + (f.disp_long | f.disp_short).astype(int) + f.adx.gt(22).astype(int) + 1
    out.append(_mk("V5 Native M15", "V5", l, s, q, "V5 without M5 execution: H4/H1 context -> M15 sweep/BOS/FVG -> next M15 open."))

    # v6 session range reaction translation.
    london = f.session == "LONDON"
    ny = f.session == "NEW_YORK"
    v6_l = (
        (london & (f.low < f.asia_low) & (f.close > f.asia_low))
        | (ny & (f.low < f.london_low) & (f.close > f.london_low))
    )
    v6_s = (
        (london & (f.high > f.asia_high) & (f.close < f.asia_high))
        | (ny & (f.high > f.london_high) & (f.close < f.london_high))
    )
    q = f.range_atr.gt(1).astype(int) + bull.astype(int) + bear.astype(int)
    out.append(_mk("V6 Session Reaction M15", "V6", v6_l, v6_s, q, "False-break reversal of completed Asia/London-morning ranges."))

    # v7 family alternative. M15-0591 itself is deliberately not reproduced or ranked.
    prev_exp_l = (f.close.shift(1) > f.hh20.shift(1)) & f.range_atr.shift(1).ge(1.4) & (f.close.shift(1) > f.open.shift(1))
    prev_exp_s = (f.close.shift(1) < f.ll20.shift(1)) & f.range_atr.shift(1).ge(1.4) & (f.close.shift(1) < f.open.shift(1))
    prev_mid = (f.open.shift(1) + f.close.shift(1)) / 2
    l = prev_exp_l & (f.low >= prev_mid) & bull & (f.close > f.close.shift(1))
    s = prev_exp_s & (f.high <= prev_mid) & bear & (f.close < f.close.shift(1))
    q = f.adx.gt(22).astype(int) + (strong_long | strong_short).astype(int) + f.range_atr.shift(1).gt(1.7).astype(int)
    out.append(_mk("V7 Momentum Alt M15", "V7 Momentum", l, s, q, "One-bar M15 expansion-continuation variant; M15-0591 held aside and excluded."))

    return out


def replay(m15: pd.DataFrame, f: pd.DataFrame, spec: dict) -> pd.DataFrame:
    mask = spec["long"] | spec["short"]
    events: list[dict] = []
    next_free = -1
    lookback = int(spec["stop_lookback"])
    for i in np.flatnonzero(mask.to_numpy()):
        if i < next_free or i + 1 >= len(m15):
            continue
        if bool(spec["long"].iat[i]) and bool(spec["short"].iat[i]):
            continue
        d = 1 if bool(spec["long"].iat[i]) else -1
        entry_i = i + 1
        entry = float(m15.open.iat[entry_i])
        atr = float(f.atr.iat[i]) if np.isfinite(f.atr.iat[i]) else np.nan
        if not np.isfinite(entry) or not np.isfinite(atr) or atr <= 0:
            continue
        a = max(0, i - lookback + 1)
        if d == 1:
            stop = float(m15.low.iloc[a:i+1].min()) - .10 * atr
            risk = entry - stop
        else:
            stop = float(m15.high.iloc[a:i+1].max()) + .10 * atr
            risk = stop - entry
        if not np.isfinite(risk) or risk <= 0:
            continue
        risk_atr = risk / atr
        if risk_atr < .35 or risk_atr > 3.0:
            continue
        target_r = float(spec["target"].iat[i])
        target = entry + d * target_r * risk
        gross = reason = None
        exit_i = None
        end = min(len(m15), entry_i + 1 + int(spec["max_hold"]))
        for j in range(entry_i, end):
            lo, hi, close = float(m15.low.iat[j]), float(m15.high.iat[j]), float(m15.close.iat[j])
            hs = lo <= stop if d == 1 else hi >= stop
            ht = hi >= target if d == 1 else lo <= target
            if hs and ht:
                gross, reason = -1.0, "stop_same_bar"
            elif hs:
                gross, reason = -1.0, "stop"
            elif ht:
                gross, reason = target_r, "target"
            elif j == end - 1:
                gross, reason = ((close - entry) / risk) * d, "time_exit"
            else:
                continue
            exit_i = j
            break
        if gross is None or exit_i is None:
            continue
        cost_r = (entry * COST_BPS / 10000.0) / risk
        events.append({
            "strategy": spec["name"], "family": spec["family"], "signal_time": f.index[i],
            "entry_time": m15.index[entry_i] + pd.Timedelta(minutes=15),
            "exit_time": m15.index[exit_i] + pd.Timedelta(minutes=15),
            "direction": d, "entry": entry, "stop": stop, "target_r": target_r,
            "gross_r": gross, "net_r": gross - cost_r, "reason": reason,
        })
        next_free = exit_i + 1
    return pd.DataFrame(events)


def _compound(trades: pd.DataFrame) -> tuple[pd.DataFrame, float, float]:
    x = trades.copy()
    bal = START_RM
    low = bal
    before, after = [], []
    for r in pd.to_numeric(x.get("net_r", pd.Series(dtype=float)), errors="coerce").fillna(0):
        before.append(bal)
        bal = max(0.0, bal * (1 + RISK_FRACTION * float(r)))
        after.append(bal)
        low = min(low, bal)
    if len(x):
        x["balance_before_rm"] = before
        x["balance_after_rm"] = after
    return x, float(bal), float(low)


def _slice(trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    t = pd.to_datetime(trades.entry_time, utc=True)
    return trades[(t >= start) & (t < end)].copy().sort_values("entry_time")


def _summary(trades: pd.DataFrame, observed_end: pd.Timestamp) -> dict:
    x = _slice(trades, START, observed_end)
    x, end_rm, low_rm = _compound(x)
    days = max((observed_end - START).total_seconds() / 86400.0, 1e-9)
    months = pd.period_range(START.tz_convert(None).to_period("M"), (observed_end - pd.Timedelta(seconds=1)).tz_convert(None).to_period("M"), freq="M")
    completed = []
    for p in months:
        month_end = pd.Timestamp(p.end_time).tz_localize("UTC") + pd.Timedelta(nanoseconds=1)
        if month_end <= observed_end:
            completed.append(p)
    counts = []
    if not x.empty:
        ep = pd.to_datetime(x.entry_time, utc=True).dt.tz_convert(None).dt.to_period("M")
        for p in completed:
            counts.append(int((ep == p).sum()))
    else:
        counts = [0 for _ in completed]
    min_completed = min(counts) if counts else 0
    return {
        "trades": int(len(x)),
        "trades_per_30d": float(len(x) * 30 / days),
        "min_completed_month_trades": int(min_completed),
        "ending_balance_rm": end_rm,
        "lowest_balance_rm": low_rm,
        "passes_frequency": bool(min_completed >= 8),
        "passes_growth": bool(end_rm > START_RM),
        "requested_fit": bool(min_completed >= 8 and end_rm > START_RM),
    }


def _monthly(trades: pd.DataFrame, observed_end: pd.Timestamp) -> pd.DataFrame:
    x = _slice(trades, START, observed_end)
    if x.empty:
        return pd.DataFrame(columns=["month", "trades", "pnl_rm", "ending_balance_rm"])
    x, _, _ = _compound(x)
    x["month"] = pd.to_datetime(x.entry_time, utc=True).dt.strftime("%Y-%m")
    rows = []
    prior = START_RM
    for month, g in x.groupby("month", sort=True):
        end_bal = float(g.balance_after_rm.iloc[-1])
        rows.append({"month": month, "trades": len(g), "pnl_rm": end_bal - prior, "ending_balance_rm": end_bal})
        prior = end_bal
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    m5 = load_m5_csv(DATA)
    m5 = m5[m5.index >= pd.Timestamp("2025-10-01", tz="UTC")].copy()
    observed_end = min(END, m5.index.max() + pd.Timedelta(minutes=5))
    if observed_end <= START:
        raise RuntimeError("No 2026 Dukascopy data available")
    m15, f = prepare(m5)
    strategies = build_strategies(f)

    rows = []
    all_trades = []
    all_monthly = []
    for spec in strategies:
        trades = replay(m15, f, spec)
        s = _summary(trades, observed_end)
        rows.append({"strategy": spec["name"], "family": spec["family"], **s, "translation": spec["note"]})
        if not trades.empty:
            z = _slice(trades, START, observed_end)
            z, _, _ = _compound(z)
            all_trades.append(z)
        mo = _monthly(trades, observed_end)
        if not mo.empty:
            mo.insert(0, "strategy", spec["name"])
            all_monthly.append(mo)

    result = pd.DataFrame(rows).sort_values(
        ["requested_fit", "ending_balance_rm", "min_completed_month_trades"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    result.to_csv(OUT / "comparison.csv", index=False)
    if all_trades:
        pd.concat(all_trades, ignore_index=True).to_csv(OUT / "all_trades.csv", index=False)
    if all_monthly:
        pd.concat(all_monthly, ignore_index=True).to_csv(OUT / "monthly.csv", index=False)

    passing = result[result.requested_fit]
    top = result.iloc[0] if len(result) else None
    lines = [
        "# CASIO Native-M15 All-Strategy-Family Benchmark — 2026",
        "",
        "## Test rule",
        "",
        "- Source: `data/xauusd_m5_dukascopy_research.csv`, resampled to native M15 before signal logic.",
        f"- Test: **2026-01-01 through {observed_end.isoformat()}**.",
        "- Start **RM100** independently for every strategy.",
        "- Risk **5% of current balance** per filled trade.",
        "- User frequency target: **at least 8 filled trades in every completed month**.",
        "- Reward target standardized to **2R / 3R / 4R depending on setup quality**.",
        "- Cost: **1 bp round trip**. Same-bar stop/target collision is stop-first.",
        "- Main judgment: does RM100 grow while satisfying the monthly trade floor?",
        "",
        "## M15-0591 status",
        "",
        "**M15-0591 is deliberately held aside. It is not rerun, modified, ranked, or used to define these translations.**",
        "",
        "## Important comparability note",
        "",
        "These are native-M15 translations of each historical CASIO strategy family, not claims of exact Pine/M5 parity. The point of this batch is to ask whether each strategy idea behaves differently when its execution timeframe is M15 under one common RM100/5%/2R-4R test.",
        "",
        f"Families/strategies tested: **{len(result)}**. Requested-fit passes: **{len(passing)}**.",
        "",
        "## Results",
        "",
        result[["strategy", "family", "trades", "trades_per_30d", "min_completed_month_trades", "ending_balance_rm", "lowest_balance_rm", "passes_frequency", "passes_growth", "requested_fit"]].to_markdown(index=False),
        "",
    ]
    if top is not None:
        lines += [
            "## Top result under the user's test",
            "",
            f"**{top.strategy}**: RM100 -> **RM{float(top.ending_balance_rm):.2f}**, {int(top.trades)} trades, minimum **{int(top.min_completed_month_trades)}** trades in a completed month. Requested fit: **{'PASS' if bool(top.requested_fit) else 'FAIL'}**.",
            "",
        ]
    if len(passing):
        lines += ["## Strategies that pass both conditions", "", passing[["strategy", "trades", "min_completed_month_trades", "ending_balance_rm", "lowest_balance_rm"]].to_markdown(index=False), ""]
    else:
        lines += ["## Strategies that pass both conditions", "", "None.", ""]
    lines += [
        "## Translation inventory",
        "",
        result[["strategy", "family", "translation"]].to_markdown(index=False),
        "",
        "## Interpretation",
        "",
        "A PASS here means only that the fixed M15 translation satisfied the requested 2026 money/frequency test. It does not make the strategy proven outside this period. M15-0591 remains separate for later decision-making.",
        "",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    summary = {
        "observed_end": observed_end.isoformat(),
        "strategies_tested": int(len(result)),
        "passing": int(len(passing)),
        "top_strategy": None if top is None else str(top.strategy),
        "top_ending_balance_rm": None if top is None else float(top.ending_balance_rm),
        "m15_0591": "HELD_ASIDE_NOT_RANKED",
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
