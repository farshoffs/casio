from __future__ import annotations
from pathlib import Path
import argparse,json,math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import DEV_END,metrics,month_stats,yearly
from .historical_first_ny_strict import prep,replay

def rows_for(f,name,fam,bias,window,entry_mode,adx,vol,depth,wait):
    win=f[window].fillna(False)
    if bias=="h4d1":
        up=f.h4d1_up.fillna(False);dn=f.h4d1_dn.fillna(False)
    elif bias=="triple":
        up=f.triple_up.fillna(False);dn=f.triple_dn.fillna(False)
    elif bias=="h4":
        up=f.h4_up.fillna(False);dn=f.h4_dn.fillna(False)
    else:
        up=pd.Series(True,index=f.index);dn=pd.Series(True,index=f.index)

    bull=f.close>f.open;bear=f.close<f.open
    strong_bull=bull&(f.body_atr>=0.55)&(f.body_frac>=0.65)
    strong_bear=bear&(f.body_atr>=0.55)&(f.body_frac>=0.65)
    volok=f.vol_ratio>=vol

    if fam=="IMPULSE12":
        lo=win&up&volok&(f.adx>=adx)&strong_bull&(f.close>f.ph12)
        sh=win&dn&volok&(f.adx>=adx)&strong_bear&(f.close<f.pl12)
    elif fam=="EMA20":
        lo=win&up&volok&(f.adx>=adx)&bull&(f.low<=f.ema20)&(f.close>f.ema20)&(f.pdi>f.mdi)
        sh=win&dn&volok&(f.adx>=adx)&bear&(f.high>=f.ema20)&(f.close<f.ema20)&(f.mdi>f.pdi)
    elif fam=="VWAP":
        lo=win&up&volok&(f.adx>=adx)&bull&(f.low<=f.ny_vwap)&(f.close>f.ny_vwap)&(f.pdi>f.mdi)
        sh=win&dn&volok&(f.adx>=adx)&bear&(f.high>=f.ny_vwap)&(f.close<f.ny_vwap)&(f.mdi>f.pdi)
    elif fam=="ON_SWEEP":
        lo=win&volok&bull&(f.low<f.on_l)&(f.close>f.on_l)&(f.lwb>=1.2)
        sh=win&volok&bear&(f.high>f.on_h)&(f.close<f.on_h)&(f.uwb>=1.2)
        if bias!="none":
            lo&=up;sh&=dn
    elif fam=="OR_RETEST":
        eligible=f.ny_min>=10*60
        lo=win&eligible&up&volok&bull&(f.close.shift(1)>f.or_h.shift(1))&(f.low<=f.or_h)&(f.close>f.or_h)
        sh=win&eligible&dn&volok&bear&(f.close.shift(1)<f.or_l.shift(1))&(f.high>=f.or_l)&(f.close<f.or_l)
    elif fam=="ON_RETEST":
        eligible=f.ny_min>=8*60+30
        lo=win&eligible&up&volok&bull&(f.close.shift(1)>f.on_h.shift(1))&(f.low<=f.on_h)&(f.close>f.on_h)
        sh=win&eligible&dn&volok&bear&(f.close.shift(1)<f.on_l.shift(1))&(f.high>=f.on_l)&(f.close<f.on_l)
    elif fam=="RSI2":
        lo=win&up&volok&bull&(f.rsi2.shift(1)<=8)&(f.rsi2>=25)&(f.close>f.ema20)
        sh=win&dn&volok&bear&(f.rsi2.shift(1)>=92)&(f.rsi2<=75)&(f.close<f.ema20)
    else: raise ValueError(fam)

    out=[]
    for i in np.flatnonzero((lo.fillna(False)|sh.fillna(False)).to_numpy()):
        r=f.iloc[i];d=1 if bool(lo.iat[i]) else -1;a=float(r.atr14)
        if not np.isfinite(a) or a<=0:continue
        if entry_mode=="market":
            ent=np.nan
        elif entry_mode=="half":
            ent=float((r.high+r.low)/2)
        else:
            ent=float(r.high-depth*(r.high-r.low)) if d==1 else float(r.low+depth*(r.high-r.low))
        stop=float(r.low-0.04*a) if d==1 else float(r.high+0.04*a)
        out.append({"signal_time":f.index[i],"available":f.index[i]+pd.Timedelta(minutes=5),
                    "ny_date":r.ny_date,"direction":d,"entry_limit":ent,"stop":stop,"atr":a,"wait_min":wait})
    return pd.DataFrame(out)

def specs():
    out=[]
    for fam in ["IMPULSE12","EMA20","VWAP","ON_SWEEP","OR_RETEST","ON_RETEST","RSI2"]:
      biases=["none","h4","h4d1"] if fam=="ON_SWEEP" else ["h4","h4d1","triple"]
      for b in biases:
       for w in ["NY_FULL","NY_CORE"]:
        for ent,depth in [("market",0),("half",0.5),("deep",0.705),("deep",0.886),("deep",0.90)]:
         for adx in [18,26]:
          for vol in [0.8,1.15]:
           name=f"NYFAST__{fam}__{b}__{w}__{ent}{depth}__A{adx}__V{vol}"
           out.append((name,fam,b,w,ent,adx,vol,depth,30))
    return out

def run(data_path,output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path);m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy()
    f=prep(m5);sp=specs();rows=[];yrs=[];alltr=[]
    for name,fam,b,w,e,a,v,d,wait in sp:
        tr=replay(m5,rows_for(f,name,fam,b,w,e,a,v,d,wait),name)
        if not tr.empty:alltr.append(tr)
        ov=metrics(tr);ms=month_stats(tr);y=yearly(tr)
        rows.append({"strategy":name,"family":fam,"bias":b,"window":w,"entry":e,"depth":d,"adx":a,"vol":v,
                     "trades":ov["trades"],"wr":ov["wr"],"expectancy_r":ov["expectancy_r"],"pf":ov["pf"],
                     "dd":ov["max_dd_pct"],"end_rm":ov["end_rm"],**ms,
                     "positive_years":int((y.expectancy_r>0).sum()),"pf_years":int((y.pf>1).sum()),
                     "worst_year_exp":float(y.expectancy_r.min()),"worst_year_dd":float(y.max_dd_pct.max())})
        for rr in y.itertuples(index=False):yrs.append({"strategy":name,**rr._asdict()})
    rd=pd.DataFrame(rows)
    rd["strict"]=(rd.wr>=60)&(rd.dd<=25)&(rd.min_month>=8)&(rd.positive_years.eq(4))&(rd.pf_years.eq(4))
    rd["dist"]=np.maximum(0,60-rd.wr)*3+np.maximum(0,rd.dd-25)+np.maximum(0,8-rd.min_month)*6+(4-rd.positive_years)*25
    ranked=rd.sort_values(["strict","dist","positive_years","min_month","wr","expectancy_r"],ascending=[False,True,False,False,False,False])
    yd=pd.DataFrame(yrs);ranked.to_csv(out/"ranked.csv",index=False);yd.to_csv(out/"yearly.csv",index=False)
    if alltr:pd.concat(alltr,ignore_index=True).to_csv(out/"trades.csv",index=False)
    strict=ranked[ranked.strict]
    lines=["# Focused DST-Aware New York Search — 2017-2020","",
           "America/New_York session only; one entry max per NY date. Fixed RR3, RM100, 5% risk, real stop, 1bp cost, same-bar stop-first.",
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
    p.add_argument("--output",default="reports/historical-first-ny-fast");a=p.parse_args();run(a.data,a.output)
if __name__=="__main__":main()
