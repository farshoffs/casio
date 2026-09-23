from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import (
    DEV_END, atr, di_adx, resample, align_completed,
    replay, combine_setups, metrics, month_stats, yearly,
)


@dataclass(frozen=True)
class Card:
    name: str
    tf: str
    minutes: int
    lookback: int
    vol_min: float
    adx_min: float
    body_min: float
    session: str = "ALL"
    cooldown: int = 2


CARDS = (
    Card("M15_DON5_ALIGN", "15min", 15, 5, 0.0, 16, 0.25),
    Card("M15_DON8_ALIGN", "15min", 15, 8, 0.0, 16, 0.25),
    Card("M15_DON10_ALIGN", "15min", 15, 10, 0.0, 16, 0.30),
    Card("M15_DON12_ALIGN", "15min", 15, 12, 0.0, 17, 0.30),
    Card("M15_DON20_ALIGN", "15min", 15, 20, 0.0, 18, 0.35),
    Card("M5_DON20_ALIGN", "5min", 5, 20, 0.0, 18, 0.40, "PRIMARY", 3),
    Card("M5_DON30_ALIGN", "5min", 5, 30, 0.0, 18, 0.40, "PRIMARY", 3),
    Card("M5_VOL20_ALIGN", "5min", 5, 20, 1.20, 18, 0.45, "PRIMARY", 3),
    Card("M5_VOL30_ALIGN", "5min", 5, 30, 1.25, 18, 0.45, "PRIMARY", 3),
)


def session_mask(index: pd.DatetimeIndex) -> np.ndarray:
    mins = index.hour * 60 + index.minute
    london = (mins >= 7*60) & (mins < 11*60)
    ny = (mins >= 12*60+30) & (mins < 16*60+30)
    return london | ny


def add_htf_bias(m5: pd.DataFrame, x: pd.DataFrame, minutes: int) -> pd.DataFrame:
    h4 = resample(m5, "4h")
    d1 = resample(m5, "1D")
    for h in (h4,d1):
        h["ema20"] = h.close.ewm(span=20,adjust=False).mean()
        h["ema50"] = h.close.ewm(span=50,adjust=False).mean()
        h["slope20"] = h.ema20.diff(3)
    close_times=x.index+pd.Timedelta(minutes=minutes)
    for p,h,period in [("h4",h4,pd.Timedelta(hours=4)),("d1",d1,pd.Timedelta(days=1))]:
        for col in ["ema20","ema50","slope20"]:
            x[f"{p}_{col}"]=align_completed(h[col],close_times,period).to_numpy()
    x["align_up"]=(x.d1_ema20>x.d1_ema50)&(x.d1_slope20>0)&(x.h4_ema20>x.h4_ema50)&(x.h4_slope20>0)
    x["align_down"]=(x.d1_ema20<x.d1_ema50)&(x.d1_slope20<0)&(x.h4_ema20<x.h4_ema50)&(x.h4_slope20<0)
    return x


def frame(m5: pd.DataFrame, card: Card) -> pd.DataFrame:
    x = m5[["open","high","low","close","volume"]].copy() if card.tf=="5min" else resample(m5,card.tf)
    x["atr14"]=atr(x,14)
    pdi,mdi,adx=di_adx(x,14)
    x["pdi"],x["mdi"],x["adx"]=pdi,mdi,adx
    x["body_atr"]=(x.close-x.open).abs()/x.atr14.replace(0,np.nan)
    x["prev_high"]=x.high.shift(1).rolling(card.lookback).max()
    x["prev_low"]=x.low.shift(1).rolling(card.lookback).min()
    x["vol_med20"]=x.volume.rolling(20,min_periods=10).median()
    x["vol_ratio"]=x.volume/x.vol_med20.replace(0,np.nan)
    return add_htf_bias(m5,x,card.minutes)


