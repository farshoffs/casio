from __future__ import annotations
from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import (
    DEV_START, DEV_END, START_RM, RISK_FRACTION, ROUND_TRIP_BPS,
    atr, di_adx, resample, align_completed, metrics, month_stats, yearly,
)
from .historical_first_session import prep as session_prep


def strict_bias_frame(m5):
    f=resample(m5,"15min")
    f["atr14"]=atr(f,14)
    pdi,mdi,adx=di_adx(f,14); f["pdi"],f["mdi"],f["adx"]=pdi,mdi,adx
    f["body_atr"]=(f.close-f.open).abs()/f.atr14.replace(0,np.nan)
    h4=resample(m5,"4h"); d1=resample(m5,"1D")
    for x in (h4,d1):
        x["ema20"]=x.close.ewm(span=20,adjust=False).mean()
        x["ema50"]=x.close.ewm(span=50,adjust=False).mean()
        x["slope20"]=x.ema20.diff(3)
    ct=f.index+pd.Timedelta(minutes=15)
    for p,x,period in [("h4",h4,pd.Timedelta(hours=4)),("d1",d1,pd.Timedelta(days=1))]:
        for col in ["ema20","ema50","slope20"]:
            f[f"{p}_{col}"]=align_completed(x[col],ct,period).to_numpy()
    f["up"]=(f.d1_ema20>f.d1_ema50)&(f.d1_slope20>0)&(f.h4_ema20>f.h4_ema50)&(f.h4_slope20>0)
    f["dn"]=(f.d1_ema20<f.d1_ema50)&(f.d1_slope20<0)&(f.h4_ema20<f.h4_ema50)&(f.h4_slope20<0)
    return f


def don8_signals(m5):
    f=strict_bias_frame(m5)
    ph=f.high.shift(1).rolling(8).max(); pl=f.low.shift(1).rolling(8).min()
    lo=f.up&(f.close>ph)&(f.adx>=16)&(f.body_atr>=0.25)
    sh=f.dn&(f.close<pl)&(f.adx>=16)&(f.body_atr>=0.25)
    rows=[]
    for i in np.flatnonzero((lo.fillna(False)|sh.fillna(False)).to_numpy()):
        d=1 if bool(lo.iat[i]) else -1; row=f.iloc[i]; a=float(row.atr14)
        recent=f.iloc[max(0,i-5):i+1]
        stop=float(recent.low.min()-0.08*a) if d==1 else float(recent.high.max()+0.08*a)
        level=float(ph.iat[i] if d==1 else pl.iat[i])
        rows.append({"source":"DON8","signal_time":f.index[i],"available":f.index[i]+pd.Timedelta(minutes=15),
                     "direction":d,"entry_level":level,"stop":stop,"atr14":a})
    return pd.DataFrame(rows)


def session_signals(m5,which):
    f=session_prep(m5); mins=f.index.hour*60+f.index.minute
    if which=="ASIA":
        active=(mins>=7*60)&(mins<11*60)
        lo=active&(f.close>f.asia_high)&(f.close.shift(1)<=f.asia_high)&(f.body_atr>=0.25)
        sh=active&(f.close<f.asia_low)&(f.close.shift(1)>=f.asia_low)&(f.body_atr>=0.25)
        long_level=f.asia_high; short_level=f.asia_low
    else:
        active=(mins>=13*60+30)&(mins<16*60+30)
        lo=active&(f.close>f.ny_high)&(f.close.shift(1)<=f.ny_high)&(f.body_atr>=0.25)
        sh=active&(f.close<f.ny_low)&(f.close.shift(1)>=f.ny_low)&(f.body_atr>=0.25)
        long_level=f.ny_high; short_level=f.ny_low
    rows=[]
    for i in np.flatnonzero((lo.fillna(False)|sh.fillna(False)).to_numpy()):
        d=1 if bool(lo.iat[i]) else -1; row=f.iloc[i]; a=float(row.atr14)
        recent=f.iloc[max(0,i-3):i+1]
        stop=float(recent.low.min()-0.08*a) if d==1 else float(recent.high.max()+0.08*a)
        level=float(long_level.iat[i] if d==1 else short_level.iat[i])
        rows.append({"source":which,"signal_time":f.index[i],"available":f.index[i]+pd.Timedelta(minutes=15),
                     "direction":d,"entry_level":level,"stop":stop,"atr14":a})
    return pd.DataFrame(rows)


def combine(parts,name):
    x=pd.concat([p.copy() for p in parts if not p.empty],ignore_index=True)
    if x.empty:return x
    x=x.sort_values(["signal_time","source"]).drop_duplicates(["signal_time","direction"],keep="first")
    x["strategy"]=name
    return x.reset_index(drop=True)


