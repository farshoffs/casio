from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import argparse,json,math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import atr,di_adx,resample,align_completed,metrics,month_stats,yearly

START=pd.Timestamp("2017-01-01",tz="UTC"); END=pd.Timestamp("2021-01-01",tz="UTC")
RR=3.0; COST_BPS=1.0

@dataclass(frozen=True)
class Spec:
    family:str; bias:str; window:str; retrace:float; wait:int; confirm:str; disp:float; volmin:float

def add_ny_fields(x):
    z=x.copy(); local=z.index.tz_convert("America/New_York")
    z["ny_date"]=pd.Index(local.date); z["ny_min"]=local.hour*60+local.minute
    m=z.ny_min
    z["NY_FULL"]=(m>=8*60)&(m<17*60)
    z["NY_CORE"]=(m>=8*60+30)&(m<12*60+30)
    z["NY_CASH_AM"]=(m>=9*60+30)&(m<12*60+30)
    overnight=(m>=0)&(m<8*60+30)
    orb=(m>=9*60+30)&(m<10*60)
    for mask,hname,lname in [(overnight,"on_h","on_l"),(orb,"or_h","or_l")]:
        st=z.loc[mask].groupby("ny_date").agg(**{hname:("high","max"),lname:("low","min")})
        z[hname]=z.ny_date.map(st[hname]); z[lname]=z.ny_date.map(st[lname])
    return z

def prep(m1):
    m15=resample(m1,"15min")
    m15["atr14"]=atr(m15,14)
    pdi,mdi,adx=di_adx(m15,14);m15["pdi"],m15["mdi"],m15["adx"]=pdi,mdi,adx
    m15["rsi2"]=100-(100/(1+(m15.close.diff().clip(lower=0).ewm(alpha=.5,adjust=False).mean()/(-m15.close.diff().clip(upper=0)).ewm(alpha=.5,adjust=False).mean().replace(0,np.nan))))
    m15["ema20"]=m15.close.ewm(span=20,adjust=False).mean();m15["ema50"]=m15.close.ewm(span=50,adjust=False).mean()
    m15["body"]=(m15.close-m15.open).abs();m15["range"]=m15.high-m15.low
    m15["body_atr"]=m15.body/m15.atr14.replace(0,np.nan);m15["body_frac"]=m15.body/m15.range.replace(0,np.nan)
    m15["ph8"]=m15.high.shift(1).rolling(8).max();m15["pl8"]=m15.low.shift(1).rolling(8).min()
    m15["ph16"]=m15.high.shift(1).rolling(16).max();m15["pl16"]=m15.low.shift(1).rolling(16).min()
    m15["volmed"]=m15.volume.rolling(20,min_periods=10).median();m15["volratio"]=m15.volume/m15.volmed.replace(0,np.nan)
    m15=add_ny_fields(m15)
    ny=m15.NY_FULL
    pv=(m15.close*m15.volume).where(ny); vv=m15.volume.where(ny)
    m15["ny_vwap"]=pv.groupby(m15.ny_date).cumsum()/vv.groupby(m15.ny_date).cumsum().replace(0,np.nan)

    h1=resample(m1,"1h"); h4=resample(m1,"4h"); d1=resample(m1,"1D")
    for x in (h1,h4,d1):
        x["ema20"]=x.close.ewm(span=20,adjust=False).mean();x["ema50"]=x.close.ewm(span=50,adjust=False).mean()
        x["s20"]=x.ema20.diff(3)
    ct=m15.index+pd.Timedelta(minutes=15)
    for p,x,period in [("h1",h1,pd.Timedelta(hours=1)),("h4",h4,pd.Timedelta(hours=4)),("d1",d1,pd.Timedelta(days=1))]:
        for col in ["ema20","ema50","s20"]:m15[f"{p}_{col}"]=align_completed(x[col],ct,period).to_numpy()
        m15[f"{p}_up"]=(m15[f"{p}_ema20"]>m15[f"{p}_ema50"])&(m15[f"{p}_s20"]>0)
        m15[f"{p}_dn"]=(m15[f"{p}_ema20"]<m15[f"{p}_ema50"])&(m15[f"{p}_s20"]<0)
    m15["h4d1_up"]=m15.h4_up&m15.d1_up;m15["h4d1_dn"]=m15.h4_dn&m15.d1_dn
    m15["triple_up"]=m15.h1_up&m15.h4_up&m15.d1_up;m15["triple_dn"]=m15.h1_dn&m15.h4_dn&m15.d1_dn
    return m15

