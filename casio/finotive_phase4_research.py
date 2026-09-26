from __future__ import annotations

from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

from .v3_core import _atr, _resample, load_m5_csv

START_BALANCE=2500.0
RISK=0.005
FLOOR=5.0
COST_R=0.05

def _safe(x):
    if isinstance(x,dict): return {str(k):_safe(v) for k,v in x.items()}
    if isinstance(x,list): return [_safe(v) for v in x]
    if isinstance(x,pd.Timestamp): return x.isoformat()
    if isinstance(x,np.integer): return int(x)
    if isinstance(x,(np.floating,float)):
        y=float(x); return y if math.isfinite(y) else None
    if isinstance(x,(np.bool_,bool)): return bool(x)
    return x

def _atr_series(df,n=14):
    return _atr(df,n)

def _trading_day(ts):
    ny=pd.Timestamp(ts).tz_convert("America/New_York")
    return (ny-pd.Timedelta(hours=17)).strftime("%Y-%m-%d")

def _replay_level(m5,start_i,d,entry,stop,target,maxbars):
    risk=abs(entry-stop)
    for j in range(start_i,min(len(m5),start_i+maxbars)):
        lo=float(m5.low.iat[j]); hi=float(m5.high.iat[j]); cl=float(m5.close.iat[j])
        hs=lo<=stop if d==1 else hi>=stop
        ht=hi>=target if d==1 else lo<=target
        if hs and ht:return j,-1.0,"stop_same_bar"
        if hs:return j,-1.0,"stop"
        if ht:return j,abs(target-entry)/risk,"target"
        if j==min(len(m5),start_i+maxbars)-1:return j,(cl-entry)/risk*d,"time"
    return start_i,0.0,"time"

def h1_choch_fvg_fade(symbol,m5,target_r=2.0):
    h=_resample(m5,"1h")
    h["atr"]=_atr_series(h,14)
    # causal 10-bar local structure proxy. New break + three-candle FVG is the
    # textbook direction; we test the empirically suggested opposite direction.
    h["hi10"]=h.high.shift(1).rolling(10,min_periods=10).max()
    h["lo10"]=h.low.shift(1).rolling(10,min_periods=10).min()
    bull_break=(h.close>h.hi10)&(h.close>h.open)
    bear_break=(h.close<h.lo10)&(h.close<h.open)
    bull_fvg=(h.low>h.high.shift(2))&bull_break
    bear_fvg=(h.high<h.low.shift(2))&bear_break

    pos=pd.Series(np.arange(len(m5)),index=m5.index)
    rows=[]
    for i in np.flatnonzero((bull_fvg|bear_fvg).fillna(False).to_numpy()):
        if i+1>=len(h): continue
        textbook=1 if bool(bull_fvg.iat[i]) else -1
        d=-textbook
        # textbook FVG midpoint; wait for a retrace to the gap, then fade it.
        if textbook==1:
            zone_lo=float(h.high.iat[i-2]); zone_hi=float(h.low.iat[i])
        else:
            zone_lo=float(h.high.iat[i]); zone_hi=float(h.low.iat[i-2])
        mid=(zone_lo+zone_hi)/2
        signal_close=h.index[i]+pd.Timedelta(hours=1)
        candidates=m5.index[(m5.index>=signal_close)&(m5.index<signal_close+pd.Timedelta(hours=12))]
        fill_i=None
        for ts in candidates:
            j=int(pos.loc[ts])
            if float(m5.low.iat[j])<=mid<=float(m5.high.iat[j]):
                fill_i=j;break
        if fill_i is None:continue
        entry=mid
        a=float(h.atr.iat[i])
        if not np.isfinite(a) or a<=0:continue
        # minimum stop floor addresses the tight-stop/commission issue noted in
        # the empirical study. Stop sits beyond signal extreme or >=0.35 H1 ATR.
        if d==1:
            structural=float(h.low.iloc[max(0,i-2):i+1].min())
            stop=min(structural-.05*a,entry-.35*a)
        else:
            structural=float(h.high.iloc[max(0,i-2):i+1].max())
            stop=max(structural+.05*a,entry+.35*a)
        risk=abs(entry-stop)
        if risk<=0:continue
        target=entry+d*target_r*risk
        j,r,reason=_replay_level(m5,fill_i,d,entry,stop,target,72)
        rows.append({"symbol":symbol,"engine":f"{symbol}_H1_CHOCH_FVG_FADE_{target_r:g}R",
                     "entry_time":m5.index[fill_i],"exit_time":m5.index[j]+pd.Timedelta(minutes=5),
                     "direction":d,"net_r":float(r-COST_R),"reason":reason})
    return pd.DataFrame(rows)

