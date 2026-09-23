from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import json
import math

import numpy as np
import pandas as pd

from .v3_core import load_m5_csv


DEV_START = pd.Timestamp("2017-01-01", tz="UTC")
DEV_END = pd.Timestamp("2021-01-01", tz="UTC")
START_RM = 100.0
RISK_FRACTION = 0.05
TARGET_R = 3.0
ROUND_TRIP_BPS = 1.0


@dataclass(frozen=True)
class Card:
    name: str
    family: str
    stop_lookback: int = 5
    cooldown_bars: int = 2


CARDS = (
    Card("ADX_DI_ROTATION", "adx_di", 5, 2),
    Card("ADX_DI_STRONG", "adx_di_strong", 5, 3),
    Card("TICKVOL_BREAKOUT", "tickvol_breakout", 5, 2),
    Card("TICKVOL_CONTINUATION", "tickvol_cont", 5, 2),
    Card("DONCHIAN20_TREND", "donchian20", 6, 2),
    Card("DONCHIAN10_TREND", "donchian10", 5, 2),
    Card("EMA20_PULLBACK", "ema20_pullback", 6, 2),
    Card("EMA50_DEEP_PULLBACK", "ema50_pullback", 8, 3),
    Card("BB_SQUEEZE_BREAK", "bb_squeeze", 6, 3),
    Card("RSI8_TREND_RECLAIM", "rsi8_reclaim", 6, 2),
)


def rma(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df.close.shift(1)
    tr = pd.concat(
        [(df.high - df.low), (df.high - pc).abs(), (df.low - pc).abs()],
        axis=1,
    ).max(axis=1)
    return rma(tr, n)


def di_adx(df: pd.DataFrame, n: int = 14) -> tuple[pd.Series, pd.Series, pd.Series]:
    up = df.high.diff()
    down = -df.low.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    a = atr(df, n)
    pdi = 100.0 * rma(plus_dm, n) / a.replace(0, np.nan)
    mdi = 100.0 * rma(minus_dm, n) / a.replace(0, np.nan)
    dx = 100.0 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    adx = rma(dx, n)
    return pdi, mdi, adx


def rsi(close: pd.Series, n: int = 8) -> pd.Series:
    d = close.diff()
    g = d.clip(lower=0)
    l = (-d).clip(lower=0)
    ag = rma(g, n)
    al = rma(l, n)
    rs = ag / al.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    out = out.where(al > 0, 100.0)
    out = out.where(ag > 0, 0.0)
    return out


def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    return df.resample(rule, label="left", closed="left", origin="epoch").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    ).dropna(subset=["open", "high", "low", "close"])


def align_completed(series: pd.Series, target_index: pd.DatetimeIndex, period: pd.Timedelta) -> pd.Series:
    x = series.copy()
    x.index = x.index + period
    y = x.reindex(target_index, method="ffill")
    y.index = target_index
    return y


