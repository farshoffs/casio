from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import (
    DEV_END, atr, di_adx, resample, align_completed,
    replay, metrics, month_stats, yearly,
)


@dataclass(frozen=True)
class Card:
    name: str
    bias: str
    lookback: int
    adx_min: float
    body_min: float
    vol_min: float = 0.0
    cooldown: int = 2


CARDS = (
    Card("STRICT_ALIGN_DON8", "strict", 8, 16, 0.25),
    Card("STRICT_ALIGN_DON10", "strict", 10, 16, 0.30),
    Card("SOFT_ALIGN_DON8", "soft", 8, 16, 0.25),
    Card("SOFT_ALIGN_DON10", "soft", 10, 16, 0.30),
    Card("ONE_SLOPE_DON8", "one_slope", 8, 16, 0.25),
    Card("ONE_SLOPE_DON10", "one_slope", 10, 16, 0.30),
    Card("D1_DOMINANT_DON8", "d1_dom", 8, 17, 0.30),
    Card("D1_DOMINANT_DON10", "d1_dom", 10, 17, 0.30),
    Card("SOFT_ALIGN_VOL10", "soft", 10, 17, 0.35, 1.10),
    Card("ONE_SLOPE_VOL10", "one_slope", 10, 17, 0.35, 1.10),
)


def prep(m5):
    f=resample(m5,"15min")
    f["atr14"]=atr(f,14)
    pdi,mdi,adx=di_adx(f,14)
    f["pdi"],f["mdi"],f["adx"]=pdi,mdi,adx
    f["body_atr"]=(f.close-f.open).abs()/f.atr14.replace(0,np.nan)
    f["vol_med20"]=f.volume.rolling(20,min_periods=10).median()
    f["vol_ratio"]=f.volume/f.vol_med20.replace(0,np.nan)
    h4=resample(m5,"4h"); d1=resample(m5,"1D")
    for x in (h4,d1):
        x["ema20"]=x.close.ewm(span=20,adjust=False).mean()
        x["ema50"]=x.close.ewm(span=50,adjust=False).mean()
        x["slope20"]=x.ema20.diff(3)
        x["atr14"]=atr(x,14)
        x["sep_atr"]=(x.ema20-x.ema50).abs()/x.atr14.replace(0,np.nan)
    ct=f.index+pd.Timedelta(minutes=15)
    for p,x,period in [("h4",h4,pd.Timedelta(hours=4)),("d1",d1,pd.Timedelta(days=1))]:
        for col in ["ema20","ema50","slope20","sep_atr"]:
            f[f"{p}_{col}"]=align_completed(x[col],ct,period).to_numpy()
    return f


def bias(f,b):
    d1_up=f.d1_ema20>f.d1_ema50; d1_dn=f.d1_ema20<f.d1_ema50
    h4_up=f.h4_ema20>f.h4_ema50; h4_dn=f.h4_ema20<f.h4_ema50
    d1_su=f.d1_slope20>0; d1_sd=f.d1_slope20<0
    h4_su=f.h4_slope20>0; h4_sd=f.h4_slope20<0
    if b=="strict":
        return d1_up&h4_up&d1_su&h4_su, d1_dn&h4_dn&d1_sd&h4_sd
    if b=="soft":
        return d1_up&h4_up, d1_dn&h4_dn
    if b=="one_slope":
        return d1_up&h4_up&(d1_su|h4_su), d1_dn&h4_dn&(d1_sd|h4_sd)
    if b=="d1_dom":
        return d1_up&d1_su&(~h4_dn), d1_dn&d1_sd&(~h4_up)
    raise ValueError(b)


