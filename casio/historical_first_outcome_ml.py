from __future__ import annotations
from pathlib import Path
import argparse,json,math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import DEV_END,atr,di_adx,resample,align_completed,rsi,metrics,month_stats,yearly

DEV_START=pd.Timestamp("2017-01-01",tz="UTC")
TRAIN_START=pd.Timestamp("2013-01-01",tz="UTC")
RR=3.0
COST=1.0

def prep(m5):
    f=resample(m5,"15min")
    f["atr14"]=atr(f,14)
    pdi,mdi,adx=di_adx(f,14);f["pdi"],f["mdi"],f["adx"]=pdi,mdi,adx
    f["rsi8"]=rsi(f.close,8);f["rsi14"]=rsi(f.close,14)
    for n in [8,20,50,100]:
        f[f"ema{n}"]=f.close.ewm(span=n,adjust=False).mean()
    f["body"]=(f.close-f.open).abs();f["range"]=f.high-f.low
    f["body_atr"]=f.body/f.atr14.replace(0,np.nan)
    f["range_atr"]=f.range/f.atr14.replace(0,np.nan)
    f["close_pos"]=(f.close-f.low)/f.range.replace(0,np.nan)
    f["vol_med20"]=f.volume.rolling(20,min_periods=10).median()
    f["vol_ratio"]=f.volume/f.vol_med20.replace(0,np.nan)
    f["atr_med96"]=f.atr14.rolling(96,min_periods=48).median()
    f["atr_regime"]=f.atr14/f.atr_med96.replace(0,np.nan)
    for k in [1,2,3,4,6,8,12,16,24]:
        f[f"ret{k}"]=f.close.pct_change(k)*100
    for lb in [4,8,12,20,32]:
        f[f"ph{lb}"]=f.high.shift(1).rolling(lb).max()
        f[f"pl{lb}"]=f.low.shift(1).rolling(lb).min()
        f[f"pos{lb}"]=(f.close-f[f"pl{lb}"])/(f[f"ph{lb}"]-f[f"pl{lb}"]).replace(0,np.nan)

    h1=resample(m5,"1h");h4=resample(m5,"4h");d1=resample(m5,"1D")
    for x in (h1,h4,d1):
        x["atr14"]=atr(x,14)
        _,_,x["adx"]=di_adx(x,14)
        x["ema20"]=x.close.ewm(span=20,adjust=False).mean()
        x["ema50"]=x.close.ewm(span=50,adjust=False).mean()
        x["ema100"]=x.close.ewm(span=100,adjust=False).mean()
        x["s20"]=x.ema20.diff(3)
    ct=f.index+pd.Timedelta(minutes=15)
    for p,x,period in [("h1",h1,pd.Timedelta(hours=1)),("h4",h4,pd.Timedelta(hours=4)),("d1",d1,pd.Timedelta(days=1))]:
        for col in ["atr14","adx","ema20","ema50","ema100","s20","close"]:
            f[f"{p}_{col}"]=align_completed(x[col],ct,period).to_numpy()
        f[f"{p}_sep"]=(f[f"{p}_ema20"]-f[f"{p}_ema50"])/f[f"{p}_atr14"].replace(0,np.nan)
        f[f"{p}_dist20"]=(f.close-f[f"{p}_ema20"])/f[f"{p}_atr14"].replace(0,np.nan)

    mins=f.index.hour*60+f.index.minute
    f["primary"]=((mins>=7*60)&(mins<11*60))|((mins>=12*60+30)&(mins<16*60+30))
    f["hour"]=f.index.hour+f.index.minute/60
    f["dow"]=f.index.dayofweek
    return f

def candidates(m5,f,lookback):
    idx=m5.index;hi=m5.high.to_numpy(float);lo=m5.low.to_numpy(float);op=m5.open.to_numpy(float)
    rows=[]
    valid=np.flatnonzero(f.primary.fillna(False).to_numpy())
    for i in valid:
        if i<lookback-1:continue
        st=f.index[i];avail=st+pd.Timedelta(minutes=15)
        pos=idx.searchsorted(avail,side="left")
        if pos>=len(idx) or idx[pos]>=DEV_END:continue
        a=float(f.atr14.iat[i])
        if not np.isfinite(a) or a<=0:continue
        recent=f.iloc[i-lookback+1:i+1]
        for d in (1,-1):
            entry=float(op[pos])
            stop=float(recent.low.min()-0.05*a) if d==1 else float(recent.high.max()+0.05*a)
            risk=(entry-stop) if d==1 else (stop-entry)
            if not np.isfinite(risk) or risk<=0 or risk/a<0.12 or risk/a>1.8:continue
            target=entry+d*RR*risk;xp=xt=None
            # independent hypothetical label
            for j in range(pos,len(idx)):
                t=idx[j]
                if t>=DEV_END:break
                hs=lo[j]<=stop if d==1 else hi[j]>=stop
                ht=hi[j]>=target if d==1 else lo[j]<=target
                if hs:xp=stop;xt=t+pd.Timedelta(minutes=5);break
                if ht:xp=target;xt=t+pd.Timedelta(minutes=5);break
            if xp is None:continue
            gross=(xp-entry)/risk if d==1 else (entry-xp)/risk
            nr=float(gross-(entry*COST/10000)/risk)
            rows.append({"fi":i,"signal_time":st,"entry_time":idx[pos],"exit_time":xt,"direction":d,
                         "entry":entry,"stop":stop,"target":target,"risk_atr":risk/a,"net_r":nr,
                         "result":1 if nr>0 else 0})
    return pd.DataFrame(rows)