def setups(m5: pd.DataFrame, card: Card) -> pd.DataFrame:
    f=frame(m5,card)
    sm=pd.Series(session_mask(f.index),index=f.index) if card.session=="PRIMARY" else pd.Series(True,index=f.index)
    vol_ok=(f.vol_ratio>=card.vol_min) if card.vol_min>0 else pd.Series(True,index=f.index)
    lo=f.align_up & sm & vol_ok & (f.close>f.prev_high) & (f.adx>=card.adx_min) & (f.body_atr>=card.body_min)
    sh=f.align_down & sm & vol_ok & (f.close<f.prev_low) & (f.adx>=card.adx_min) & (f.body_atr>=card.body_min)
    rows=[]; last={1:-10**9,-1:-10**9}
    for i in np.flatnonzero((lo.fillna(False)|sh.fillna(False)).to_numpy()):
        d=1 if bool(lo.iat[i]) else -1
        if i-last[d] < card.cooldown: continue
        row=f.iloc[i]; a=float(row.atr14)
        if not np.isfinite(a) or a<=0: continue
        lb=max(0,i-(8 if card.tf=="5min" else 6)+1)
        recent=f.iloc[lb:i+1]
        stop=float(recent.low.min()-0.08*a) if d==1 else float(recent.high.max()+0.08*a)
        rows.append({"card":card.name,"signal_i":i,"signal_time":f.index[i],
                     "signal_close_time":f.index[i]+pd.Timedelta(minutes=card.minutes),
                     "direction":d,"stop":stop,"atr14":a,
                     "adx":float(row.adx),"vol_ratio":float(row.vol_ratio) if np.isfinite(row.vol_ratio) else np.nan})
        last[d]=i
    return pd.DataFrame(rows)


def run(data_path,output_dir):
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path)
    m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy()
    cache={c.name:setups(m5,c) for c in CARDS}
    defs={
        "PORT_M15_5_10":["M15_DON5_ALIGN","M15_DON10_ALIGN"],
        "PORT_M15_8_12":["M15_DON8_ALIGN","M15_DON12_ALIGN"],
        "PORT_M15_MULTI":["M15_DON5_ALIGN","M15_DON8_ALIGN","M15_DON10_ALIGN","M15_DON12_ALIGN"],
        "PORT_M15_M5_20":["M15_DON10_ALIGN","M5_DON20_ALIGN"],
        "PORT_M15_M5_30":["M15_DON10_ALIGN","M5_DON30_ALIGN"],
        "PORT_M15_M5_VOL":["M15_DON10_ALIGN","M5_VOL20_ALIGN","M5_VOL30_ALIGN"],
        "PORT_ALIGN_FREQUENCY":["M15_DON5_ALIGN","M15_DON10_ALIGN","M5_DON20_ALIGN","M5_VOL30_ALIGN"],
    }
    for name,members in defs.items(): cache[name]=combine_setups([cache[m] for m in members],name)

    rows=[]; yrs=[]; months=[]; alltr=[]
    for name,ss in cache.items():
        tr=replay(m5,ss)
        if not tr.empty: alltr.append(tr.assign(strategy=name))
        ov=metrics(tr); ms=month_stats(tr); y=yearly(tr)
        rows.append({"strategy":name,**ov,**ms,"positive_years":int((y.expectancy_r>0).sum()),
                     "pf_gt1_years":int((y.pf>1).sum()),"worst_year_exp_r":float(y.expectancy_r.min()),
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
    ranked.to_csv(out/"ranked.csv",index=False); yd.to_csv(out/"yearly.csv",index=False); md.to_csv(out/"monthly.csv",index=False); td.to_csv(out/"trades.csv",index=False)

    lines=["# Historical-First Phase 4 — D1/H4 aligned frequency expansion","",
           "2017-2020 development only. No forward years inspected.",
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
    p.add_argument("--output",default="reports/historical-first-frequency"); a=p.parse_args(); run(a.data,a.output)
if __name__=="__main__": main()