def asia_sweep_continuation(symbol,m5,target_r=2.0):
    # Test the empirical contrarian-to-SMC finding: a sweep of an Asian-session
    # extreme predicts continuation through the swept side, not reversal.
    idx=m5.index
    day=pd.Series(idx.floor("D"),index=idx)
    asia=(idx.hour>=2)&(idx.hour<7)  # exclude Finotive low-liquidity 22:00-01:59 UTC
    ar=m5[asia].groupby(day[asia]).agg(ah=("high","max"),al=("low","min"))
    dser=pd.Series(idx.floor("D"),index=idx)
    ah=dser.map(ar.ah); al=dser.map(ar.al)
    h1=_resample(m5,"1h")
    h1atr=_atr_series(h1,14).reindex(idx,method="ffill")
    lon=idx.tz_convert("Europe/London")
    lm=lon.hour*60+lon.minute
    window=(lm>=7*60)&(lm<12*60)
    up=window&ah.notna()&(m5.high>ah)&(m5.close>ah)
    dn=window&al.notna()&(m5.low<al)&(m5.close<al)
    rows=[]
    for i in np.flatnonzero((up|dn).fillna(False).to_numpy()):
        if i+1>=len(m5):continue
        d=1 if bool(up.iat[i]) else -1
        entry=float(m5.open.iat[i+1]); a=float(h1atr.iat[i])
        if not np.isfinite(a) or a<=0:continue
        # one signal per trading day/side is enforced later through dedupe.
        dist=max(.35*a, abs(entry-(float(ah.iat[i]) if d==1 else float(al.iat[i]))))
        stop=entry-d*dist; target=entry+d*target_r*dist
        j,r,reason=_replay_level(m5,i+1,d,entry,stop,target,72)
        rows.append({"symbol":symbol,"engine":f"{symbol}_ASIA_SWEEP_CONT_{target_r:g}R",
                     "entry_time":m5.index[i+1],"exit_time":m5.index[j]+pd.Timedelta(minutes=5),
                     "direction":d,"net_r":float(r-COST_R),"reason":reason})
    x=pd.DataFrame(rows)
    if not x.empty:
        x["td"]=x.entry_time.map(_trading_day)
        x=x.drop_duplicates(["td","direction"],keep="first").drop(columns="td")
    return x

