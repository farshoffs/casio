from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

from .v3_core import _atr, _bars_since, _resample, load_m5_csv
from .v3_m5_engine import _align_completed
from .v3_structural_aplus import _confirmed_structure


@dataclass(frozen=True)
class StructuralPortfolioConfig:
    # No ADX / RSI. Direction comes from confirmed market structure and liquidity.
    min_external_runway_r: float = 3.5
    target_r: float = 3.5
    body_min: float = 0.52
    range_atr_min: float = 0.65
    internal_sweep_fresh: int = 6
    external_sweep_fresh: int = 4
    retrace_fill_bars: int = 8
    cooldown_bars: int = 6
    max_hold_bars: int = 216
    stop_buffer_atr: float = 0.10
    min_risk_atr: float = 0.35
    max_risk_atr: float = 3.0
    # Price-action regime router for the external-sweep playbook.
    d1_range_ratio_max: float = 1.50
    h4_range_ratio_min: float = 0.80
    round_trip_cost_bps: float = 1.0


PORTFOLIO_TARGET = {
    "trades_per_30d": 8.0,
    "win_rate_low": 42.0,
    "win_rate_high": 50.0,
    "avg_win_r": 3.5,
    "avg_loss_r_max": 1.0,
    "expectancy_r_min": 0.70,
    "profit_factor_min": 2.0,
}


def _safe(x):
    if isinstance(x, dict):
        return {str(k): _safe(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_safe(v) for v in x]
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, (np.floating, float)):
        y = float(x)
        return y if math.isfinite(y) else None
    if isinstance(x, pd.Timestamp):
        return x.isoformat()
    return x


def _efficiency(s: pd.Series, n: int) -> pd.Series:
    travel = s.diff().abs().rolling(n, min_periods=n).sum()
    return (s - s.shift(n)).abs() / travel.replace(0, np.nan)


def _session(index: pd.DatetimeIndex) -> np.ndarray:
    mins = index.hour * 60 + index.minute
    return np.select(
        [(mins >= 420) & (mins < 660), (mins >= 750) & (mins < 990)],
        ["LONDON", "NEW_YORK"],
        default="OTHER",
    )


