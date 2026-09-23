from __future__ import annotations
from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import DEV_END, atr, di_adx, resample, align_completed, rsi, metrics, month_stats, yearly

START=pd.Timestamp("2017-01-01",tz="UTC")
TRAIN_START=pd.Timestamp("2016-01-01",tz="UTC")
RR=3.0
COST_BPS=1.0

def prep(m5):
    f=resample(m5,"15min")
    f["atr14"]=atr(f,14)
    pdi,mdi,adx=di_adx(f,14); f["pdi"],f["mdi"],f["adx"]=pdi,mdi,adx
    f["rsi8"]=rsi(f.close,8)
    f["ema8"]=f.close.ewm(span=8,adjust=False).mean()
    f["ema20"]=f.close.ewm(span=20,adjust=False).mean()
    f["ema50"]=f.close.ewm(span=50,adjust=False).mean()
    f["ema100"]=f.close.ewm(span=100,adjust=False).mean()
    f["body"]=(f.close-f.open).abs(); f["range"]=f.high-f.low
    f["body_atr"]=f.body/f.atr14.replace(0,np.nan)
    f["range_atr"]=f.range/f.atr14.replace(0,np.nan)
    f["close_pos"]=(f.close-f.low)/f.range.replace(0,np.nan)
    f["vol_med20"]=f.volume.rolling(20,min_periods=10).median()
    f["vol_ratio"]=f.volume/f.vol_med20.replace(0,np.nan)
    f["atr_med96"]=f.atr14.rolling(96,min_periods=48).median()
    f["atr_regime"]=f.atr14/f.atr_med96.replace(0,np.nan)
    for lb in [8,10,20]:
        f[f"ph{lb}"]=f.high.shift(1).rolling(lb).max()
        f[f"pl{lb}"]=f.low.shift(1).rolling(lb).min()
    sma20=f.close.rolling(20).mean(); std20=f.close.rolling(20).std(ddof=0)
    f["bb_up"]=sma20+2*std20; f["bb_dn"]=sma20-2*std20

    # UTC daily/session levels.
    day=f.index.floor("D"); f["day"]=day
    mins=f.index.hour*60+f.index.minute; f["mins"]=mins
    asia=(mins>=0)&(mins<6*60); nyor=(mins>=12*60+30)&(mins<13*60+30)
    ast=f.loc[asia].groupby("day").agg(asia_h=("high","max"),asia_l=("low","min"))
    nst=f.loc[nyor].groupby("day").agg(ny_h=("high","max"),ny_l=("low","min"))
    f["asia_h"]=f.day.map(ast.asia_h); f["asia_l"]=f.day.map(ast.asia_l)
    f["ny_h"]=f.day.map(nst.ny_h); f["ny_l"]=f.day.map(nst.ny_l)

    h1=resample(m5,"1h"); h4=resample(m5,"4h"); d1=resample(m5,"1D")
    for x in (h1,h4,d1):
        x["atr14"]=atr(x,14)
        x["ema20"]=x.close.ewm(span=20,adjust=False).mean()
        x["ema50"]=x.close.ewm(span=50,adjust=False).mean()
        x["ema100"]=x.close.ewm(span=100,adjust=False).mean()
        x["s20"]=x.ema20.diff(3)
    ct=f.index+pd.Timedelta(minutes=15)
    for p,x,period in [("h1",h1,pd.Timedelta(hours=1)),("h4",h4,pd.Timedelta(hours=4)),("d1",d1,pd.Timedelta(days=1))]:
        for col in ["atr14","ema20","ema50","ema100","s20","close"]:
            f[f"{p}_{col}"]=align_completed(x[col],ct,period).to_numpy()
        f[f"{p}_up"]=(f[f"{p}_ema20"]>f[f"{p}_ema50"])&(f[f"{p}_s20"]>0)
        f[f"{p}_dn"]=(f[f"{p}_ema20"]<f[f"{p}_ema50"])&(f[f"{p}_s20"]<0)
        f[f"{p}_sep"]=(f[f"{p}_ema20"]-f[f"{p}_ema50"])/f[f"{p}_atr14"].replace(0,np.nan)
        f[f"{p}_dist20"]=(f.close-f[f"{p}_ema20"])/f[f"{p}_atr14"].replace(0,np.nan)
    f["align_up"]=f.h4_up&f.d1_up; f["align_dn"]=f.h4_dn&f.d1_dn
    return f

