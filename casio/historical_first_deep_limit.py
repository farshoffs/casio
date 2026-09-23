from __future__ import annotations
from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import DEV_END, atr, di_adx, resample, align_completed, metrics, month_stats, yearly
from .historical_first_displacement_retrace import replay_pending

def prep(m5):
    f=resample(m5,"15min")
    f["atr14"]=atr(f,14)
    pdi,mdi,adx=di_adx(f,14); f["pdi"],f["mdi"],f["adx"]=pdi,mdi,adx
    f["ema20"]=f.close.ewm(span=20,adjust=False).mean()
    f["ema50"]=f.close.ewm(span=50,adjust=False).mean()
    f["body"]=(f.close-f.open).abs(); f["range"]=f.high-f.low
    f["body_atr"]=f.body/f.atr14.replace(0,np.nan)
    f["body_frac"]=f.body/f.range.replace(0,np.nan)
    f["uw"]=f.high-f[["open","close"]].max(axis=1)
    f["lw"]=f[["open","close"]].min(axis=1)-f.low
    f["uwb"]=f.uw/f.body.replace(0,np.nan); f["lwb"]=f.lw/f.body.replace(0,np.nan)
    f["ph8"]=f.high.shift(1).rolling(8).max(); f["pl8"]=f.low.shift(1).rolling(8).min()
    f["bull_engulf"]=(f.close>f.open)&(f.close.shift(1)<f.open.shift(1))&(f.open<=f.close.shift(1))&(f.close>=f.open.shift(1))
    f["bear_engulf"]=(f.close<f.open)&(f.close.shift(1)>f.open.shift(1))&(f.open>=f.close.shift(1))&(f.close<=f.open.shift(1))
    h1=resample(m5,"1h"); h4=resample(m5,"4h"); d1=resample(m5,"1D")
    for x in (h1,h4,d1):
        x["ema20"]=x.close.ewm(span=20,adjust=False).mean()
        x["ema50"]=x.close.ewm(span=50,adjust=False).mean()
        x["s20"]=x.ema20.diff(3)
    ct=f.index+pd.Timedelta(minutes=15)
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

def build(f,name,family,bias,session,retrace,wait,disp=0.0,wick=0.0,breakout=False):
    up=(f.h4d1_up if bias=="h4d1" else f.h1h4_up).fillna(False)
    dn=(f.h4d1_dn if bias=="h4d1" else f.h1h4_dn).fillna(False)
    ss=f.primary.fillna(False) if session=="PRIMARY" else pd.Series(True,index=f.index)
    bull=f.close>f.open; bear=f.close<f.open
    if family=="impulse":
        lo=up&ss&bull&(f.body_atr>=disp)&(f.body_frac>=0.60)&(f.pdi>f.mdi)&(f.adx>=16)
        sh=dn&ss&bear&(f.body_atr>=disp)&(f.body_frac>=0.60)&(f.mdi>f.pdi)&(f.adx>=16)
        if breakout:
            lo&=f.close>f.ph8; sh&=f.close<f.pl8
    elif family=="ema20_pin":
        lo=up&ss&bull&(f.low<=f.ema20)&(f.close>f.ema20)&(f.lwb>=wick)&(f.pdi>f.mdi)&(f.adx>=18)
        sh=dn&ss&bear&(f.high>=f.ema20)&(f.close<f.ema20)&(f.uwb>=wick)&(f.mdi>f.pdi)&(f.adx>=18)
    elif family=="engulf":
        lo=up&ss&f.bull_engulf&(f.low<=f.ema20)&(f.close>f.ema20)&(f.adx>=18)
        sh=dn&ss&f.bear_engulf&(f.high>=f.ema20)&(f.close<f.ema20)&(f.adx>=18)
    else: raise ValueError(family)

    idxs=np.flatnonzero((lo.fillna(False)|sh.fillna(False)).to_numpy())
    rows=[]
    for i in idxs:
        d=1 if bool(lo.iat[i]) else -1
        row=f.iloc[i]; a=float(row.atr14)
        if not np.isfinite(a) or a<=0: continue
        # Deep limit into full candle range. For longs retrace down from high; shorts up from low.
        entry=float(row.high-retrace*(row.high-row.low)) if d==1 else float(row.low+retrace*(row.high-row.low))
        stop=float(row.low-0.03*a) if d==1 else float(row.high+0.03*a)
        risk=(entry-stop) if d==1 else (stop-entry)
        if risk<=0 or risk/a<0.08 or risk/a>1.8: continue
        rows.append({"card":name,"family":family,"signal_time":f.index[i],"available_time":f.index[i]+pd.Timedelta(minutes=15),
                     "direction":d,"entry_limit":entry,"stop":stop,"atr14":a,"risk_atr":risk/a,"wait_min":wait})
    return pd.DataFrame(rows)

