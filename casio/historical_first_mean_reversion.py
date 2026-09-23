from __future__ import annotations
from pathlib import Path
import argparse,json,math
import numpy as np
import pandas as pd
from .v3_core import load_m5_csv
from .historical_first_2017_2020 import DEV_END,atr,di_adx,resample,align_completed,rsi,metrics,month_stats,yearly

START=pd.Timestamp("2017-01-01",tz="UTC"); RR=3.0; COST=1.0

def prep(m5):
    f=m5[["open","high","low","close","volume"]].copy()
    f["atr14"]=atr(f,14); pdi,mdi,adx=di_adx(f,14); f["adx"]=adx
    f["rsi2"]=rsi(f.close,2); f["rsi8"]=rsi(f.close,8)
    f["body"]=(f.close-f.open).abs(); f["range"]=f.high-f.low
    f["uw"]=f.high-f[["open","close"]].max(axis=1); f["lw"]=f[["open","close"]].min(axis=1)-f.low
    f["uwb"]=f.uw/f.body.replace(0,np.nan); f["lwb"]=f.lw/f.body.replace(0,np.nan)
    day=f.index.floor("D"); f["day"]=day
    f["vwap"]=(f.close*f.volume).groupby(day).cumsum()/f.volume.groupby(day).cumsum().replace(0,np.nan)
    f["vwap_dev"]=(f.close-f.vwap)/f.atr14.replace(0,np.nan)
    sma=f.close.rolling(20).mean(); sd=f.close.rolling(20).std(ddof=0)
    f["z20"]=(f.close-sma)/sd.replace(0,np.nan)
    for lb in [12,24,48,96]:
        f[f"ph{lb}"]=f.high.shift(1).rolling(lb).max(); f[f"pl{lb}"]=f.low.shift(1).rolling(lb).min()

    mins=f.index.hour*60+f.index.minute; f["mins"]=mins
    asia=(mins>=0)&(mins<6*60); nyor=(mins>=12*60+30)&(mins<13*60+30)
    ast=f.loc[asia].groupby(day).agg(asia_h=("high","max"),asia_l=("low","min"))
    nst=f.loc[nyor].groupby(day).agg(ny_h=("high","max"),ny_l=("low","min"))
    f["asia_h"]=day.map(ast.asia_h); f["asia_l"]=day.map(ast.asia_l)
    f["ny_h"]=day.map(nst.ny_h); f["ny_l"]=day.map(nst.ny_l)
    daily=f.groupby(day).agg(dh=("high","max"),dl=("low","min")); prev=daily.shift(1)
    f["pd_h"]=day.map(prev.dh); f["pd_l"]=day.map(prev.dl)

    h1=resample(m5,"1h"); h4=resample(m5,"4h")
    for x in (h1,h4):
        x["atr14"]=atr(x,14); _,_,x["adx"]=di_adx(x,14)
        x["ema20"]=x.close.ewm(span=20,adjust=False).mean(); x["ema50"]=x.close.ewm(span=50,adjust=False).mean()
        x["s20"]=x.ema20.diff(3)
    ct=f.index+pd.Timedelta(minutes=5)
    for p,x,period in [("h1",h1,pd.Timedelta(hours=1)),("h4",h4,pd.Timedelta(hours=4))]:
        for col in ["adx","ema20","ema50","s20","atr14"]:
            f[f"{p}_{col}"]=align_completed(x[col],ct,period).to_numpy()
        f[f"{p}_up"]=(f[f"{p}_ema20"]>f[f"{p}_ema50"])&(f[f"{p}_s20"]>0)
        f[f"{p}_dn"]=(f[f"{p}_ema20"]<f[f"{p}_ema50"])&(f[f"{p}_s20"]<0)
    return f