def prepare_features(m5: pd.DataFrame, cfg: StructuralPortfolioConfig | None = None) -> pd.DataFrame:
    cfg = cfg or StructuralPortfolioConfig()
    f = m5.copy()
    f["m5_atr"] = _atr(m5, 14)
    candle_range = (m5.high - m5.low).replace(0, np.nan)
    f["body_fraction"] = (m5.close - m5.open).abs() / candle_range
    f["close_location"] = (m5.close - m5.low) / candle_range
    f["range_atr"] = candle_range / f.m5_atr.replace(0, np.nan)
    f["prior_high5"] = m5.high.shift(1).rolling(5, min_periods=5).max()
    f["prior_low5"] = m5.low.shift(1).rolling(5, min_periods=5).min()
    f["recent_low8"] = m5.low.rolling(8, min_periods=8).min()
    f["recent_high8"] = m5.high.rolling(8, min_periods=8).max()

    for name, rule, delta in [
        ("m15", "15min", pd.Timedelta(minutes=15)),
        ("h1", "1h", pd.Timedelta(hours=1)),
        ("h4", "4h", pd.Timedelta(hours=4)),
        ("d1", "1D", pd.Timedelta(days=1)),
    ]:
        h = _resample(m5, rule)
        s = _confirmed_structure(h).add_prefix(name + "_")
        f = f.join(_align_completed(s, m5.index, delta))

    d = _resample(m5, "1D")
    drange = d.high - d.low
    dctx = pd.DataFrame(index=d.index)
    dctx["prev_day_high"] = d.high
    dctx["prev_day_low"] = d.low
    dctx["d1_efficiency20"] = _efficiency(d.close, 20)
    dctx["d1_range_ratio20"] = drange / drange.rolling(20, min_periods=20).median().replace(0, np.nan)
    f = f.join(_align_completed(dctx, m5.index, pd.Timedelta(days=1)))

    h4 = _resample(m5, "4h")
    h4range = h4.high - h4.low
    h4ctx = pd.DataFrame(index=h4.index)
    h4ctx["h4_range_ratio12"] = h4range / h4range.rolling(12, min_periods=12).median().replace(0, np.nan)
    f = f.join(_align_completed(h4ctx, m5.index, pd.Timedelta(hours=4)))

    w = m5.resample("W-MON", label="left", closed="left").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"), volume=("volume", "sum")
    ).dropna(subset=["open", "high", "low", "close"])
    wctx = pd.DataFrame({"prev_week_high": w.high, "prev_week_low": w.low}, index=w.index)
    f = f.join(_align_completed(wctx, m5.index, pd.Timedelta(days=7)))

    day_key = m5.index.floor("D")
    day_open = m5.groupby(day_key).open.first()
    f["day_open"] = pd.Series(day_key, index=m5.index).map(day_open)

    asia_src = m5[m5.index.hour < 6]
    asia = asia_src.groupby(asia_src.index.floor("D")).agg(asia_high=("high", "max"), asia_low=("low", "min"))
    day_series = pd.Series(day_key, index=m5.index)
    f["asia_high"] = day_series.map(asia.asia_high)
    f["asia_low"] = day_series.map(asia.asia_low)
    f.loc[m5.index.hour < 6, ["asia_high", "asia_low"]] = np.nan

    # M5 displacement + fair-value-gap. The model does not buy/sell the impulse close;
    # it waits for a retracement into the imbalance.
    f["disp_long"] = (
        (f.close > f.open)
        & f.body_fraction.ge(cfg.body_min)
        & f.close_location.ge(.68)
        & f.range_atr.ge(cfg.range_atr_min)
        & (f.close > f.prior_high5)
    )
    f["disp_short"] = (
        (f.close < f.open)
        & f.body_fraction.ge(cfg.body_min)
        & f.close_location.le(.32)
        & f.range_atr.ge(cfg.range_atr_min)
        & (f.close < f.prior_low5)
    )
    f["bull_fvg"] = (f.low > f.high.shift(2)) & f.disp_long
    f["bear_fvg"] = (f.high < f.low.shift(2)) & f.disp_short
    f["bull_fvg_low"] = f.high.shift(2)
    f["bull_fvg_high"] = f.low
    f["bear_fvg_low"] = f.high
    f["bear_fvg_high"] = f.low.shift(2)

    internal_sell = (f.low < f.prior_low5) & (f.close > f.prior_low5)
    internal_buy = (f.high > f.prior_high5) & (f.close < f.prior_high5)
    f["internal_sell_sweep_age"] = _bars_since(internal_sell)
    f["internal_buy_sweep_age"] = _bars_since(internal_buy)

    external_sell = pd.Series(False, index=f.index)
    external_buy = pd.Series(False, index=f.index)
    for col in ["prev_day_low", "asia_low", "h1_last_pl", "h4_last_pl", "prev_week_low"]:
        external_sell |= ((f.low < f[col]) & (f.close > f[col])).fillna(False)
    for col in ["prev_day_high", "asia_high", "h1_last_ph", "h4_last_ph", "prev_week_high"]:
        external_buy |= ((f.high > f[col]) & (f.close < f[col])).fillna(False)
    f["external_sell_sweep_age"] = _bars_since(external_sell)
    f["external_buy_sweep_age"] = _bars_since(external_buy)

    # Expansion/retest memory for playbook C.
    long_retest = pd.Series(False, index=f.index)
    short_retest = pd.Series(False, index=f.index)
    for level in ["asia_high", "prev_day_high"]:
        broke = (f.close > f[level]) & (f.close.shift(1) <= f[level]) & f[level].notna()
        age = _bars_since(broke)
        retest = age.between(1, 12) & (f.low <= f[level] + .15 * f.m5_atr) & (f.close >= f[level])
        long_retest |= _bars_since(retest).le(4)
    for level in ["asia_low", "prev_day_low"]:
        broke = (f.close < f[level]) & (f.close.shift(1) >= f[level]) & f[level].notna()
        age = _bars_since(broke)
        retest = age.between(1, 12) & (f.high >= f[level] - .15 * f.m5_atr) & (f.close <= f[level])
        short_retest |= _bars_since(retest).le(4)
    f["session_retest_long"] = long_retest
    f["session_retest_short"] = short_retest

    f["trend_vote"] = f.d1_structure_bias.fillna(0) + f.h4_structure_bias.fillna(0) + f.h1_structure_bias.fillna(0)
    return f


def _target(row: pd.Series, direction: int, entry: float, risk: float, cfg: StructuralPortfolioConfig) -> tuple[float, str, float]:
    if direction == 1:
        levels = [
            ("ASIA_H", row.asia_high), ("PDH", row.prev_day_high),
            ("H1_H", row.h1_last_ph), ("H4_H", row.h4_last_ph), ("PWH", row.prev_week_high),
        ]
        values = [(n, float(v), (float(v) - entry) / risk) for n, v in levels if np.isfinite(v) and float(v) > entry]
    else:
        levels = [
            ("ASIA_L", row.asia_low), ("PDL", row.prev_day_low),
            ("H1_L", row.h1_last_pl), ("H4_L", row.h4_last_pl), ("PWL", row.prev_week_low),
        ]
        values = [(n, float(v), (entry - float(v)) / risk) for n, v in levels if np.isfinite(v) and float(v) < entry]
    valid = [x for x in values if x[2] >= cfg.min_external_runway_r]
    if not valid:
        return np.nan, "NONE", np.nan
    name, level, rr = min(valid, key=lambda x: x[2])
    return level, name, rr


