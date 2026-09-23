from __future__ import annotations
from pathlib import Path
import argparse,json,math
import numpy as np
import pandas as pd
from .v3_core import load_m5_csv
from .historical_first_2017_2020 import DEV_END,atr,resample,align_completed,metrics,month_stats,yearly

START=pd.Timestamp("2017-01-01",tz="UTC"); RR=3.0; COST=1.0

def prep(m5):
    f=m5[["open","high","low","close","volume"]].copy()
    f["atr14"]=atr(f,14)
    f["body"]=(f.close-f.open).abs(); f["range"]=f.high-f.low
    f["body_atr"]=f.body/f.atr14.replace(0,np.nan)
    f["body_frac"]=f.body/f.range.replace(0,np.nan)
    for lb in [12,24]:
        f[f"ph{lb}"]=f.high.shift(1).rolling(lb).max()
        f[f"pl{lb}"]=f.low.shift(1).rolling(lb).min()
    mins=f.index.hour*60+f.index.minute
    f["primary"]=((mins>=7*60)&(mins<11*60))|((mins>=12*60+30)&(mins<16*60+30))
    h1=resample(m5,"1h");h4=resample(m5,"4h");d1=resample(m5,"1D")
    for x in (h1,h4,d1):
        x["ema20"]=x.close.ewm(span=20,adjust=False).mean()
        x["ema50"]=x.close.ewm(span=50,adjust=False).mean()
        x["s20"]=x.ema20.diff(3)
    ct=f.index+pd.Timedelta(minutes=5)
    for p,x,period in [("h1",h1,pd.Timedelta(hours=1)),("h4",h4,pd.Timedelta(hours=4)),("d1",d1,pd.Timedelta(days=1))]:
        for col in ["ema20","ema50","s20"]:
            f[f"{p}_{col}"]=align_completed(x[col],ct,period).to_numpy()
        f[f"{p}_up"]=(f[f"{p}_ema20"]>f[f"{p}_ema50"])&(f[f"{p}_s20"]>0)
        f[f"{p}_dn"]=(f[f"{p}_ema20"]<f[f"{p}_ema50"])&(f[f"{p}_s20"]<0)
    f["h4d1_up"]=f.h4_up&f.d1_up; f["h4d1_dn"]=f.h4_dn&f.d1_dn
    f["h1h4_up"]=f.h1_up&f.h4_up; f["h1h4_dn"]=f.h1_dn&f.h4_dn
    return f

def setups(f,bias,session,disp,lb,entry_frac,wait):
    up=(f.h4d1_up if bias=="h4d1" else f.h1h4_up).fillna(False)
    dn=(f.h4d1_dn if bias=="h4d1" else f.h1h4_dn).fillna(False)
    ss=f.primary.fillna(False) if session=="PRIMARY" else pd.Series(True,index=f.index)
    bull=(f.close>f.open)&(f.body_atr>=disp)&(f.body_frac>=0.60)&(f.close>f[f"ph{lb}"])
    bear=(f.close<f.open)&(f.body_atr>=disp)&(f.body_frac>=0.60)&(f.close<f[f"pl{lb}"])
    sig=np.flatnonzero(((up&ss&bull)|(dn&ss&bear)).fillna(False).to_numpy())
    rows=[]
    for i in sig:
        d=1 if bool((up&ss&bull).iat[i]) else -1
        # Last opposite candle before displacement, max 6 M5 bars back.
        ob=None
        for k in range(i-1,max(-1,i-7),-1):
            if k<0:break
            if d==1 and f.close.iat[k]<f.open.iat[k]:
                ob=k;break
            if d==-1 and f.close.iat[k]>f.open.iat[k]:
                ob=k;break
        if ob is None:continue
        o=float(f.open.iat[ob]);c=float(f.close.iat[ob]);h=float(f.high.iat[ob]);l=float(f.low.iat[ob])
        a=float(f.atr14.iat[i])
        if not np.isfinite(a) or a<=0:continue
        # Entry fraction measured from invalidation edge toward proximal edge.
        entry=float(l+entry_frac*(h-l)) if d==1 else float(h-entry_frac*(h-l))
        stop=float(l-0.03*a) if d==1 else float(h+0.03*a)
        risk=(entry-stop) if d==1 else (stop-entry)
        if risk<=0 or risk/a<0.04 or risk/a>1.5:continue
        rows.append({"signal_time":f.index[i],"available":f.index[i]+pd.Timedelta(minutes=5),
                     "direction":d,"entry_limit":entry,"stop":stop,"risk":risk,"wait":wait})
    return pd.DataFrame(rows)

