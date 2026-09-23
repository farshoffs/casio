from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import (
    DEV_END, atr, di_adx, resample, align_completed, rsi,
    replay, combine_setups, metrics, month_stats, yearly,
)


@dataclass(frozen=True)
class Card:
    name: str
    family: str
    stop_mode: str = "struct"
    cooldown: int = 2


CARDS = (
    Card("ASIA_BREAKOUT", "asia_breakout", "range", 4),
    Card("LONDON_ORB", "london_orb", "range", 4),
    Card("KELTNER_BREAK", "keltner", "struct", 2),
    Card("MACD_CONTINUATION", "macd", "struct", 2),
    Card("ICHIMOKU_CONTINUATION", "ichimoku", "struct", 3),
    Card("RSI2_PULLBACK", "rsi2_pullback", "struct", 2),
    Card("VWAP_RECLAIM", "vwap_reclaim", "struct", 2),
    Card("ATR_EXPANSION", "atr_expansion", "struct", 2),
    Card("ROC_MOMENTUM", "roc_momentum", "struct", 2),
    Card("EMA_RIBBON_BREAK", "ema_ribbon", "struct", 2),
    Card("BB_TREND_BREAK", "bb_trend", "struct", 3),
    Card("ADX_PULLBACK_BREAK", "adx_pullback_break", "struct", 2),
)


def prepare(m5: pd.DataFrame) -> pd.DataFrame:
    x = resample(m5, "15min")
    h4 = resample(m5, "4h")
    d1 = resample(m5, "1D")

    x["atr14"] = atr(x, 14)
    pdi, mdi, adx = di_adx(x, 14)
    x["pdi"], x["mdi"], x["adx"] = pdi, mdi, adx
    x["rsi2"] = rsi(x.close, 2)
    x["rsi8"] = rsi(x.close, 8)
    x["ema8"] = x.close.ewm(span=8, adjust=False).mean()
    x["ema20"] = x.close.ewm(span=20, adjust=False).mean()
    x["ema50"] = x.close.ewm(span=50, adjust=False).mean()
    x["ema100"] = x.close.ewm(span=100, adjust=False).mean()
    x["body_atr"] = (x.close - x.open).abs() / x.atr14.replace(0, np.nan)
    x["range_atr"] = (x.high - x.low) / x.atr14.replace(0, np.nan)
    x["prev_high10"] = x.high.shift(1).rolling(10).max()
    x["prev_low10"] = x.low.shift(1).rolling(10).min()
    x["prev_high20"] = x.high.shift(1).rolling(20).max()
    x["prev_low20"] = x.low.shift(1).rolling(20).min()

    # MACD standard 12/26/9
    x["macd"] = x.close.ewm(span=12, adjust=False).mean() - x.close.ewm(span=26, adjust=False).mean()
    x["macd_sig"] = x.macd.ewm(span=9, adjust=False).mean()
    x["macd_hist"] = x.macd - x.macd_sig

    # Keltner standard-ish EMA20 +/- 1.5 ATR
    x["kc_mid"] = x.ema20
    x["kc_up"] = x.kc_mid + 1.5 * x.atr14
    x["kc_dn"] = x.kc_mid - 1.5 * x.atr14

    # Bollinger 20/2
    sma20 = x.close.rolling(20).mean()
    std20 = x.close.rolling(20).std(ddof=0)
    x["bb_up"] = sma20 + 2.0 * std20
    x["bb_dn"] = sma20 - 2.0 * std20

    # Ichimoku standard 9/26/52, current-cloud usage only (no forward lookahead).
    x["tenkan"] = (x.high.rolling(9).max() + x.low.rolling(9).min()) / 2.0
    x["kijun"] = (x.high.rolling(26).max() + x.low.rolling(26).min()) / 2.0
    x["span_a_now"] = ((x.tenkan + x.kijun) / 2.0).shift(26)
    x["span_b_now"] = ((x.high.rolling(52).max() + x.low.rolling(52).min()) / 2.0).shift(26)
    x["cloud_hi"] = pd.concat([x.span_a_now, x.span_b_now], axis=1).max(axis=1)
    x["cloud_lo"] = pd.concat([x.span_a_now, x.span_b_now], axis=1).min(axis=1)

    # ROC momentum.
    x["roc12"] = x.close.pct_change(12) * 100.0

    # Daily anchored VWAP from M15 tick volume.
    day = x.index.floor("D")
    pv = x.close * x.volume
    x["day_vwap"] = pv.groupby(day).cumsum() / x.volume.groupby(day).cumsum().replace(0, np.nan)

    # Session ranges, causal by day.
    minutes = x.index.hour * 60 + x.index.minute
    asia = (minutes >= 0) & (minutes < 6 * 60)
    london_or = (minutes >= 7 * 60) & (minutes < 8 * 60)
    london_trade = (minutes >= 7 * 60) & (minutes < 11 * 60 + 30)

    temp = x.copy()
    temp["day"] = day
    temp["asia_high_raw"] = np.where(asia, temp.high, np.nan)
    temp["asia_low_raw"] = np.where(asia, temp.low, np.nan)
    temp["lor_high_raw"] = np.where(london_or, temp.high, np.nan)
    temp["lor_low_raw"] = np.where(london_or, temp.low, np.nan)
    # Full Asia range is known from 06:00 onward. London OR known from 08:00 onward.
    asia_hi_by_day = temp.groupby("day").asia_high_raw.max()
    asia_lo_by_day = temp.groupby("day").asia_low_raw.min()
    lor_hi_by_day = temp.groupby("day").lor_high_raw.max()
    lor_lo_by_day = temp.groupby("day").lor_low_raw.min()
    x["asia_high"] = day.map(asia_hi_by_day)
    x["asia_low"] = day.map(asia_lo_by_day)
    x["lor_high"] = day.map(lor_hi_by_day)
    x["lor_low"] = day.map(lor_lo_by_day)
    x["after_asia"] = minutes >= 6 * 60
    x["london_trade"] = london_trade
    x["after_lor"] = minutes >= 8 * 60

    for h in (h4, d1):
        h["atr14"] = atr(h, 14)
        h["ema20"] = h.close.ewm(span=20, adjust=False).mean()
        h["ema50"] = h.close.ewm(span=50, adjust=False).mean()
        h["ema100"] = h.close.ewm(span=100, adjust=False).mean()
        h["slope20"] = h.ema20.diff(3)

    close_times = x.index + pd.Timedelta(minutes=15)
    for prefix, h, period in [("h4", h4, pd.Timedelta(hours=4)), ("d1", d1, pd.Timedelta(days=1))]:
        for col in ["ema20", "ema50", "ema100", "slope20", "atr14", "close"]:
            x[f"{prefix}_{col}"] = align_completed(h[col], close_times, period).to_numpy()

    x["d1_up"] = (x.d1_ema20 > x.d1_ema50) & (x.d1_slope20 > 0)
    x["d1_down"] = (x.d1_ema20 < x.d1_ema50) & (x.d1_slope20 < 0)
    x["h4_up"] = (x.h4_ema20 > x.h4_ema50) & (x.h4_slope20 > 0)
    x["h4_down"] = (x.h4_ema20 < x.h4_ema50) & (x.h4_slope20 < 0)
    x["align_up"] = x.d1_up & x.h4_up
    x["align_down"] = x.d1_down & x.h4_down
    return x