def replay_retest(m5,sigs,horizon_min):
    if sigs.empty:return pd.DataFrame()
    idx=m5.index; lows=m5.low.to_numpy(float); highs=m5.high.to_numpy(float); opens=m5.open.to_numpy(float)
    rows=[]; busy=None
    for s in sigs.itertuples(index=False):
        st=pd.Timestamp(s.signal_time)
        if st<DEV_START or st>=DEV_END: continue
        start=idx.searchsorted(pd.Timestamp(s.available),side="left")
        if start>=len(idx):continue
        if busy is not None and idx[start]<=busy: continue
        deadline=pd.Timestamp(s.available)+pd.Timedelta(minutes=horizon_min)
        fill=None
        level=float(s.entry_level); d=int(s.direction); stop=float(s.stop)
        for j in range(start,len(idx)):
            t=idx[j]
            if t>=deadline or t>=DEV_END: break
            if lows[j]<=level<=highs[j]:
                fill=j; break
        if fill is None: continue
        et=idx[fill]; risk=level-stop if d==1 else stop-level
        if not np.isfinite(risk) or risk<=0: continue
        risk_atr=risk/float(s.atr14)
        if risk_atr<0.20 or risk_atr>2.5: continue
        target=level+d*3*risk; xp=xt=reason=None
        for j in range(fill,len(idx)):
            t=idx[j]
            if t>=DEV_END: break
            hs=(lows[j]<=stop) if d==1 else (highs[j]>=stop)
            ht=(highs[j]>=target) if d==1 else (lows[j]<=target)
            if hs:
                xp=stop; xt=t+pd.Timedelta(minutes=5); reason="SL_same_bar" if ht else "SL"; break
            if ht:
                xp=target; xt=t+pd.Timedelta(minutes=5); reason="TP"; break
        if xp is None: continue
        gross=(xp-level)/risk if d==1 else (level-xp)/risk
        cost=(level*ROUND_TRIP_BPS/10000)/risk; net=float(gross-cost)
        rows.append({"strategy":getattr(s,"strategy",s.source),"source":s.source,"signal_time":st,"entry_time":et,
                     "exit_time":xt,"direction":"BUY" if d==1 else "SELL","entry":level,"stop":stop,"target":target,
                     "risk_atr":risk_atr,"gross_r":float(gross),"cost_r":float(cost),"net_r":net,
                     "result":"WIN" if net>0 else "LOSS","exit_reason":reason})
        busy=xt
    return pd.DataFrame(rows)


def run(data_path,output_dir):
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path); m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy()
    don=don8_signals(m5); asia=session_signals(m5,"ASIA"); ny=session_signals(m5,"NY")
    variants={
        "DON8_RETEST_60":(combine([don],"DON8_RETEST_60"),60),
        "NY_RETEST_60":(combine([ny],"NY_RETEST_60"),60),
        "ASIA_RETEST_60":(combine([asia],"ASIA_RETEST_60"),60),
        "DON8_NY_RETEST_60":(combine([don,ny],"DON8_NY_RETEST_60"),60),
        "DON8_SESSION_RETEST_60":(combine([don,asia,ny],"DON8_SESSION_RETEST_60"),60),
        "DON8_SESSION_RETEST_120":(combine([don,asia,ny],"DON8_SESSION_RETEST_120"),120),
    }
    rows=[]; yrs=[]; months=[]; alltr=[]
    for name,(ss,h) in variants.items():
        tr=replay_retest(m5,ss,h)
        if not tr.empty: alltr.append(tr.assign(strategy=name))
        ov=metrics(tr); ms=month_stats(tr); y=yearly(tr)
        rows.append({"strategy":name,**ov,**ms,"positive_years":int((y.expectancy_r>0).sum()),
                     "pf_gt1_years":int((y.pf>1).sum()),"worst_year_exp_r":float(y.expectancy_r.min()),
                     "worst_year_dd_pct":float(y.max_dd_pct.max())})
        for rr in y.itertuples(index=False): yrs.append({"strategy":name,**rr._asdict()})
        pp=pd.to_datetime(tr.entry_time,utc=True).dt.to_period("M") if not tr.empty else pd.Series([],dtype="period[M]")
        for p in pd.period_range("2017-01","2020-12",freq="M"):
            g=tr[pp==p] if not tr.empty else tr
            months.append({"strategy":name,"month":str(p),**metrics(g)})
    ranked=pd.DataFrame(rows).sort_values(
        ["positive_years","pf_gt1_years","min_month","avg_month","worst_year_exp_r","expectancy_r","pf","worst_year_dd_pct"],
        ascending=[False,False,False,False,False,False,False,True])
    yd=pd.DataFrame(yrs); md=pd.DataFrame(months); td=pd.concat(alltr,ignore_index=True) if alltr else pd.DataFrame()
    ranked.to_csv(out/"ranked.csv",index=False); yd.to_csv(out/"yearly.csv",index=False); md.to_csv(out/"monthly.csv",index=False); td.to_csv(out/"trades.csv",index=False)
    lines=["# Historical-First Phase 8 — breakout retest execution","",
           "2017-2020 only. Fixed 3R, real structural SL, RM100, 5% risk, 1bp cost.","",
           "| Strategy | Trades | Avg/mo | Min/mo | >=8 | Pos years | WR | ExpR | PF | Worst ExpR | Worst DD | End RM |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in ranked.itertuples(index=False):
        pf="∞" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(f"| {r.strategy} | {r.trades} | {r.avg_month:.2f} | {r.min_month} | {r.months_ge8}/48 | {r.positive_years}/4 | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.worst_year_exp_r:+.3f} | {r.worst_year_dd_pct:.2f}% | RM{r.end_rm:.2f} |")
    for strategy in ranked.strategy:
        lines+=["",f"## {strategy}","","| Year | Trades | WR | ExpR | PF | DD | RM100 → |","|---|---:|---:|---:|---:|---:|---:|"]
        for r in yd[yd.strategy==strategy].itertuples(index=False):
            pf="∞" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
            lines.append(f"| {r.year} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.max_dd_pct:.2f}% | RM{r.end_rm:.2f} |")
    report="\n".join(lines)+"\n"; (out/"REPORT.md").write_text(report)
    (out/"summary.json").write_text(json.dumps({"window":"2017-2020","ranked":ranked.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")},indent=2))
    print(report)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output",default="reports/historical-first-retest"); a=p.parse_args(); run(a.data,a.output)
if __name__=="__main__": main()
