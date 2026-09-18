from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ENGINE_ID = "RR10"


@dataclass(frozen=True)
class RegimeRouterConfig:
    target_r: float = 3.0
    support_bars: int = 2
    primary_1_start_minute: int = 7 * 60
    primary_1_end_minute: int = 12 * 60
    primary_2_start_minute: int = 12 * 60 + 30
    primary_2_end_minute: int = 17 * 60


def load_price_csv(path: str | Path) -> tuple[pd.DataFrame, str]:
    df = pd.read_csv(path)
    timestamp_col = "timestamp" if "timestamp" in df.columns else "time_utc" if "time_utc" in df.columns else None
    if timestamp_col is None:
        raise ValueError("CSV needs timestamp or time_utc")
    required = {"open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"missing columns: {', '.join(sorted(missing))}")
    df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True, errors="raise")
    df = df.sort_values(timestamp_col).drop_duplicates(timestamp_col, keep="last")
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="raise")
    volume_col = "volume" if "volume" in df.columns else "tick_volume" if "tick_volume" in df.columns else None
    if volume_col is None:
        df["volume"] = 0.0
    elif volume_col != "volume":
        df["volume"] = pd.to_numeric(df[volume_col], errors="coerce").fillna(0.0)
    tf = "UNKNOWN"
    if "timeframe" in df.columns and len(df):
        tf = str(df["timeframe"].iloc[-1]).upper()
    else:
        delta = df[timestamp_col].diff().dropna().median()
        if pd.notna(delta):
            mins = round(delta.total_seconds() / 60)
            tf = f"M{mins}" if mins < 60 else (f"H{mins//60}" if mins % 60 == 0 else f"M{mins}")
    x = df.set_index(timestamp_col)[["open", "high", "low", "close", "volume"]]
    if tf == "M15":
        return x, tf
    x = x.resample("15min", label="left", closed="left", origin="epoch").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), volume=("volume", "sum")
    ).dropna(subset=["open", "high", "low", "close"])
    return x, tf


def _resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    return df.resample(rule, label="left", closed="left", origin="epoch").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), volume=("volume", "sum")
    ).dropna(subset=["open", "high", "low", "close"])


def _ema(values: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(values), np.nan, dtype=float)
    if not len(values):
        return out
    e = float(values[0]); k = 2.0 / (n + 1.0); out[0] = e
    for i in range(1, len(values)):
        e = float(values[i]) * k + e * (1.0 - k)
        out[i] = e
    return out


def _wilder(values: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(values), np.nan, dtype=float)
    if not len(values):
        return out
    s = float(values[0]) if np.isfinite(values[0]) else 0.0
    out[0] = s
    for i in range(1, len(values)):
        v = float(values[i]) if np.isfinite(values[i]) else 0.0
        s = (s * (n - 1) + v) / n
        out[i] = s
    return out


