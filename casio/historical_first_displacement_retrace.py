from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import (
    DEV_END, atr, di_adx, resample, align_completed,
    metrics, month_stats, yearly,
)

START = pd.Timestamp("2017-01-01", tz="UTC")
RISK_FRACTION = 0.05
ROUND_TRIP_BPS = 1.0
RR = 3.0


@dataclass(frozen=True)
class Card:
    name: str
    family: str
    bias: str = "h4d1"
    session: str = "PRIMARY"
    disp_atr: float = 0.8
    body_frac: float = 0.70
    retrace: float = 0.50
    wait_min: int = 60
    lookback: int = 12
    stop_buf_atr: float = 0.04


def prep(m5: pd.DataFrame) -> pd.DataFrame:
    f = resample(m5, "15min")
    f["atr14"] = atr(f, 14)
    pdi, mdi, adx = di_adx(f, 14)
    f["pdi"], f["mdi"], f["adx"] = pdi, mdi, adx
    f["body"] = (f.close - f.open).abs()
    f["range"] = f.high - f.low
    f["body_atr"] = f.body / f.atr14.replace(0, np.nan)
    f["body_frac"] = f.body / f.range.replace(0, np.nan)
    f["close_pos"] = (f.close - f.low) / f.range.replace(0, np.nan)

    for lb in [8, 12, 20, 32]:
        f[f"ph{lb}"] = f.high.shift(1).rolling(lb).max()
        f[f"pl{lb}"] = f.low.shift(1).rolling(lb).min()

    # UTC session reference levels.
    f["day"] = f.index.floor("D")
    mins = f.index.hour * 60 + f.index.minute
    f["mins"] = mins
    asia = (mins >= 0) & (mins < 6 * 60)
    nyor = (mins >= 12 * 60 + 30) & (mins < 13 * 60 + 30)
    stats = f.loc[asia].groupby("day").agg(asia_h=("high","max"), asia_l=("low","min"))
    f["asia_h"] = f.day.map(stats.asia_h)
    f["asia_l"] = f.day.map(stats.asia_l)
    nyst = f.loc[nyor].groupby("day").agg(ny_h=("high","max"), ny_l=("low","min"))
    f["ny_h"] = f.day.map(nyst.ny_h)
    f["ny_l"] = f.day.map(nyst.ny_l)

    daily = f.groupby("day").agg(day_h=("high","max"), day_l=("low","min"))
    prev = daily.shift(1)
    f["pd_h"] = f.day.map(prev.day_h)
    f["pd_l"] = f.day.map(prev.day_l)

    # Completed higher-timeframe bias.
    h1 = resample(m5, "1h")
    h4 = resample(m5, "4h")
    d1 = resample(m5, "1D")
    for x in (h1, h4, d1):
        x["ema20"] = x.close.ewm(span=20, adjust=False).mean()
        x["ema50"] = x.close.ewm(span=50, adjust=False).mean()
        x["s20"] = x.ema20.diff(3)

    ct = f.index + pd.Timedelta(minutes=15)
    for p, x, period in [
        ("h1", h1, pd.Timedelta(hours=1)),
        ("h4", h4, pd.Timedelta(hours=4)),
        ("d1", d1, pd.Timedelta(days=1)),
    ]:
        for col in ["ema20","ema50","s20"]:
            f[f"{p}_{col}"] = align_completed(x[col], ct, period).to_numpy()
        f[f"{p}_up"] = (f[f"{p}_ema20"] > f[f"{p}_ema50"]) & (f[f"{p}_s20"] > 0)
        f[f"{p}_dn"] = (f[f"{p}_ema20"] < f[f"{p}_ema50"]) & (f[f"{p}_s20"] < 0)

    f["h4d1_up"] = f.h4_up & f.d1_up
    f["h4d1_dn"] = f.h4_dn & f.d1_dn
    f["triple_up"] = f.h1_up & f.h4_up & f.d1_up
    f["triple_dn"] = f.h1_dn & f.h4_dn & f.d1_dn

    # Mechanical FVG based on completed three-candle structure.
    f["bull_fvg"] = f.low > f.high.shift(2)
    f["bear_fvg"] = f.high < f.low.shift(2)
    f["bull_fvg_lo"] = f.high.shift(2)
    f["bull_fvg_hi"] = f.low
    f["bear_fvg_lo"] = f.high
    f["bear_fvg_hi"] = f.low.shift(2)
    return f