def signals(f,family,dev,wick,lb,h1adx,session):
    m=f.mins
    if session=="ALL": ss=pd.Series(True,index=f.index)
    elif session=="PRIMARY": ss=pd.Series(((m>=7*60)&(m<11*60))|((m>=12*60+30)&(m<16*60+30)),index=f.index)
    elif session=="LONDON": ss=pd.Series((m>=7*60)&(m<11*60),index=f.index)
    else: ss=pd.Series((m>=12*60+30)&(m<16*60+30),index=f.index)
    rangegate=(f.h1_adx<=h1adx)
    bull=(f.close>f.open)&(f.lwb>=wick); bear=(f.close<f.open)&(f.uwb>=wick)
    ph=f[f"ph{lb}"]; pl=f[f"pl{lb}"]

    if family=="vwap_extreme":
        lo=ss&bull&(f.vwap_dev<=-dev)&(f.rsi2<=25)
        sh=ss&bear&(f.vwap_dev>=dev)&(f.rsi2>=75)
    elif family=="vwap_range":
        lo=ss&rangegate&bull&(f.vwap_dev<=-dev)&(f.rsi2<=20)
        sh=ss&rangegate&bear&(f.vwap_dev>=dev)&(f.rsi2>=80)
    elif family=="zscore_range":
        lo=ss&rangegate&bull&(f.z20<=-dev)&(f.rsi2<=20)
        sh=ss&rangegate&bear&(f.z20>=dev)&(f.rsi2>=80)
    elif family=="rolling_sweep":
        lo=ss&bull&(f.low<pl)&(f.close>pl)&(f.rsi2<=30)
        sh=ss&bear&(f.high>ph)&(f.close<ph)&(f.rsi2>=70)
    elif family=="asia_false":
        win=(m>=7*60)&(m<11*60)
        lo=win&bull&(f.low<f.asia_l)&(f.close>f.asia_l)
        sh=win&bear&(f.high>f.asia_h)&(f.close<f.asia_h)
    elif family=="ny_false":
        win=(m>=13*60+30)&(m<16*60+30)
        lo=win&bull&(f.low<f.ny_l)&(f.close>f.ny_l)
        sh=win&bear&(f.high>f.ny_h)&(f.close<f.ny_h)
    elif family=="pd_false":
        win=((m>=7*60)&(m<11*60))|((m>=12*60+30)&(m<16*60+30))
        lo=win&bull&(f.low<f.pd_l)&(f.close>f.pd_l)
        sh=win&bear&(f.high>f.pd_h)&(f.close<f.pd_h)
    else: raise ValueError(family)
    return lo.fillna(False),sh.fillna(False)

def build_trades(m5,f,lo,sh,name,stopbuf):
    idx=m5.index; hi=m5.high.to_numpy(float); low=m5.low.to_numpy(float); op=m5.open.to_numpy(float)
    sigidx=np.flatnonzero((lo|sh).to_numpy()); setups=[]
    for i in sigidx:
        st=f.index[i]; pos=idx.searchsorted(st+pd.Timedelta(minutes=5),side="left")
        if pos>=len(idx) or idx[pos]>=DEV_END: continue
        d=1 if bool(lo.iat[i]) else -1; a=float(f.atr14.iat[i])
        entry=float(op[pos]); stop=float(f.low.iat[i]-stopbuf*a) if d==1 else float(f.high.iat[i]+stopbuf*a)
        risk=(entry-stop) if d==1 else (stop-entry)
        if not np.isfinite(risk) or risk<=0 or risk/a<0.04 or risk/a>1.0: continue
        setups.append((st,pos,d,entry,stop,risk))
    rows=[]; busy=None
    for st,pos,d,entry,stop,risk in setups:
        et=idx[pos]
        if et<START: continue
        if busy is not None and et<=busy: continue
        target=entry+d*RR*risk; xp=xt=reason=None
        for j in range(pos,len(idx)):
            t=idx[j]
            if t>=DEV_END: break
            hs=low[j]<=stop if d==1 else hi[j]>=stop
            ht=hi[j]>=target if d==1 else low[j]<=target
            if hs: xp=stop;xt=t+pd.Timedelta(minutes=5);reason="SL_same_bar" if ht else "SL";break
            if ht: xp=target;xt=t+pd.Timedelta(minutes=5);reason="TP";break
        if xp is None:continue
        gross=(xp-entry)/risk if d==1 else (entry-xp)/risk; nr=float(gross-(entry*COST/10000)/risk)
        rows.append({"signal_time":st,"entry_time":et,"exit_time":xt,"direction":"BUY" if d==1 else "SELL",
                     "net_r":nr,"r_multiple":nr,"result":"WIN" if nr>0 else "LOSS","exit_reason":reason})
        busy=xt
    return pd.DataFrame(rows)