def equal_swing_sweep_continuation(symbol,m5,target_r=2.0):
    # M15 equal-high/low cluster -> break and acceptance -> continuation.
    q=_resample(m5,"15min")
    q["atr"]=_atr_series(q,14)
    ph=q.high.shift(1).rolling(20,min_periods=20).max()
    pl=q.low.shift(1).rolling(20,min_periods=20).min()
    # Previous range extreme must have been touched at least twice within 0.12 ATR.
    touches_hi=((q.high.shift(1).rolling(20).max()-q.high.shift(1).rolling(20).min())*0) # aligned shell
    hi_tol=.12*q.atr
    lo_tol=.12*q.atr
    hi_count=pd.Series(0,index=q.index,dtype=float)
    lo_count=pd.Series(0,index=q.index,dtype=float)
    for k in range(1,21):
        hi_count += ((ph-q.high.shift(k)).abs()<=hi_tol).fillna(False).astype(int)
        lo_count += ((q.low.shift(k)-pl).abs()<=lo_tol).fillna(False).astype(int)
    up=(hi_count>=2)&(q.close>ph+.03*q.atr)&(q.close>q.open)
    dn=(lo_count>=2)&(q.close<pl-.03*q.atr)&(q.close<q.open)

    pos=pd.Series(np.arange(len(m5)),index=m5.index)
    rows=[]
    for i in np.flatnonzero((up|dn).fillna(False).to_numpy()):
        d=1 if bool(up.iat[i]) else -1
        close_ts=q.index[i]+pd.Timedelta(minutes=15)
        cand=m5.index[m5.index>=close_ts]
        if not len(cand):continue
        j0=int(pos.loc[cand[0]])
        entry=float(m5.open.iat[j0]); a=float(q.atr.iat[i])
        if not np.isfinite(a) or a<=0:continue
        level=float(ph.iat[i] if d==1 else pl.iat[i])
        dist=max(.35*a,abs(entry-level)+.08*a)
        stop=entry-d*dist; target=entry+d*target_r*dist
        j,r,reason=_replay_level(m5,j0,d,entry,stop,target,96)
        rows.append({"symbol":symbol,"engine":f"{symbol}_EQ_SWEEP_CONT_{target_r:g}R",
                     "entry_time":m5.index[j0],"exit_time":m5.index[j]+pd.Timedelta(minutes=5),
                     "direction":d,"net_r":float(r-COST_R),"reason":reason})
    return pd.DataFrame(rows)

def metrics(tr,a,b):
    if tr is None or tr.empty:return {"trades":0,"exp":None,"pf":None,"wr":None}
    t=pd.to_datetime(tr.entry_time,utc=True)
    r=pd.to_numeric(tr.loc[(t>=pd.Timestamp(a,tz="UTC"))&(t<pd.Timestamp(b,tz="UTC")),"net_r"],errors="coerce").dropna()
    if r.empty:return {"trades":0,"exp":None,"pf":None,"wr":None}
    w=r[r>0];l=r[r<0]
    return {"trades":int(len(r)),"exp":float(r.mean()),"pf":float(w.sum()/(-l.sum())) if len(l) else 999.0,"wr":float((r>0).mean()*100)}

def valid_pre2026(tr):
    d=metrics(tr,"2020-01-01","2023-01-01");v=metrics(tr,"2023-01-01","2026-01-01")
    ok=d["trades"]>=20 and v["trades"]>=15 and (d["exp"] or -9)>0 and (v["exp"] or -9)>0 and (d["pf"] or 0)>1 and (v["pf"] or 0)>1
    return ok,d,v

def sim_month(tr,month):
    end=month+pd.offsets.MonthBegin(1)
    if tr.empty:x=tr.copy()
    else:
        t=pd.to_datetime(tr.entry_time,utc=True);x=tr[(t>=month)&(t<end)].sort_values(["entry_time","engine"]).copy()
    eq=START_BALANCE;peak=eq;free=pd.Timestamp("1900-01-01",tz="UTC")
    cur=None;day_start=eq;day_pnl=0.;losses=0;mpd=0;worst=0.;maxdd=0.;used=0;breach=False
    def finish():
        nonlocal mpd,worst
        if cur is None:return
        pi=day_pnl/START_BALANCE*100;pd_=day_pnl/day_start*100 if day_start else 0
        worst=min(worst,pd_)
        if pi>=.5:mpd+=1
    for r in x.itertuples(index=False):
        et=pd.Timestamp(r.entry_time);xt=pd.Timestamp(r.exit_time)
        if et<free:continue
        td=_trading_day(et)
        if td!=cur:
            finish()
            if (eq/START_BALANCE-1)*100>=FLOOR and mpd>=5:break
            cur=td;day_start=eq;day_pnl=0.;losses=0
        if losses>=2:continue
        pnl=eq*RISK*float(r.net_r);eq+=pnl;day_pnl+=pnl;used+=1;free=xt
        if float(r.net_r)<0:losses+=1
        peak=max(peak,eq);maxdd=max(maxdd,(peak-eq)/peak*100)
        if (day_start-eq)/day_start*100>=3 or (START_BALANCE-eq)/START_BALANCE*100>=6:
            breach=True;break
    finish()
    ret=(eq/START_BALANCE-1)*100
    return {"month":month.strftime("%Y-%m"),"return_pct":ret,"mpd":mpd,"trades":used,"max_dd":maxdd,"worst_day":worst,"breach":breach,"pass5":ret>=5 and mpd>=5 and not breach}

