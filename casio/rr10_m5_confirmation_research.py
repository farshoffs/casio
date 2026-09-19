from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from casio.regime_router_engine import (
    RegimeRouterConfig,
    _bias,
    _bars_since_sweep,
    _indicators,
    _last_closed,
    _mtf_target,
    _primary,
    _quality,
    _resample,
    replay_engine,
)

DATA = Path("data/xauusd_m5_secondary_octafx_mt4.csv")
OUT = Path("reports/regime-router-canonical/m5-confirmation-research")
START = pd.Timestamp("2016-01-01", tz="UTC")
SCORE_START = pd.Timestamp("2017-03-04", tz="UTC")
RISK_FRAC = 0.05
TARGET_R = 3.0


def load_m5(path: Path) -> pd.DataFrame:
    head = pd.read_csv(path, nrows=0)
    cols = {str(c).strip().lower(): c for c in head.columns}
    if "timestamp" in cols:
        tc = cols["timestamp"]
        df = pd.read_csv(path, usecols=[tc, cols["open"], cols["high"], cols["low"], cols["close"], cols.get("volume", cols.get("tick_volume"))] if ("volume" in cols or "tick_volume" in cols) else [tc, cols["open"], cols["high"], cols["low"], cols["close"]])
        df[tc] = pd.to_datetime(df[tc], utc=True, errors="raise")
    elif "time_utc" in cols:
        tc = cols["time_utc"]
        use = [tc, cols["open"], cols["high"], cols["low"], cols["close"]]
        if "volume" in cols:
            use.append(cols["volume"])
        elif "tick_volume" in cols:
            use.append(cols["tick_volume"])
        df = pd.read_csv(path, usecols=use)
        df[tc] = pd.to_datetime(df[tc], utc=True, errors="raise")
    elif "date" in cols and "time" in cols:
        df = pd.read_csv(path)
        tc = "_timestamp"
        df[tc] = pd.to_datetime(df[cols["date"]].astype(str) + " " + df[cols["time"]].astype(str), utc=True, errors="raise")
    else:
        raise ValueError(f"Unsupported M5 columns: {list(head.columns)}")

    rename = {
        cols["open"]: "open",
        cols["high"]: "high",
        cols["low"]: "low",
        cols["close"]: "close",
    }
    if "volume" in cols:
        rename[cols["volume"]] = "volume"
    elif "tick_volume" in cols:
        rename[cols["tick_volume"]] = "volume"
    df = df.rename(columns=rename)
    if "volume" not in df.columns:
        df["volume"] = 0.0
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"])
    df = df.sort_values(tc).drop_duplicates(tc, keep="last").set_index(tc)
    df.index.name = "timestamp"
    return df.loc[df.index >= START, ["open", "high", "low", "close", "volume"]]


def efficiency(close: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(close), np.nan)
    for i in range(n, len(close)):
        path = np.abs(np.diff(close[i - n : i + 1])).sum()
        out[i] = abs(close[i] - close[i - n]) / path if path > 0 else 0.0
    return out


def micro_0591_flags(m5: pd.DataFrame) -> np.ndarray:
    ind = _indicators(m5)
    a = m5[["open", "high", "low", "close"]].to_numpy(float)
    atr = ind["atr"]
    flags = np.zeros(len(m5), dtype=np.int8)
    state = 0
    imp_seq = 0
    imp_open = imp_close = imp_high = imp_low = imp_atr = broken = pull_extreme = np.nan
    for i in range(20, len(m5)):
        o, high, low, close = map(float, a[i])
        at = float(atr[i])
        if not np.isfinite(at) or at <= 0:
            continue
        rng = max(high - low, 1e-8)
        body = abs(close - o) / rng
        loc = (close - low) / rng
        ratr = rng / at
        hh20 = np.max(a[i - 20:i, 1])
        ll20 = np.min(a[i - 20:i, 2])
        imp_l = ratr >= 1.20 and body >= .55 and loc >= .72 and close > hh20
        imp_s = ratr >= 1.20 and body >= .55 and loc <= .28 and close < ll20
        if state == 0:
            if imp_l and not imp_s:
                state = 1; imp_seq = i
                imp_open, imp_close, imp_high, imp_low, imp_atr, broken, pull_extreme = o, close, high, low, at, hh20, low
            elif imp_s and not imp_l:
                state = -1; imp_seq = i
                imp_open, imp_close, imp_high, imp_low, imp_atr, broken, pull_extreme = o, close, high, low, at, ll20, high
            continue
        if i <= imp_seq:
            continue
        age = i - imp_seq
        imp_body = abs(imp_close - imp_open)
        if age > 4:
            state = 0
            continue
        if state == 1:
            pull_extreme = min(pull_extreme, low)
            invalid = low < imp_low - .30 * imp_atr
            touched = low <= imp_close - .18 * imp_body and high >= imp_close - .50 * imp_body
            confirm = close > o and close > broken
            if invalid:
                state = 0
            elif touched and confirm:
                flags[i] = 1
                state = 0
        else:
            pull_extreme = max(pull_extreme, high)
            invalid = high > imp_high + .30 * imp_atr
            touched = high >= imp_close + .18 * imp_body and low <= imp_close + .50 * imp_body
            confirm = close < o and close < broken
            if invalid:
                state = 0
            elif touched and confirm:
                flags[i] = -1
                state = 0
    return flags