def _indicators(df: pd.DataFrame) -> dict[str, np.ndarray]:
    high = df.high.to_numpy(float); low = df.low.to_numpy(float); close = df.close.to_numpy(float)
    tr = np.zeros(len(df), dtype=float)
    plus = np.zeros(len(df), dtype=float); minus = np.zeros(len(df), dtype=float)
    for i in range(len(df)):
        r = high[i] - low[i]
        tr[i] = r if i == 0 else max(r, abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
        if i:
            up = high[i] - high[i - 1]; down = low[i - 1] - low[i]
            plus[i] = up if up > down and up > 0 else 0.0
            minus[i] = down if down > up and down > 0 else 0.0
    atr = _wilder(tr, 14); str_ = _wilder(tr, 14); sp = _wilder(plus, 14); sm = _wilder(minus, 14)
    dx = np.full(len(df), np.nan, dtype=float)
    for i in range(len(df)):
        if not str_[i]:
            continue
        pdi = 100.0 * sp[i] / str_[i]; mdi = 100.0 * sm[i] / str_[i]; den = pdi + mdi
        dx[i] = 100.0 * abs(pdi - mdi) / den if den else 0.0
    return {"atr": atr, "e20": _ema(close, 20), "e50": _ema(close, 50),
            "adx": _wilder(np.where(np.isfinite(dx), dx, 0.0), 14)}


def _bias(close: float, e20: float, e50: float) -> int:
    return 1 if e20 > e50 and close > e20 else -1 if e20 < e50 and close < e20 else 0


def _quality(q: int) -> int:
    return 4 if q >= 4 else 3 if q >= 2 else 2


def _mtf_target(base: int, direction: int, h1_bias: int, h4_bias: int, h4_adx: float) -> tuple[bool, int]:
    blocked = h1_bias == -direction and h4_bias == -direction
    base_grade = 2 if base >= 4 else 1 if base >= 3 else 0
    align = int(h1_bias == direction) + int(h4_bias == direction)
    strong = int(align == 2 and h4_adx >= 18.0)
    score = base_grade + align + strong
    return (not blocked, 4 if score >= 3 else 3 if score >= 1 else 2)


def _primary(ts: pd.Timestamp, cfg: RegimeRouterConfig) -> bool:
    minute = ts.hour * 60 + ts.minute
    return (cfg.primary_1_start_minute <= minute < cfg.primary_1_end_minute) or (
        cfg.primary_2_start_minute <= minute < cfg.primary_2_end_minute
    )


def _bars_since_sweep(arr: np.ndarray, i: int, sell: bool, max_age: int = 6) -> int:
    for age in range(max_age + 1):
        j = i - age
        if j < 20:
            break
        if sell:
            ref = np.min(arr[j - 20:j, 2]); ok = arr[j, 2] < ref and arr[j, 3] > ref
        else:
            ref = np.max(arr[j - 20:j, 1]); ok = arr[j, 1] > ref and arr[j, 3] < ref
        if ok:
            return age
    return 999


def _last_closed(close_ms: np.ndarray, close_time_ms: int) -> int:
    return int(np.searchsorted(close_ms, close_time_ms, side="right") - 1)


def replay_engine(m15: pd.DataFrame, cfg: RegimeRouterConfig | None = None) -> tuple[pd.DataFrame, dict[str, Any] | None]:
    cfg = cfg or RegimeRouterConfig()
    if len(m15) < 500:
        raise ValueError("RR10 needs at least 500 M15 bars")
    h1 = _resample(m15, "1h"); h4 = _resample(m15, "4h"); d1 = _resample(m15, "1D")
    mi = _indicators(m15); h1i = _indicators(h1); h4i = _indicators(h4)
    M = m15[["open", "high", "low", "close"]].to_numpy(float)
    H1 = h1[["open", "high", "low", "close"]].to_numpy(float)
    H4 = h4[["open", "high", "low", "close"]].to_numpy(float)
    D1 = d1[["open", "high", "low", "close"]].to_numpy(float)
    m15_ms = m15.index.view("int64") // 1_000_000
    h1_close = h1.index.view("int64") // 1_000_000 + 3_600_000
    h4_close = h4.index.view("int64") // 1_000_000 + 14_400_000
    d1_close = d1.index.view("int64") // 1_000_000 + 86_400_000

    seq = 0; ms = 0; impulse_seq = 0
    imp_open = imp_close = imp_high = imp_low = imp_atr = broken = pull_extreme = np.nan
    last = {k: -10**9 for k in ("mL", "mS", "vL", "vS", "oL", "oS", "pL", "pS", "fL", "fS")}
    active: dict[str, Any] | None = None
    events: list[dict[str, Any]] = []

    for i in range(60, len(m15)):
        bar = M[i]; atr = mi["atr"][i]
        if not np.isfinite(atr) or atr <= 0:
            continue
        close_time_ms = int(m15_ms[i] + 900_000)
        hi1 = _last_closed(h1_close, close_time_ms); hi4 = _last_closed(h4_close, close_time_ms); di = _last_closed(d1_close, close_time_ms)
        if hi1 < 55 or hi4 < 55 or di < 0:
            continue

        if active is not None:
            stop_hit = bar[2] <= active["stop"] if active["direction"] == 1 else bar[1] >= active["stop"]
            target_hit = bar[1] >= active["target"] if active["direction"] == 1 else bar[2] <= active["target"]
            if stop_hit or target_hit:
                active["exit_time_utc"] = (m15.index[i] + pd.Timedelta(minutes=15)).isoformat()
                active["result_r"] = -1.0 if stop_hit else cfg.target_r
                active["exit_reason"] = "stop_same_bar" if stop_hit and target_hit else "stop" if stop_hit else "target"
                events.append(active.copy())
                active = None

        seq += 1
        o, high, low, close = map(float, bar)
        candle_range = max(high - low, 1e-8); body_frac = abs(close - o) / candle_range
        close_loc = (close - low) / candle_range; range_atr = candle_range / atr
        bull = close > o; bear = close < o
        hh5 = np.max(M[i - 5:i, 1]); ll5 = np.min(M[i - 5:i, 2])
        hh10 = np.max(M[i - 10:i, 1]); ll10 = np.min(M[i - 10:i, 2])
        hh20 = np.max(M[i - 20:i, 1]); ll20 = np.min(M[i - 20:i, 2])
        bull_fvg = low > M[i - 2, 1]; bear_fvg = high < M[i - 2, 2]
        disp_long = bull and body_frac >= .55 and close_loc >= .68 and range_atr >= .80 and close > hh5
        disp_short = bear and body_frac >= .55 and close_loc <= .32 and range_atr >= .80 and close < ll5
        sell_sweep_age = _bars_since_sweep(M, i, True); buy_sweep_age = _bars_since_sweep(M, i, False)
        primary = _primary(m15.index[i], cfg)
        h1_bias = _bias(H1[hi1, 3], h1i["e20"][hi1], h1i["e50"][hi1])
        h4_bias = _bias(H4[hi4, 3], h4i["e20"][hi4], h4i["e50"][hi4]); h4_adx = float(h4i["adx"][hi4])
        strong_long = h1_bias == 1 and h4_bias == 1; strong_short = h1_bias == -1 and h4_bias == -1
        htf_long = h1_bias >= 0 and h4_bias >= 0; htf_short = h1_bias <= 0 and h4_bias <= 0
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
        spl = _mtf_target(sp_base_r, 1, h1_bias, h4_bias, h4_adx); sps = _mtf_target(sp_base_r, -1, h1_bias, h4_bias, h4_adx)
        sp_long = sp_base_long and spl[0]; sp_short = sp_base_short and sps[0]
        sp_dir = 1 if sp_long and not sp_short else -1 if sp_short and not sp_long else 0

        m0591_dir = 0; m0591_stop = np.nan
        imp_long = range_atr >= 1.20 and body_frac >= .55 and close_loc >= .72 and close > hh20
        imp_short = range_atr >= 1.20 and body_frac >= .55 and close_loc <= .28 and close < ll20
        if ms == 0:
            if imp_long and not imp_short:
                ms = 1; impulse_seq = seq; imp_open = o; imp_close = close; imp_high = high; imp_low = low; imp_atr = atr; broken = hh20; pull_extreme = low
            elif imp_short and not imp_long:
                ms = -1; impulse_seq = seq; imp_open = o; imp_close = close; imp_high = high; imp_low = low; imp_atr = atr; broken = ll20; pull_extreme = high
        elif seq > impulse_seq:
            age = seq - impulse_seq; imp_body = abs(imp_close - imp_open)
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
                        m0591_dir = 1; m0591_stop = pull_extreme - .12 * imp_atr
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
                        m0591_dir = -1; m0591_stop = pull_extreme + .12 * imp_atr
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
            old_router_selected_0591 = m0591_dir != 0 and m0591_dir == h1_bias
        else:
            old_router_selected_0591 = sp_dir == 0 and m0591_dir != 0 and support_dir >= 2
        canonical = (
            active is None
            and old_router_selected_0591
            and not primary
            and align_count >= 1
            and np.isfinite(m0591_stop)
        )
        if canonical:
            direction = int(m0591_dir); entry = close; stop = float(m0591_stop); risk = abs(entry - stop)
            if risk > 0:
                active = {
                    "engine": ENGINE_ID,
                    "event": "signal",
                    "signal_id": f"{ENGINE_ID}:{int(close_time_ms)}:{direction}",
                    "symbol": "XAUUSD",
                    "timeframe": "15",
                    "signal_bar_open_utc": m15.index[i].isoformat(),
                    "entry_time_utc": (m15.index[i] + pd.Timedelta(minutes=15)).isoformat(),
                    "direction": direction,
                    "entry": entry,
                    "stop": stop,
                    "target": entry + direction * cfg.target_r * risk,
                    "rr": cfg.target_r,
                    "support": int(support_dir),
                    "h1_bias": int(h1_bias),
                    "h4_bias": int(h4_bias),
                    "h4_adx": h4_adx,
                    "align_count": int(align_count),
                    "router_mode": "TREND" if strong_trend else "MIXED",
                    "source": "M15-0591-CANONICAL",
                }

    return pd.DataFrame(events), active


def latest_signal(data_path: str | Path, max_age_minutes: int = 35, now: pd.Timestamp | None = None) -> dict[str, Any] | None:
    m15, source_tf = load_price_csv(data_path)
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    now = now.tz_localize("UTC") if now.tzinfo is None else now.tz_convert("UTC")
    m15 = m15[m15.index + pd.Timedelta(minutes=15) <= now]
    _, active = replay_engine(m15)
    if active is None:
        return None
    entry_time = pd.Timestamp(active["entry_time_utc"])
    age = (now - entry_time).total_seconds() / 60.0
    if age < 0 or age > max_age_minutes:
        return None
    payload = dict(active)
    payload.update({
        "schema": "casio.regime-router.rr10",
        "direction": "long" if int(active["direction"]) == 1 else "short",
        "feed_adapter": f"{source_tf}->M15" if source_tf != "M15" else "M15",
    })
    return payload


def main() -> None:
    p = argparse.ArgumentParser(description="CASIO RR10 canonical Regime Router")
    p.add_argument("--data", required=True)
    p.add_argument("--output", default="tmp/casio_regime_router_signal.json")
    p.add_argument("--max-age-minutes", type=int, default=35)
    args = p.parse_args()
    payload = latest_signal(args.data, args.max_age_minutes)
    out = Path(args.output)
    if out.exists():
        out.unlink()
    if payload is None:
        print("CASIO RR10: no fresh canonical signal")
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