def masks(f: pd.DataFrame, family: str) -> tuple[pd.Series, pd.Series]:
    bull = f.align_up
    bear = f.align_down

    if family == "asia_breakout":
        window = f.after_asia & f.london_trade
        lo = bull & window & (f.close > f.asia_high) & (f.close.shift(1) <= f.asia_high.shift(1)) & (f.body_atr >= 0.35)
        sh = bear & window & (f.close < f.asia_low) & (f.close.shift(1) >= f.asia_low.shift(1)) & (f.body_atr >= 0.35)

    elif family == "london_orb":
        window = f.after_lor & f.london_trade
        lo = bull & window & (f.close > f.lor_high) & (f.close.shift(1) <= f.lor_high.shift(1)) & (f.body_atr >= 0.30)
        sh = bear & window & (f.close < f.lor_low) & (f.close.shift(1) >= f.lor_low.shift(1)) & (f.body_atr >= 0.30)

    elif family == "keltner":
        lo = bull & (f.close > f.kc_up) & (f.close.shift(1) <= f.kc_up.shift(1)) & (f.adx >= 18)
        sh = bear & (f.close < f.kc_dn) & (f.close.shift(1) >= f.kc_dn.shift(1)) & (f.adx >= 18)

    elif family == "macd":
        lo = bull & (f.macd > f.macd_sig) & (f.macd.shift(1) <= f.macd_sig.shift(1)) & (f.macd > 0) & (f.close > f.ema20)
        sh = bear & (f.macd < f.macd_sig) & (f.macd.shift(1) >= f.macd_sig.shift(1)) & (f.macd < 0) & (f.close < f.ema20)

    elif family == "ichimoku":
        lo = bull & (f.close > f.cloud_hi) & (f.tenkan > f.kijun) & (f.close > f.kijun) & (f.close.shift(1) <= f.cloud_hi.shift(1))
        sh = bear & (f.close < f.cloud_lo) & (f.tenkan < f.kijun) & (f.close < f.kijun) & (f.close.shift(1) >= f.cloud_lo.shift(1))

    elif family == "rsi2_pullback":
        lo = bull & (f.rsi2.shift(1) < 10) & (f.rsi2 >= 20) & (f.close > f.ema20) & (f.close > f.open)
        sh = bear & (f.rsi2.shift(1) > 90) & (f.rsi2 <= 80) & (f.close < f.ema20) & (f.close < f.open)

    elif family == "vwap_reclaim":
        lo = bull & (f.low <= f.day_vwap) & (f.close > f.day_vwap) & (f.close > f.open) & (f.adx >= 16)
        sh = bear & (f.high >= f.day_vwap) & (f.close < f.day_vwap) & (f.close < f.open) & (f.adx >= 16)

    elif family == "atr_expansion":
        lo = bull & (f.close > f.prev_high10) & (f.range_atr >= 1.20) & (f.body_atr >= 0.65)
        sh = bear & (f.close < f.prev_low10) & (f.range_atr >= 1.20) & (f.body_atr >= 0.65)

    elif family == "roc_momentum":
        lo = bull & (f.roc12 > 0.35) & (f.roc12.shift(1) <= 0.35) & (f.close > f.ema20)
        sh = bear & (f.roc12 < -0.35) & (f.roc12.shift(1) >= -0.35) & (f.close < f.ema20)

    elif family == "ema_ribbon":
        up_ribbon = (f.ema8 > f.ema20) & (f.ema20 > f.ema50)
        dn_ribbon = (f.ema8 < f.ema20) & (f.ema20 < f.ema50)
        lo = bull & up_ribbon & (f.close > f.prev_high10) & (f.adx >= 17)
        sh = bear & dn_ribbon & (f.close < f.prev_low10) & (f.adx >= 17)

    elif family == "bb_trend":
        lo = bull & (f.close > f.bb_up) & (f.close.shift(1) <= f.bb_up.shift(1)) & (f.adx >= 17)
        sh = bear & (f.close < f.bb_dn) & (f.close.shift(1) >= f.bb_dn.shift(1)) & (f.adx >= 17)

    elif family == "adx_pullback_break":
        lo = bull & (f.adx >= 22) & (f.low.shift(1) <= f.ema20.shift(1)) & (f.close > f.high.shift(1)) & (f.pdi > f.mdi)
        sh = bear & (f.adx >= 22) & (f.high.shift(1) >= f.ema20.shift(1)) & (f.close < f.low.shift(1)) & (f.mdi > f.pdi)

    else:
        raise ValueError(family)
    return lo.fillna(False), sh.fillna(False)