def prepare_features(m5: pd.DataFrame) -> pd.DataFrame:
    m15 = resample(m5, "15min")
    h1 = resample(m5, "1h")

    for x in (m15, h1):
        x["atr14"] = atr(x, 14)
        x["ema20"] = x.close.ewm(span=20, adjust=False).mean()
        x["ema50"] = x.close.ewm(span=50, adjust=False).mean()
        x["ema100"] = x.close.ewm(span=100, adjust=False).mean()

    pdi, mdi, adx = di_adx(m15, 14)
    m15["pdi"] = pdi
    m15["mdi"] = mdi
    m15["adx"] = adx
    m15["rsi8"] = rsi(m15.close, 8)

    m15["body"] = (m15.close - m15.open).abs()
    m15["body_atr"] = m15.body / m15.atr14.replace(0, np.nan)
    m15["range_atr"] = (m15.high - m15.low) / m15.atr14.replace(0, np.nan)
    m15["vol_med20"] = m15.volume.rolling(20, min_periods=10).median()
    m15["vol_ratio"] = m15.volume / m15.vol_med20.replace(0, np.nan)

    m15["prev_high10"] = m15.high.shift(1).rolling(10).max()
    m15["prev_low10"] = m15.low.shift(1).rolling(10).min()
    m15["prev_high20"] = m15.high.shift(1).rolling(20).max()
    m15["prev_low20"] = m15.low.shift(1).rolling(20).min()

    mean20 = m15.close.rolling(20).mean()
    std20 = m15.close.rolling(20).std(ddof=0)
    m15["bb_upper"] = mean20 + 2 * std20
    m15["bb_lower"] = mean20 - 2 * std20
    m15["bb_width"] = (m15.bb_upper - m15.bb_lower) / mean20.replace(0, np.nan)
    # Causal squeeze reference: only prior bars.
    m15["bb_width_q25"] = m15.bb_width.shift(1).rolling(96, min_periods=48).quantile(0.25)

    # H1 values only become available after each H1 candle closes.
    close_times = m15.index + pd.Timedelta(minutes=15)
    for col in ["ema20", "ema50", "ema100", "atr14", "close"]:
        m15[f"h1_{col}"] = align_completed(h1[col], close_times, pd.Timedelta(hours=1)).to_numpy()

    h1_slope = h1.ema50.diff(3)
    m15["h1_ema50_slope3"] = align_completed(h1_slope, close_times, pd.Timedelta(hours=1)).to_numpy()

    m15["h1_up"] = (
        (m15.h1_ema20 > m15.h1_ema50)
        & (m15.h1_ema50 > m15.h1_ema100)
        & (m15.h1_ema50_slope3 > 0)
    )
    m15["h1_down"] = (
        (m15.h1_ema20 < m15.h1_ema50)
        & (m15.h1_ema50 < m15.h1_ema100)
        & (m15.h1_ema50_slope3 < 0)
    )
    return m15


def masks(f: pd.DataFrame, family: str) -> tuple[pd.Series, pd.Series]:
    pdi_cross_up = (f.pdi > f.mdi) & (f.pdi.shift(1) <= f.mdi.shift(1))
    pdi_cross_dn = (f.mdi > f.pdi) & (f.mdi.shift(1) <= f.pdi.shift(1))

    if family == "adx_di":
        lo = f.h1_up & (f.adx >= 20) & pdi_cross_up & (f.close > f.ema20) & (f.body_atr >= 0.25)
        sh = f.h1_down & (f.adx >= 20) & pdi_cross_dn & (f.close < f.ema20) & (f.body_atr >= 0.25)
    elif family == "adx_di_strong":
        lo = f.h1_up & (f.adx >= 27) & pdi_cross_up & (f.close > f.ema20) & (f.body_atr >= 0.40)
        sh = f.h1_down & (f.adx >= 27) & pdi_cross_dn & (f.close < f.ema20) & (f.body_atr >= 0.40)
    elif family == "tickvol_breakout":
        lo = f.h1_up & (f.close > f.prev_high10) & (f.vol_ratio >= 1.25) & (f.body_atr >= 0.45)
        sh = f.h1_down & (f.close < f.prev_low10) & (f.vol_ratio >= 1.25) & (f.body_atr >= 0.45)
    elif family == "tickvol_cont":
        lo = f.h1_up & (f.close > f.prev_high10) & (f.vol_ratio >= 1.05) & (f.body_atr >= 0.30)
        sh = f.h1_down & (f.close < f.prev_low10) & (f.vol_ratio >= 1.05) & (f.body_atr >= 0.30)
    elif family == "donchian20":
        lo = f.h1_up & (f.close > f.prev_high20) & (f.adx >= 18) & (f.range_atr >= 0.65)
        sh = f.h1_down & (f.close < f.prev_low20) & (f.adx >= 18) & (f.range_atr >= 0.65)
    elif family == "donchian10":
        lo = f.h1_up & (f.close > f.prev_high10) & (f.adx >= 16) & (f.range_atr >= 0.55)
        sh = f.h1_down & (f.close < f.prev_low10) & (f.adx >= 16) & (f.range_atr >= 0.55)
    elif family == "ema20_pullback":
        lo = (
            f.h1_up
            & (f.low <= f.ema20)
            & (f.close > f.ema20)
            & (f.close > f.open)
            & (f.pdi > f.mdi)
            & (f.adx >= 17)
        )
        sh = (
            f.h1_down
            & (f.high >= f.ema20)
            & (f.close < f.ema20)
            & (f.close < f.open)
            & (f.mdi > f.pdi)
            & (f.adx >= 17)
        )
    elif family == "ema50_pullback":
        lo = (
            f.h1_up
            & (f.low <= f.ema50)
            & (f.close > f.ema50)
            & (f.close > f.open)
            & (f.pdi > f.mdi)
        )
        sh = (
            f.h1_down
            & (f.high >= f.ema50)
            & (f.close < f.ema50)
            & (f.close < f.open)
            & (f.mdi > f.pdi)
        )
    elif family == "bb_squeeze":
        squeeze = f.bb_width.shift(1) <= f.bb_width_q25
        lo = f.h1_up & squeeze & (f.close > f.bb_upper) & (f.body_atr >= 0.35)
        sh = f.h1_down & squeeze & (f.close < f.bb_lower) & (f.body_atr >= 0.35)
    elif family == "rsi8_reclaim":
        lo = (
            f.h1_up
            & (f.rsi8.shift(1) <= 35)
            & (f.rsi8 > 35)
            & (f.close > f.ema20)
            & (f.close > f.open)
        )
        sh = (
            f.h1_down
            & (f.rsi8.shift(1) >= 65)
            & (f.rsi8 < 65)
            & (f.close < f.ema20)
            & (f.close < f.open)
        )
    else:
        raise ValueError(family)
    return lo.fillna(False), sh.fillna(False)


