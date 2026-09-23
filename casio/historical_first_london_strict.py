from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import argparse,json,math
import numpy as np
import pandas as pd
from .v3_core import load_m5_csv
from .historical_first_2017_2020 import DEV_END,atr,di_adx,resample,align_completed,metrics,month_stats,yearly

START=pd.Timestamp("2017-01-01",tz="UTC");RR=3.0;COST=1.0

@dataclass(frozen=True)
class Spec:
    name:str; family:str; bias:str; window:str; entry:str; adx:float; vol:float; lb:int; wait:int

def prep(m5):
    f=m5[["open","high","low","close","volume"]].copy()
    f["atr14"]=atr(f,14);pdi,mdi,adx=di_adx(f,14);f["pdi"],f["mdi"],f["adx"]=pdi,mdi,adx
    f["ema20"]=f.close.ewm(span=20,adjust=False).mean();f["ema50"]=f.close.ewm(span=50,adjust=False).mean()
    f["body"]=(f.close-f.open).abs();f["range"]=f.high-f.low
    f["body_atr"]=f.body/f.atr14.replace(0,np.nan);f["body_frac"]=f.body/f.range.replace(0,np.nan)
    f["uw"]=f.high-f[["open","close"]].max(axis=1);f["lw"]=f[["open","close"]].min(axis=1)-f.low
    f["uwb"]=f.uw/f.body.replace(0,np.nan);f["lwb"]=f.lw/f.body.replace(0,np.nan)
    f["vol_med20"]=f.volume.rolling(20,min_periods=10).median();f["vol_ratio"]=f.volume/f.vol_med20.replace(0,np.nan)
    for lb in [12,24,48]:f[f"ph{lb}"]=f.high.shift(1).rolling(lb).max();f[f"pl{lb}"]=f.low.shift(1).rolling(lb).min()

    h1=resample(m5,"1h");h4=resample(m5,"4h");d1=resample(m5,"1D")
    for x in (h1,h4,d1):
        x["ema20"]=x.close.ewm(span=20,adjust=False).mean();x["ema50"]=x.close.ewm(span=50,adjust=False).mean();x["s20"]=x.ema20.diff(3)
    ct=f.index+pd.Timedelta(minutes=5)
    for p,x,period in [("h1",h1,pd.Timedelta(hours=1)),("h4",h4,pd.Timedelta(hours=4)),("d1",d1,pd.Timedelta(days=1))]:
        for col in ["ema20","ema50","s20"]:f[f"{p}_{col}"]=align_completed(x[col],ct,period).to_numpy()
        f[f"{p}_up"]=(f[f"{p}_ema20"]>f[f"{p}_ema50"])&(f[f"{p}_s20"]>0);f[f"{p}_dn"]=(f[f"{p}_ema20"]<f[f"{p}_ema50"])&(f[f"{p}_s20"]<0)
    f["h4d1_up"]=f.h4_up&f.d1_up;f["h4d1_dn"]=f.h4_dn&f.d1_dn
    f["triple_up"]=f.h1_up&f.h4_up&f.d1_up;f["triple_dn"]=f.h1_dn&f.h4_dn&f.d1_dn

    local=f.index.tz_convert("Europe/London");f["ldn_date"]=pd.Index(local.date);f["ldn_min"]=local.hour*60+local.minute
    m=f.ldn_min
    f["LDN_FULL"]=(m>=7*60)&(m<13*60);f["LDN_AM"]=(m>=8*60)&(m<12*60)
    pre=(m>=0)&(m<8*60);orb=(m>=8*60)&(m<8*60+30)
    st=f.loc[pre].groupby("ldn_date").agg(pre_h=("high","max"),pre_l=("low","min"));f["pre_h"]=f.ldn_date.map(st.pre_h);f["pre_l"]=f.ldn_date.map(st.pre_l)
    ost=f.loc[orb].groupby("ldn_date").agg(or_h=("high","max"),or_l=("low","min"));f["or_h"]=f.ldn_date.map(ost.or_h);f["or_l"]=f.ldn_date.map(ost.or_l)
    return f

def bias(f,b):
    if b=="none":return pd.Series(True,index=f.index),pd.Series(True,index=f.index)
    if b=="h4d1":return f.h4d1_up.fillna(False),f.h4d1_dn.fillna(False)
    return f.triple_up.fillna(False),f.triple_dn.fillna(False)

