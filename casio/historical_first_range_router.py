from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import json
import math

import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import (
    DEV_START, DEV_END, START_RM, RISK_FRACTION,
    atr, di_adx, resample, align_completed,
    prepare_features, replay, combine_setups, metrics, month_stats, yearly,
    build_setups, CARDS,
)


@dataclass(frozen=True)
class RangeCard:
    name: str
    family: str
    h1_adx_max: float
    h1_sep_max: float
    stop_lookback: int = 3
    cooldown_bars: int = 2


RANGE_CARDS = (
    RangeCard("SWEEP_FADE_18", "sweep", 18.0, 0.55, 3, 2),
    RangeCard("SWEEP_FADE_22", "sweep", 22.0, 0.70, 3, 2),
    RangeCard("FAILED_BREAK_22", "failed_break", 22.0, 0.80, 3, 2),
    RangeCard("BB_FADE_18", "bb_fade", 18.0, 0.60, 3, 2),
    RangeCard("BB_FADE_22", "bb_fade", 22.0, 0.80, 3, 2),
    RangeCard("VOL_CLIMAX_FADE", "vol_climax", 24.0, 0.90, 3, 3),
    RangeCard("RSI_RANGE_RECLAIM", "rsi_range", 20.0, 0.75, 4, 2),
)


def add_h1_regime(m5: pd.DataFrame, f: pd.DataFrame) -> pd.DataFrame:
    h1 = resample(m5, "1h")
    pdi, mdi, adx = di_adx(h1, 14)
    h1["adx"] = adx
    h1["atr14"] = atr(h1, 14)
    h1["ema20"] = h1.close.ewm(span=20, adjust=False).mean()
    h1["ema50"] = h1.close.ewm(span=50, adjust=False).mean()
    h1["sep_atr"] = (h1.ema20 - h1.ema50).abs() / h1.atr14.replace(0, np.nan)
    close_times = f.index + pd.Timedelta(minutes=15)
    f = f.copy()
    f["h1_adx"] = align_completed(h1.adx, close_times, pd.Timedelta(hours=1)).to_numpy()
    f["h1_sep_atr"] = align_completed(h1.sep_atr, close_times, pd.Timedelta(hours=1)).to_numpy()
    return f


def range_masks(f: pd.DataFrame, c: RangeCard) -> tuple[pd.Series, pd.Series]:
    gate = (f.h1_adx <= c.h1_adx_max) & (f.h1_sep_atr <= c.h1_sep_max)

    swept_low10 = (f.low < f.prev_low10) & (f.close > f.prev_low10)
    swept_high10 = (f.high > f.prev_high10) & (f.close < f.prev_high10)
    swept_low20 = (f.low < f.prev_low20) & (f.close > f.prev_low20)
    swept_high20 = (f.high > f.prev_high20) & (f.close < f.prev_high20)

    if c.family == "sweep":
        lo = gate & swept_low20 & (f.rsi8 <= 38) & (f.close > f.open)
        sh = gate & swept_high20 & (f.rsi8 >= 62) & (f.close < f.open)
    elif c.family == "failed_break":
        lo = gate & swept_low10 & (f.close > f.open) & (f.body_atr >= 0.20)
        sh = gate & swept_high10 & (f.close < f.open) & (f.body_atr >= 0.20)
    elif c.family == "bb_fade":
        lo = gate & (f.low < f.bb_lower) & (f.close > f.bb_lower) & (f.rsi8 <= 35) & (f.close > f.open)
        sh = gate & (f.high > f.bb_upper) & (f.close < f.bb_upper) & (f.rsi8 >= 65) & (f.close < f.open)
    elif c.family == "vol_climax":
        lo = gate & swept_low10 & (f.vol_ratio >= 1.40) & (f.rsi8 <= 40) & (f.close > f.open)
        sh = gate & swept_high10 & (f.vol_ratio >= 1.40) & (f.rsi8 >= 60) & (f.close < f.open)
    elif c.family == "rsi_range":
        lo = gate & (f.rsi8.shift(1) <= 25) & (f.rsi8 > 25) & (f.close > f.open)
        sh = gate & (f.rsi8.shift(1) >= 75) & (f.rsi8 < 75) & (f.close < f.open)
    else:
        raise ValueError(c.family)
    return lo.fillna(False), sh.fillna(False)


def build_range_setups(f: pd.DataFrame, c: RangeCard) -> pd.DataFrame:
    lo, sh = range_masks(f, c)
    rows = []
    last = {1: -10**9, -1: -10**9}
    for i in np.flatnonzero((lo | sh).to_numpy()):
        d = 1 if bool(lo.iat[i]) else -1
        if i - last[d] < c.cooldown_bars:
            continue
        row = f.iloc[i]
        a = float(row.atr14)
        if not np.isfinite(a) or a <= 0:
            continue
        # Tight reversal stop: beyond the rejection signal extreme.
        stop = float(row.low - 0.08 * a) if d == 1 else float(row.high + 0.08 * a)
        rows.append({
            "card": c.name,
            "signal_i": i,
            "signal_time": f.index[i],
            "signal_close_time": f.index[i] + pd.Timedelta(minutes=15),
            "direction": d,
            "stop": stop,
            "atr14": a,
            "adx": float(row.h1_adx) if np.isfinite(row.h1_adx) else np.nan,
            "vol_ratio": float(row.vol_ratio) if np.isfinite(row.vol_ratio) else np.nan,
        })
        last[d] = i
    return pd.DataFrame(rows)