def generate_candidates(m15: pd.DataFrame) -> pd.DataFrame:
    cfg = RegimeRouterConfig(target_r=TARGET_R)
    h1 = _resample(m15, "1h")
    h4 = _resample(m15, "4h")
    d1 = _resample(m15, "1D")
    mi = _indicators(m15)
    h1i = _indicators(h1)
    h4i = _indicators(h4)

    M = m15[["open", "high", "low", "close"]].to_numpy(float)
    H1 = h1[["open", "high", "low", "close"]].to_numpy(float)
    H4 = h4[["open", "high", "low", "close"]].to_numpy(float)
    D1 = d1[["open", "high", "low", "close"]].to_numpy(float)

    m15_ms = m15.index.view("int64") // 1_000_000
    h1_close = h1.index.view("int64") // 1_000_000 + 3_600_000
    h4_close = h4.index.view("int64") // 1_000_000 + 14_400_000
    d1_close = d1.index.view("int64") // 1_000_000 + 86_400_000

    h4_er20 = efficiency(H4[:, 3], 20)
    atr_pct = h4i["atr"] / np.maximum(H4[:, 3], 1e-8)
    med120 = pd.Series(atr_pct).rolling(120, min_periods=60).median().to_numpy()
    h4_pace = atr_pct / med120

    seq = 0
    ms = 0
    impulse_seq = 0
    imp_open = imp_close = imp_high = imp_low = imp_atr = broken = pull_extreme = np.nan
    last = {k: -10**9 for k in ("mL", "mS", "vL", "vS", "oL", "oS", "pL", "pS", "fL", "fS")}
    rows: list[dict[str, Any]] = []

    for i in range(60, len(m15)):
        bar = M[i]
        atr = mi["atr"][i]
        if not np.isfinite(atr) or atr <= 0:
            continue
        close_time_ms = int(m15_ms[i] + 900_000)
        hi1 = _last_closed(h1_close, close_time_ms)
        hi4 = _last_closed(h4_close, close_time_ms)
        di = _last_closed(d1_close, close_time_ms)
        if hi1 < 55 or hi4 < 120 or di < 0:
            continue

        seq += 1
        o, high, low, close = map(float, bar)
        candle_range = max(high - low, 1e-8)
        body_frac = abs(close - o) / candle_range
        close_loc = (close - low) / candle_range
        range_atr = candle_range / atr
        bull = close > o
        bear = close < o
        hh5 = np.max(M[i - 5:i, 1]); ll5 = np.min(M[i - 5:i, 2])
        hh10 = np.max(M[i - 10:i, 1]); ll10 = np.min(M[i - 10:i, 2])
        hh20 = np.max(M[i - 20:i, 1]); ll20 = np.min(M[i - 20:i, 2])
        bull_fvg = low > M[i - 2, 1]
        bear_fvg = high < M[i - 2, 2]
        disp_long = bull and body_frac >= .55 and close_loc >= .68 and range_atr >= .80 and close > hh5
        disp_short = bear and body_frac >= .55 and close_loc <= .32 and range_atr >= .80 and close < ll5
        sell_sweep_age = _bars_since_sweep(M, i, True)
        buy_sweep_age = _bars_since_sweep(M, i, False)
        primary = _primary(m15.index[i], cfg)
        h1_bias = _bias(H1[hi1, 3], h1i["e20"][hi1], h1i["e50"][hi1])
        h4_bias = _bias(H4[hi4, 3], h4i["e20"][hi4], h4i["e50"][hi4])
        h4_adx = float(h4i["adx"][hi4])
        strong_long = h1_bias == 1 and h4_bias == 1
        strong_short = h1_bias == -1 and h4_bias == -1
        htf_long = h1_bias >= 0 and h4_bias >= 0
        htf_short = h1_bias <= 0 and h4_bias <= 0
        strong_trend = h1_bias != 0 and h1_bias == h4_bias and h4_adx >= 18.0

        v1_long = mi["e20"][i] > mi["e50"][i] and close > hh10 and bull and body_frac >= .45
        v1_short = mi["e20"][i] < mi["e50"][i] and close < ll10 and bear and body_frac >= .45
        v1_dir = 1 if v1_long and not v1_short else -1 if v1_short and not v1_long else 0

        out_long = primary and ((sell_sweep_age <= 2 and bull_fvg) or (strong_long and disp_long and low <= mi["e20"][i] + .25 * atr))
        out_short = primary and ((buy_sweep_age <= 2 and bear_fvg) or (strong_short and disp_short and high >= mi["e20"][i] - .25 * atr))
        out_dir = 1 if out_long and not out_short else -1 if out_short and not out_long else 0

        sf_long = primary and htf_long and sell_sweep_age <= 6 and (disp_long or bull_fvg)
        sf_short = primary and htf_short and buy_sweep_age <= 6 and (disp_short or bear_fvg)
        sf_dir = 1 if sf_long and not sf_short else -1 if sf_short and not sf_long else 0

        prev_day_high = float(D1[di, 1]); prev_day_low = float(D1[di, 2])
        sp_base_long = (strong_long and sell_sweep_age <= 5 and bull_fvg) or (htf_long and sell_sweep_age <= 2 and bull_fvg) or (
            primary and htf_long and low <= prev_day_high + .15 * atr and close > prev_day_high and bull_fvg
        )
        sp_base_short = (strong_short and buy_sweep_age <= 5 and bear_fvg) or (htf_short and buy_sweep_age <= 2 and bear_fvg) or (
            primary and htf_short and high >= prev_day_low - .15 * atr and close < prev_day_low and bear_fvg
        )
        sp_base_r = _quality(int(primary) + int(strong_long or strong_short) + int(bull_fvg or bear_fvg) + int(disp_long or disp_short))
        spl = _mtf_target(sp_base_r, 1, h1_bias, h4_bias, h4_adx)
        sps = _mtf_target(sp_base_r, -1, h1_bias, h4_bias, h4_adx)
        sp_long = sp_base_long and spl[0]
        sp_short = sp_base_short and sps[0]
        sp_dir = 1 if sp_long and not sp_short else -1 if sp_short and not sp_long else 0

        m0591_dir = 0
        m0591_stop = np.nan
        imp_long = range_atr >= 1.20 and body_frac >= .55 and close_loc >= .72 and close > hh20
        imp_short = range_atr >= 1.20 and body_frac >= .55 and close_loc <= .28 and close < ll20
        if ms == 0:
            if imp_long and not imp_short:
                ms = 1; impulse_seq = seq
                imp_open, imp_close, imp_high, imp_low, imp_atr, broken, pull_extreme = o, close, high, low, atr, hh20, low
            elif imp_short and not imp_long:
                ms = -1; impulse_seq = seq
                imp_open, imp_close, imp_high, imp_low, imp_atr, broken, pull_extreme = o, close, high, low, atr, ll20, high
        elif seq > impulse_seq:
            age = seq - impulse_seq
            imp_body = abs(imp_close - imp_open)
            if age > 4:
                ms = 0
            elif ms == 1:
                pull_extreme = min(pull_extreme, low)
                invalid = low < imp_low - .30 * imp_atr
                touched = low <= imp_close - .18 * imp_body and high >= imp_close - .50 * imp_body
                confirm = close > o and close > broken
                if invalid:
                    ms = 0
                elif touched and confirm:
                    allowed, _ = _mtf_target(3, 1, h1_bias, h4_bias, h4_adx)
                    if allowed:
                        m0591_dir = 1
                        m0591_stop = pull_extreme - .12 * imp_atr
                    ms = 0
            else:
                pull_extreme = max(pull_extreme, high)
                invalid = high > imp_high + .30 * imp_atr
                touched = high >= imp_close + .18 * imp_body and low <= imp_close + .50 * imp_body
                confirm = close < o and close < broken
                if invalid:
                    ms = 0
                elif touched and confirm:
                    allowed, _ = _mtf_target(3, -1, h1_bias, h4_bias, h4_adx)
                    if allowed:
                        m0591_dir = -1
                        m0591_stop = pull_extreme + .12 * imp_atr
                    ms = 0

        if m0591_dir == 1: last["mL"] = seq
        if m0591_dir == -1: last["mS"] = seq
        if v1_dir == 1: last["vL"] = seq
        if v1_dir == -1: last["vS"] = seq
        if out_dir == 1: last["oL"] = seq
        if out_dir == -1: last["oS"] = seq
        if sp_dir == 1: last["pL"] = seq
        if sp_dir == -1: last["pS"] = seq
        if sf_dir == 1: last["fL"] = seq
        if sf_dir == -1: last["fS"] = seq

        recent = lambda x: seq - x <= cfg.support_bars
        support_long = sum(int(recent(last[k])) for k in ("mL", "vL", "oL", "pL", "fL"))
        support_short = sum(int(recent(last[k])) for k in ("mS", "vS", "oS", "pS", "fS"))
        support_dir = support_long if m0591_dir == 1 else support_short
        align_count = int(h1_bias == m0591_dir) + int(h4_bias == m0591_dir) if m0591_dir else 0

        if strong_trend:
            selected = m0591_dir != 0 and m0591_dir == h1_bias
        else:
            selected = sp_dir == 0 and m0591_dir != 0 and support_dir >= 2

        canonical_candidate = selected and not primary and align_count >= 1 and np.isfinite(m0591_stop)
        if not canonical_candidate:
            continue

        direction = int(m0591_dir)
        v1_recent = recent(last["vL"] if direction == 1 else last["vS"])
        er20 = float(h4_er20[hi4])
        pace = float(h4_pace[hi4])
        mixed_bad = (not strong_trend) and h4_bias == direction and np.isfinite(er20) and er20 < 0.25 and np.isfinite(pace) and pace < 1.10
        trend_bad = strong_trend and (not v1_recent) and np.isfinite(pace) and pace < 1.00
        rows.append({
            "signal_time": m15.index[i] + pd.Timedelta(minutes=15),
            "signal_bar_open": m15.index[i],
            "direction": direction,
            "entry0": close,
            "stop": float(m0591_stop),
            "router_mode": "TREND" if strong_trend else "MIXED",
            "support": int(support_dir),
            "h1_bias": int(h1_bias),
            "h4_bias": int(h4_bias),
            "h4_adx": h4_adx,
            "h4_er20": er20,
            "h4_pace": pace,
            "v1_recent": bool(v1_recent),
            "questionable": bool(mixed_bad or trend_bad),
            "questionable_type": "MIXED_STALLED_H4" if mixed_bad else "TREND_NO_V1_SLOW" if trend_bad else "NORMAL",
        })
    return pd.DataFrame(rows)