def sigs(f,s):
    up,dn=bias(f,s.bias);win=f[s.window].fillna(False);vol=(f.vol_ratio>=s.vol) if s.vol>0 else pd.Series(True,index=f.index)
    ph=f[f"ph{s.lb}"];pl=f[f"pl{s.lb}"]
    bull=(f.close>f.open);bear=(f.close<f.open);disp_b=bull&(f.body_atr>=.55)&(f.body_frac>=.65);disp_s=bear&(f.body_atr>=.55)&(f.body_frac>=.65)
    rej_b=bull&(f.lwb>=1.2);rej_s=bear&(f.uwb>=1.2)
    if s.family=="pre_break":
        eligible=f.ldn_min>=8*60
        lo=win&eligible&up&vol&disp_b&(f.close>f.pre_h)&(f.close.shift(1)<=f.pre_h.shift(1))
        sh=win&eligible&dn&vol&disp_s&(f.close<f.pre_l)&(f.close.shift(1)>=f.pre_l.shift(1))
    elif s.family=="pre_sweep":
        lo=win&vol&rej_b&(f.low<f.pre_l)&(f.close>f.pre_l)
        sh=win&vol&rej_s&(f.high>f.pre_h)&(f.close<f.pre_h)
    elif s.family=="orb_break":
        eligible=f.ldn_min>=8*60+30
        lo=win&eligible&up&vol&disp_b&(f.close>f.or_h)&(f.close.shift(1)<=f.or_h.shift(1))
        sh=win&eligible&dn&vol&disp_s&(f.close<f.or_l)&(f.close.shift(1)>=f.or_l.shift(1))
    elif s.family=="ema20":
        lo=win&up&vol&rej_b&(f.low<=f.ema20)&(f.close>f.ema20)&(f.adx>=s.adx)
        sh=win&dn&vol&rej_s&(f.high>=f.ema20)&(f.close<f.ema20)&(f.adx>=s.adx)
    elif s.family=="disp":
        lo=win&up&vol&disp_b&(f.close>ph)&(f.adx>=s.adx);sh=win&dn&vol&disp_s&(f.close<pl)&(f.adx>=s.adx)
    else:raise ValueError
    rows=[]
    for i in np.flatnonzero((lo.fillna(False)|sh.fillna(False)).to_numpy()):
        r=f.iloc[i];d=1 if bool(lo.iat[i]) else -1;a=float(r.atr14)
        if not np.isfinite(a) or a<=0:continue
        if s.entry=="market":entry=np.nan
        elif s.entry=="half":entry=float((r.open+r.close)/2)
        elif s.entry=="deep705":entry=float(r.high-.705*(r.high-r.low)) if d==1 else float(r.low+.705*(r.high-r.low))
        elif s.entry=="deep886":entry=float(r.high-.886*(r.high-r.low)) if d==1 else float(r.low+.886*(r.high-r.low))
        else:raise ValueError
        stop=float(r.low-.04*a) if d==1 else float(r.high+.04*a)
        rows.append({"signal_time":f.index[i],"available":f.index[i]+pd.Timedelta(minutes=5),"ldn_date":r.ldn_date,
                     "direction":d,"entry_limit":entry,"stop":stop,"atr":a,"wait":s.wait})
    return pd.DataFrame(rows)

def replay(m5,ss):
    if ss.empty:return pd.DataFrame()
    idx=m5.index;hi=m5.high.to_numpy(float);lo=m5.low.to_numpy(float);op=m5.open.to_numpy(float);rows=[];busy=None;days=set()
    for s in ss.sort_values("available").itertuples(index=False):
        st=pd.Timestamp(s.signal_time)
        if st<START or st>=DEV_END or s.ldn_date in days:continue
        av=pd.Timestamp(s.available)
        if busy is not None and av<=busy:continue
        pos=idx.searchsorted(av,side="left")
        if pos>=len(idx):continue
        if np.isnan(float(s.entry_limit)):fill=pos;entry=float(op[fill])
        else:
            entry=float(s.entry_limit);expiry=av+pd.Timedelta(minutes=int(s.wait));fill=None
            for j in range(pos,len(idx)):
                if idx[j]>=expiry or idx[j]>=DEV_END:break
                if lo[j]<=entry<=hi[j]:fill=j;break
            if fill is None:continue
        d=int(s.direction);stop=float(s.stop);risk=(entry-stop) if d==1 else (stop-entry);a=float(s.atr)
        if risk<=0 or risk/a<.08 or risk/a>2:continue
        target=entry+d*RR*risk;xp=xt=None
        for j in range(fill,len(idx)):
            if idx[j]>=DEV_END:break
            hs=lo[j]<=stop if d==1 else hi[j]>=stop;ht=hi[j]>=target if d==1 else lo[j]<=target
            if hs:xp=stop;xt=idx[j]+pd.Timedelta(minutes=5);break
            if ht:xp=target;xt=idx[j]+pd.Timedelta(minutes=5);break
        if xp is None:continue
        nr=float(((xp-entry)/risk if d==1 else (entry-xp)/risk)-(entry*COST/10000)/risk)
        rows.append({"signal_time":st,"entry_time":idx[fill],"exit_time":xt,"direction":"BUY" if d==1 else "SELL","net_r":nr,"r_multiple":nr,"result":"WIN" if nr>0 else "LOSS"})
        busy=xt;days.add(s.ldn_date)
    return pd.DataFrame(rows)