def setup_frame(f: pd.DataFrame, cfg: StructuralPortfolioConfig | None = None) -> pd.DataFrame:
    cfg = cfg or StructuralPortfolioConfig()
    idx = f.index
    session = _session(idx)
    primary = pd.Series(session != "OTHER", index=idx)
    vote = f.trend_vote.fillna(0)
    trend_long = (vote >= 2) & (f.m15_structure_bias.fillna(0) >= 0)
    trend_short = (vote <= -2) & (f.m15_structure_bias.fillna(0) <= 0)

    # A: trend pullback continuation.
    pb_long = primary & trend_long & f.internal_sell_sweep_age.le(cfg.internal_sweep_fresh) & f.bull_fvg
    pb_short = primary & trend_short & f.internal_buy_sweep_age.le(cfg.internal_sweep_fresh) & f.bear_fvg

    # B: external-liquidity sweep with a pure-price regime router.
    regime_ok = f.d1_range_ratio20.le(cfg.d1_range_ratio_max) & f.h4_range_ratio12.ge(cfg.h4_range_ratio_min)
    sw_long = primary & regime_ok & f.external_sell_sweep_age.le(cfg.external_sweep_fresh) & (vote >= 0) & f.bull_fvg
    sw_short = primary & regime_ok & f.external_buy_sweep_age.le(cfg.external_sweep_fresh) & (vote <= 0) & f.bear_fvg

    # C: session expansion and retest.
    rt_long = primary & trend_long & f.session_retest_long & f.bull_fvg
    rt_short = primary & trend_short & f.session_retest_short & f.bear_fvg

    rows = []
    last = {1: -999, -1: -999}
    mask = pb_long | pb_short | sw_long | sw_short | rt_long | rt_short
    for i in np.flatnonzero(mask.to_numpy()):
        if sw_long.iat[i]: direction, playbook = 1, "EXTERNAL_SWEEP"
        elif sw_short.iat[i]: direction, playbook = -1, "EXTERNAL_SWEEP"
        elif rt_long.iat[i]: direction, playbook = 1, "SESSION_EXPANSION_RETEST"
        elif rt_short.iat[i]: direction, playbook = -1, "SESSION_EXPANSION_RETEST"
        elif pb_long.iat[i]: direction, playbook = 1, "TREND_PULLBACK"
        elif pb_short.iat[i]: direction, playbook = -1, "TREND_PULLBACK"
        else: continue
        if i - last[direction] < cfg.cooldown_bars:
            continue
        last[direction] = i
        row = f.iloc[i]
        if direction == 1:
            entry = (float(row.bull_fvg_low) + float(row.bull_fvg_high)) / 2
            stop = float(row.recent_low8) - cfg.stop_buffer_atr * float(row.m5_atr)
            risk = entry - stop
            day_aligned = entry > float(row.day_open)
        else:
            entry = (float(row.bear_fvg_low) + float(row.bear_fvg_high)) / 2
            stop = float(row.recent_high8) + cfg.stop_buffer_atr * float(row.m5_atr)
            risk = stop - entry
            day_aligned = entry < float(row.day_open)
        if not np.isfinite(risk) or not np.isfinite(row.m5_atr):
            continue
        risk_atr = risk / float(row.m5_atr)
        if risk_atr < cfg.min_risk_atr or risk_atr > cfg.max_risk_atr:
            continue
        # Trend continuation should agree with the current daily auction.
        if playbook == "TREND_PULLBACK" and not day_aligned:
            continue
        liq, liq_type, runway = _target(row, direction, entry, risk, cfg)
        if not np.isfinite(runway):
            continue
        rows.append({
            "signal_i": i, "signal_time": idx[i], "direction": direction,
            "playbook": playbook, "session": session[i],
            "entry": entry, "stop": stop, "risk": risk,
            "target": entry + direction * cfg.target_r * risk, "target_r": cfg.target_r,
            "external_liquidity": liq, "external_liquidity_type": liq_type,
            "external_runway_r": runway,
            "trend_vote": int(vote.iat[i]) if np.isfinite(vote.iat[i]) else 0,
            "day_open_aligned": bool(day_aligned),
            "d1_range_ratio20": float(row.d1_range_ratio20) if np.isfinite(row.d1_range_ratio20) else np.nan,
            "h4_range_ratio12": float(row.h4_range_ratio12) if np.isfinite(row.h4_range_ratio12) else np.nan,
        })
    return pd.DataFrame(rows)


