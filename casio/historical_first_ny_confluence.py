from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import argparse,json,math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import DEV_END,metrics,month_stats,yearly
from .historical_first_ny_strict import prep,replay

START=pd.Timestamp("2017-01-01",tz="UTC")

@dataclass(frozen=True)
class Spec:
    name:str
    trigger:str
    bias:str
    window:str
    score_min:int
    adx_min:float
    vol_min:float
    entry_mode:str
    wait_min:int=30

def make_rows(f,s):
    win=f[s.window].fillna(False)
    if s.bias=="h4":
        ub=f.h4_up.fillna(False); db=f.h4_dn.fillna(False)
    elif s.bias=="h4d1":
        ub=f.h4d1_up.fillna(False); db=f.h4d1_dn.fillna(False)
    else:
        ub=pd.Series(True,index=f.index); db=pd.Series(True,index=f.index)

    after10=f.ny_min>=10*60
    or_mid=(f.or_h+f.or_l)/2

    # Causal confluence score known at completed M5 close.
    long_parts=[
        (f.ema8>f.ema20)&(f.ema20>f.ema50),
        f.close>f.ny_vwap,
        f.pdi>f.mdi,
        f.adx>=s.adx_min,
        f.vol_ratio>=s.vol_min,
        (~after10)|(f.close>or_mid),
        f.h1_up.fillna(False),
    ]
    short_parts=[
        (f.ema8<f.ema20)&(f.ema20<f.ema50),
        f.close<f.ny_vwap,
        f.mdi>f.pdi,
        f.adx>=s.adx_min,
        f.vol_ratio>=s.vol_min,
        (~after10)|(f.close<or_mid),
        f.h1_dn.fillna(False),
    ]
    ls=sum(x.astype(int) for x in long_parts)
    ss=sum(x.astype(int) for x in short_parts)
    bull=f.close>f.open; bear=f.close<f.open

    if s.trigger=="ema20_touch":
        lt=bull&(f.low<=f.ema20)&(f.close>f.ema20)
        st=bear&(f.high>=f.ema20)&(f.close<f.ema20)
    elif s.trigger=="vwap_touch":
        lt=bull&(f.low<=f.ny_vwap)&(f.close>f.ny_vwap)
        st=bear&(f.high>=f.ny_vwap)&(f.close<f.ny_vwap)
    elif s.trigger=="rsi2_reclaim":
        lt=bull&(f.rsi2.shift(1)<=10)&(f.rsi2>=25)
        st=bear&(f.rsi2.shift(1)>=90)&(f.rsi2<=75)
    elif s.trigger=="or_retest":
        lt=after10&bull&(f.low<=f.or_h)&(f.close>f.or_h)&(f.close.shift(1)>f.or_h.shift(1))
        st=after10&bear&(f.high>=f.or_l)&(f.close<f.or_l)&(f.close.shift(1)<f.or_l.shift(1))
    elif s.trigger=="on_retest":
        eligible=f.ny_min>=8*60+30
        lt=eligible&bull&(f.low<=f.on_h)&(f.close>f.on_h)&(f.close.shift(1)>f.on_h.shift(1))
        st=eligible&bear&(f.high>=f.on_l)&(f.close<f.on_l)&(f.close.shift(1)<f.on_l.shift(1))
    elif s.trigger=="break12":
        lt=bull&(f.close>f.ph12)
        st=bear&(f.close<f.pl12)
    else: raise ValueError(s.trigger)

    lo=(win&ub&lt&(ls>=s.score_min)).fillna(False)
    sh=(win&db&st&(ss>=s.score_min)).fillna(False)
    rows=[]
    for i in np.flatnonzero((lo|sh).to_numpy()):
        r=f.iloc[i]; d=1 if bool(lo.iat[i]) else -1
        a=float(r.atr14)
        if not np.isfinite(a) or a<=0: continue
        if s.entry_mode=="market":
            ent=np.nan
        elif s.entry_mode=="half":
            ent=float((r.open+r.close)/2)
        else:
            ent=float(r.high-0.705*(r.high-r.low)) if d==1 else float(r.low+0.705*(r.high-r.low))
        stop=float(r.low-0.04*a) if d==1 else float(r.high+0.04*a)
        rows.append({"signal_time":f.index[i],"available":f.index[i]+pd.Timedelta(minutes=5),
                     "ny_date":r.ny_date,"direction":d,"entry_limit":ent,"stop":stop,"atr":a,"wait_min":s.wait_min})
    return pd.DataFrame(rows)