def m5_confirm(
    row: pd.Series,
    m5: pd.DataFrame,
    m5_ind: dict[str, np.ndarray],
    micro: np.ndarray,
    method: str,
    window_min: int,
) -> tuple[bool, pd.Timestamp | None, float | None, pd.Timestamp]:
    t = pd.Timestamp(row.signal_time)
    direction = int(row.direction)
    stop = float(row.stop)
    entry0 = float(row.entry0)
    deadline = t + pd.Timedelta(minutes=window_min)
    idx = m5.index
    A = m5[["open", "high", "low", "close"]].to_numpy(float)
    start = int(idx.searchsorted(t, side="left"))
    end = int(idx.searchsorted(deadline, side="left"))
    end = min(end, len(m5))

    # A recent completed M5 micro-0591 can confirm method B/C immediately.
    if method in ("B", "C"):
        prior_end = int(idx.searchsorted(t, side="left"))
        lo = max(0, prior_end - 2)
        if np.any(micro[lo:prior_end] == direction):
            return True, t, entry0, t

    pulled = False
    for j in range(start, end):
        o, hi, lo_, cl = map(float, A[j])
        close_t = idx[j] + pd.Timedelta(minutes=5)
        if direction == 1 and lo_ <= stop:
            return False, None, None, close_t
        if direction == -1 and hi >= stop:
            return False, None, None, close_t

        if direction == 1:
            if lo_ <= entry0 or cl < o:
                pulled = True
        else:
            if hi >= entry0 or cl > o:
                pulled = True

        a_ok = False
        if method in ("A", "C") and j >= 3 and pulled:
            rng = max(hi - lo_, 1e-8)
            body = abs(cl - o) / rng
            if direction == 1:
                a_ok = cl > o and body >= .45 and cl > np.max(A[j - 3:j, 1]) and cl > m5_ind["e20"][j]
            else:
                a_ok = cl < o and body >= .45 and cl < np.min(A[j - 3:j, 2]) and cl < m5_ind["e20"][j]

        b_ok = method in ("B", "C") and micro[j] == direction
        if a_ok or b_ok:
            return True, close_t, cl, close_t

    return False, None, None, deadline