def bias_masks(f: pd.DataFrame, b: str):
    if b == "h4d1":
        return f.h4d1_up.fillna(False), f.h4d1_dn.fillna(False)
    if b == "triple":
        return f.triple_up.fillna(False), f.triple_dn.fillna(False)
    if b == "h4":
        return f.h4_up.fillna(False), f.h4_dn.fillna(False)
    if b == "none":
        return pd.Series(True,index=f.index), pd.Series(True,index=f.index)
    raise ValueError(b)


def session_mask(f: pd.DataFrame, s: str):
    m = f.mins
    if s == "ALL":
        return pd.Series(True, index=f.index)
    if s == "PRIMARY":
        return pd.Series(((m >= 7*60) & (m < 11*60)) | ((m >= 12*60+30) & (m < 16*60+30)), index=f.index)
    if s == "LONDON":
        return pd.Series((m >= 7*60) & (m < 11*60), index=f.index)
    if s == "NY":
        return pd.Series((m >= 12*60+30) & (m < 16*60+30), index=f.index)
    raise ValueError(s)


def setups(f: pd.DataFrame, c: Card) -> pd.DataFrame:
    up, dn = bias_masks(f, c.bias)
    ss = session_mask(f, c.session)
    ph = f[f"ph{c.lookback}"]
    pl = f[f"pl{c.lookback}"]

    disp_bull = (
        (f.close > f.open)
        & (f.body_atr >= c.disp_atr)
        & (f.body_frac >= c.body_frac)
        & (f.close_pos >= 0.75)
    )
    disp_bear = (
        (f.close < f.open)
        & (f.body_atr >= c.disp_atr)
        & (f.body_frac >= c.body_frac)
        & (f.close_pos <= 0.25)
    )

    rows = []

    for i in range(2, len(f)):
        row = f.iloc[i]
        direction = 0
        entry = stop = np.nan
        family = c.family

        if family == "displacement_retrace":
            if bool(up.iat[i] and ss.iat[i] and disp_bull.iat[i] and row.close > ph.iat[i]):
                direction = 1
                entry = float(row.close - c.retrace * (row.close - row.open))
                stop = float(row.low - c.stop_buf_atr * row.atr14)
            elif bool(dn.iat[i] and ss.iat[i] and disp_bear.iat[i] and row.close < pl.iat[i]):
                direction = -1
                entry = float(row.close + c.retrace * (row.open - row.close))
                stop = float(row.high + c.stop_buf_atr * row.atr14)

        elif family == "fvg_ce":
            # Current bar is candle 3; candle i-1 must be the displacement candle.
            prev = f.iloc[i-1]
            prev_bull = (
                prev.close > prev.open
                and prev.body_atr >= c.disp_atr
                and prev.body_frac >= c.body_frac
            )
            prev_bear = (
                prev.close < prev.open
                and prev.body_atr >= c.disp_atr
                and prev.body_frac >= c.body_frac
            )
            if bool(up.iat[i] and ss.iat[i] and row.bull_fvg and prev_bull):
                direction = 1
                entry = float((row.bull_fvg_lo + row.bull_fvg_hi) / 2.0)
                stop = float(min(f.low.iloc[i-2:i+1]) - c.stop_buf_atr * row.atr14)
            elif bool(dn.iat[i] and ss.iat[i] and row.bear_fvg and prev_bear):
                direction = -1
                entry = float((row.bear_fvg_lo + row.bear_fvg_hi) / 2.0)
                stop = float(max(f.high.iloc[i-2:i+1]) + c.stop_buf_atr * row.atr14)

        elif family == "sweep_displacement":
            # Sweep against trend + strong close back through swept level.
            if bool(up.iat[i] and ss.iat[i] and row.low < pl.iat[i] and row.close > pl.iat[i] and disp_bull.iat[i]):
                direction = 1
                entry = float(row.close - c.retrace * (row.close - row.open))
                stop = float(row.low - c.stop_buf_atr * row.atr14)
            elif bool(dn.iat[i] and ss.iat[i] and row.high > ph.iat[i] and row.close < ph.iat[i] and disp_bear.iat[i]):
                direction = -1
                entry = float(row.close + c.retrace * (row.open - row.close))
                stop = float(row.high + c.stop_buf_atr * row.atr14)

        elif family == "asia_sweep_displacement":
            london = 7*60 <= int(row.mins) < 11*60
            if london and bool(up.iat[i] and row.low < row.asia_l and row.close > row.asia_l and disp_bull.iat[i]):
                direction = 1
                entry = float(row.close - c.retrace * (row.close - row.open))
                stop = float(row.low - c.stop_buf_atr * row.atr14)
            elif london and bool(dn.iat[i] and row.high > row.asia_h and row.close < row.asia_h and disp_bear.iat[i]):
                direction = -1
                entry = float(row.close + c.retrace * (row.open - row.close))
                stop = float(row.high + c.stop_buf_atr * row.atr14)

        elif family == "pd_sweep_displacement":
            primary = ((7*60 <= int(row.mins) < 11*60) or (12*60+30 <= int(row.mins) < 16*60+30))
            if primary and bool(up.iat[i] and row.low < row.pd_l and row.close > row.pd_l and disp_bull.iat[i]):
                direction = 1
                entry = float(row.close - c.retrace * (row.close - row.open))
                stop = float(row.low - c.stop_buf_atr * row.atr14)
            elif primary and bool(dn.iat[i] and row.high > row.pd_h and row.close < row.pd_h and disp_bear.iat[i]):
                direction = -1
                entry = float(row.close + c.retrace * (row.open - row.close))
                stop = float(row.high + c.stop_buf_atr * row.atr14)

        if direction == 0 or not np.isfinite(entry) or not np.isfinite(stop):
            continue
        risk = (entry - stop) if direction == 1 else (stop - entry)
        a = float(row.atr14)
        if not np.isfinite(a) or a <= 0 or risk <= 0:
            continue
        risk_atr = risk / a
        if risk_atr < 0.15 or risk_atr > 2.5:
            continue

        rows.append({
            "card": c.name,
            "family": c.family,
            "signal_time": f.index[i],
            "available_time": f.index[i] + pd.Timedelta(minutes=15),
            "direction": direction,
            "entry_limit": entry,
            "stop": stop,
            "atr14": a,
            "risk_atr": risk_atr,
            "wait_min": c.wait_min,
        })
    return pd.DataFrame(rows)