def specs():
    out=[]
    for bias in ["h4d1","h1h4"]:
      for session in ["PRIMARY","ALL"]:
       for disp in [0.4,0.6,0.8]:
        for rt in [0.705,0.79,0.886]:
         for wait in [15,30,60]:
          for br in [False,True]:
           out.append((f"IMP__{bias}__{session}__D{disp}__R{rt}__W{wait}__B{int(br)}","impulse",bias,session,rt,wait,disp,0.0,br))
       for wick in [1.5,2.2]:
        for rt in [0.50,0.705,0.79]:
         for wait in [15,30,60]:
          out.append((f"PIN__{bias}__{session}__K{wick}__R{rt}__W{wait}","ema20_pin",bias,session,rt,wait,0.0,wick,False))
       for rt in [0.50,0.705,0.79]:
        for wait in [30,60]:
         out.append((f"ENG__{bias}__{session}__R{rt}__W{wait}","engulf",bias,session,rt,wait,0.0,0.0,False))
    return out

def run(data_path,output_dir):
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path); m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy()
    f=prep(m5)
    rows=[]; yrs=[]; alltr=[]
    sp=specs()
    for name,fam,bias,session,rt,wait,disp,wick,br in sp:
        tr=replay_pending(m5,build(f,name,fam,bias,session,rt,wait,disp,wick,br))
        if not tr.empty: alltr.append(tr.assign(strategy=name))
        ov=metrics(tr); ms=month_stats(tr); y=yearly(tr)
        rows.append({"strategy":name,"family":fam,"bias":bias,"session":session,"retrace":rt,"wait":wait,
                     "disp":disp,"wick":wick,"breakout":br,"trades":ov["trades"],"wr":ov["wr"],"expectancy_r":ov["expectancy_r"],
                     "pf":ov["pf"],"dd":ov["max_dd_pct"],"end_rm":ov["end_rm"],**ms,
                     "positive_years":int((y.expectancy_r>0).sum()),"pf_years":int((y.pf>1).sum()),
                     "worst_year_exp":float(y.expectancy_r.min()),"worst_year_dd":float(y.max_dd_pct.max())})
        for rr in y.itertuples(index=False): yrs.append({"strategy":name,**rr._asdict()})
    rd=pd.DataFrame(rows)
    rd["strict"]=(rd.wr>=60)&(rd.dd<=25)&(rd.min_month>=8)&(rd.positive_years.eq(4))&(rd.pf_years.eq(4))
    rd["dist"]=np.maximum(0,60-rd.wr)*3+np.maximum(0,rd.dd-25)+np.maximum(0,8-rd.min_month)*5+(4-rd.positive_years)*20
    ranked=rd.sort_values(["strict","dist","positive_years","min_month","wr","expectancy_r"],ascending=[False,True,False,False,False,False])
    yd=pd.DataFrame(yrs)
    ranked.to_csv(out/"ranked.csv",index=False); yd.to_csv(out/"yearly.csv",index=False)
    if alltr: pd.concat(alltr,ignore_index=True).to_csv(out/"trades.csv",index=False)
    strict=ranked[ranked.strict]
    lines=["# Deep Limit Entry Search — 2017-2020","",
           "Families: HTF-aligned impulse retrace, breakout-impulse retrace, EMA20 pin-bar limit, engulfing limit.",
           "Entry at 50%-88.6% retracement of completed signal range; real SL beyond signal wick.",
           "Fixed RR3, 1bp cost, RM100, 5% risk, same-bar stop-first. 2021+ sealed.","",
           f"Specs: {len(sp)}; strict passes: {len(strict)}.","",
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
    report="\n".join(lines)+"\n"; (out/"REPORT.md").write_text(report)
    (out/"summary.json").write_text(json.dumps({"specs":len(sp),"strict_count":int(len(strict)),
      "strict":strict.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records"),
      "closest":ranked.head(30).replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")},indent=2))
    print(report)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output",default="reports/historical-first-deep-limit")
    a=p.parse_args(); run(a.data,a.output)
if __name__=="__main__": main()