def signals(f,s):
    win=f[s.window].fillna(False)
    if s.bias=="h4d1":up=f.h4d1_up.fillna(False);dn=f.h4d1_dn.fillna(False)
    else:up=f.triple_up.fillna(False);dn=f.triple_dn.fillna(False)
    bull=f.close>f.open;bear=f.close<f.open;vol=f.volratio>=s.volmin
    strongb=bull&(f.body_atr>=s.disp)&(f.body_frac>=.6)
    strongs=bear&(f.body_atr>=s.disp)&(f.body_frac>=.6)

    if s.family=="break8":
        lo=win&up&vol&strongb&(f.close>f.ph8)&(f.adx>=18)
        sh=win&dn&vol&strongs&(f.close<f.pl8)&(f.adx>=18)
    elif s.family=="break16":
        lo=win&up&vol&strongb&(f.close>f.ph16)&(f.adx>=18)
        sh=win&dn&vol&strongs&(f.close<f.pl16)&(f.adx>=18)
    elif s.family=="ema20":
        lo=win&up&vol&bull&(f.low<=f.ema20)&(f.close>f.ema20)&(f.pdi>f.mdi)&(f.adx>=18)
        sh=win&dn&vol&bear&(f.high>=f.ema20)&(f.close<f.ema20)&(f.mdi>f.pdi)&(f.adx>=18)
    elif s.family=="vwap":
        lo=win&up&vol&bull&(f.low<=f.ny_vwap)&(f.close>f.ny_vwap)&(f.pdi>f.mdi)
        sh=win&dn&vol&bear&(f.high>=f.ny_vwap)&(f.close<f.ny_vwap)&(f.mdi>f.pdi)
    elif s.family=="or_break":
        eligible=f.ny_min>=10*60
        lo=win&eligible&up&vol&strongb&(f.close>f.or_h)&(f.close.shift(1)<=f.or_h.shift(1))
        sh=win&eligible&dn&vol&strongs&(f.close<f.or_l)&(f.close.shift(1)>=f.or_l.shift(1))
    elif s.family=="on_sweep":
        bullrej=bull&(f.low<f.on_l)&(f.close>f.on_l)
        bearrej=bear&(f.high>f.on_h)&(f.close<f.on_h)
        lo=win&up&vol&bullrej;sh=win&dn&vol&bearrej
    elif s.family=="rsi2":
        lo=win&up&vol&bull&(f.rsi2.shift(1)<=10)&(f.rsi2>=25)&(f.close>f.ema20)
        sh=win&dn&vol&bear&(f.rsi2.shift(1)>=90)&(f.rsi2<=75)&(f.close<f.ema20)
    else:raise ValueError(s.family)

    rows=[]
    for i in np.flatnonzero((lo.fillna(False)|sh.fillna(False)).to_numpy()):
        r=f.iloc[i]
        rows.append({"signal_time":f.index[i],"available":f.index[i]+pd.Timedelta(minutes=15),"ny_date":r.ny_date,
                     "direction":1 if bool(lo.iat[i]) else -1,"h":float(r.high),"l":float(r.low),"atr":float(r.atr14)})
    return pd.DataFrame(rows)