def replay_pending(m5: pd.DataFrame, ss: pd.DataFrame) -> pd.DataFrame:
    if ss.empty:
        return pd.DataFrame()
    idx = m5.index
    rows = []
    busy_until = None

    for s in ss.itertuples(index=False):
        st = pd.Timestamp(s.signal_time)
        if st < START or st >= DEV_END:
            continue
        avail = pd.Timestamp(s.available_time)
        if busy_until is not None and avail <= busy_until:
            continue

        start_pos = idx.searchsorted(avail, side="left")
        expiry = avail + pd.Timedelta(minutes=int(s.wait_min))
        fill_pos = None
        for j in range(start_pos, len(idx)):
            t = idx[j]
            if t >= expiry or t >= DEV_END:
                break
            bar = m5.iloc[j]
            if float(bar.low) <= float(s.entry_limit) <= float(bar.high):
                fill_pos = j
                break
        if fill_pos is None:
            continue

        et = idx[fill_pos]
        if busy_until is not None and et <= busy_until:
            continue

        d = int(s.direction)
        entry = float(s.entry_limit)
        stop = float(s.stop)
        risk = (entry - stop) if d == 1 else (stop - entry)
        if risk <= 0:
            continue
        target = entry + d * RR * risk

        exit_price = exit_time = reason = None
        for j in range(fill_pos, len(idx)):
            t = idx[j]
            if t >= DEV_END:
                break
            lo, hi = float(m5.iloc[j].low), float(m5.iloc[j].high)
            hit_s = lo <= stop if d == 1 else hi >= stop
            hit_t = hi >= target if d == 1 else lo <= target
            if hit_s:
                exit_price = stop
                exit_time = t + pd.Timedelta(minutes=5)
                reason = "SL_same_bar" if hit_t else "SL"
                break
            if hit_t:
                exit_price = target
                exit_time = t + pd.Timedelta(minutes=5)
                reason = "TP"
                break
        if exit_price is None:
            continue

        gross_r = (exit_price-entry)/risk if d==1 else (entry-exit_price)/risk
        cost_r = (entry * ROUND_TRIP_BPS / 10000.0) / risk
        net_r = float(gross_r - cost_r)
        rows.append({
            "card": s.card,
            "family": s.family,
            "signal_time": st,
            "entry_time": et,
            "exit_time": exit_time,
            "direction": "BUY" if d == 1 else "SELL",
            "entry": entry,
            "stop": stop,
            "target": target,
            "gross_r": float(gross_r),
            "cost_r": float(cost_r),
            "net_r": net_r,
            "r_multiple": net_r,
            "result": "WIN" if net_r > 0 else "LOSS",
            "exit_reason": reason,
        })
        busy_until = exit_time
    return pd.DataFrame(rows)