def find_exit(m5: pd.DataFrame, entry_time: pd.Timestamp, direction: int, entry: float, stop: float) -> tuple[pd.Timestamp | None, float | None]:
    risk = abs(entry - stop)
    if risk <= 0 or (direction == 1 and entry <= stop) or (direction == -1 and entry >= stop):
        return entry_time, -1.0
    target = entry + direction * TARGET_R * risk
    idx = m5.index
    A = m5[["open", "high", "low", "close"]].to_numpy(float)
    start = int(idx.searchsorted(entry_time, side="left"))
    for j in range(start, len(m5)):
        hi = float(A[j, 1]); lo = float(A[j, 2])
        stop_hit = lo <= stop if direction == 1 else hi >= stop
        target_hit = hi >= target if direction == 1 else lo <= target
        if stop_hit or target_hit:
            return idx[j] + pd.Timedelta(minutes=5), (-1.0 if stop_hit else TARGET_R)
    return None, None


def simulate(cands: pd.DataFrame, m5: pd.DataFrame, method: str | None, window_min: int = 0) -> tuple[pd.DataFrame, dict[str, int]]:
    ind = _indicators(m5)
    micro = micro_0591_flags(m5) if method in ("B", "C") else np.zeros(len(m5), dtype=np.int8)
    available = SCORE_START
    trades: list[dict[str, Any]] = []
    counts = {"questionable_seen": 0, "questionable_confirmed": 0, "questionable_rejected": 0}

    for _, row in cands.iterrows():
        t = pd.Timestamp(row.signal_time)
        if t < SCORE_START or t < available:
            continue
        if bool(row.questionable):
            counts["questionable_seen"] += 1

        if bool(row.questionable) and method is not None:
            ok, et, ep, fail_or_confirm_t = m5_confirm(row, m5, ind, micro, method, window_min)
            if not ok:
                counts["questionable_rejected"] += 1
                available = max(available, fail_or_confirm_t)
                continue
            counts["questionable_confirmed"] += 1
            entry_time = et
            entry = float(ep)
        else:
            entry_time = t
            entry = float(row.entry0)

        exit_time, result = find_exit(m5, entry_time, int(row.direction), entry, float(row.stop))
        if result is None:
            break
        trades.append({
            **row.to_dict(),
            "entry_time": entry_time,
            "entry": entry,
            "exit_time": exit_time,
            "result_r": float(result),
            "m5_method": method or "NONE",
            "m5_window_min": window_min,
        })
        available = exit_time

    return pd.DataFrame(trades), counts