def build_setups(f: pd.DataFrame, card: Card) -> pd.DataFrame:
    lo, sh = masks(f, card.family)
    rows = []
    last = {1: -10**9, -1: -10**9}
    all_mask = lo | sh
    for i in np.flatnonzero(all_mask.to_numpy()):
        d = 1 if bool(lo.iat[i]) else -1
        if i - last[d] < card.cooldown_bars:
            continue
        row = f.iloc[i]
        a = float(row.atr14)
        if not np.isfinite(a) or a <= 0:
            continue
        lb0 = max(0, i - card.stop_lookback + 1)
        recent = f.iloc[lb0 : i + 1]
        stop = float(recent.low.min() - 0.10 * a) if d == 1 else float(recent.high.max() + 0.10 * a)
        rows.append({
            "card": card.name,
            "signal_i": i,
            "signal_time": f.index[i],
            "signal_close_time": f.index[i] + pd.Timedelta(minutes=15),
            "direction": d,
            "stop": stop,
            "atr14": a,
            "adx": float(row.adx) if np.isfinite(row.adx) else np.nan,
            "vol_ratio": float(row.vol_ratio) if np.isfinite(row.vol_ratio) else np.nan,
        })
        last[d] = i
    return pd.DataFrame(rows)


def replay(m5: pd.DataFrame, setups: pd.DataFrame) -> pd.DataFrame:
    if setups.empty:
        return pd.DataFrame()
    idx = m5.index
    busy_until = None
    rows = []
    for s in setups.itertuples(index=False):
        st = pd.Timestamp(s.signal_time)
        if st < DEV_START or st >= DEV_END:
            continue
        pos = idx.searchsorted(pd.Timestamp(s.signal_close_time), side="left")
        if pos >= len(idx):
            continue
        et = idx[pos]
        if et >= DEV_END:
            continue
        if busy_until is not None and et <= busy_until:
            continue

        entry = float(m5.iloc[pos].open)
        d = int(s.direction)
        stop = float(s.stop)
        risk = entry - stop if d == 1 else stop - entry
        if not np.isfinite(risk) or risk <= 0:
            continue
        risk_atr = risk / float(s.atr14)
        if risk_atr < 0.25 or risk_atr > 2.5:
            continue
        target = entry + d * TARGET_R * risk

        xp = xt = reason = None
        for j in range(pos, len(idx)):
            t = idx[j]
            if t >= DEV_END:
                break
            lo = float(m5.iloc[j].low)
            hi = float(m5.iloc[j].high)
            if d == 1:
                hit_s, hit_t = lo <= stop, hi >= target
            else:
                hit_s, hit_t = hi >= stop, lo <= target
            if hit_s:
                xp, xt = stop, t + pd.Timedelta(minutes=5)
                reason = "SL_same_bar" if hit_t else "SL"
                break
            if hit_t:
                xp, xt, reason = target, t + pd.Timedelta(minutes=5), "TP"
                break
        if xp is None:
            continue

        gross_r = (xp - entry) / risk if d == 1 else (entry - xp) / risk
        cost_r = (entry * ROUND_TRIP_BPS / 10000.0) / risk
        net_r = float(gross_r - cost_r)
        rows.append({
            "card": s.card,
            "signal_time": st,
            "entry_time": et,
            "exit_time": xt,
            "direction": "BUY" if d == 1 else "SELL",
            "entry": entry,
            "stop": stop,
            "target": target,
            "risk_atr": risk_atr,
            "gross_r": float(gross_r),
            "cost_r": float(cost_r),
            "net_r": net_r,
            "result": "WIN" if net_r > 0 else "LOSS",
            "exit_reason": reason,
        })
        busy_until = xt
    return pd.DataFrame(rows)


