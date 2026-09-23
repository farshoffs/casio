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
    DEV_START, DEV_END,
    atr, di_adx, resample, align_completed, rsi,
    replay, combine_setups, metrics, month_stats, yearly,
)


@dataclass(frozen=True)
class HTFCard:
    name: str
    family: str
    bias: str
    stop_lookback: int = 6
    cooldown_bars: int = 2


CARDS = (
    HTFCard("D1_DON10", "don10", "d1", 6, 2),
    HTFCard("D1_VOL_BREAK", "volbreak", "d1", 6, 2),
    HTFCard("D1_EMA20_PULLBACK", "pull20", "d1", 7, 2),
    HTFCard("D1_ADX_DI", "adxdi", "d1", 6, 2),
    HTFCard("H4_DON10", "don10", "h4", 6, 2),
    HTFCard("H4_VOL_BREAK", "volbreak", "h4", 6, 2),
    HTFCard("H4_EMA20_PULLBACK", "pull20", "h4", 7, 2),
    HTFCard("H4_ADX_DI", "adxdi", "h4", 6, 2),
    HTFCard("D1_H4_DON10", "don10", "align", 6, 2),
    HTFCard("D1_H4_VOL_BREAK", "volbreak", "align", 6, 2),
    HTFCard("D1_H4_PULL20", "pull20", "align", 7, 2),
    HTFCard("D1_H4_RSI8_RECLAIM", "rsi_reclaim", "align", 7, 2),
)


def prep(m5: pd.DataFrame) -> pd.DataFrame:
    m15 = resample(m5, "15min")
    h4 = resample(m5, "4h")
    d1 = resample(m5, "1D")

    pdi, mdi, adx = di_adx(m15, 14)
    m15["pdi"] = pdi
    m15["mdi"] = mdi
    m15["adx"] = adx
    m15["atr14"] = atr(m15, 14)
    m15["ema20"] = m15.close.ewm(span=20, adjust=False).mean()
    m15["ema50"] = m15.close.ewm(span=50, adjust=False).mean()
    m15["rsi8"] = rsi(m15.close, 8)
    m15["body_atr"] = (m15.close - m15.open).abs() / m15.atr14.replace(0, np.nan)
    m15["vol_med20"] = m15.volume.rolling(20, min_periods=10).median()
    m15["vol_ratio"] = m15.volume / m15.vol_med20.replace(0, np.nan)
    m15["prev_high10"] = m15.high.shift(1).rolling(10).max()
    m15["prev_low10"] = m15.low.shift(1).rolling(10).min()

    for x in (h4, d1):
        x["atr14"] = atr(x, 14)
        x["ema20"] = x.close.ewm(span=20, adjust=False).mean()
        x["ema50"] = x.close.ewm(span=50, adjust=False).mean()
        x["ema100"] = x.close.ewm(span=100, adjust=False).mean()
        x["slope20"] = x.ema20.diff(3)

    close_times = m15.index + pd.Timedelta(minutes=15)
    for prefix, x, period in [
        ("h4", h4, pd.Timedelta(hours=4)),
        ("d1", d1, pd.Timedelta(days=1)),
    ]:
        for col in ["ema20","ema50","ema100","slope20","atr14","close"]:
            m15[f"{prefix}_{col}"] = align_completed(x[col], close_times, period).to_numpy()

    m15["d1_up"] = (m15.d1_ema20 > m15.d1_ema50) & (m15.d1_slope20 > 0)
    m15["d1_down"] = (m15.d1_ema20 < m15.d1_ema50) & (m15.d1_slope20 < 0)
    m15["h4_up"] = (m15.h4_ema20 > m15.h4_ema50) & (m15.h4_slope20 > 0)
    m15["h4_down"] = (m15.h4_ema20 < m15.h4_ema50) & (m15.h4_slope20 < 0)
    m15["align_up"] = m15.d1_up & m15.h4_up
    m15["align_down"] = m15.d1_down & m15.h4_down
    return m15