def build(f: pd.DataFrame, c: Card) -> pd.DataFrame:
    lo, sh = masks(f, c.family)
    rows = []
    last = {1: -10**9, -1: -10**9}
    for i in np.flatnonzero((lo | sh).to_numpy()):
        d = 1 if bool(lo.iat[i]) else -1
        if i - last[d] < c.cooldown:
            continue
        row = f.iloc[i]
        a = float(row.atr14)
        if not np.isfinite(a) or a <= 0:
            continue

        if c.stop_mode == "range" and c.family == "asia_breakout":
            stop = float(row.asia_low if d == 1 else row.asia_high)
        elif c.stop_mode == "range" and c.family == "london_orb":
            stop = float(row.lor_low if d == 1 else row.lor_high)
        else:
            recent = f.iloc[max(0, i - 5): i + 1]
            stop = float(recent.low.min() - 0.08 * a) if d == 1 else float(recent.high.max() + 0.08 * a)

        if not np.isfinite(stop):
            continue
        rows.append({
            "card": c.name,
            "signal_i": i,
            "signal_time": f.index[i],
            "signal_close_time": f.index[i] + pd.Timedelta(minutes=15),
            "direction": d,
            "stop": stop,
            "atr14": a,
            "adx": float(row.adx) if np.isfinite(row.adx) else np.nan,
            "vol_ratio": float(row.volume / row.volume) if np.isfinite(row.volume) and row.volume != 0 else np.nan,
        })
        last[d] = i
    return pd.DataFrame(rows)