def specs():
    out=[]
    for t in ["ema20_touch","vwap_touch","rsi2_reclaim","or_retest","on_retest","break12"]:
      for b in ["h4","h4d1"]:
       for w in ["NY_FULL","NY_CORE"]:
        for score in [4,5,6]:
         for adx in [14,20,26]:
          for vol in [0.8,1.0,1.2]:
           for e in ["market","half","deep705"]:
            name=f"NYCONF__{t}__{b}__{w}__S{score}__A{adx}__V{vol}__{e}"
            out.append(Spec(name,t,b,w,score,adx,vol,e,30))
    return out

def run(data_path,output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path)
    m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy()
    f=prep(m5);sp=specs()
    rows=[];yrs=[];alltr=[]
    for s in sp:
        tr=replay(m5,make_rows(f,s),s.name)
        if not tr.empty:alltr.append(tr)
        ov=metrics(tr);ms=month_stats(tr);y=yearly(tr)
        rows.append({"strategy":s.name,"trigger":s.trigger,"bias":s.bias,"window":s.window,"score_min":s.score_min,
                     "adx_min":s.adx_min,"vol_min":s.vol_min,"entry_mode":s.entry_mode,
                     "trades":ov["trades"],"wr":ov["wr"],"expectancy_r":ov["expectancy_r"],"pf":ov["pf"],
                     "dd":ov["max_dd_pct"],"end_rm":ov["end_rm"],**ms,
                     "positive_years":int((y.expectancy_r>0).sum()),"pf_years":int((y.pf>1).sum()),
                     "worst_year_exp":float(y.expectancy_r.min()),"worst_year_dd":float(y.max_dd_pct.max())})
        for rr in y.itertuples(index=False):yrs.append({"strategy":s.name,**rr._asdict()})
    rd=pd.DataFrame(rows)
    rd["strict"]=(rd.wr>=60)&(rd.dd<=25)&(rd.min_month>=8)&(rd.positive_years.eq(4))&(rd.pf_years.eq(4))
    rd["dist"]=np.maximum(0,60-rd.wr)*3+np.maximum(0,rd.dd-25)+np.maximum(0,8-rd.min_month)*6+(4-rd.positive_years)*25
    ranked=rd.sort_values(["strict","dist","positive_years","min_month","wr","expectancy_r"],ascending=[False,True,False,False,False,False])
    yd=pd.DataFrame(yrs);ranked.to_csv(out/"ranked.csv",index=False);yd.to_csv(out/"yearly.csv",index=False)
    if alltr:pd.concat(alltr,ignore_index=True).to_csv(out/"trades.csv",index=False)
    strict=ranked[ranked.strict]
    lines=["# DST-Aware New York Confluence Search — 2017-2020","",
           "Only America/New_York session windows. One entry max per NY date. Causal score: EMA stack, NY VWAP, DI, ADX, volume, OR location, H1 trend.",
           "Fixed 3R, real signal-wick SL, RM100, 5% risk, 1bp cost, same-bar stop-first. 2021+ sealed.","",
           f"Specs {len(sp)}; strict passes {len(strict)}.","",
           "| Strategy | Trades | WR | ExpR | PF | DD | Avg/mo | Min/mo | Years |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in ranked.head(35).itertuples(index=False):
        pf="inf" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(f"| {r.strategy} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.dd:.2f}% | {r.avg_month:.2f} | {r.min_month} | {r.positive_years}/4 |")
    for strategy in (strict.strategy.tolist() if len(strict) else ranked.head(8).strategy.tolist()):
        lines+=["",f"## {strategy}","","| Year | Trades | WR | ExpR | PF | DD | RM100 -> |","|---|---:|---:|---:|---:|---:|---:|"]
        for r in yd[yd.strategy==strategy].itertuples(index=False):
            pf="inf" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
            lines.append(f"| {r.year} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.max_dd_pct:.2f}% | RM{r.end_rm:.2f} |")
    report="\n".join(lines)+"\n";(out/"REPORT.md").write_text(report)
    (out/"summary.json").write_text(json.dumps({"specs":len(sp),"strict_count":int(len(strict)),
      "strict":strict.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records"),
      "closest":ranked.head(35).replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")},indent=2))
    print(report)

def main():
    p=argparse.ArgumentParser();p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output",default="reports/historical-first-ny-confluence");a=p.parse_args();run(a.data,a.output)
if __name__=="__main__":main()