def features(cand,f):
    ix=cand.fi.to_numpy(int);d=cand.direction.to_numpy(float)
    z=f.iloc[ix]
    X=pd.DataFrame(index=cand.index)
    X["direction"]=d
    X["risk_atr"]=cand.risk_atr.to_numpy(float)
    X["hour_sin"]=np.sin(2*np.pi*z.hour.to_numpy(float)/24)
    X["hour_cos"]=np.cos(2*np.pi*z.hour.to_numpy(float)/24)
    X["dow_sin"]=np.sin(2*np.pi*z.dow.to_numpy(float)/7)
    X["dow_cos"]=np.cos(2*np.pi*z.dow.to_numpy(float)/7)
    for col in ["adx","rsi8","rsi14","body_atr","range_atr","close_pos","vol_ratio","atr_regime",
                "h1_adx","h4_adx","d1_adx"]:
        X[col]=pd.to_numeric(z[col],errors="coerce").to_numpy()
    X["pdi_gap_dir"]=(z.pdi.to_numpy()-z.mdi.to_numpy())*d
    for col in ["ret1","ret2","ret3","ret4","ret6","ret8","ret12","ret16","ret24"]:
        X[col+"_dir"]=pd.to_numeric(z[col],errors="coerce").to_numpy()*d
    for n in [8,20,50,100]:
        X[f"ema{n}_dist_dir"]=((z.close-z[f"ema{n}"])/z.atr14).to_numpy()*d
    for p in ["h1","h4","d1"]:
        X[f"{p}_sep_dir"]=pd.to_numeric(z[f"{p}_sep"],errors="coerce").to_numpy()*d
        X[f"{p}_dist20_dir"]=pd.to_numeric(z[f"{p}_dist20"],errors="coerce").to_numpy()*d
    for lb in [4,8,12,20,32]:
        # Directional location: long high position good positive, short low position mirrored.
        pos=pd.to_numeric(z[f"pos{lb}"],errors="coerce").to_numpy()
        X[f"pos{lb}_dir"]=np.where(d>0,pos,1-pos)
    return X.replace([np.inf,-np.inf],np.nan).fillna(0.0)

def live_trades(g):
    g=g[g.accept & g.exit_time.notna()].sort_values(["entry_time","score"],ascending=[True,False])
    rows=[];busy=None
    # Same timestamp can have both directions; take higher score only.
    g=g.drop_duplicates("entry_time",keep="first")
    for r in g.itertuples(index=False):
        et=pd.Timestamp(r.entry_time)
        if busy is not None and et<=busy:continue
        rows.append({"signal_time":r.signal_time,"entry_time":et,"exit_time":r.exit_time,
                     "direction":"BUY" if int(r.direction)==1 else "SELL","net_r":float(r.net_r),
                     "r_multiple":float(r.net_r),"result":"WIN" if float(r.net_r)>0 else "LOSS","score":float(r.score)})
        busy=pd.Timestamp(r.exit_time)
    return pd.DataFrame(rows)

