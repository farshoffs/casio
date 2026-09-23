from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import DEV_END, atr, resample, align_completed, metrics, month_stats, yearly

START=pd.Timestamp("2017-01-01",tz="UTC")
RR=3.0
ROUND_TRIP_BPS=1.0

@dataclass(frozen=True)
class Card:
    name:str
    bias:str
    sweep_lb:int
    mss_lb:int
    sweep_to_mss:int
    disp_atr:float
    fvg_after_mss:int
    entry_wait:int

def prep(m5):
    f=m5[["open","high","low","close","volume"]].copy()
    f["atr14"]=atr(f,14)
    f["body"]=(f.close-f.open).abs()
    f["range"]=f.high-f.low
    f["body_atr"]=f.body/f.atr14.replace(0,np.nan)
    f["body_frac"]=f.body/f.range.replace(0,np.nan)
    f["bull_fvg"]=f.low>f.high.shift(2)
    f["bear_fvg"]=f.high<f.low.shift(2)
    f["bull_fvg_lo"]=f.high.shift(2); f["bull_fvg_hi"]=f.low
    f["bear_fvg_lo"]=f.high; f["bear_fvg_hi"]=f.low.shift(2)

    for lb in [6,12,24,48]:
        f[f"ph{lb}"]=f.high.shift(1).rolling(lb).max()
        f[f"pl{lb}"]=f.low.shift(1).rolling(lb).min()

    h1=resample(m5,"1h"); h4=resample(m5,"4h"); d1=resample(m5,"1D")
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
    f["h1h4_up"]=f.h1_up&f.h4_up; f["h1h4_dn"]=f.h1_dn&f.h4_dn
    f["h4d1_up"]=f.h4_up&f.d1_up; f["h4d1_dn"]=f.h4_dn&f.d1_dn
    mins=f.index.hour*60+f.index.minute
    f["primary"]=((mins>=7*60)&(mins<11*60))|((mins>=12*60+30)&(mins<16*60+30))
    return f

def cards():
    out=[]
    for bias in ["h1h4","h4d1"]:
      for slb in [12,24]:
       for mlb in [6,12]:
        for smw in [12,24]:
         for disp in [0.6,0.9]:
          for ew in [6,12]:
            name=f"MSS_FVG__{bias}__S{slb}__M{mlb}__SM{smw}__D{disp}__E{ew}"
            out.append(Card(name,bias,slb,mlb,smw,disp,12,ew))
    return out

