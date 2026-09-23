from __future__ import annotations
from pathlib import Path
import argparse,json,math
import numpy as np
import pandas as pd
from .v3_core import load_m5_csv
from .historical_first_2017_2020 import DEV_END,atr,resample,align_completed,metrics,month_stats,yearly

START=pd.Timestamp("2017-01-01",tz="UTC");RR=3.0;COST=1.0

def prep(m5):
    f=m5[["open","high","low","close","volume"]].copy()
    f["atr14"]=atr(f,14);f["range"]=f.high-f.low;f["body"]=(f.close-f.open).abs()
    f["body_atr"]=f.body/f.atr14.replace(0,np.nan)
    f["inside"]=(f.high<f.high.shift(1))&(f.low>f.low.shift(1))
    for n in [4,7]:
        f[f"nr{n}"]=f.range==f.range.rolling(n).min()
    for lb in [6,12,24]:
        f[f"ph{lb}"]=f.high.shift(1).rolling(lb).max();f[f"pl{lb}"]=f.low.shift(1).rolling(lb).min()
    mins=f.index.hour*60+f.index.minute
    f["primary"]=((mins>=7*60)&(mins<11*60))|((mins>=12*60+30)&(mins<16*60+30))
    h1=resample(m5,"1h");h4=resample(m5,"4h");d1=resample(m5,"1D")
    for x in (h1,h4,d1):
        x["ema20"]=x.close.ewm(span=20,adjust=False).mean();x["ema50"]=x.close.ewm(span=50,adjust=False).mean()
        x["s20"]=x.ema20.diff(3)
    ct=f.index+pd.Timedelta(minutes=5)
    for p,x,period in [("h1",h1,pd.Timedelta(hours=1)),("h4",h4,pd.Timedelta(hours=4)),("d1",d1,pd.Timedelta(days=1))]:
        for col in ["ema20","ema50","s20"]:f[f"{p}_{col}"]=align_completed(x[col],ct,period).to_numpy()
        f[f"{p}_up"]=(f[f"{p}_ema20"]>f[f"{p}_ema50"])&(f[f"{p}_s20"]>0)
        f[f"{p}_dn"]=(f[f"{p}_ema20"]<f[f"{p}_ema50"])&(f[f"{p}_s20"]<0)
    f["h1h4_up"]=f.h1_up&f.h4_up;f["h1h4_dn"]=f.h1_dn&f.h4_dn
    f["h4d1_up"]=f.h4_up&f.d1_up;f["h4d1_dn"]=f.h4_dn&f.d1_dn
    f["triple_up"]=f.h1_up&f.h4_up&f.d1_up;f["triple_dn"]=f.h1_dn&f.h4_dn&f.d1_dn
    return f

def bias(f,b):
    if b=="h1h4":return f.h1h4_up.fillna(False),f.h1h4_dn.fillna(False)
    if b=="h4d1":return f.h4d1_up.fillna(False),f.h4d1_dn.fillna(False)
    return f.triple_up.fillna(False),f.triple_dn.fillna(False)

def masks(f,fam,b,sess,lb,nr):
    up,dn=bias(f,b);ss=f.primary.fillna(False) if sess=="PRIMARY" else pd.Series(True,index=f.index)
    bull=f.close>f.open;bear=f.close<f.open
    if fam=="nr_break":
        comp=f[f"nr{nr}"].shift(1).fillna(False)
        lo=up&ss&comp&(f.close>f.high.shift(1))&bull
        sh=dn&ss&comp&(f.close<f.low.shift(1))&bear
    elif fam=="inside_break":
        ins=f.inside.shift(1).fillna(False)
        lo=up&ss&ins&(f.close>f.high.shift(1))&bull
        sh=dn&ss&ins&(f.close<f.low.shift(1))&bear
    elif fam=="three_pull":
        # three counter-trend closes, then continuation break of last pullback candle.
        red=(f.close<f.open);green=(f.close>f.open)
        pull_long=red.shift(1)&red.shift(2)&red.shift(3)
        pull_short=green.shift(1)&green.shift(2)&green.shift(3)
        lo=up&ss&pull_long&bull&(f.close>f.high.shift(1))
        sh=dn&ss&pull_short&bear&(f.close<f.low.shift(1))
    elif fam=="two_pull":
        red=(f.close<f.open);green=(f.close>f.open)
        lo=up&ss&red.shift(1)&red.shift(2)&bull&(f.close>f.high.shift(1))
        sh=dn&ss&green.shift(1)&green.shift(2)&bear&(f.close<f.low.shift(1))
    elif fam=="swing_break":
        lo=up&ss&bull&(f.close>f[f"ph{lb}"])&(f.body_atr>=0.35)
        sh=dn&ss&bear&(f.close<f[f"pl{lb}"])&(f.body_atr>=0.35)
    else:raise ValueError(fam)
    return lo.fillna(False),sh.fillna(False)

