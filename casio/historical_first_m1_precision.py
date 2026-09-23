from __future__ import annotations
from pathlib import Path
import argparse,json,math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import atr,di_adx,resample,align_completed,metrics,month_stats,yearly

START=pd.Timestamp("2017-01-01",tz="UTC");END=pd.Timestamp("2021-01-01",tz="UTC")
RR=3.0;COST=1.0

def prep(m1):
    m15=resample(m1,"15min")
    m15["atr14"]=atr(m15,14)
    pdi,mdi,adx=di_adx(m15,14);m15["pdi"],m15["mdi"],m15["adx"]=pdi,mdi,adx
    m15["ema20"]=m15.close.ewm(span=20,adjust=False).mean()
    m15["ema50"]=m15.close.ewm(span=50,adjust=False).mean()
    m15["body"]=(m15.close-m15.open).abs();m15["range"]=m15.high-m15.low
    m15["body_atr"]=m15.body/m15.atr14.replace(0,np.nan)
    m15["body_frac"]=m15.body/m15.range.replace(0,np.nan)
    m15["ph8"]=m15.high.shift(1).rolling(8).max();m15["pl8"]=m15.low.shift(1).rolling(8).min()
    mins=m15.index.hour*60+m15.index.minute
    m15["primary"]=((mins>=7*60)&(mins<11*60))|((mins>=12*60+30)&(mins<16*60+30))
    h4=resample(m1,"4h");d1=resample(m1,"1D")
    for x in (h4,d1):
        x["ema20"]=x.close.ewm(span=20,adjust=False).mean();x["ema50"]=x.close.ewm(span=50,adjust=False).mean()
        x["s20"]=x.ema20.diff(3)
    ct=m15.index+pd.Timedelta(minutes=15)
    for p,x,period in [("h4",h4,pd.Timedelta(hours=4)),("d1",d1,pd.Timedelta(days=1))]:
        for col in ["ema20","ema50","s20"]:m15[f"{p}_{col}"]=align_completed(x[col],ct,period).to_numpy()
        m15[f"{p}_up"]=(m15[f"{p}_ema20"]>m15[f"{p}_ema50"])&(m15[f"{p}_s20"]>0)
        m15[f"{p}_dn"]=(m15[f"{p}_ema20"]<m15[f"{p}_ema50"])&(m15[f"{p}_s20"]<0)
    m15["up"]=m15.h4_up&m15.d1_up;m15["dn"]=m15.h4_dn&m15.d1_dn
    return m15

def signals(m15,family,disp,session):
    ss=m15.primary if session=="PRIMARY" else pd.Series(True,index=m15.index)
    bull=m15.close>m15.open;bear=m15.close<m15.open
    if family=="breakout":
        lo=m15.up&ss&bull&(m15.body_atr>=disp)&(m15.body_frac>=.6)&(m15.close>m15.ph8)&(m15.adx>=16)
        sh=m15.dn&ss&bear&(m15.body_atr>=disp)&(m15.body_frac>=.6)&(m15.close<m15.pl8)&(m15.adx>=16)
    else:
        lo=m15.up&ss&bull&(m15.low<=m15.ema20)&(m15.close>m15.ema20)&(m15.pdi>m15.mdi)&(m15.adx>=16)
        sh=m15.dn&ss&bear&(m15.high>=m15.ema20)&(m15.close<m15.ema20)&(m15.mdi>m15.pdi)&(m15.adx>=16)
    rows=[]
    for i in np.flatnonzero((lo.fillna(False)|sh.fillna(False)).to_numpy()):
        r=m15.iloc[i];rows.append({"signal_time":m15.index[i],"available":m15.index[i]+pd.Timedelta(minutes=15),
          "direction":1 if bool(lo.iat[i]) else -1,"o":float(r.open),"h":float(r.high),"l":float(r.low),"c":float(r.close),"atr15":float(r.atr14)})
    return pd.DataFrame(rows)