def find_setups(f,c):
    n=len(f)
    o=f.open.to_numpy(float); h=f.high.to_numpy(float); l=f.low.to_numpy(float); cl=f.close.to_numpy(float)
    atrv=f.atr14.to_numpy(float); ba=f.body_atr.to_numpy(float); bf=f.body_frac.to_numpy(float)
    phs=f[f"ph{c.sweep_lb}"].to_numpy(float); pls=f[f"pl{c.sweep_lb}"].to_numpy(float)
    phm=f[f"ph{c.mss_lb}"].to_numpy(float); plm=f[f"pl{c.mss_lb}"].to_numpy(float)
    bull=f.bull_fvg.fillna(False).to_numpy(bool); bear=f.bear_fvg.fillna(False).to_numpy(bool)
    bfl=f.bull_fvg_lo.to_numpy(float); bfh=f.bull_fvg_hi.to_numpy(float)
    sfl=f.bear_fvg_lo.to_numpy(float); sfh=f.bear_fvg_hi.to_numpy(float)
    prim=f.primary.fillna(False).to_numpy(bool)
    if c.bias=="h1h4":
        up=f.h1h4_up.fillna(False).to_numpy(bool); dn=f.h1h4_dn.fillna(False).to_numpy(bool)
    else:
        up=f.h4d1_up.fillna(False).to_numpy(bool); dn=f.h4d1_dn.fillna(False).to_numpy(bool)

    sw_long=prim&up&(l<pls)&(cl>pls)
    sw_short=prim&dn&(h>phs)&(cl<phs)
    sw_idx=np.flatnonzero(sw_long|sw_short)
    rows=[]

    for i in sw_idx:
        d=1 if sw_long[i] else -1
        sweep_ext=l[i] if d==1 else h[i]

        # Confirm market structure shift after the sweep.
        mss=None
        end=min(n,i+1+c.sweep_to_mss)
        for j in range(i+1,end):
            if d==1 and np.isfinite(phm[j]) and cl[j]>phm[j]:
                mss=j; break
            if d==-1 and np.isfinite(plm[j]) and cl[j]<plm[j]:
                mss=j; break
        if mss is None: continue

        # Find directional FVG created after MSS, requiring displacement on middle candle.
        fg=None
        fend=min(n,mss+1+c.fvg_after_mss)
        for k in range(mss+1,fend):
            mid=k-1
            if mid<1: continue
            qual=np.isfinite(ba[mid]) and np.isfinite(bf[mid]) and ba[mid]>=c.disp_atr and bf[mid]>=0.60
            if not qual: continue
            if d==1 and bull[k] and cl[mid]>o[mid]:
                fg=k; entry=(bfl[k]+bfh[k])/2; break
            if d==-1 and bear[k] and cl[mid]<o[mid]:
                fg=k; entry=(sfl[k]+sfh[k])/2; break
        if fg is None or not np.isfinite(entry): continue

        stop=sweep_ext-0.04*atrv[fg] if d==1 else sweep_ext+0.04*atrv[fg]
        risk=(entry-stop) if d==1 else (stop-entry)
        if not np.isfinite(risk) or risk<=0 or risk/atrv[fg]<0.15 or risk/atrv[fg]>4.0: continue

        # Pending CE fill after FVG candle closes.
        fill=None
        start=fg+1; fend=min(n,start+c.entry_wait)
        for q in range(start,fend):
            if l[q]<=entry<=h[q]:
                fill=q; break
        if fill is None: continue

        rows.append({"card":c.name,"family":"sweep_mss_fvg","signal_time":f.index[i],
                     "entry_time":f.index[fill],"fill_pos":fill,"direction":d,"entry":float(entry),
                     "stop":float(stop),"atr14":float(atrv[fg]),"sweep_pos":i,"mss_pos":mss,"fvg_pos":fg})
    return pd.DataFrame(rows)

def replay(m5,ss):
    if ss.empty: return pd.DataFrame()
    idx=m5.index; h=m5.high.to_numpy(float); l=m5.low.to_numpy(float)
    rows=[]; busy=None
    for s in ss.sort_values("entry_time").itertuples(index=False):
        et=pd.Timestamp(s.entry_time)
        if et<START or et>=DEV_END: continue
        if busy is not None and et<=busy: continue
        d=int(s.direction); entry=float(s.entry); stop=float(s.stop)
        risk=(entry-stop) if d==1 else (stop-entry)
        if risk<=0: continue
        target=entry+d*RR*risk
        xp=xt=reason=None
        for j in range(int(s.fill_pos),len(idx)):
            t=idx[j]
            if t>=DEV_END: break
            hs=l[j]<=stop if d==1 else h[j]>=stop
            ht=h[j]>=target if d==1 else l[j]<=target
            if hs:
                xp=stop; xt=t+pd.Timedelta(minutes=5); reason="SL_same_bar" if ht else "SL"; break
            if ht:
                xp=target; xt=t+pd.Timedelta(minutes=5); reason="TP"; break
        if xp is None: continue
        gross=(xp-entry)/risk if d==1 else (entry-xp)/risk
        cost=(entry*ROUND_TRIP_BPS/10000)/risk
        nr=float(gross-cost)
        rows.append({"card":s.card,"signal_time":s.signal_time,"entry_time":et,"exit_time":xt,
                     "direction":"BUY" if d==1 else "SELL","entry":entry,"stop":stop,"target":target,
                     "net_r":nr,"r_multiple":nr,"result":"WIN" if nr>0 else "LOSS","exit_reason":reason})
        busy=xt
    return pd.DataFrame(rows)