def replay(m5,f,lo,sh,stopbars):
    idx=m5.index;hi=m5.high.to_numpy(float);low=m5.low.to_numpy(float);op=m5.open.to_numpy(float)
    sig=np.flatnonzero((lo|sh).to_numpy());setups=[]
    for i in sig:
        d=1 if bool(lo.iat[i]) else -1;a=float(f.atr14.iat[i])
        pos=idx.searchsorted(f.index[i]+pd.Timedelta(minutes=5),side="left")
        if pos>=len(idx) or idx[pos]>=DEV_END or not np.isfinite(a) or a<=0:continue
        recent=f.iloc[max(0,i-stopbars+1):i+1]
        entry=float(op[pos]);stop=float(recent.low.min()-0.03*a) if d==1 else float(recent.high.max()+0.03*a)
        risk=(entry-stop) if d==1 else (stop-entry)
        if risk<=0 or risk/a<0.08 or risk/a>1.6:continue
        setups.append((f.index[i],pos,d,entry,stop,risk))
    rows=[];busy=None
    for st,pos,d,entry,stop,risk in setups:
        et=idx[pos]
        if et<START:continue
        if busy is not None and et<=busy:continue
        target=entry+d*RR*risk;xp=xt=reason=None
        for j in range(pos,len(idx)):
            if idx[j]>=DEV_END:break
            hs=low[j]<=stop if d==1 else hi[j]>=stop
            ht=hi[j]>=target if d==1 else low[j]<=target
            if hs:xp=stop;xt=idx[j]+pd.Timedelta(minutes=5);reason="SL_same_bar" if ht else "SL";break
            if ht:xp=target;xt=idx[j]+pd.Timedelta(minutes=5);reason="TP";break
        if xp is None:continue
        nr=float(((xp-entry)/risk if d==1 else (entry-xp)/risk)-(entry*COST/10000)/risk)
        rows.append({"signal_time":st,"entry_time":et,"exit_time":xt,"direction":"BUY" if d==1 else "SELL",
                     "net_r":nr,"r_multiple":nr,"result":"WIN" if nr>0 else "LOSS","exit_reason":reason})
        busy=xt
    return pd.DataFrame(rows)

def run(data_path,output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path);m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy();f=prep(m5)
    specs=[]
    for b in ["h1h4","h4d1","triple"]:
      for s in ["PRIMARY","ALL"]:
       for fam in ["nr_break","inside_break","two_pull","three_pull"]:
        for stopbars in [2,3,5]:
         for nr in ([4,7] if fam=="nr_break" else [4]):
          specs.append((fam,b,s,12,nr,stopbars))
       for lb in [6,12,24]:
        for stopbars in [2,3,5]:specs.append(("swing_break",b,s,lb,4,stopbars))
    rows=[];yrs=[];alltr=[]
    for fam,b,s,lb,nr,sb in specs:
        name=f"PAT__{fam}__{b}__{s}__L{lb}__N{nr}__S{sb}"
        lo,sh=masks(f,fam,b,s,lb,nr);tr=replay(m5,f,lo,sh,sb)
        if not tr.empty:alltr.append(tr.assign(strategy=name))
        ov=metrics(tr);ms=month_stats(tr);y=yearly(tr)
        rows.append({"strategy":name,"family":fam,"bias":b,"session":s,"lookback":lb,"nr":nr,"stopbars":sb,
                     "trades":ov["trades"],"wr":ov["wr"],"expectancy_r":ov["expectancy_r"],"pf":ov["pf"],"dd":ov["max_dd_pct"],
                     "end_rm":ov["end_rm"],**ms,"positive_years":int((y.expectancy_r>0).sum()),"pf_years":int((y.pf>1).sum())})
        for rr in y.itertuples(index=False):yrs.append({"strategy":name,**rr._asdict()})
    rd=pd.DataFrame(rows);rd["strict"]=(rd.wr>=60)&(rd.dd<=25)&(rd.min_month>=8)&(rd.positive_years.eq(4))&(rd.pf_years.eq(4))
    rd["dist"]=np.maximum(0,60-rd.wr)*3+np.maximum(0,rd.dd-25)+np.maximum(0,8-rd.min_month)*5+(4-rd.positive_years)*20
    ranked=rd.sort_values(["strict","dist","positive_years","min_month","wr","expectancy_r"],ascending=[False,True,False,False,False,False])
    yd=pd.DataFrame(yrs);ranked.to_csv(out/"ranked.csv",index=False);yd.to_csv(out/"yearly.csv",index=False)
    if alltr:pd.concat(alltr,ignore_index=True).to_csv(out/"trades.csv",index=False)
    strict=ranked[ranked.strict]
    lines=["# M5 Classical Price-Action Pattern Search","",
           "NR4/NR7, inside-bar breakout, 2/3-bar pullback continuation, swing breakout. Completed HTF bias, fixed3R, structural SL.",
           "2017-2020 only; 1bp cost; 5% risk; same-bar stop-first; 2021+ sealed.","",
           f"Specs {len(specs)}; strict passes {len(strict)}.","",
           "| Strategy | Trades | WR | ExpR | PF | DD | Avg/mo | Min/mo | Years |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in ranked.head(30).itertuples(index=False):
        pf="inf" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(f"| {r.strategy} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.dd:.2f}% | {r.avg_month:.2f} | {r.min_month} | {r.positive_years}/4 |")
    report="\n".join(lines)+"\n";(out/"REPORT.md").write_text(report)
    (out/"summary.json").write_text(json.dumps({"specs":len(specs),"strict_count":int(len(strict)),
      "strict":strict.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records"),
      "closest":ranked.head(30).replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")},indent=2))
    print(report)

def main():
    p=argparse.ArgumentParser();p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output",default="reports/historical-first-patterns");a=p.parse_args();run(a.data,a.output)
if __name__=="__main__":main()