def make_cards():
    out = []
    for family in ["displacement_retrace","fvg_ce","sweep_displacement","asia_sweep_displacement","pd_sweep_displacement"]:
        biases = ["h4d1","triple"] if family not in ["asia_sweep_displacement","pd_sweep_displacement"] else ["h4d1","none"]
        sessions = ["PRIMARY","ALL"] if family in ["displacement_retrace","fvg_ce","sweep_displacement"] else ["ALL"]
        for b in biases:
            for s in sessions:
                for da in [0.7, 0.9, 1.1, 1.3]:
                    for bf in [0.65, 0.75, 0.85]:
                        for rt in [0.50, 0.618, 0.705]:
                            for wait in [30, 60, 120]:
                                for lb in ([8,12,20] if family in ["displacement_retrace","sweep_displacement"] else [12]):
                                    name = f"{family}__{b}__{s}__D{da}__B{bf}__R{rt}__W{wait}__L{lb}"
                                    out.append(Card(name,family,b,s,da,bf,rt,wait,lb,0.04))
    return out


def strict_pass(r):
    return r.wr >= 60 and r.dd <= 25 and r.min_month >= 8 and r.positive_years == 4 and r.pf_years == 4


def run(data_path, output_dir):
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    raw = load_m5_csv(data_path)
    m5 = raw[(raw.index >= pd.Timestamp("2016-01-01",tz="UTC")) & (raw.index < DEV_END)].copy()
    f = prep(m5)

    rows=[]; yrs=[]; trades=[]
    cards = make_cards()
    for c in cards:
        tr = replay_pending(m5, setups(f,c))
        if not tr.empty:
            trades.append(tr.assign(strategy=c.name))
        ov = metrics(tr.rename(columns={"net_r":"net_r"}) if not tr.empty else tr)
        ms = month_stats(tr)
        y = yearly(tr)
        rows.append({
            "strategy":c.name,"family":c.family,"bias":c.bias,
            "disp_atr":c.disp_atr,"body_frac":c.body_frac,"retrace":c.retrace,"wait_min":c.wait_min,"lookback":c.lookback,
            "trades":ov["trades"],"wr":ov["wr"],"expectancy_r":ov["expectancy_r"],"pf":ov["pf"],
            "dd":ov["max_dd_pct"],"end_rm":ov["end_rm"],**ms,
            "positive_years":int((y.expectancy_r>0).sum()),
            "pf_years":int((y.pf>1).sum()),
            "worst_year_exp":float(y.expectancy_r.min()),
            "worst_year_dd":float(y.max_dd_pct.max()),
        })
        for rr in y.itertuples(index=False):
            yrs.append({"strategy":c.name,**rr._asdict()})

    rd = pd.DataFrame(rows)
    rd["strict"] = rd.apply(strict_pass,axis=1)
    rd["dist"] = (
        np.maximum(0,60-rd.wr)*3
        + np.maximum(0,rd.dd-25)
        + np.maximum(0,8-rd.min_month)*5
        + (4-rd.positive_years)*20
    )
    ranked = rd.sort_values(
        ["strict","dist","positive_years","min_month","wr","expectancy_r"],
        ascending=[False,True,False,False,False,False]
    )
    yd = pd.DataFrame(yrs)
    ranked.to_csv(out/"ranked.csv",index=False)
    yd.to_csv(out/"yearly.csv",index=False)
    if trades:
        pd.concat(trades,ignore_index=True).to_csv(out/"trades.csv",index=False)

    strict = ranked[ranked.strict]
    lines = [
        "# Historical-First Displacement / Retracement Search","",
        "2017-2020 development only; 2021+ sealed.",
        "Hard target: RR3, WR>=60%, max DD<=25%, minimum 8 trades every month, profitable 4/4 years.",
        "Pending limit entries are only eligible after the M15 setup/pattern is fully closed. M5 fills and exits; same-bar stop wins; 1bp cost; RM100; 5% risk.","",
        f"Cards tested: {len(cards)}. Strict passes: {len(strict)}.","",
        "## Strict passes",""
    ]
    if strict.empty:
        lines.append("No candidate met all hard constraints.")
    else:
        lines += ["| Strategy | Trades | WR | ExpR | PF | DD | Avg/mo | Min/mo | Years |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for r in strict.itertuples(index=False):
            lines.append(f"| {r.strategy} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {r.pf:.2f} | {r.dd:.2f}% | {r.avg_month:.2f} | {r.min_month} | {r.positive_years}/4 |")

    lines += ["","## Closest candidates","",
              "| Strategy | Family | Trades | WR | ExpR | PF | DD | Avg/mo | Min/mo | Years | Dist |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in ranked.head(25).itertuples(index=False):
        pf = "∞" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(f"| {r.strategy} | {r.family} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.dd:.2f}% | {r.avg_month:.2f} | {r.min_month} | {r.positive_years}/4 | {r.dist:.1f} |")

    detail = strict.strategy.tolist() if len(strict) else ranked.head(8).strategy.tolist()
    for strategy in detail:
        lines += ["",f"## {strategy}","","| Year | Trades | WR | ExpR | PF | DD | RM100 -> |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for r in yd[yd.strategy==strategy].itertuples(index=False):
            pf = "∞" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
            lines.append(f"| {r.year} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.max_dd_pct:.2f}% | RM{r.end_rm:.2f} |")

    report="\n".join(lines)+"\n"
    (out/"REPORT.md").write_text(report,encoding="utf-8")
    (out/"summary.json").write_text(json.dumps({
        "cards":len(cards),
        "strict_passes":int(len(strict)),
        "strict":strict.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records"),
        "closest":ranked.head(25).replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")
    },indent=2),encoding="utf-8")
    print(report)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output",default="reports/historical-first-displacement-retrace")
    a=p.parse_args(); run(a.data,a.output)

if __name__=="__main__":
    main()