def run(data_path,output_dir):
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path)
    m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy()
    f=prep(m5)
    rows=[]; yrs=[]; alltr=[]
    cs=cards()
    for c in cs:
        tr=replay(m5,find_setups(f,c))
        if not tr.empty: alltr.append(tr.assign(strategy=c.name))
        ov=metrics(tr); ms=month_stats(tr); y=yearly(tr)
        rows.append({"strategy":c.name,"bias":c.bias,"sweep_lb":c.sweep_lb,"mss_lb":c.mss_lb,
                     "sweep_to_mss":c.sweep_to_mss,"disp_atr":c.disp_atr,"entry_wait":c.entry_wait,
                     "trades":ov["trades"],"wr":ov["wr"],"expectancy_r":ov["expectancy_r"],"pf":ov["pf"],
                     "dd":ov["max_dd_pct"],"end_rm":ov["end_rm"],**ms,
                     "positive_years":int((y.expectancy_r>0).sum()),"pf_years":int((y.pf>1).sum()),
                     "worst_year_exp":float(y.expectancy_r.min()),"worst_year_dd":float(y.max_dd_pct.max())})
        for rr in y.itertuples(index=False): yrs.append({"strategy":c.name,**rr._asdict()})
    rd=pd.DataFrame(rows)
    rd["strict"]=(rd.wr>=60)&(rd.dd<=25)&(rd.min_month>=8)&(rd.positive_years.eq(4))&(rd.pf_years.eq(4))
    rd["dist"]=np.maximum(0,60-rd.wr)*3+np.maximum(0,rd.dd-25)+np.maximum(0,8-rd.min_month)*5+(4-rd.positive_years)*20
    ranked=rd.sort_values(["strict","dist","positive_years","min_month","wr","expectancy_r"],ascending=[False,True,False,False,False,False])
    yd=pd.DataFrame(yrs)
    ranked.to_csv(out/"ranked.csv",index=False); yd.to_csv(out/"yearly.csv",index=False)
    if alltr: pd.concat(alltr,ignore_index=True).to_csv(out/"trades.csv",index=False)
    strict=ranked[ranked.strict]
    lines=["# Sweep -> MSS -> FVG -> CE Retrace Search","",
           "2017-2020 only; 2021+ sealed.",
           "M5 execution, completed HTF bias, London/NY sweep, causal MSS, later FVG, then CE pending entry.",
           "Fixed RR3, real sweep-extreme stop + 0.04ATR, 1bp cost, RM100, 5% risk, same-bar stop-first.","",
           f"Cards: {len(cs)}; strict passes: {len(strict)}.","",
           "| Strategy | Trades | WR | ExpR | PF | DD | Avg/mo | Min/mo | Years |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in ranked.head(25).itertuples(index=False):
        pf="inf" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(f"| {r.strategy} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.dd:.2f}% | {r.avg_month:.2f} | {r.min_month} | {r.positive_years}/4 |")
    for strategy in (strict.strategy.tolist() if len(strict) else ranked.head(6).strategy.tolist()):
        lines+=["",f"## {strategy}","","| Year | Trades | WR | ExpR | PF | DD | RM100 -> |","|---|---:|---:|---:|---:|---:|---:|"]
        for r in yd[yd.strategy==strategy].itertuples(index=False):
            pf="inf" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
            lines.append(f"| {r.year} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.max_dd_pct:.2f}% | RM{r.end_rm:.2f} |")
    report="\n".join(lines)+"\n"; (out/"REPORT.md").write_text(report)
    (out/"summary.json").write_text(json.dumps({"cards":len(cs),"strict_count":int(len(strict)),
      "strict":strict.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records"),
      "closest":ranked.head(25).replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")},indent=2))
    print(report)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output",default="reports/historical-first-mss-fvg")
    a=p.parse_args(); run(a.data,a.output)
if __name__=="__main__": main()