def make_specs():
    out=[]
    for fam in ["pre_break","pre_sweep","orb_break","ema20","disp"]:
      for b in ["none","h4d1","triple"]:
       if fam in ["pre_break","orb_break","ema20","disp"] and b=="none":continue
       for w in ["LDN_FULL","LDN_AM"]:
        for e in ["market","half","deep705","deep886"]:
         for a in [16,24,28]:
          for v in [0,1.15]:
           for lb in [12,48]:
            out.append(Spec(f"LDN__{fam}__{b}__{w}__{e}__A{a}__V{v}__L{lb}",fam,b,w,e,a,v,lb,60))
    return out

def run(data_path,output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True);raw=load_m5_csv(data_path);m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy();f=prep(m5)
    rows=[];yrs=[];alltr=[];sp=make_specs()
    for s in sp:
        tr=replay(m5,sigs(f,s))
        if not tr.empty:alltr.append(tr.assign(strategy=s.name))
        ov=metrics(tr);ms=month_stats(tr);y=yearly(tr)
        rows.append({"strategy":s.name,"family":s.family,"trades":ov["trades"],"wr":ov["wr"],"expectancy_r":ov["expectancy_r"],"pf":ov["pf"],"dd":ov["max_dd_pct"],"end_rm":ov["end_rm"],**ms,
                     "positive_years":int((y.expectancy_r>0).sum()),"pf_years":int((y.pf>1).sum())})
        for rr in y.itertuples(index=False):yrs.append({"strategy":s.name,**rr._asdict()})
    rd=pd.DataFrame(rows);rd["strict"]=(rd.wr>=60)&(rd.dd<=25)&(rd.min_month>=8)&(rd.positive_years.eq(4))&(rd.pf_years.eq(4))
    rd["dist"]=np.maximum(0,60-rd.wr)*3+np.maximum(0,rd.dd-25)+np.maximum(0,8-rd.min_month)*5+(4-rd.positive_years)*20
    ranked=rd.sort_values(["strict","dist","positive_years","min_month","wr","expectancy_r"],ascending=[False,True,False,False,False,False]);yd=pd.DataFrame(yrs)
    ranked.to_csv(out/"ranked.csv",index=False);yd.to_csv(out/"yearly.csv",index=False)
    if alltr:pd.concat(alltr,ignore_index=True).to_csv(out/"trades.csv",index=False)
    strict=ranked[ranked.strict];lines=["# DST-Aware London Strict Search — 2017-2020","",
      "Europe/London local clock; pre-London range, opening range, sweep, EMA pullback, displacement. One entry max per London date.",
      "RR3, RM100, 5% risk, real stop, 1bp cost, same-bar stop-first; 2021+ sealed.","",f"Specs {len(sp)}; strict passes {len(strict)}.","",
      "| Strategy | Trades | WR | ExpR | PF | DD | Avg/mo | Min/mo | Years |","|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in ranked.head(35).itertuples(index=False):
        pf="inf" if math.isinf(float(r.pf)) else f"{r.pf:.2f}";lines.append(f"| {r.strategy} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.dd:.2f}% | {r.avg_month:.2f} | {r.min_month} | {r.positive_years}/4 |")
    report="\n".join(lines)+"\n";(out/"REPORT.md").write_text(report);(out/"summary.json").write_text(json.dumps({"strict_count":int(len(strict)),"closest":ranked.head(35).replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")},indent=2));print(report)
def main():
    p=argparse.ArgumentParser();p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv");p.add_argument("--output",default="reports/historical-first-london");a=p.parse_args();run(a.data,a.output)
if __name__=="__main__":main()