def replay(m5: pd.DataFrame, setups: pd.DataFrame, cfg: StructuralPortfolioConfig | None = None) -> pd.DataFrame:
    cfg = cfg or StructuralPortfolioConfig()
    if setups.empty:
        return pd.DataFrame()
    events = []; next_free = -1
    for s in setups.sort_values("signal_i").itertuples(index=False):
        sig = int(s.signal_i)
        if sig < next_free: continue
        d = int(s.direction); entry = float(s.entry); stop = float(s.stop); risk = float(s.risk)
        fill = None
        for j in range(sig + 1, min(len(m5), sig + 1 + cfg.retrace_fill_bars)):
            lo, hi = float(m5.low.iat[j]), float(m5.high.iat[j])
            if (lo <= stop if d == 1 else hi >= stop): break
            if lo <= entry <= hi:
                fill = j; break
        if fill is None: continue
        target = entry + d * cfg.target_r * risk
        end = min(len(m5), fill + 1 + cfg.max_hold_bars)
        gross = reason = exit_i = None
        for j in range(fill + 1, end):
            lo, hi, close = float(m5.low.iat[j]), float(m5.high.iat[j]), float(m5.close.iat[j])
            hs = lo <= stop if d == 1 else hi >= stop
            ht = hi >= target if d == 1 else lo <= target
            if hs and ht: gross, reason = -1.0, "stop_same_bar"
            elif hs: gross, reason = -1.0, "stop"
            elif ht: gross, reason = cfg.target_r, "target"
            elif j == end - 1: gross, reason = (close - entry) / risk * d, "time_exit"
            else: continue
            exit_i = j; break
        if gross is None or exit_i is None: continue
        cost_r = (entry * cfg.round_trip_cost_bps / 10000.0) / risk
        e = s._asdict(); e.update(
            entry_time=m5.index[fill] + pd.Timedelta(minutes=5),
            exit_time=m5.index[exit_i] + pd.Timedelta(minutes=5),
            gross_r=gross, net_r=gross - cost_r, reason=reason,
        )
        events.append(e); next_free = exit_i + 1
    return pd.DataFrame(events)


def metrics(trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    if trades.empty: return {"trades": 0, "trades_per_30d": 0.0}
    tt = pd.to_datetime(trades.entry_time, utc=True)
    r = pd.to_numeric(trades.loc[(tt >= start) & (tt < end), "net_r"], errors="coerce").dropna()
    days = max((end - start).total_seconds() / 86400, 1e-9)
    if r.empty: return {"trades": 0, "trades_per_30d": 0.0}
    wins = r[r > .05]; losses = r[r < -.05]; curve = r.cumsum(); dd = curve.cummax() - curve
    return {
        "trades": int(len(r)), "trades_per_30d": float(len(r) * 30 / days),
        "win_rate": float(len(wins) * 100 / len(r)),
        "avg_win_r": float(wins.mean()) if len(wins) else None,
        "avg_loss_r": float(-losses.mean()) if len(losses) else None,
        "expectancy_r": float(r.mean()),
        "profit_factor": float(wins.sum() / (-losses.sum())) if len(losses) else (999.0 if len(wins) else None),
        "max_drawdown_r": float(dd.max()) if len(dd) else 0.0,
    }


def run_latest_first(data_path: str | Path, output_dir: str | Path, min_year: int | None = None) -> dict:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    m5 = load_m5_csv(data_path)
    cfg = StructuralPortfolioConfig()
    f = prepare_features(m5, cfg)
    setups = setup_frame(f, cfg)
    trades = replay(m5, setups, cfg)
    latest = int(m5.index.max().year); earliest = int(m5.index.min().year)
    floor = min_year if min_year is not None else earliest
    yearly = []
    for year in range(latest, floor - 1, -1):
        a = pd.Timestamp(f"{year}-01-01", tz="UTC"); b = pd.Timestamp(f"{year + 1}-01-01", tz="UTC")
        yearly.append({"year": year, **metrics(trades, a, b)})
    setups.to_csv(out / "setups.csv", index=False)
    trades.to_csv(out / "trades.csv", index=False)
    summary = {
        "coverage": {"rows": len(m5), "start": m5.index.min(), "end": m5.index.max()},
        "target": PORTFOLIO_TARGET,
        "yearly_latest_first": yearly,
        "note": "Research challenger only. No ADX/RSI. Live v3 remains unchanged.",
    }
    (out / "summary.json").write_text(json.dumps(_safe(summary), indent=2), encoding="utf-8")
    return summary


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data/xauusd_m5.csv")
    p.add_argument("--output", default="reports/structural-portfolio-latest")
    p.add_argument("--min-year", type=int, default=None)
    a = p.parse_args()
    print(json.dumps(_safe(run_latest_first(a.data, a.output, a.min_year)), indent=2))


if __name__ == "__main__":
    main()
