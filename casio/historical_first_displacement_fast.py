from __future__ import annotations
from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import DEV_END, metrics, month_stats, yearly
from .historical_first_displacement_retrace import prep, replay_pending

def build_fast(f, family, session, da, bf, rt, wait, lb):
    up=f.h4d1_up.fillna(False); dn=f.h4d1_dn.fillna(False)
    if session=="PRIMARY":
        m=f.mins
        ss=pd.Series(((m>=7*60)&(m<11*60))|((m>=12*60+30)&(m<16*60+30)),index=f.index)
    else:
        ss=pd.Series(True,index=f.index)

    disp_bull=(f.close>f.open)&(f.body_atr>=da)&(f.body_frac>=bf)&(f.close_pos>=0.75)
    disp_bear=(f.close<f.open)&(f.body_atr>=da)&(f.body_frac>=bf)&(f.close_pos<=0.25)

    if family=="fvg_ce":
        pb=(f.close.shift(1)>f.open.shift(1))&(f.body_atr.shift(1)>=da)&(f.body_frac.shift(1)>=bf)
        ps=(f.close.shift(1)<f.open.shift(1))&(f.body_atr.shift(1)>=da)&(f.body_frac.shift(1)>=bf)
        lo=up&ss&f.bull_fvg&pb
        sh=dn&ss&f.bear_fvg&ps
        entry_long=(f.bull_fvg_lo+f.bull_fvg_hi)/2
        entry_short=(f.bear_fvg_lo+f.bear_fvg_hi)/2
        stop_long=pd.concat([f.low.shift(2),f.low.shift(1),f.low],axis=1).min(axis=1)-0.04*f.atr14
        stop_short=pd.concat([f.high.shift(2),f.high.shift(1),f.high],axis=1).max(axis=1)+0.04*f.atr14
    elif family=="sweep_displacement":
        ph=f[f"ph{lb}"]; pl=f[f"pl{lb}"]
        lo=up&ss&(f.low<pl)&(f.close>pl)&disp_bull
        sh=dn&ss&(f.high>ph)&(f.close<ph)&disp_bear
        entry_long=f.close-rt*(f.close-f.open)
        entry_short=f.close+rt*(f.open-f.close)
        stop_long=f.low-0.04*f.atr14
        stop_short=f.high+0.04*f.atr14
    else:
        raise ValueError(family)

    idxs=np.flatnonzero((lo.fillna(False)|sh.fillna(False)).to_numpy())
    rows=[]
    for i in idxs:
        d=1 if bool(lo.iat[i]) else -1
        entry=float(entry_long.iat[i] if d==1 else entry_short.iat[i])
        stop=float(stop_long.iat[i] if d==1 else stop_short.iat[i])
        a=float(f.atr14.iat[i])
        if not np.isfinite(entry) or not np.isfinite(stop) or not np.isfinite(a) or a<=0:
            continue
        risk=(entry-stop) if d==1 else (stop-entry)
        if risk<=0 or risk/a<0.15 or risk/a>2.5:
            continue
        rows.append({"card":f"FAST__{family}__{session}__D{da}__B{bf}__R{rt}__W{wait}__L{lb}",
                     "family":family,"signal_time":f.index[i],"available_time":f.index[i]+pd.Timedelta(minutes=15),
                     "direction":d,"entry_limit":entry,"stop":stop,"atr14":a,"risk_atr":risk/a,"wait_min":wait})
    return pd.DataFrame(rows)

def run(data_path,output_dir):
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path)
    m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy()
    f=prep(m5)
    rows=[]; yrs=[]; alltr=[]
    specs=[]
    for fam in ["fvg_ce","sweep_displacement"]:
      for session in ["PRIMARY","ALL"]:
       for da in [0.9,1.2]:
        for bf in [0.70,0.82]:
         for rt in [0.50,0.705]:
          for wait in [30,90]:
           for lb in ([8,20] if fam=="sweep_displacement" else [12]):
            specs.append((fam,session,da,bf,rt,wait,lb))
    for fam,session,da,bf,rt,wait,lb in specs:
        ss=build_fast(f,fam,session,da,bf,rt,wait,lb)
        tr=replay_pending(m5,ss)
        name=f"FAST__{fam}__{session}__D{da}__B{bf}__R{rt}__W{wait}__L{lb}"
        if not tr.empty: alltr.append(tr.assign(strategy=name))
        ov=metrics(tr); ms=month_stats(tr); y=yearly(tr)
        rows.append({"strategy":name,"family":fam,"session":session,"disp_atr":da,"body_frac":bf,"retrace":rt,
                     "wait_min":wait,"lookback":lb,"trades":ov["trades"],"wr":ov["wr"],"expectancy_r":ov["expectancy_r"],
                     "pf":ov["pf"],"dd":ov["max_dd_pct"],"end_rm":ov["end_rm"],**ms,
                     "positive_years":int((y.expectancy_r>0).sum()),"pf_years":int((y.pf>1).sum()),
                     "worst_year_exp":float(y.expectancy_r.min()),"worst_year_dd":float(y.max_dd_pct.max())})
        for rr in y.itertuples(index=False): yrs.append({"strategy":name,**rr._asdict()})
    rd=pd.DataFrame(rows)
    rd["strict"]=(rd.wr>=60)&(rd.dd<=25)&(rd.min_month>=8)&(rd.positive_years.eq(4))&(rd.pf_years.eq(4))
    rd["dist"]=np.maximum(0,60-rd.wr)*3+np.maximum(0,rd.dd-25)+np.maximum(0,8-rd.min_month)*5+(4-rd.positive_years)*20
    ranked=rd.sort_values(["strict","dist","positive_years","min_month","wr","expectancy_r"],ascending=[False,True,False,False,False,False])
    yd=pd.DataFrame(yrs)
    ranked.to_csv(out/"ranked.csv",index=False); yd.to_csv(out/"yearly.csv",index=False)
    if alltr: pd.concat(alltr,ignore_index=True).to_csv(out/"trades.csv",index=False)
    strict=ranked[ranked.strict]
    lines=["# Fast Displacement/FVG Shortlist — 2017-2020","",
           "Same rules as pending-entry research; vectorized setup detection only.",
           "Hard target: RR3, WR>=60%, DD<=25%, min8 every month, 4/4 profitable years.","",
           f"Specs: {len(specs)}; strict passes: {len(strict)}.","",
           "| Strategy | Trades | WR | ExpR | PF | DD | Avg/mo | Min/mo | Years |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in ranked.head(25).itertuples(index=False):
        pf="inf" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(f"| {r.strategy} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.dd:.2f}% | {r.avg_month:.2f} | {r.min_month} | {r.positive_years}/4 |")
    report="\n".join(lines)+"\n"; (out/"REPORT.md").write_text(report)
    (out/"summary.json").write_text(json.dumps({"strict_count":int(len(strict)),
      "strict":strict.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records"),
      "closest":ranked.head(25).replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")},indent=2))
    print(report)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output",default="reports/historical-first-displacement-fast")
    a=p.parse_args(); run(a.data,a.output)
if __name__=="__main__": main()