def combine_setups(parts: list[pd.DataFrame], name: str) -> pd.DataFrame:
    xs = [x.copy() for x in parts if not x.empty]
    if not xs:
        return pd.DataFrame()
    x = pd.concat(xs, ignore_index=True).sort_values(["signal_time", "card"])
    x = x.drop_duplicates(["signal_time", "direction"], keep="first")
    x["card"] = name
    return x.reset_index(drop=True)


def max_streak(vals: list[bool], wanted: bool) -> int:
    best = cur = 0
    for v in vals:
        if v == wanted:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def metrics(tr: pd.DataFrame) -> dict:
    if tr.empty:
        return {
            "trades": 0, "wins": 0, "losses": 0, "wr": 0.0, "expectancy_r": 0.0,
            "pf": 0.0, "max_dd_pct": 0.0, "max_win_streak": 0, "max_loss_streak": 0,
            "end_rm": START_RM, "return_pct": 0.0,
        }
    r = tr.net_r.astype(float)
    wins = int((r > 0).sum())
    losses = int((r < 0).sum())
    gw = float(r[r > 0].sum())
    gl = float(-r[r < 0].sum())
    pf = gw / gl if gl > 0 else math.inf
    bal = START_RM
    peak = bal
    dd = 0.0
    outcomes = []
    for rv in r:
        bal *= max(0.0, 1.0 + RISK_FRACTION * rv)
        peak = max(peak, bal)
        dd = max(dd, (peak - bal) / peak if peak > 0 else 0.0)
        outcomes.append(rv > 0)
    return {
        "trades": int(len(r)),
        "wins": wins,
        "losses": losses,
        "wr": wins * 100.0 / len(r),
        "expectancy_r": float(r.mean()),
        "pf": float(pf),
        "max_dd_pct": dd * 100.0,
        "max_win_streak": max_streak(outcomes, True),
        "max_loss_streak": max_streak(outcomes, False),
        "end_rm": float(bal),
        "return_pct": (bal / START_RM - 1.0) * 100.0,
    }


def month_stats(tr: pd.DataFrame) -> dict:
    periods = pd.period_range("2017-01", "2020-12", freq="M")
    if tr.empty:
        counts = [0] * len(periods)
    else:
        p = pd.to_datetime(tr.entry_time, utc=True).dt.to_period("M")
        counts = [int((p == m).sum()) for m in periods]
    return {
        "avg_month": float(np.mean(counts)),
        "min_month": int(min(counts)),
        "months_ge8": int(sum(x >= 8 for x in counts)),
        "months_total": len(counts),
    }