def run(eur_path,aud_path,jpy_path,output):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    data={"EURUSD":load_m5_csv(eur_path),"AUDUSD":load_m5_csv(aud_path),"USDJPY":load_m5_csv(jpy_path)}
    sleeves={}
    for sym,df in data.items():
        for rr in (1.5,2.0,2.5):
            if sym in ("EURUSD","AUDUSD"):
                sleeves[f"{sym}_CHOCH_FVG_FADE_{rr:g}R"]=h1_choch_fvg_fade(sym,df,rr)
            sleeves[f"{sym}_ASIA_SWEEP_CONT_{rr:g}R"]=asia_sweep_continuation(sym,df,rr)
            sleeves[f"{sym}_EQ_SWEEP_CONT_{rr:g}R"]=equal_swing_sweep_continuation(sym,df,rr)

    rows=[];valid=[]
    for n,tr in sleeves.items():
        ok,d,v=valid_pre2026(tr)
        rows.append({"sleeve":n,"valid":ok,**{f"disc_{k}":z for k,z in d.items()},**{f"val_{k}":z for k,z in v.items()}})
        if ok:valid.append(n)
    vf=pd.DataFrame(rows).sort_values(["valid","val_exp","disc_exp"],ascending=[False,False,False],na_position="last")
    vf.to_csv(out/"validation.csv",index=False)

    # Do not stack multiple RR variants of the same engine. Choose by worst pre-2026
    # expectancy only, then freeze before the 2026 holdout.
    selected=[]
    if not vf.empty:
        q=vf[vf.valid].copy();q["robust"]=q[["disc_exp","val_exp"]].min(axis=1)
        q["family"]=q.sleeve.str.replace(r"_[0-9.]+R$","",regex=True)
        selected=q.sort_values("robust",ascending=False).groupby("family",as_index=False).head(1).sleeve.tolist()

    xs=[sleeves[n] for n in selected if not sleeves[n].empty]
    pt=pd.concat(xs,ignore_index=True).sort_values("entry_time") if xs else pd.DataFrame(columns=["entry_time","exit_time","net_r","engine"])
    pt.to_csv(out/"selected_trades.csv",index=False)

    months=list(pd.date_range(pd.Timestamp("2026-01-01",tz="UTC"),pd.Timestamp("2026-09-01",tz="UTC"),freq="MS"))
    ms=[sim_month(pt,m) for m in months]
    mf=pd.DataFrame(ms);mf.to_csv(out/"monthly_2026.csv",index=False)
    summary={"selected":selected,"months_pass5":int(sum(x["pass5"] for x in ms)),"all_pass":bool(all(x["pass5"] for x in ms)) if ms else False,
             "worst_month":float(min(x["return_pct"] for x in ms)) if ms else None,"avg_month":float(np.mean([x["return_pct"] for x in ms])) if ms else None}
    (out/"summary.json").write_text(json.dumps(_safe(summary),indent=2),encoding="utf-8")
    report="\n".join(["# CASIO Phase 4 — SMC Inversion / Sweep Continuation","",
        "Selection: 2020-22 discovery + 2023-25 validation only. 2026 is untouched holdout.",
        "All setups avoid the Finotive 22:00-01:59 UTC low-liquidity entry window by construction where session-specific.",
        "","## Validation","~~~text",vf.to_string(index=False),"~~~","","Selected: "+", ".join(selected),
        "","## 2026 monthly floor","~~~text",mf.to_string(index=False),"~~~","",json.dumps(_safe(summary),indent=2)])
    (out/"REPORT.md").write_text(report,encoding="utf-8");print(report)
    return summary

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--eur",required=True);p.add_argument("--aud",required=True);p.add_argument("--jpy",required=True);p.add_argument("--output",default="reports/finotive-phase4")
    a=p.parse_args();run(a.eur,a.aud,a.jpy,a.output)

if __name__=="__main__":main()