def entries(m1,sig,s):
    if sig.empty:return pd.DataFrame()
    idx=m1.index;op=m1.open.to_numpy(float);hi=m1.high.to_numpy(float);lo=m1.low.to_numpy(float);cl=m1.close.to_numpy(float)
    local=idx.tz_convert("America/New_York");nym=(local.hour*60+local.minute).to_numpy()
    rows=[]
    for q in sig.itertuples(index=False):
        d=int(q.direction);rng=float(q.h-q.l)
        if rng<=0:continue
        level=float(q.h-s.retrace*rng) if d==1 else float(q.l+s.retrace*rng)
        start=idx.searchsorted(pd.Timestamp(q.available),side="left");expiry=pd.Timestamp(q.available)+pd.Timedelta(minutes=s.wait)
        touch=None
        for j in range(start,len(idx)):
            if idx[j]>=expiry or idx[j]>=END:break
            # confirmation/fill must remain inside NY full session.
            if not (8*60<=nym[j]<17*60):continue
            if lo[j]<=level<=hi[j]:touch=j;break
        if touch is None:continue
        conf=None
        for j in range(touch,min(len(idx),touch+8)):
            if not (8*60<=nym[j]<17*60):break
            rng1=max(hi[j]-lo[j],1e-12);body=max(abs(cl[j]-op[j]),1e-12)
            if d==1:
                lw=min(op[j],cl[j])-lo[j]
                if s.confirm=="pin":ok=cl[j]>op[j] and lw/body>=1.2 and (cl[j]-lo[j])/rng1>=.7
                elif s.confirm=="engulf":ok=j>0 and cl[j]>op[j] and cl[j]>hi[j-1]
                elif s.confirm=="bos2":ok=j>=2 and cl[j]>max(hi[j-1],hi[j-2])
                else:ok=j>=3 and cl[j]>max(hi[j-1],hi[j-2],hi[j-3])
            else:
                uw=hi[j]-max(op[j],cl[j])
                if s.confirm=="pin":ok=cl[j]<op[j] and uw/body>=1.2 and (hi[j]-cl[j])/rng1>=.7
                elif s.confirm=="engulf":ok=j>0 and cl[j]<op[j] and cl[j]<lo[j-1]
                elif s.confirm=="bos2":ok=j>=2 and cl[j]<min(lo[j-1],lo[j-2])
                else:ok=j>=3 and cl[j]<min(lo[j-1],lo[j-2],lo[j-3])
            if ok:conf=j;break
        if conf is None or conf+1>=len(idx):continue
        ep=conf+1
        if not (8*60<=nym[ep]<17*60):continue
        entry=float(op[ep]);a=float(q.atr)
        stop=float(np.min(lo[touch:conf+1])-.01*a) if d==1 else float(np.max(hi[touch:conf+1])+.01*a)
        risk=(entry-stop) if d==1 else (stop-entry)
        if not np.isfinite(risk) or risk<=0 or risk/a<.015 or risk/a>.8:continue
        rows.append({"signal_time":q.signal_time,"entry_time":idx[ep],"entry_pos":ep,"ny_date":q.ny_date,
                     "direction":d,"entry":entry,"stop":stop,"risk":risk})
    return pd.DataFrame(rows)

def replay(m1,ss,name):
    if ss.empty:return pd.DataFrame()
    idx=m1.index;hi=m1.high.to_numpy(float);lo=m1.low.to_numpy(float)
    rows=[];busy=None;days=set()
    for q in ss.sort_values("entry_time").itertuples(index=False):
        et=pd.Timestamp(q.entry_time)
        if et<START or et>=END or q.ny_date in days:continue
        if busy is not None and et<=busy:continue
        d=int(q.direction);entry=float(q.entry);stop=float(q.stop);risk=float(q.risk);target=entry+d*RR*risk
        xp=xt=reason=None
        for j in range(int(q.entry_pos),len(idx)):
            if idx[j]>=END:break
            hs=lo[j]<=stop if d==1 else hi[j]>=stop;ht=hi[j]>=target if d==1 else lo[j]<=target
            if hs:xp=stop;xt=idx[j]+pd.Timedelta(minutes=1);reason="SL_same_bar" if ht else "SL";break
            if ht:xp=target;xt=idx[j]+pd.Timedelta(minutes=1);reason="TP";break
        if xp is None:continue
        nr=float(((xp-entry)/risk if d==1 else (entry-xp)/risk)-(entry*COST_BPS/10000)/risk)
        rows.append({"strategy":name,"signal_time":q.signal_time,"entry_time":et,"exit_time":xt,
                     "direction":"BUY" if d==1 else "SELL","net_r":nr,"r_multiple":nr,
                     "result":"WIN" if nr>0 else "LOSS","exit_reason":reason})
        days.add(q.ny_date);busy=xt
    return pd.DataFrame(rows)

def specs():
    out=[]
    for fam in ["break8","break16","ema20","vwap","or_break","on_sweep","rsi2"]:
     for bias in ["h4d1","triple"]:
      for window in ["NY_FULL","NY_CORE","NY_CASH_AM"]:
       for rt in [.5,.705,.79,.886,.90]:
        for wait in [15,30,60]:
         for conf in ["pin","engulf","bos2","bos3"]:
          for disp in ([.5,.8] if fam in ["break8","break16","or_break"] else [0]):
           for vol in [.8,1.15]:
            out.append(Spec(fam,bias,window,rt,wait,conf,disp,vol))
    return out