def bias_masks(f: pd.DataFrame, bias: str) -> tuple[pd.Series,pd.Series]:
    if bias == "d1":
        return f.d1_up.fillna(False), f.d1_down.fillna(False)
    if bias == "h4":
        return f.h4_up.fillna(False), f.h4_down.fillna(False)
    if bias == "align":
        return f.align_up.fillna(False), f.align_down.fillna(False)
    raise ValueError(bias)


def signal_masks(f: pd.DataFrame, card: HTFCard) -> tuple[pd.Series,pd.Series]:
    up, dn = bias_masks(f, card.bias)
    pdi_cross_up = (f.pdi > f.mdi) & (f.pdi.shift(1) <= f.mdi.shift(1))
    pdi_cross_dn = (f.mdi > f.pdi) & (f.mdi.shift(1) <= f.pdi.shift(1))

    if card.family == "don10":
        lo = up & (f.close > f.prev_high10) & (f.body_atr >= 0.30) & (f.adx >= 16)
        sh = dn & (f.close < f.prev_low10) & (f.body_atr >= 0.30) & (f.adx >= 16)
    elif card.family == "volbreak":
        lo = up & (f.close > f.prev_high10) & (f.vol_ratio >= 1.10) & (f.body_atr >= 0.35)
        sh = dn & (f.close < f.prev_low10) & (f.vol_ratio >= 1.10) & (f.body_atr >= 0.35)
    elif card.family == "pull20":
        lo = up & (f.low <= f.ema20) & (f.close > f.ema20) & (f.close > f.open) & (f.pdi > f.mdi)
        sh = dn & (f.high >= f.ema20) & (f.close < f.ema20) & (f.close < f.open) & (f.mdi > f.pdi)
    elif card.family == "adxdi":
        lo = up & pdi_cross_up & (f.adx >= 19) & (f.close > f.ema20)
        sh = dn & pdi_cross_dn & (f.adx >= 19) & (f.close < f.ema20)
    elif card.family == "rsi_reclaim":
        lo = up & (f.rsi8.shift(1) <= 35) & (f.rsi8 > 35) & (f.close > f.ema20) & (f.close > f.open)
        sh = dn & (f.rsi8.shift(1) >= 65) & (f.rsi8 < 65) & (f.close < f.ema20) & (f.close < f.open)
    else:
        raise ValueError(card.family)
    return lo.fillna(False), sh.fillna(False)


def setups(f: pd.DataFrame, card: HTFCard) -> pd.DataFrame:
    lo, sh = signal_masks(f, card)
    rows=[]
    last={1:-10**9,-1:-10**9}
    for i in np.flatnonzero((lo|sh).to_numpy()):
        d=1 if bool(lo.iat[i]) else -1
        if i-last[d] < card.cooldown_bars:
            continue
        row=f.iloc[i]
        a=float(row.atr14)
        if not np.isfinite(a) or a<=0:
            continue
        recent=f.iloc[max(0,i-card.stop_lookback+1):i+1]
        stop=float(recent.low.min()-0.08*a) if d==1 else float(recent.high.max()+0.08*a)
        rows.append({
            "card":card.name,"signal_i":i,"signal_time":f.index[i],
            "signal_close_time":f.index[i]+pd.Timedelta(minutes=15),
            "direction":d,"stop":stop,"atr14":a,
            "adx":float(row.adx) if np.isfinite(row.adx) else np.nan,
            "vol_ratio":float(row.vol_ratio) if np.isfinite(row.vol_ratio) else np.nan,
        })
        last[d]=i
    return pd.DataFrame(rows)