def build_entries(m1,sig,retrace,wait,confirm):
    idx=m1.index;op=m1.open.to_numpy(float);hi=m1.high.to_numpy(float);lo=m1.low.to_numpy(float);cl=m1.close.to_numpy(float)
    rows=[]
    for s in sig.itertuples(index=False):
        d=int(s.direction);rng=float(s.h-s.l)
        if rng<=0:continue
        level=float(s.h-retrace*rng) if d==1 else float(s.l+retrace*rng)
        start=idx.searchsorted(pd.Timestamp(s.available),side="left");expiry=pd.Timestamp(s.available)+pd.Timedelta(minutes=wait)
        touch=None
        for j in range(start,len(idx)):
            if idx[j]>=expiry or idx[j]>=END:break
            if lo[j]<=level<=hi[j]:touch=j;break
        if touch is None:continue
        confpos=None;end=min(len(idx),touch+6)
        for j in range(touch,end):
            rng1=max(hi[j]-lo[j],1e-12);body=max(abs(cl[j]-op[j]),1e-12)
            if d==1:
                lw=min(op[j],cl[j])-lo[j]
                if confirm=="pin":ok=cl[j]>op[j] and lw/body>=1.2 and (cl[j]-lo[j])/rng1>=.7
                elif confirm=="engulf":ok=j>0 and cl[j]>op[j] and cl[j]>hi[j-1]
                else:ok=j>=2 and cl[j]>max(hi[j-1],hi[j-2])
            else:
                uw=hi[j]-max(op[j],cl[j])
                if confirm=="pin":ok=cl[j]<op[j] and uw/body>=1.2 and (hi[j]-cl[j])/rng1>=.7
                elif confirm=="engulf":ok=j>0 and cl[j]<op[j] and cl[j]<lo[j-1]
                else:ok=j>=2 and cl[j]<min(lo[j-1],lo[j-2])
            if ok:confpos=j;break
        if confpos is None or confpos+1>=len(idx):continue
        ep=confpos+1;entry=float(op[ep]);a=float(s.atr15)
        stop=float(np.min(lo[touch:confpos+1])-.01*a) if d==1 else float(np.max(hi[touch:confpos+1])+.01*a)
        risk=(entry-stop) if d==1 else (stop-entry)
        if not np.isfinite(risk) or risk<=0 or risk/a<.015 or risk/a>.7:continue
        rows.append({"signal_time":s.signal_time,"entry_time":idx[ep],"entry_pos":ep,"direction":d,"entry":entry,"stop":stop,"risk":risk})
    return pd.DataFrame(rows)

def replay(m1,ss):
    if ss.empty:return pd.DataFrame()
    idx=m1.index;hi=m1.high.to_numpy(float);lo=m1.low.to_numpy(float)
    rows=[];busy=None
    for s in ss.sort_values("entry_time").itertuples(index=False):
        et=pd.Timestamp(s.entry_time)
        if et<START or et>=END:continue
        if busy is not None and et<=busy:continue
        d=int(s.direction);entry=float(s.entry);stop=float(s.stop);risk=float(s.risk);target=entry+d*RR*risk
        xp=xt=reason=None
        for j in range(int(s.entry_pos),len(idx)):
            if idx[j]>=END:break
            hs=lo[j]<=stop if d==1 else hi[j]>=stop;ht=hi[j]>=target if d==1 else lo[j]<=target
            if hs:xp=stop;xt=idx[j]+pd.Timedelta(minutes=1);reason="SL_same_bar" if ht else "SL";break
            if ht:xp=target;xt=idx[j]+pd.Timedelta(minutes=1);reason="TP";break
        if xp is None:continue
        nr=float(((xp-entry)/risk if d==1 else (entry-xp)/risk)-(entry*COST/10000)/risk)
        rows.append({"signal_time":s.signal_time,"entry_time":et,"exit_time":xt,"direction":"BUY" if d==1 else "SELL",
                     "net_r":nr,"r_multiple":nr,"result":"WIN" if nr>0 else "LOSS","exit_reason":reason})
        busy=xt
    return pd.DataFrame(rows)