def run(data_path,output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    m1=load_m5_csv(data_path);m1=m1[(m1.index>=pd.Timestamp("2016-10-01",tz="UTC"))&(m1.index<END)].copy()
    f=prep(m1);sp=specs();rows=[];yrs=[];alltr=[]
    cache={}
    for s in sp:
        key=(s.family,s.bias,s.window,s.disp,s.volmin)
        if key not in cache:cache[key]=signals(f,s)
        tr=replay(m1,entries(m1,cache[key],s),f"NYM1__{s.family}__{s.bias}__{s.window}__R{s.retrace}__W{s.wait}__{s.confirm}__D{s.disp}__V{s.volmin}")
        name=f"NYM1__{s.family}__{s.bias}__{s.window}__R{s.retrace}__W{s.wait}__{s.confirm}__D{s.disp}__V{s.volmin}"
        if not tr.empty:alltr.append(tr)
        ov=metrics(tr);ms=month_stats(tr);y=yearly(tr)
        rows.append({"strategy":name,"family":s.family,"bias":s.bias,"window":s.window,"retrace":s.retrace,"wait":s.wait,"confirm":s.confirm,
                     "trades":ov["trades"],"wr":ov["wr"],"expectancy_r":ov["expectancy_r"],"pf":ov["pf"],"dd":ov["max_dd_pct"],"end_rm":ov["end_rm"],**ms,
                     "positive_years":int((y.expectancy_r>0).sum()),"pf_years":int((y.pf>1).sum())})
        for rr in y.itertuples(index=False):yrs.append({"strategy":name,**rr._asdict()})
    rd=pd.DataFrame(rows);rd["strict"]=(rd.wr>=60)&(rd.dd<=25)&(rd.min_month>=8)&(rd.positive_years.eq(4))&(rd.pf_years.eq(4))
    rd["dist"]=np.maximum(0,60-rd.wr)*3+np.maximum(0,rd.dd-25)+np.maximum(0,8-rd.min_month)*6+(4-rd.positive_years)*25
    ranked=rd.sort_values(["strict","dist","positive_years","min_month","wr","expectancy_r"],ascending=[False,True,False,False,False,False])
    yd=pd.DataFrame(yrs);ranked.to_csv(out/"ranked.csv",index=False);yd.to_csv(out/"yearly.csv",index=False)
    if alltr:pd.concat(alltr,ignore_index=True).to_csv(out/"trades.csv",index=False)
    strict=ranked[ranked.strict]
    lines=["# DST-Aware New York M1 Precision — 2017-2020","",
      "NY-only M15 setup -> deep retrace -> M1 confirmation -> next M1 open. One entry max per NY date.",
      "Fixed 3R, real M1 pullback stop, RM100, 5% risk, 1bp cost, same-M1 stop-first. 2021+ sealed.","",
      f"Specs {len(sp)}; strict passes {len(strict)}.","",
      "| Strategy | Trades | WR | ExpR | PF | DD | Avg/mo | Min/mo | Years |","|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in ranked.head(40).itertuples(index=False):
        pf="inf" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(f"| {r.strategy} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.dd:.2f}% | {r.avg_month:.2f} | {r.min_month} | {r.positive_years}/4 |")
    for strategy in (strict.strategy.tolist() if len(strict) else ranked.head(10).strategy.tolist()):
        lines+=["",f"## {strategy}","","| Year | Trades | WR | ExpR | PF | DD | RM100 -> |","|---|---:|---:|---:|---:|---:|---:|"]
        for r in yd[yd.strategy==strategy].itertuples(index=False):
            pf="inf" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
            lines.append(f"| {r.year} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.max_dd_pct:.2f}% | RM{r.end_rm:.2f} |")
    report="\n".join(lines)+"\n";(out/"REPORT.md").write_text(report)
    (out/"summary.json").write_text(json.dumps({"specs":len(sp),"strict_count":int(len(strict)),
      "strict":strict.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records"),
      "closest":ranked.head(40).replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")},indent=2))
    print(report)

def main():
    p=argparse.ArgumentParser();p.add_argument("--data",required=True);p.add_argument("--output",default="reports/historical-first-ny-m1")
    a=p.parse_args();run(a.data,a.output)
if __name__=="__main__":main()