def replay(m5,ss):
    if ss.empty:return pd.DataFrame()
    idx=m5.index;hi=m5.high.to_numpy(float);lo=m5.low.to_numpy(float)
    rows=[];busy=None
    for s in ss.itertuples(index=False):
        st=pd.Timestamp(s.signal_time)
        if st<START or st>=DEV_END:continue
        avail=pd.Timestamp(s.available);start=idx.searchsorted(avail,side="left");expiry=avail+pd.Timedelta(minutes=int(s.wait))
        fill=None
        for j in range(start,len(idx)):
            if idx[j]>=expiry or idx[j]>=DEV_END:break
            if lo[j]<=float(s.entry_limit)<=hi[j]:fill=j;break
        if fill is None:continue
        et=idx[fill]
        if busy is not None and et<=busy:continue
        d=int(s.direction);entry=float(s.entry_limit);stop=float(s.stop);risk=float(s.risk)
        target=entry+d*RR*risk;xp=xt=reason=None
        for j in range(fill,len(idx)):
            t=idx[j]
            if t>=DEV_END:break
            hs=lo[j]<=stop if d==1 else hi[j]>=stop
            ht=hi[j]>=target if d==1 else lo[j]<=target
            if hs:xp=stop;xt=t+pd.Timedelta(minutes=5);reason="SL_same_bar" if ht else "SL";break
            if ht:xp=target;xt=t+pd.Timedelta(minutes=5);reason="TP";break
        if xp is None:continue
        gross=(xp-entry)/risk if d==1 else (entry-xp)/risk
        nr=float(gross-(entry*COST/10000)/risk)
        rows.append({"signal_time":st,"entry_time":et,"exit_time":xt,"direction":"BUY" if d==1 else "SELL",
                     "net_r":nr,"r_multiple":nr,"result":"WIN" if nr>0 else "LOSS","exit_reason":reason})
        busy=xt
    return pd.DataFrame(rows)

def run(data_path,output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path);m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy()
    f=prep(m5)
    specs=[(b,s,d,lb,ef,w) for b in ["h4d1","h1h4"] for s in ["PRIMARY","ALL"] for d in [0.8,1.1] for lb in [12,24] for ef in [0.25,0.5,0.75] for w in [30,90]]
    rows=[];yrs=[];alltr=[]
    for b,s,d,lb,ef,w in specs:
        name=f"OB__{b}__{s}__D{d}__L{lb}__E{ef}__W{w}"
        tr=replay(m5,setups(f,b,s,d,lb,ef,w))
        if not tr.empty:alltr.append(tr.assign(strategy=name))
        ov=metrics(tr);ms=month_stats(tr);y=yearly(tr)
        rows.append({"strategy":name,"bias":b,"session":s,"disp":d,"lookback":lb,"entry_frac":ef,"wait":w,
                     "trades":ov["trades"],"wr":ov["wr"],"expectancy_r":ov["expectancy_r"],"pf":ov["pf"],"dd":ov["max_dd_pct"],
                     "end_rm":ov["end_rm"],**ms,"positive_years":int((y.expectancy_r>0).sum()),"pf_years":int((y.pf>1).sum()),
                     "worst_year_exp":float(y.expectancy_r.min()),"worst_year_dd":float(y.max_dd_pct.max())})
        for rr in y.itertuples(index=False):yrs.append({"strategy":name,**rr._asdict()})
    rd=pd.DataFrame(rows)
    rd["strict"]=(rd.wr>=60)&(rd.dd<=25)&(rd.min_month>=8)&(rd.positive_years.eq(4))&(rd.pf_years.eq(4))
    rd["dist"]=np.maximum(0,60-rd.wr)*3+np.maximum(0,rd.dd-25)+np.maximum(0,8-rd.min_month)*5+(4-rd.positive_years)*20
    ranked=rd.sort_values(["strict","dist","positive_years","min_month","wr","expectancy_r"],ascending=[False,True,False,False,False,False])
    yd=pd.DataFrame(yrs);ranked.to_csv(out/"ranked.csv",index=False);yd.to_csv(out/"yearly.csv",index=False)
    if alltr:pd.concat(alltr,ignore_index=True).to_csv(out/"trades.csv",index=False)
    strict=ranked[ranked.strict]
    lines=["# M5 Order-Block Retest Search — 2017-2020","",
           "Completed HTF bias + M5 displacement/BOS -> last opposite candle -> pending order-block retrace -> wick invalidation -> fixed3R.",
           "No BE/protected SL. 1bp cost, RM100, 5% risk, same-bar stop-first. 2021+ sealed.","",
           f"Specs {len(specs)}; strict passes {len(strict)}.","",
           "| Strategy | Trades | WR | ExpR | PF | DD | Avg/mo | Min/mo | Years |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in ranked.head(30).itertuples(index=False):
        pf="inf" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(f"| {r.strategy} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.dd:.2f}% | {r.avg_month:.2f} | {r.min_month} | {r.positive_years}/4 |")
    for strategy in (strict.strategy.tolist() if len(strict) else ranked.head(8).strategy.tolist()):
        lines+=["",f"## {strategy}","","| Year | Trades | WR | ExpR | PF | DD | RM100 -> |","|---|---:|---:|---:|---:|---:|---:|"]
        for r in yd[yd.strategy==strategy].itertuples(index=False):
            pf="inf" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
            lines.append(f"| {r.year} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.max_dd_pct:.2f}% | RM{r.end_rm:.2f} |")
    report="\n".join(lines)+"\n";(out/"REPORT.md").write_text(report)
    (out/"summary.json").write_text(json.dumps({"specs":len(specs),"strict_count":int(len(strict)),
      "strict":strict.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records"),
      "closest":ranked.head(30).replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")},indent=2))
    print(report)

def main():
    p=argparse.ArgumentParser();p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output",default="reports/historical-first-order-block");a=p.parse_args();run(a.data,a.output)
if __name__=="__main__":main()