def run(data_path: str|Path, output_dir: str|Path):
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path)
    m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy()
    f=prep(m5)
    cache={c.name:setups(f,c) for c in CARDS}
    defs={
        "PORT_D1_CORE":["D1_DON10","D1_VOL_BREAK","D1_EMA20_PULLBACK"],
        "PORT_H4_CORE":["H4_DON10","H4_VOL_BREAK","H4_EMA20_PULLBACK"],
        "PORT_ALIGN_CORE":["D1_H4_DON10","D1_H4_VOL_BREAK","D1_H4_PULL20","D1_H4_RSI8_RECLAIM"],
        "PORT_D1_H4_MIX":["D1_DON10","H4_EMA20_PULLBACK","D1_H4_VOL_BREAK"],
        "PORT_HTF_MOMENTUM":["D1_ADX_DI","H4_ADX_DI","D1_H4_DON10"],
    }
    for name,members in defs.items():
        cache[name]=combine_setups([cache[m] for m in members],name)

    rows=[]; yrs=[]; months=[]; alltr=[]
    for name,ss in cache.items():
        tr=replay(m5,ss)
        if not tr.empty: alltr.append(tr.assign(strategy=name))
        ov=metrics(tr); ms=month_stats(tr); y=yearly(tr)
        rows.append({"strategy":name,**ov,**ms,
                     "positive_years":int((y.expectancy_r>0).sum()),
                     "pf_gt1_years":int((y.pf>1).sum()),
                     "worst_year_exp_r":float(y.expectancy_r.min()),
                     "worst_year_dd_pct":float(y.max_dd_pct.max())})
        for rr in y.itertuples(index=False): yrs.append({"strategy":name,**rr._asdict()})
        pp=pd.to_datetime(tr.entry_time,utc=True).dt.to_period("M") if not tr.empty else pd.Series([],dtype="period[M]")
        for p in pd.period_range("2017-01","2020-12",freq="M"):
            g=tr[pp==p] if not tr.empty else tr
            months.append({"strategy":name,"month":str(p),**metrics(g)})

    ranked=pd.DataFrame(rows).sort_values(
        ["positive_years","pf_gt1_years","min_month","avg_month","worst_year_exp_r","expectancy_r","pf","worst_year_dd_pct"],
        ascending=[False,False,False,False,False,False,False,True])
    yd=pd.DataFrame(yrs); md=pd.DataFrame(months); td=pd.concat(alltr,ignore_index=True) if alltr else pd.DataFrame()
    ranked.to_csv(out/"ranked.csv",index=False); yd.to_csv(out/"yearly.csv",index=False)
    md.to_csv(out/"monthly.csv",index=False); td.to_csv(out/"trades.csv",index=False)

    lines=["# Historical-First Phase 3 — H4/D1 regime, M15 execution","",
           "Development only: 2017-2020. No 2021+ inspection.",
           "RR3, RM100, 5% risk, 1bp cost, conservative same-bar stop-first.","",
           "| Strategy | Trades | Avg/mo | Min/mo | >=8 | Pos years | WR | ExpR | PF | Worst ExpR | Worst DD | End RM |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in ranked.itertuples(index=False):
        pf="∞" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(f"| {r.strategy} | {r.trades} | {r.avg_month:.2f} | {r.min_month} | {r.months_ge8}/48 | {r.positive_years}/4 | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.worst_year_exp_r:+.3f} | {r.worst_year_dd_pct:.2f}% | RM{r.end_rm:.2f} |")
    for strategy in ranked.head(10).strategy:
        lines+=["",f"## {strategy}","","| Year | Trades | WR | ExpR | PF | DD | RM100 → |","|---|---:|---:|---:|---:|---:|---:|"]
        for r in yd[yd.strategy==strategy].itertuples(index=False):
            pf="∞" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
            lines.append(f"| {r.year} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.max_dd_pct:.2f}% | RM{r.end_rm:.2f} |")
    report="\n".join(lines)+"\n"; (out/"REPORT.md").write_text(report)
    (out/"summary.json").write_text(json.dumps({"window":"2017-2020","top":ranked.head(10).replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")},indent=2))
    print(report)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output",default="reports/historical-first-htf"); a=p.parse_args(); run(a.data,a.output)
if __name__=="__main__": main()