def run(data_path, output_dir):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    raw = load_m5_csv(data_path)
    m5 = raw[(raw.index >= pd.Timestamp("2016-01-01", tz="UTC")) & (raw.index < DEV_END)].copy()
    f = prepare(m5)

    cache = {c.name: build(f, c) for c in CARDS}
    defs = {
        "PORT_BREAKOUT_ALT": ["ASIA_BREAKOUT", "KELTNER_BREAK", "ATR_EXPANSION"],
        "PORT_TREND_ALT": ["MACD_CONTINUATION", "ICHIMOKU_CONTINUATION", "EMA_RIBBON_BREAK"],
        "PORT_PULLBACK_ALT": ["RSI2_PULLBACK", "VWAP_RECLAIM", "ADX_PULLBACK_BREAK"],
        "PORT_SESSION_TREND": ["ASIA_BREAKOUT", "LONDON_ORB", "BB_TREND_BREAK"],
        "PORT_DIVERSE_ALT": ["ASIA_BREAKOUT", "MACD_CONTINUATION", "RSI2_PULLBACK", "ATR_EXPANSION"],
    }
    for name, members in defs.items():
        cache[name] = combine_setups([cache[m] for m in members], name)

    rows, yrs, months, alltr = [], [], [], []
    for name, ss in cache.items():
        tr = replay(m5, ss)
        if not tr.empty:
            alltr.append(tr.assign(strategy=name))
        ov = metrics(tr)
        ms = month_stats(tr)
        y = yearly(tr)
        rows.append({
            "strategy": name, **ov, **ms,
            "positive_years": int((y.expectancy_r > 0).sum()),
            "pf_gt1_years": int((y.pf > 1).sum()),
            "worst_year_exp_r": float(y.expectancy_r.min()),
            "worst_year_dd_pct": float(y.max_dd_pct.max()),
        })
        for rr in y.itertuples(index=False):
            yrs.append({"strategy": name, **rr._asdict()})
        pp = pd.to_datetime(tr.entry_time, utc=True).dt.to_period("M") if not tr.empty else pd.Series([], dtype="period[M]")
        for p in pd.period_range("2017-01", "2020-12", freq="M"):
            g = tr[pp == p] if not tr.empty else tr
            months.append({"strategy": name, "month": str(p), **metrics(g)})

    ranked = pd.DataFrame(rows).sort_values(
        ["positive_years","pf_gt1_years","min_month","avg_month","worst_year_exp_r","expectancy_r","pf","worst_year_dd_pct"],
        ascending=[False,False,False,False,False,False,False,True]
    )
    yd = pd.DataFrame(yrs)
    md = pd.DataFrame(months)
    td = pd.concat(alltr, ignore_index=True) if alltr else pd.DataFrame()
    ranked.to_csv(out/"ranked.csv", index=False)
    yd.to_csv(out/"yearly.csv", index=False)
    md.to_csv(out/"monthly.csv", index=False)
    td.to_csv(out/"trades.csv", index=False)

    lines = [
        "# Historical-First Phase 5 — Alternative Systems",
        "",
        "Development window only: 2017-2020. No 2021+ inspection.",
        "RR3, RM100, 5% risk, 1bp cost, one position at a time, same-M5 stop-first.",
        "",
        "| Strategy | Trades | Avg/mo | Min/mo | >=8 | Pos years | WR | ExpR | PF | Worst ExpR | Worst DD | End RM |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in ranked.itertuples(index=False):
        pf = "∞" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(
            f"| {r.strategy} | {r.trades} | {r.avg_month:.2f} | {r.min_month} | {r.months_ge8}/48 | "
            f"{r.positive_years}/4 | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | "
            f"{r.worst_year_exp_r:+.3f} | {r.worst_year_dd_pct:.2f}% | RM{r.end_rm:.2f} |"
        )
    for strategy in ranked.head(10).strategy:
        lines += ["", f"## {strategy}", "",
                  "| Year | Trades | WR | ExpR | PF | DD | RM100 → |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for r in yd[yd.strategy == strategy].itertuples(index=False):
            pf = "∞" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
            lines.append(
                f"| {r.year} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | "
                f"{r.max_dd_pct:.2f}% | RM{r.end_rm:.2f} |"
            )

    report = "\n".join(lines) + "\n"
    (out/"REPORT.md").write_text(report, encoding="utf-8")
    (out/"summary.json").write_text(json.dumps({
        "window":"2017-2020",
        "families":["session breakout","keltner","macd","ichimoku","rsi2 pullback","vwap","atr expansion","roc","ema ribbon","bollinger trend","adx pullback"],
        "top":ranked.head(12).replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")
    }, indent=2), encoding="utf-8")
    print(report)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output", default="reports/historical-first-alternative-systems")
    a = p.parse_args()
    run(a.data, a.output)

if __name__ == "__main__":
    main()