def run(data_path,output_dir):
    from sklearn.ensemble import HistGradientBoostingClassifier,ExtraTreesClassifier
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path);m5=raw[(raw.index>=TRAIN_START)&(raw.index<DEV_END)].copy()
    f=prep(m5)
    allc=[]
    for lb in [3,5]:
        c=candidates(m5,f,lb);c["stop_lb"]=lb;allc.append(c)
    cand=pd.concat(allc,ignore_index=True)
    X=features(cand,f)
    y=cand.result.astype(int)

    months=pd.period_range("2017-01","2020-12",freq="M")
    models={
      "HGB":lambda:HistGradientBoostingClassifier(max_iter=160,max_leaf_nodes=31,learning_rate=.05,min_samples_leaf=40,l2_regularization=3,random_state=42),
      "ET":lambda:ExtraTreesClassifier(n_estimators=180,max_depth=14,min_samples_leaf=12,max_features=.7,n_jobs=-1,class_weight="balanced",random_state=42)
    }
    qs=[.90,.95,.97,.98,.99,.995]
    scored=[]
    for m in months:
        ms=m.start_time.tz_localize("UTC");me=(m+1).start_time.tz_localize("UTC")
        test=(cand.signal_time>=ms)&(cand.signal_time<me)
        train=(cand.signal_time>=TRAIN_START)&(pd.to_datetime(cand.exit_time,utc=True)<ms)
        if train.sum()<2000 or y[train].nunique()<2:continue
        for mn,maker in models.items():
            model=maker();model.fit(X.loc[train],y.loc[train])
            pt=model.predict_proba(X.loc[test])[:,1];ptr=model.predict_proba(X.loc[train])[:,1]
            base=cand.loc[test].copy();base["score"]=pt;base["model"]=mn;base["month"]=str(m)
            for q in qs:
                th=float(np.quantile(ptr,q))
                z=base.copy();z["selector"]=f"Q{q*100:g}";z["threshold"]=th;z["accept"]=z.score>=th
                scored.append(z)
    sd=pd.concat(scored,ignore_index=True)
    rows=[];yrs=[];alltr=[]
    for (model,selector,slb),g in sd.groupby(["model","selector","stop_lb"]):
        tr=live_trades(g);name=f"OUTCOME__{model}__{selector}__SL{slb}"
        if not tr.empty:alltr.append(tr.assign(strategy=name))
        ov=metrics(tr);ms=month_stats(tr);yr=yearly(tr)
        rows.append({"strategy":name,"model":model,"selector":selector,"stop_lb":slb,
                     "trades":ov["trades"],"wr":ov["wr"],"expectancy_r":ov["expectancy_r"],"pf":ov["pf"],"dd":ov["max_dd_pct"],
                     "end_rm":ov["end_rm"],**ms,"positive_years":int((yr.expectancy_r>0).sum()),"pf_years":int((yr.pf>1).sum()),
                     "worst_year_exp":float(yr.expectancy_r.min()),"worst_year_dd":float(yr.max_dd_pct.max())})
        for rr in yr.itertuples(index=False):yrs.append({"strategy":name,**rr._asdict()})
    rd=pd.DataFrame(rows)
    rd["strict"]=(rd.wr>=60)&(rd.dd<=25)&(rd.min_month>=8)&(rd.positive_years.eq(4))&(rd.pf_years.eq(4))
    rd["dist"]=np.maximum(0,60-rd.wr)*3+np.maximum(0,rd.dd-25)+np.maximum(0,8-rd.min_month)*5+(4-rd.positive_years)*20
    ranked=rd.sort_values(["strict","dist","positive_years","min_month","wr","expectancy_r"],ascending=[False,True,False,False,False,False])
    yd=pd.DataFrame(yrs);ranked.to_csv(out/"ranked.csv",index=False);yd.to_csv(out/"yearly.csv",index=False)
    if alltr:pd.concat(alltr,ignore_index=True).to_csv(out/"trades.csv",index=False)
    strict=ranked[ranked.strict]
    lines=["# Outcome-First Walk-Forward State Selector — 2017-2020","",
           "Pre-2017 history is training only. Each month 2017-2020 is scored by models trained exclusively on outcomes completed before that month.",
           "Candidate states: every primary-session M15 bar, both BUY and SELL, structural 3/5-bar swing SL +0.05ATR, fixed TP3R.",
           "No 2021+ data. One live position at a time; 1bp cost; RM100; 5% risk; same-M5 stop-first.","",
           f"Labeled candidate outcomes: {len(cand)}. Strict passes: {len(strict)}.","",
           "| Strategy | Trades | WR | ExpR | PF | DD | Avg/mo | Min/mo | Years |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in ranked.itertuples(index=False):
        pf="inf" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(f"| {r.strategy} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.dd:.2f}% | {r.avg_month:.2f} | {r.min_month} | {r.positive_years}/4 |")
    for strategy in (strict.strategy.tolist() if len(strict) else ranked.head(8).strategy.tolist()):
        lines+=["",f"## {strategy}","","| Year | Trades | WR | ExpR | PF | DD | RM100 -> |","|---|---:|---:|---:|---:|---:|---:|"]
        for r in yd[yd.strategy==strategy].itertuples(index=False):
            pf="inf" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
            lines.append(f"| {r.year} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.max_dd_pct:.2f}% | RM{r.end_rm:.2f} |")
    report="\n".join(lines)+"\n";(out/"REPORT.md").write_text(report)
    (out/"summary.json").write_text(json.dumps({"candidates":len(cand),"strict_count":int(len(strict)),
      "strict":strict.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records"),
      "ranked":ranked.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")},indent=2))
    print(report)

def main():
    p=argparse.ArgumentParser();p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output",default="reports/historical-first-outcome-ml");a=p.parse_args();run(a.data,a.output)
if __name__=="__main__":main()