def setups(f,c):
    up,dn=bias(f,c.bias)
    ph=f.high.shift(1).rolling(c.lookback).max()
    pl=f.low.shift(1).rolling(c.lookback).min()
    vol=(f.vol_ratio>=c.vol_min) if c.vol_min>0 else pd.Series(True,index=f.index)
    lo=up&vol&(f.close>ph)&(f.adx>=c.adx_min)&(f.body_atr>=c.body_min)
    sh=dn&vol&(f.close<pl)&(f.adx>=c.adx_min)&(f.body_atr>=c.body_min)
    rows=[]; last={1:-10**9,-1:-10**9}
    for i in np.flatnonzero((lo.fillna(False)|sh.fillna(False)).to_numpy()):
        d=1 if bool(lo.iat[i]) else -1
        if i-last[d]<c.cooldown: continue
        row=f.iloc[i]; a=float(row.atr14)
        if not np.isfinite(a) or a<=0: continue
        recent=f.iloc[max(0,i-5):i+1]
        stop=float(recent.low.min()-0.08*a) if d==1 else float(recent.high.max()+0.08*a)
        rows.append({"card":c.name,"signal_i":i,"signal_time":f.index[i],
                     "signal_close_time":f.index[i]+pd.Timedelta(minutes=15),
                     "direction":d,"stop":stop,"atr14":a,"adx":float(row.adx),
                     "vol_ratio":float(row.vol_ratio) if np.isfinite(row.vol_ratio) else np.nan})
        last[d]=i
    return pd.DataFrame(rows)


def run(data_path,output_dir):
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path); m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy()
    f=prep(m5)
    rows=[]; yrs=[]; months=[]; alltr=[]
    for c in CARDS:
        tr=replay(m5,setups(f,c))
        if not tr.empty: alltr.append(tr.assign(strategy=c.name))
        ov=metrics(tr); ms=month_stats(tr); y=yearly(tr)
        rows.append({"strategy":c.name,**ov,**ms,"positive_years":int((y.expectancy_r>0).sum()),
                     "pf_gt1_years":int((y.pf>1).sum()),"worst_year_exp_r":float(y.expectancy_r.min()),
                     "worst_year_dd_pct":float(y.max_dd_pct.max())})
        for rr in y.itertuples(index=False): yrs.append({"strategy":c.name,**rr._asdict()})
        pp=pd.to_datetime(tr.entry_time,utc=True).dt.to_period("M") if not tr.empty else pd.Series([],dtype="period[M]")
        for p in pd.period_range("2017-01","2020-12",freq="M"):
            g=tr[pp==p] if not tr.empty else tr
            months.append({"strategy":c.name,"month":str(p),**metrics(g)})
    ranked=pd.DataFrame(rows).sort_values(
        ["positive_years","pf_gt1_years","min_month","avg_month","worst_year_exp_r","expectancy_r","pf","worst_year_dd_pct"],
        ascending=[False,False,False,False,False,False,False,True])
    yd=pd.DataFrame(yrs); md=pd.DataFrame(months); td=pd.concat(alltr,ignore_index=True) if alltr else pd.DataFrame()
    ranked.to_csv(out/"ranked.csv",index=False); yd.to_csv(out/"yearly.csv",index=False); md.to_csv(out/"monthly.csv",index=False); td.to_csv(out/"trades.csv",index=False)
    lines=["# Historical-First Phase 5 — bias gate sweep","",
           "2017-2020 only. Forward years still sealed.",
           "RR3, RM100, 5% risk, 1bp cost.","",
           "| Strategy | Trades | Avg/mo | Min/mo | >=8 | Pos years | WR | ExpR | PF | Worst ExpR | Worst DD | End RM |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in ranked.itertuples(index=False):
        pf="∞" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(f"| {r.strategy} | {r.trades} | {r.avg_month:.2f} | {r.min_month} | {r.months_ge8}/48 | {r.positive_years}/4 | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.worst_year_exp_r:+.3f} | {r.worst_year_dd_pct:.2f}% | RM{r.end_rm:.2f} |")
    for strategy in ranked.head(8).strategy:
        lines+=["",f"## {strategy}","","| Year | Trades | WR | ExpR | PF | DD | RM100 → |","|---|---:|---:|---:|---:|---:|---:|"]
        for r in yd[yd.strategy==strategy].itertuples(index=False):
            pf="∞" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
            lines.append(f"| {r.year} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.max_dd_pct:.2f}% | RM{r.end_rm:.2f} |")
    report="\n".join(lines)+"\n"; (out/"REPORT.md").write_text(report)
    (out/"summary.json").write_text(json.dumps({"window":"2017-2020","top":ranked.head(8).replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")},indent=2))
    print(report)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output",default="reports/historical-first-bias"); a=p.parse_args(); run(a.data,a.output)
if __name__=="__main__": main()