def run(data_path: str | Path, output_dir: str | Path) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    raw = load_m5_csv(data_path)
    m5 = raw[(raw.index >= pd.Timestamp("2016-06-01", tz="UTC")) & (raw.index < DEV_END)].copy()
    f = add_h1_regime(m5, prepare_features(m5))

    # Rebuild selected trend cards on the same feature frame.
    base_by_name = {c.name: c for c in CARDS}
    trend_names = ["BB_SQUEEZE_BREAK", "DONCHIAN10_TREND", "TICKVOL_CONTINUATION", "ADX_DI_ROTATION"]
    setup_cache = {name: build_setups(f, base_by_name[name]) for name in trend_names}
    for c in RANGE_CARDS:
        setup_cache[c.name] = build_range_setups(f, c)

    # Causal portfolios: independent trend + range playbooks.
    defs = {
        "ROUTER_BB_SWEEP18": ["BB_SQUEEZE_BREAK", "SWEEP_FADE_18"],
        "ROUTER_BB_SWEEP22": ["BB_SQUEEZE_BREAK", "SWEEP_FADE_22"],
        "ROUTER_DONCHIAN_SWEEP22": ["DONCHIAN10_TREND", "SWEEP_FADE_22"],
        "ROUTER_VOL_SWEEP22": ["TICKVOL_CONTINUATION", "SWEEP_FADE_22"],
        "ROUTER_BB_FAILED22": ["BB_SQUEEZE_BREAK", "FAILED_BREAK_22"],
        "ROUTER_BB_BBFADE22": ["BB_SQUEEZE_BREAK", "BB_FADE_22"],
        "ROUTER_TREND_RANGE": ["BB_SQUEEZE_BREAK", "DONCHIAN10_TREND", "SWEEP_FADE_22", "BB_FADE_22"],
        "ROUTER_DIVERSE_RANGE": ["BB_SQUEEZE_BREAK", "ADX_DI_ROTATION", "SWEEP_FADE_22", "VOL_CLIMAX_FADE"],
        "RANGE_PORTFOLIO": ["SWEEP_FADE_22", "FAILED_BREAK_22", "BB_FADE_22", "VOL_CLIMAX_FADE", "RSI_RANGE_RECLAIM"],
    }
    for name, members in defs.items():
        setup_cache[name] = combine_setups([setup_cache[m] for m in members], name)

    rows = []
    yr_rows = []
    monthly_rows = []
    trade_frames = []

    for name, setups in setup_cache.items():
        tr = replay(m5, setups)
        if not tr.empty:
            trade_frames.append(tr.assign(strategy=name))
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
            yr_rows.append({"strategy": name, **rr._asdict()})
        periods = pd.period_range("2017-01", "2020-12", freq="M")
        pp = pd.to_datetime(tr.entry_time, utc=True).dt.to_period("M") if not tr.empty else pd.Series([], dtype="period[M]")
        for p in periods:
            g = tr[pp == p] if not tr.empty else tr
            monthly_rows.append({"strategy": name, "month": str(p), **metrics(g)})

    ranked = pd.DataFrame(rows).sort_values(
        ["positive_years", "pf_gt1_years", "min_month", "avg_month", "worst_year_exp_r", "expectancy_r", "pf", "worst_year_dd_pct"],
        ascending=[False, False, False, False, False, False, False, True],
    )
    yd = pd.DataFrame(yr_rows)
    md = pd.DataFrame(monthly_rows)
    td = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame()
    ranked.to_csv(out / "ranked.csv", index=False)
    yd.to_csv(out / "yearly.csv", index=False)
    md.to_csv(out / "monthly.csv", index=False)
    td.to_csv(out / "trades.csv", index=False)

    lines = [
        "# Historical-First Phase 2 — Range + Regime Router (2017–2020 only)",
        "",
        "No 2021+ data is inspected here.",
        "Fixed RR3, RM100, 5% risk, 1bp round-trip cost, stop-first same-M5 convention.",
        "",
        "| Strategy | Trades | Avg/mo | Min/mo | >=8 months | Pos years | WR | ExpR | PF | Worst ExpR | Worst DD | End RM |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in ranked.itertuples(index=False):
        pf = "∞" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(
            f"| {r.strategy} | {r.trades} | {r.avg_month:.2f} | {r.min_month} | {r.months_ge8}/48 | "
            f"{r.positive_years}/4 | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | "
            f"{r.worst_year_exp_r:+.3f} | {r.worst_year_dd_pct:.2f}% | RM{r.end_rm:.2f} |"
        )

    for strategy in ranked.head(8).strategy:
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
    (out / "REPORT.md").write_text(report, encoding="utf-8")
    (out / "summary.json").write_text(json.dumps({
        "window": "2017-2020",
        "method": "trend + range regime cards; no forward data inspected",
        "top": ranked.head(10).replace({np.nan: None, np.inf: None, -np.inf: None}).to_dict("records"),
    }, indent=2), encoding="utf-8")
    print(report)
    return ranked


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output", default="reports/historical-first-range-router")
    a = p.parse_args()
    run(a.data, a.output)


if __name__ == "__main__":
    main()