def add_signals(f):
    rows=[]
    def emit(mask,d,fam):
        for i in np.flatnonzero(mask.fillna(False).to_numpy()):
            rows.append((i,d,fam))
    bull=f.close>f.open; bear=f.close<f.open
    up=f.align_up; dn=f.align_dn

    emit(up&(f.close>f.ph8)&(f.adx>=16)&(f.body_atr>=0.25),1,"don8")
    emit(dn&(f.close<f.pl8)&(f.adx>=16)&(f.body_atr>=0.25),-1,"don8")
    ribup=(f.ema8>f.ema20)&(f.ema20>f.ema50); ribdn=(f.ema8<f.ema20)&(f.ema20<f.ema50)
    emit(up&ribup&(f.close>f.ph10)&(f.adx>=17),1,"ema_ribbon")
    emit(dn&ribdn&(f.close<f.pl10)&(f.adx>=17),-1,"ema_ribbon")
    emit(up&(f.close>f.ph10)&(f.vol_ratio>=1.10)&(f.body_atr>=0.35),1,"volume_break")
    emit(dn&(f.close<f.pl10)&(f.vol_ratio>=1.10)&(f.body_atr>=0.35),-1,"volume_break")
    emit(up&(f.low<=f.ema20)&(f.close>f.ema20)&bull&(f.pdi>f.mdi)&(f.adx>=17),1,"ema_pullback")
    emit(dn&(f.high>=f.ema20)&(f.close<f.ema20)&bear&(f.mdi>f.pdi)&(f.adx>=17),-1,"ema_pullback")
    emit(up&(f.close>f.bb_up)&(f.close.shift(1)<=f.bb_up.shift(1))&(f.adx>=17),1,"bb_break")
    emit(dn&(f.close<f.bb_dn)&(f.close.shift(1)>=f.bb_dn.shift(1))&(f.adx>=17),-1,"bb_break")

    # Raw session breakouts add diverse candidates; model must decide whether to accept.
    m=f.mins
    london=(m>=7*60)&(m<11*60)
    ny=(m>=13*60+30)&(m<16*60+30)
    emit(london&(f.close>f.asia_h)&(f.close.shift(1)<=f.asia_h.shift(1))&(f.body_atr>=0.25),1,"asia_break")
    emit(london&(f.close<f.asia_l)&(f.close.shift(1)>=f.asia_l.shift(1))&(f.body_atr>=0.25),-1,"asia_break")
    emit(ny&(f.close>f.ny_h)&(f.close.shift(1)<=f.ny_h.shift(1))&(f.body_atr>=0.25),1,"ny_break")
    emit(ny&(f.close<f.ny_l)&(f.close.shift(1)>=f.ny_l.shift(1))&(f.body_atr>=0.25),-1,"ny_break")

    sig=pd.DataFrame(rows,columns=["i","direction","family"]).drop_duplicates(["i","direction","family"])
    if sig.empty: return sig
    rr=f.iloc[sig.i.to_numpy()].copy().reset_index()
    rr=rr.rename(columns={rr.columns[0]:"signal_time"})
    sig=sig.reset_index(drop=True)
    out=pd.concat([sig,rr.reset_index(drop=True)],axis=1)
    return out

def feature_table(sig):
    x=pd.DataFrame(index=sig.index)
    x["direction"]=sig.direction.astype(float)
    x["hour_sin"]=np.sin(2*np.pi*sig.signal_time.dt.hour/24)
    x["hour_cos"]=np.cos(2*np.pi*sig.signal_time.dt.hour/24)
    x["dow_sin"]=np.sin(2*np.pi*sig.signal_time.dt.dayofweek/7)
    x["dow_cos"]=np.cos(2*np.pi*sig.signal_time.dt.dayofweek/7)
    cols=["adx","rsi8","body_atr","range_atr","close_pos","vol_ratio","atr_regime",
          "h1_sep","h4_sep","d1_sep","h1_dist20","h4_dist20","d1_dist20"]
    for col in cols: x[col]=pd.to_numeric(sig[col],errors="coerce")
    x["pdi_gap"]=(sig.pdi-sig.mdi)*sig.direction
    x["ema20_dist"]=(sig.close-sig.ema20)/sig.atr14.replace(0,np.nan)*sig.direction
    fams=["don8","ema_ribbon","volume_break","ema_pullback","bb_break","asia_break","ny_break"]
    for fam in fams: x[f"fam_{fam}"]=(sig.family==fam).astype(float)
    return x.replace([np.inf,-np.inf],np.nan).fillna(0.0)