def metrics(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, float]:
    if df.empty:
        return {"trades":0,"wins":0,"wr":0.0,"exp":0.0,"pf":0.0,"freq":0.0,"dd":0.0,"end_rm":100.0,"net_r":0.0}
    x = df[(pd.to_datetime(df.entry_time, utc=True) >= start) & (pd.to_datetime(df.entry_time, utc=True) < end)].copy()
    if x.empty:
        return {"trades":0,"wins":0,"wr":0.0,"exp":0.0,"pf":0.0,"freq":0.0,"dd":0.0,"end_rm":100.0,"net_r":0.0}
    r = x.result_r.to_numpy(float)
    n = len(r); wins = int((r > 0).sum())
    gp = float(r[r > 0].sum()); gl = float(-r[r < 0].sum())
    eq = 100.0; peak = eq; maxdd = 0.0
    for rr in r:
        eq *= 1.0 + RISK_FRAC * rr
        peak = max(peak, eq)
        maxdd = max(maxdd, (peak - eq) / peak if peak else 0.0)
    days = max((end - start).total_seconds() / 86400.0, 1.0)
    return {
        "trades": n,
        "wins": wins,
        "wr": wins / n * 100.0,
        "exp": float(r.mean()),
        "pf": gp / gl if gl > 0 else float("inf"),
        "freq": n / days * 30.0,
        "dd": maxdd * 100.0,
        "end_rm": eq,
        "net_r": float(r.sum()),
    }