def yearly(tr: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for y in range(2017, 2021):
        if tr.empty:
            g = tr
        else:
            years = pd.to_datetime(tr.entry_time, utc=True).dt.year
            g = tr[years == y]
        rows.append({"year": y, **metrics(g)})
    return pd.DataFrame(rows)


def rank_row(overall: dict, y: pd.DataFrame, ms: dict) -> tuple:
    positive_years = int((y.expectancy_r > 0).sum())
    pf_years = int((y.pf > 1.0).sum())
    worst_year_exp = float(y.expectancy_r.min())
    worst_year_dd = float(y.max_dd_pct.max())
    meets_min8 = ms["min_month"] >= 8
    meets_avg8 = ms["avg_month"] >= 8
    # Sorting tuple only; no parameter mutation based on score.
    return (
        positive_years,
        pf_years,
        int(meets_min8),
        int(meets_avg8),
        worst_year_exp,
        overall["expectancy_r"],
        overall["pf"],
        -worst_year_dd,
    )


def run(data_path: str | Path, output_dir: str | Path) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    m5_all = load_m5_csv(data_path)
    # Warm-up begins six months before the development window.
    m5 = m5_all[(m5_all.index >= pd.Timestamp("2016-06-01", tz="UTC")) & (m5_all.index < DEV_END)].copy()
    f = prepare_features(m5)

    setup_cache = {c.name: build_setups(f, c) for c in CARDS}

    # Technique portfolios add independent setup families instead of loosening one rule.
    portfolio_defs = {
        "PORT_MOMENTUM": ["ADX_DI_ROTATION", "TICKVOL_CONTINUATION", "DONCHIAN10_TREND"],
        "PORT_TREND": ["DONCHIAN20_TREND", "EMA20_PULLBACK", "RSI8_TREND_RECLAIM"],
        "PORT_VOLUME_TREND": ["TICKVOL_BREAKOUT", "EMA20_PULLBACK", "DONCHIAN10_TREND"],
        "PORT_DIVERSE": ["ADX_DI_ROTATION", "TICKVOL_BREAKOUT", "EMA20_PULLBACK", "BB_SQUEEZE_BREAK"],
        "PORT_BROAD": ["ADX_DI_ROTATION", "TICKVOL_CONTINUATION", "DONCHIAN20_TREND", "EMA20_PULLBACK", "BB_SQUEEZE_BREAK", "RSI8_TREND_RECLAIM"],
    }
    for name, members in portfolio_defs.items():
        setup_cache[name] = combine_setups([setup_cache[m] for m in members], name)

    overall_rows = []
    yearly_rows = []
    monthly_rows = []
    trade_cache = {}

    for name, setups in setup_cache.items():
        tr = replay(m5, setups)
        trade_cache[name] = tr
        ov = metrics(tr)
        ms = month_stats(tr)
        yr = yearly(tr)
        key = rank_row(ov, yr, ms)
        overall_rows.append({
            "strategy": name,
            **ov,
            **ms,
            "positive_years": int((yr.expectancy_r > 0).sum()),
            "pf_gt1_years": int((yr.pf > 1.0).sum()),
            "worst_year_exp_r": float(yr.expectancy_r.min()),
            "worst_year_dd_pct": float(yr.max_dd_pct.max()),
            "_rank": key,
        })
        for r in yr.itertuples(index=False):
            yearly_rows.append({"strategy": name, **r._asdict()})

        periods = pd.period_range("2017-01", "2020-12", freq="M")
        p = pd.to_datetime(tr.entry_time, utc=True).dt.to_period("M") if not tr.empty else pd.Series([], dtype="period[M]")
        for m in periods:
            g = tr[p == m] if not tr.empty else tr
            mm = metrics(g)
            monthly_rows.append({"strategy": name, "month": str(m), **mm})

    overall = pd.DataFrame(overall_rows)
    overall = overall.sort_values(
        ["positive_years", "pf_gt1_years", "min_month", "avg_month", "worst_year_exp_r", "expectancy_r", "pf", "worst_year_dd_pct"],
        ascending=[False, False, False, False, False, False, False, True],
    )
    yearly_df = pd.DataFrame(yearly_rows)
    monthly_df = pd.DataFrame(monthly_rows)
    trades_df = pd.concat([x.assign(strategy=k) for k, x in trade_cache.items()], ignore_index=True) if trade_cache else pd.DataFrame()

    # Remove non-serializable helper.
    if "_rank" in overall:
        overall = overall.drop(columns=["_rank"])

    overall.to_csv(out / "development_ranked.csv", index=False)
    yearly_df.to_csv(out / "development_yearly.csv", index=False)
    monthly_df.to_csv(out / "development_monthly.csv", index=False)
    trades_df.to_csv(out / "development_trades.csv", index=False)

    top = overall.head(8).copy()
    lines = [
        "# CASIO Historical-First Research — Development 2017–2020",
        "",
        f"Feed: secondary OctaFX/Octa Markets MT4 XAUUSD M5. Data slice used: {m5.index.min().isoformat()} -> {m5.index.max().isoformat()}",
        "Selection window: 2017-01-01 through 2020-12-31 only.",
        "2021+ is intentionally not inspected by this workflow.",
        "",
        "Execution: M15 technique cards, completed H1 context, next-M5-open entry, fixed 3R target, structural swing + 0.1ATR stop.",
        "Conservative same-M5 ordering: stop first. One position at a time. 1bp round-trip cost included.",
        "Money model: RM100 start, 5% current-equity risk per trade.",
        "",
        f"Volume non-zero ratio in development slice: {(m5.volume.fillna(0) > 0).mean()*100:.2f}%",
        "",
        "## Ranked development candidates",
        "",
        "| Strategy | Trades | Avg/mo | Min/mo | Months >=8 | Pos years | WR | ExpR | PF | Worst yr ExpR | Worst yr DD | RM100 → |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in overall.itertuples(index=False):
        pf = "∞" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(
            f"| {r.strategy} | {r.trades} | {r.avg_month:.2f} | {r.min_month} | {r.months_ge8}/48 | "
            f"{r.positive_years}/4 | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | "
            f"{r.worst_year_exp_r:+.3f} | {r.worst_year_dd_pct:.2f}% | RM{r.end_rm:.2f} |"
        )

    for strategy in top.strategy.tolist():
        lines += ["", f"## {strategy}", ""]
        y = yearly_df[yearly_df.strategy == strategy]
        lines += [
            "| Year | Trades | W | L | WR | ExpR | PF | DD | RM100 → |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for r in y.itertuples(index=False):
            pf = "∞" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
            lines.append(
                f"| {r.year} | {r.trades} | {r.wins} | {r.losses} | {r.wr:.2f}% | "
                f"{r.expectancy_r:+.3f} | {pf} | {r.max_dd_pct:.2f}% | RM{r.end_rm:.2f} |"
            )

    report = "\n".join(lines) + "\n"
    (out / "REPORT.md").write_text(report, encoding="utf-8")

    summary = {
        "selection_window": ["2017-01-01", "2020-12-31"],
        "feed": "secondary_octafx_mt4",
        "target": {
            "rr": 3.0,
            "start_rm": 100.0,
            "risk_fraction": 0.05,
            "desired_min_trades_per_month": 8,
            "avoid_catastrophic_yearly_drawdown": True,
        },
        "method": "small fixed family set; selection uses 2017-2020 only; no 2021+ inspection",
        "top": top.replace({np.nan: None, np.inf: None, -np.inf: None}).to_dict(orient="records"),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(report)
    return summary


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output", default="reports/historical-first-2017-2020")
    a = p.parse_args()
    run(a.data, a.output)


if __name__ == "__main__":
    main()