def label_all(m5,sig):
    idx=m5.index; hi=m5.high.to_numpy(float); lo=m5.low.to_numpy(float); op=m5.open.to_numpy(float)
    rows=[]
    for r in sig.itertuples(index=False):
        st=pd.Timestamp(r.signal_time)
        pos=idx.searchsorted(st+pd.Timedelta(minutes=15),side="left")
        if pos>=len(idx) or idx[pos]>=DEV_END: rows.append((pd.NaT,np.nan,np.nan,np.nan,np.nan)); continue
        entry=float(op[pos]); d=int(r.direction); a=float(r.atr14)
        stop=float(r.low-0.05*a) if d==1 else float(r.high+0.05*a)
        risk=(entry-stop) if d==1 else (stop-entry)
        if not np.isfinite(risk) or risk<=0 or risk/a<0.10 or risk/a>2.0:
            rows.append((pd.NaT,np.nan,np.nan,np.nan,np.nan)); continue
        target=entry+d*RR*risk; xp=xt=None
        for j in range(pos,len(idx)):
            t=idx[j]
            if t>=DEV_END: break
            hs=lo[j]<=stop if d==1 else hi[j]>=stop
            ht=hi[j]>=target if d==1 else lo[j]<=target
            if hs: xp=stop; xt=t+pd.Timedelta(minutes=5); break
            if ht: xp=target; xt=t+pd.Timedelta(minutes=5); break
        if xp is None: rows.append((pd.NaT,np.nan,np.nan,np.nan,np.nan)); continue
        gross=(xp-entry)/risk if d==1 else (entry-xp)/risk
        cost=(entry*COST_BPS/10000)/risk
        net=float(gross-cost)
        rows.append((xt,net,entry,stop,target))
    lab=pd.DataFrame(rows,columns=["exit_time","net_r","entry","stop","target"],index=sig.index)
    return pd.concat([sig,lab],axis=1)

def selected_trades(scored,selector):
    # selector is boolean Series. Enforce one position at a time using the independently resolved exit.
    g=scored[selector & scored.exit_time.notna()].sort_values("signal_time")
    rows=[]; busy=None
    for r in g.itertuples(index=False):
        entry_time=pd.Timestamp(r.signal_time)+pd.Timedelta(minutes=15)
        if busy is not None and entry_time<=busy: continue
        rows.append({"signal_time":r.signal_time,"entry_time":entry_time,"exit_time":r.exit_time,
                     "direction":"BUY" if int(r.direction)==1 else "SELL","net_r":float(r.net_r),
                     "r_multiple":float(r.net_r),"result":"WIN" if float(r.net_r)>0 else "LOSS",
                     "family":r.family,"score":float(r.score)})
        busy=pd.Timestamp(r.exit_time)
    return pd.DataFrame(rows)