def run(data_path,output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    m1=load_m5_csv(data_path);m1=m1[(m1.index>=pd.Timestamp("2016-10-01",tz="UTC"))&(m1.index<END)].copy()
    m15=prep(m1)
    rows=[];yrs=[];alltr=[];specs=[]
    for fam in ["breakout","pullback"]:
      for session in ["PRIMARY","ALL"]:
       for disp in ([.5,.7,.9] if fam=="breakout" else [0]):
        sig=signals(m15,fam,disp,session)
        for rt in [.705,.79,.886,.90]:
         for wait in [15,30,60]:
          for conf in ["pin","engulf","bos2"]:
           specs.append((fam,session,disp,rt,wait,conf,sig))
    for fam,session,disp,rt,wait,conf,sig in specs:
        name=f"M1__{fam}__{session}__D{disp}__R{rt}__W{wait}__{conf}"
        tr=replay(m1,build_entries(m1,sig,rt,wait,conf))
        if not tr.empty:alltr.append(tr.assign(strategy=name))
        ov=metrics(tr);ms=month_stats(tr);y=yearly(tr)
        rows.append({"strategy":name,"family":fam,"session":session,"disp":disp,"retrace":rt,"wait":wait,"confirm":conf,
          "trades":ov["trades"],"wr":ov["wr"],"expectancy_r":ov["expectancy_r"],"pf":ov["pf"],"dd":ov["max_dd_pct"],"end_rm":ov["end_rm"],**ms,
          "positive_years":int((y.expectancy_r>0).sum()),"pf_years":int((y.pf>1).sum())})
        for rr in y.itertuples(index=False):yrs.append({"strategy":name,**rr._asdict()})
    rd=pd.DataFrame(rows);rd["strict"]=(rd.wr>=60)&(rd.dd<=25)&(rd.min_month>=8)&(rd.positive_years.eq(4))&(rd.pf_years.eq(4))
    rd["dist"]=np.maximum(0,60-rd.wr)*3+np.maximum(0,rd.dd-25)+np.maximum(0,8-rd.min_month)*5+(4-rd.positive_years)*20
    ranked=rd.sort_values(["strict","dist","positive_years","min_month","wr","expectancy_r"],ascending=[False,True,False,False,False,False])
    yd=pd.DataFrame(yrs);ranked.to_csv(out/"ranked.csv",index=False);yd.to_csv(out/"yearly.csv",index=False)
    if alltr:pd.concat(alltr,ignore_index=True).to_csv(out/"trades.csv",index=False)
    strict=ranked[ranked.strict]
    lines=["# Dukascopy M1 Precision Study — 2017-2020","",
      "M15 HTF-aligned setup -> deep retrace -> M1 pin/engulf/micro-BOS -> next M1 open; M1 path replay.",
      "Fixed3R, real M1 pullback SL +0.01 M15 ATR, 1bp cost, RM100, 5% risk, same-M1 stop-first.","",
      f"Specs {len(specs)}; strict passes {len(strict)}.","",
      "| Strategy | Trades | WR | ExpR | PF | DD | Avg/mo | Min/mo | Years |","|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in ranked.head(30).itertuples(index=False):
        pf="inf" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(f"| {r.strategy} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.dd:.2f}% | {r.avg_month:.2f} | {r.min_month} | {r.positive_years}/4 |")
    report="\n".join(lines)+"\n";(out/"REPORT.md").write_text(report)
    (out/"summary.json").write_text(json.dumps({"strict_count":int(len(strict)),
      "strict":strict.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records"),
      "closest":ranked.head(30).replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")},indent=2))
    print(report)

def main():
    p=argparse.ArgumentParser();p.add_argument("--data",required=True);p.add_argument("--output",default="reports/historical-first-m1")
    a=p.parse_args();run(a.data,a.output)
if __name__=="__main__":main()