def specs():
    out=[]
    for fam in ["vwap_extreme","vwap_range"]:
      for dev in [1.0,1.5,2.0,2.5]:
       for wick in [0.8,1.5,2.5]:
        for adx in [18,22,28]:
         for sess in ["ALL","PRIMARY"]:
          out.append((fam,dev,wick,24,adx,sess,0.03))
    for dev in [1.5,2.0,2.5,3.0]:
      for wick in [0.8,1.5,2.5]:
       for adx in [18,22,28]:
        for sess in ["ALL","PRIMARY"]:
         out.append(("zscore_range",dev,wick,24,adx,sess,0.03))
    for lb in [12,24,48,96]:
      for wick in [0.8,1.5,2.5]:
       for sess in ["ALL","PRIMARY"]:
        out.append(("rolling_sweep",0,wick,lb,99,sess,0.03))
    for fam in ["asia_false","ny_false","pd_false"]:
      for wick in [0.5,1.0,1.5,2.0]:
       out.append((fam,0,wick,24,99,"ALL",0.03))
    return out

def run(data_path,output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path);m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy()
    f=prep(m5)
    rows=[];yrs=[];alltr=[];sp=specs()
    for k,(fam,dev,wick,lb,h1adx,sess,buf) in enumerate(sp):
        name=f"MR__{fam}__D{dev}__K{wick}__L{lb}__A{h1adx}__{sess}"
        lo,sh=signals(f,fam,dev,wick,lb,h1adx,sess)
        tr=build_trades(m5,f,lo,sh,name,buf)
        if not tr.empty:alltr.append(tr.assign(strategy=name))
        ov=metrics(tr);ms=month_stats(tr);y=yearly(tr)
        rows.append({"strategy":name,"family":fam,"dev":dev,"wick":wick,"lb":lb,"h1adx":h1adx,"session":sess,
                     "trades":ov["trades"],"wr":ov["wr"],"expectancy_r":ov["expectancy_r"],"pf":ov["pf"],
                     "dd":ov["max_dd_pct"],"end_rm":ov["end_rm"],**ms,
                     "positive_years":int((y.expectancy_r>0).sum()),"pf_years":int((y.pf>1).sum()),
                     "worst_year_exp":float(y.expectancy_r.min()),"worst_year_dd":float(y.max_dd_pct.max())})
        for rr in y.itertuples(index=False):yrs.append({"strategy":name,**rr._asdict()})
    rd=pd.DataFrame(rows)
    rd["strict"]=(rd.wr>=60)&(rd.dd<=25)&(rd.min_month>=8)&(rd.positive_years.eq(4))&(rd.pf_years.eq(4))
    rd["dist"]=np.maximum(0,60-rd.wr)*3+np.maximum(0,rd.dd-25)+np.maximum(0,8-rd.min_month)*5+(4-rd.positive_years)*20
    ranked=rd.sort_values(["strict","dist","positive_years","min_month","wr","expectancy_r"],ascending=[False,True,False,False,False,False])
    yd=pd.DataFrame(yrs);ranked.to_csv(out/"ranked.csv",index=False);yd.to_csv(out/"yearly.csv",index=False)
    if alltr:pd.concat(alltr,ignore_index=True).to_csv(out/"trades.csv",index=False)
    strict=ranked[ranked.strict]
    lines=["# M5 Extreme Mean-Reversion / False-Break Search","",
           "2017-2020 only; VWAP/BB-z extremes, rolling liquidity sweeps, Asia/NY/previous-day false breaks.",
           "Entry next M5 open after rejection candle, stop beyond rejection wick +0.03ATR, fixed3R, 1bp cost, 5% risk.","",
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
    p.add_argument("--output",default="reports/historical-first-mean-reversion");a=p.parse_args();run(a.data,a.output)
if __name__=="__main__":main()