def run(data_path,output_dir):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline

    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path); m5=raw[(raw.index>=TRAIN_START)&(raw.index<DEV_END)].copy()
    f=prep(m5); sig=add_signals(f)
    sig["signal_time"]=pd.to_datetime(sig.signal_time,utc=True)
    data=label_all(m5,sig)
    data=data[data.exit_time.notna()].copy()
    X=feature_table(data)
    y=(data.net_r>0).astype(int)

    months=pd.period_range("2017-01","2020-12",freq="M")
    model_defs={
      "HGB": lambda: HistGradientBoostingClassifier(max_iter=120,max_leaf_nodes=15,learning_rate=0.06,
                  min_samples_leaf=30,l2_regularization=2.0,random_state=42),
      "LOGIT": lambda: make_pipeline(StandardScaler(),LogisticRegression(C=0.5,max_iter=1000,class_weight="balanced",random_state=42))
    }
    quantiles=[0.55,0.65,0.75,0.85,0.90]
    abs_thresholds=[0.40,0.45,0.50,0.55,0.60]
    scored_parts=[]

    for m in months:
        mstart=m.start_time.tz_localize("UTC"); mend=(m+1).start_time.tz_localize("UTC")
        test_mask=(data.signal_time>=mstart)&(data.signal_time<mend)
        # Only outcomes known before month start are allowed into training.
        train_mask=(data.signal_time>=TRAIN_START)&(pd.to_datetime(data.exit_time,utc=True)<mstart)
        if train_mask.sum()<200 or y[train_mask].nunique()<2: continue
        for model_name,maker in model_defs.items():
            model=maker(); model.fit(X.loc[train_mask],y.loc[train_mask])
            ptest=model.predict_proba(X.loc[test_mask])[:,1]
            ptrain=model.predict_proba(X.loc[train_mask])[:,1]
            base=data.loc[test_mask].copy()
            base["score"]=ptest; base["model"]=model_name; base["month"]=str(m)
            # Store one copy per selector later by duplicating compactly.
            for q in quantiles:
                th=float(np.quantile(ptrain,q))
                z=base.copy(); z["selector"]=f"Q{int(q*100)}"; z["threshold"]=th; z["accept"]=z.score>=th
                scored_parts.append(z)
            for th in abs_thresholds:
                z=base.copy(); z["selector"]=f"P{int(th*100)}"; z["threshold"]=th; z["accept"]=z.score>=th
                scored_parts.append(z)

    scored=pd.concat(scored_parts,ignore_index=True) if scored_parts else pd.DataFrame()
    rows=[]; yrs=[]; alltr=[]
    for (model,selector),g in scored.groupby(["model","selector"]):
        tr=selected_trades(g,g.accept.astype(bool))
        name=f"WFML__{model}__{selector}"
        if not tr.empty: alltr.append(tr.assign(strategy=name))
        ov=metrics(tr); ms=month_stats(tr); yr=yearly(tr)
        rows.append({"strategy":name,"model":model,"selector":selector,"trades":ov["trades"],"wr":ov["wr"],
                     "expectancy_r":ov["expectancy_r"],"pf":ov["pf"],"dd":ov["max_dd_pct"],"end_rm":ov["end_rm"],
                     **ms,"positive_years":int((yr.expectancy_r>0).sum()),"pf_years":int((yr.pf>1).sum()),
                     "worst_year_exp":float(yr.expectancy_r.min()),"worst_year_dd":float(yr.max_dd_pct.max())})
        for rr in yr.itertuples(index=False): yrs.append({"strategy":name,**rr._asdict()})
    rd=pd.DataFrame(rows)
    rd["strict"]=(rd.wr>=60)&(rd.dd<=25)&(rd.min_month>=8)&(rd.positive_years.eq(4))&(rd.pf_years.eq(4))
    rd["dist"]=np.maximum(0,60-rd.wr)*3+np.maximum(0,rd.dd-25)+np.maximum(0,8-rd.min_month)*5+(4-rd.positive_years)*20
    ranked=rd.sort_values(["strict","dist","positive_years","min_month","wr","expectancy_r"],ascending=[False,True,False,False,False,False])
    yd=pd.DataFrame(yrs)
    ranked.to_csv(out/"ranked.csv",index=False); yd.to_csv(out/"yearly.csv",index=False)
    if alltr: pd.concat(alltr,ignore_index=True).to_csv(out/"trades.csv",index=False)
    strict=ranked[ranked.strict]
    lines=["# Walk-Forward ML Router — 2017-2020","",
           "Initial data starts 2016. Model refits at each month boundary and uses only trade outcomes whose exits occurred before that month.",
           "No 2021+ data. Base opportunities are multiple M15 setup families; classifier only filters entries.",
           "Fixed RR3, real signal-wick SL +0.05ATR, one position at a time, 1bp cost, RM100, 5% risk.","",
           f"Base labeled opportunities: {len(data)}. Strategies: {len(ranked)}. Strict passes: {len(strict)}.","",
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
    report="\n".join(lines)+"\n"; (out/"REPORT.md").write_text(report)
    (out/"summary.json").write_text(json.dumps({"base_signals":len(data),"strict_count":int(len(strict)),
      "strict":strict.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records"),
      "ranked":ranked.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")},indent=2))
    print(report)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output",default="reports/historical-first-walkforward-ml")
    a=p.parse_args(); run(a.data,a.output)
if __name__=="__main__": main()
