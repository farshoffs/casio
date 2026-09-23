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
    family: str
    bias: str
    vol_min: float = 0.0
    cooldown: int = 8


CARDS = (
    Card("ASIA_BREAK_RAW", "asia_break", "none", 0.0),
    Card("ASIA_BREAK_H4", "asia_break", "h4", 0.0),
    Card("ASIA_BREAK_ALIGN", "asia_break", "align", 0.0),
    Card("ASIA_BREAK_VOL_H4", "asia_break", "h4", 1.15),
    Card("ASIA_SWEEP_REV", "asia_sweep", "none", 1.10),
    Card("PD_BREAK_H4", "pd_break", "h4", 0.0),
    Card("PD_BREAK_ALIGN", "pd_break", "align", 0.0),
    Card("NY_OR_BREAK_RAW", "ny_or", "none", 0.0),
    Card("NY_OR_BREAK_H4", "ny_or", "h4", 0.0),
    Card("NY_OR_BREAK_ALIGN", "ny_or", "align", 0.0),
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
    ct=f.index+pd.Timedelta(minutes=15)
    for p,x,period in [("h4",h4,pd.Timedelta(hours=4)),("d1",d1,pd.Timedelta(days=1))]:
        for col in ["ema20","ema50","slope20"]:
            f[f"{p}_{col}"]=align_completed(x[col],ct,period).to_numpy()
    f["h4_up"]=(f.h4_ema20>f.h4_ema50)&(f.h4_slope20>0)
    f["h4_dn"]=(f.h4_ema20<f.h4_ema50)&(f.h4_slope20<0)
    f["d1_up"]=(f.d1_ema20>f.d1_ema50)&(f.d1_slope20>0)
    f["d1_dn"]=(f.d1_ema20<f.d1_ema50)&(f.d1_slope20<0)
    f["align_up"]=f.h4_up&f.d1_up
    f["align_dn"]=f.h4_dn&f.d1_dn

    # UTC-normalized daily/session reference levels.
    f["date"]=f.index.floor("D")
    mins=f.index.hour*60+f.index.minute
    asia=(mins>=0)&(mins<6*60)
    ny_or=(mins>=12*60+30)&(mins<13*60+30)
    daily=f.groupby("date").agg(day_high=("high","max"),day_low=("low","min"))
    prev=daily.shift(1)
    f["prev_day_high"]=f["date"].map(prev.day_high)
    f["prev_day_low"]=f["date"].map(prev.day_low)

    asia_stats=f.loc[asia].groupby("date").agg(asia_high=("high","max"),asia_low=("low","min"))
    f["asia_high"]=f["date"].map(asia_stats.asia_high)
    f["asia_low"]=f["date"].map(asia_stats.asia_low)

    ny_stats=f.loc[ny_or].groupby("date").agg(ny_high=("high","max"),ny_low=("low","min"))
    f["ny_high"]=f["date"].map(ny_stats.ny_high)
    f["ny_low"]=f["date"].map(ny_stats.ny_low)
    return f


def bias_ok(f,c):
    if c.bias=="none":
        return pd.Series(True,index=f.index),pd.Series(True,index=f.index)
    if c.bias=="h4":
        return f.h4_up.fillna(False),f.h4_dn.fillna(False)
    if c.bias=="align":
        return f.align_up.fillna(False),f.align_dn.fillna(False)
    raise ValueError(c.bias)


def signal_masks(f,c):
    mins=f.index.hour*60+f.index.minute
    long_bias,short_bias=bias_ok(f,c)
    vol=(f.vol_ratio>=c.vol_min) if c.vol_min>0 else pd.Series(True,index=f.index)

    if c.family=="asia_break":
        session=(mins>=7*60)&(mins<11*60)
        lo=session&long_bias&vol&(f.close>f.asia_high)&(f.close.shift(1)<=f.asia_high)&(f.body_atr>=0.25)
        sh=session&short_bias&vol&(f.close<f.asia_low)&(f.close.shift(1)>=f.asia_low)&(f.body_atr>=0.25)
    elif c.family=="asia_sweep":
        session=(mins>=7*60)&(mins<11*60)
        lo=session&vol&(f.low<f.asia_low)&(f.close>f.asia_low)&(f.close>f.open)
        sh=session&vol&(f.high>f.asia_high)&(f.close<f.asia_high)&(f.close<f.open)
    elif c.family=="pd_break":
        session=((mins>=7*60)&(mins<11*60))|((mins>=12*60+30)&(mins<16*60+30))
        lo=session&long_bias&vol&(f.close>f.prev_day_high)&(f.close.shift(1)<=f.prev_day_high)&(f.body_atr>=0.25)
        sh=session&short_bias&vol&(f.close<f.prev_day_low)&(f.close.shift(1)>=f.prev_day_low)&(f.body_atr>=0.25)
    elif c.family=="ny_or":
        session=(mins>=13*60+30)&(mins<16*60+30)
        lo=session&long_bias&vol&(f.close>f.ny_high)&(f.close.shift(1)<=f.ny_high)&(f.body_atr>=0.25)
        sh=session&short_bias&vol&(f.close<f.ny_low)&(f.close.shift(1)>=f.ny_low)&(f.body_atr>=0.25)
    else:
        raise ValueError(c.family)
    return lo.fillna(False),sh.fillna(False)


def setups(f,c):
    lo,sh=signal_masks(f,c)
    rows=[]; last={1:-10**9,-1:-10**9}
    for i in np.flatnonzero((lo|sh).to_numpy()):
        d=1 if bool(lo.iat[i]) else -1
        if i-last[d]<c.cooldown: continue
        row=f.iloc[i]; a=float(row.atr14)
        if not np.isfinite(a) or a<=0: continue
        recent=f.iloc[max(0,i-3):i+1]
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
    f=prep(m5); cache={c.name:setups(f,c) for c in CARDS}
    defs={
        "PORT_SESSION_RAW":["ASIA_BREAK_RAW","NY_OR_BREAK_RAW","PD_BREAK_H4"],
        "PORT_SESSION_H4":["ASIA_BREAK_H4","NY_OR_BREAK_H4","PD_BREAK_H4"],
        "PORT_SESSION_ALIGN":["ASIA_BREAK_ALIGN","NY_OR_BREAK_ALIGN","PD_BREAK_ALIGN"],
        "PORT_ASIA_PD":["ASIA_BREAK_H4","PD_BREAK_H4"],
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
    lines=["# Historical-First Phase 6 — Session breakout research","",
           "2017-2020 development only. RR3, RM100, 5% risk, 1bp cost.","",
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
    p.add_argument("--output",default="reports/historical-first-session"); a=p.parse_args(); run(a.data,a.output)
if __name__=="__main__": main()