def fmt(m: dict[str, float]) -> str:
    return f"{m['trades']} trades, {m['wr']:.2f}% WR, {m['exp']:+.3f}R exp, PF {m['pf']:.2f}, {m['freq']:.2f}/30d, DD {m['dd']:.2f}%"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    m5 = load_m5(DATA)
    m15 = _resample(m5, "15min")
    cands = generate_candidates(m15)

    policies: dict[str, tuple[str | None, int]] = {
        "IMMEDIATE": (None, 0),
        "A15_STRUCTURE": ("A", 15),
        "A30_STRUCTURE": ("A", 30),
        "B15_MICRO0591": ("B", 15),
        "B30_MICRO0591": ("B", 30),
        "C15_EITHER": ("C", 15),
        "C30_EITHER": ("C", 30),
    }

    results: dict[str, pd.DataFrame] = {}
    counts: dict[str, dict[str, int]] = {}
    for name, (method, win) in policies.items():
        print("running", name, flush=True)
        results[name], counts[name] = simulate(cands, m5, method, win)

    data_end = m5.index.max() + pd.Timedelta(minutes=5)
    dev_start = SCORE_START
    dev_end = pd.Timestamp("2024-01-01", tz="UTC")
    hold_start = dev_end
    hold_end = min(data_end, pd.Timestamp("2026-01-31", tz="UTC"))

    rows = []
    for name, df in results.items():
        for label, s, e in [
            ("2017-2023", dev_start, dev_end),
            ("2020-2023", pd.Timestamp("2020-01-01", tz="UTC"), dev_end),
            ("2024-2025", hold_start, min(hold_end, pd.Timestamp("2026-01-01", tz="UTC"))),
        ]:
            m = metrics(df, s, e)
            rows.append({"policy":name,"period":label,**m,**counts[name]})
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT / "summary.csv", index=False)

    year_rows = []
    for name, df in results.items():
        for y in range(2017, 2027):
            s = max(SCORE_START, pd.Timestamp(f"{y}-01-01", tz="UTC"))
            e = min(data_end, pd.Timestamp(f"{y+1}-01-01", tz="UTC"))
            if e <= s:
                continue
            m = metrics(df, s, e)
            year_rows.append({"policy":name,"year":y,**m})
    yearly = pd.DataFrame(year_rows)
    yearly.to_csv(OUT / "yearly.csv", index=False)

    # Raw questionable confirmation rates, independent of one-active-trade selection.
    qrows = []
    q = cands[(cands.signal_time >= SCORE_START) & cands.questionable].copy()
    ind = _indicators(m5)
    micro = micro_0591_flags(m5)
    for name, (method, win) in policies.items():
        if method is None:
            continue
        for typ, group in q.groupby("questionable_type"):
            ok = 0
            for _, row in group.iterrows():
                yes, *_ = m5_confirm(row, m5, ind, micro, method, win)
                ok += int(yes)
            qrows.append({"policy":name,"questionable_type":typ,"signals":len(group),"confirmed":ok,"confirm_rate_pct":100.0*ok/len(group) if len(group) else 0.0})
    pd.DataFrame(qrows).to_csv(OUT / "questionable_confirmation_rates.csv", index=False)

    base_dev = metrics(results["IMMEDIATE"], dev_start, dev_end)
    eligible = []
    for name in policies:
        if name == "IMMEDIATE":
            continue
        m = metrics(results[name], dev_start, dev_end)
        if m["freq"] >= 0.85 * base_dev["freq"] and m["exp"] > base_dev["exp"] and m["dd"] < base_dev["dd"]:
            eligible.append((m["exp"], name, m))
    selected = max(eligible)[1] if eligible else None

    lines = []
    lines += [
        "# RR10 Conditional M5 Confirmation Research — Secondary Feed",
        "",
        "## Scope",
        "",
        "Research only. **No live RR10 files are modified.**",
        "",
        "The canonical M15/H1/H4 RR10 router and 0591 signal logic are frozen. M5 is used only when an otherwise-valid M15 RR10 signal is classified as questionable by the existing research hypotheses:",
        "",
        "- MIXED: H4 aligned with direction + H4 ER20 < 0.25 + normalized H4 pace < 1.10",
        "- TREND: no recent V1 confirmation + normalized H4 pace < 1.00",
        "",
        "Normal/favourable RR10 signals enter immediately exactly as before.",
        "",
        "### Data limitation",
        "",
        "This first M5 pass uses the repository's **OctaFX / Octa Markets MT4 secondary XAUUSD M5 dataset**, not FxPro M5.",
        f"- M5 coverage used: {m5.index.min().isoformat()} -> {m5.index.max().isoformat()}",
        f"- M5 rows used after warm-up cut: {len(m5):,}",
        f"- Resampled M15 rows: {len(m15):,}",
        f"- Raw RR10 candidate signals from 2017-03-04 onward: {int((cands.signal_time >= SCORE_START).sum()):,}",
        "",
        "Therefore this is a **cross-broker robustness experiment**, not execution-grade FxPro validation.",
        "",
        "## M5 confirmation variants",
        "",
        "- **A / STRUCTURE**: after a pullback/opposite M5 bar, require a directional M5 close breaking the prior 3-bar local extreme with >=45% body and on the correct side of M5 EMA20.",
        "- **B / MICRO0591**: require an M5 0591 confirmation in the same direction; a confirmation in the last two completed M5 bars can validate immediately.",
        "- **C / EITHER**: accept the first A or B confirmation.",
        "- Windows tested: 15 and 30 minutes.",
        "",
        "For delayed entries the original M15 structural stop is preserved. The 3R target is recalculated from the actual confirmed M5 entry to that same structural stop. Stop-first is used on an M5 bar if stop and target collide.",
        "",
        "## Aggregate results",
        "",
        "| Policy | 2017-2023 | 2020-2023 | 2024-2025 |",
        "|---|---|---|---|",
    ]
    for name in policies:
        a = metrics(results[name], dev_start, dev_end)
        b = metrics(results[name], pd.Timestamp("2020-01-01", tz="UTC"), dev_end)
        c = metrics(results[name], hold_start, min(hold_end, pd.Timestamp("2026-01-01", tz="UTC")))
        lines.append(f"| {name} | {fmt(a)} | {fmt(b)} | {fmt(c)} |")

    lines += ["", "## Pre-registered development selection rule", ""]
    lines += [
        "A candidate is considered development-promising only if, versus IMMEDIATE on 2017-2023, it:",
        "- retains at least 85% of trade frequency,",
        "- improves expectancy, and",
        "- reduces max drawdown.",
        "",
        f"Selected by development data only: **{selected or 'NONE'}**.",
        "",
    ]
    if selected:
        lines += [
            "The 2024-2025 result for that candidate is treated as the holdout check and was not used to choose it.",
            "",
        ]

    lines += [
        "## Important interpretation",
        "",
        "Because the M5 feed is from a different broker than the FxPro M15 research base, a positive result here means the *idea is robust enough to justify an FxPro-M5 validation*. It does not justify deployment by itself.",
        "",
        "A full deployment decision still requires genuine FxPro XAUUSD M5 history aligned to the FxPro M15 feed.",
        "",
        "No TradingView Pine, cBot, canonical RR10 Python engine, or live configuration was changed.",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "metadata.json").write_text(json.dumps({
        "source":"OctaFX / Octa Markets MT4 secondary M5",
        "m5_start":m5.index.min().isoformat(),
        "m5_end":m5.index.max().isoformat(),
        "m5_rows":len(m5),
        "m15_rows":len(m15),
        "selected_development_candidate":selected,
        "policies":policies,
    }, indent=2), encoding="utf-8")

    print((OUT / "REPORT.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
