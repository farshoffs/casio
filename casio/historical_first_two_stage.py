from __future__ import annotations
from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import DEV_END, atr, di_adx, resample, align_completed, metrics, month_stats, yearly

START=pd.Timestamp("2017-01-01",tz="UTC")
RR=3.0
COST_BPS=1.0

def prep(m5):
    m15=resample(m5,"15min")
    m15["atr14"]=atr(m15,14)
    pdi,mdi,adx=di_adx(m15,14); m15["pdi"],m15["mdi"],m15["adx"]=pdi,mdi,adx
    m15["body"]=(m15.close-m15.open).abs()
    m15["range"]=m15.high-m15.low
    m15["body_atr"]=m15.body/m15.atr14.replace(0,np.nan)
    m15["body_frac"]=m15.body/m15.range.replace(0,np.nan)
    m15["ph8"]=m15.high.shift(1).rolling(8).max()
    m15["pl8"]=m15.low.shift(1).rolling(8).min()
    mins=m15.index.hour*60+m15.index.minute
    m15["primary"]=((mins>=7*60)&(mins<11*60))|((mins>=12*60+30)&(mins<16*60+30))

    h4=resample(m5,"4h"); d1=resample(m5,"1D")
    for x in (h4,d1):
        x["ema20"]=x.close.ewm(span=20,adjust=False).mean()
        x["ema50"]=x.close.ewm(span=50,adjust=False).mean()
        x["s20"]=x.ema20.diff(3)
    ct=m15.index+pd.Timedelta(minutes=15)
    for p,x,period in [("h4",h4,pd.Timedelta(hours=4)),("d1",d1,pd.Timedelta(days=1))]:
        for col in ["ema20","ema50","s20"]:
            m15[f"{p}_{col}"]=align_completed(x[col],ct,period).to_numpy()
        m15[f"{p}_up"]=(m15[f"{p}_ema20"]>m15[f"{p}_ema50"])&(m15[f"{p}_s20"]>0)
        m15[f"{p}_dn"]=(m15[f"{p}_ema20"]<m15[f"{p}_ema50"])&(m15[f"{p}_s20"]<0)
    m15["align_up"]=m15.h4_up&m15.d1_up
    m15["align_dn"]=m15.h4_dn&m15.d1_dn
    return m15

def base_signals(m15,disp,session):
    ss=m15.primary if session=="PRIMARY" else pd.Series(True,index=m15.index)
    bull=(m15.close>m15.open)&(m15.body_atr>=disp)&(m15.body_frac>=0.60)
    bear=(m15.close<m15.open)&(m15.body_atr>=disp)&(m15.body_frac>=0.60)
    lo=m15.align_up&ss&bull&(m15.close>m15.ph8)&(m15.adx>=16)
    sh=m15.align_dn&ss&bear&(m15.close<m15.pl8)&(m15.adx>=16)
    rows=[]
    for i in np.flatnonzero((lo.fillna(False)|sh.fillna(False)).to_numpy()):
        r=m15.iloc[i]; d=1 if bool(lo.iat[i]) else -1
        rows.append({"signal_time":m15.index[i],"available":m15.index[i]+pd.Timedelta(minutes=15),
                     "direction":d,"sig_o":float(r.open),"sig_h":float(r.high),"sig_l":float(r.low),
                     "sig_c":float(r.close),"atr15":float(r.atr14)})
    return pd.DataFrame(rows)

def confirm_setup(m5, sig, retrace, wait_min, confirm):
    idx=m5.index
    hi=m5.high.to_numpy(float); lo=m5.low.to_numpy(float)
    op=m5.open.to_numpy(float); cl=m5.close.to_numpy(float)
    rows=[]
    for s in sig.itertuples(index=False):
        d=int(s.direction)
        rng=float(s.sig_h-s.sig_l)
        if rng<=0: continue
        level=float(s.sig_h-retrace*rng) if d==1 else float(s.sig_l+retrace*rng)
        start=idx.searchsorted(pd.Timestamp(s.available),side="left")
        expiry=pd.Timestamp(s.available)+pd.Timedelta(minutes=wait_min)
        touch=None
        for j in range(start,len(idx)):
            if idx[j]>=expiry or idx[j]>=DEV_END: break
            if lo[j]<=level<=hi[j]:
                touch=j; break
        if touch is None: continue

        # After the first touch, require completed M5 confirmation; never enter on the touch bar before close.
        end=min(len(idx),touch+4)
        cpos=None
        for j in range(touch,end):
            body=abs(cl[j]-op[j])
            rng5=max(hi[j]-lo[j],1e-12)
            if d==1:
                lower=min(op[j],cl[j])-lo[j]
                if confirm=="pin":
                    ok=(cl[j]>op[j]) and (lower/max(body,1e-12)>=1.2) and ((cl[j]-lo[j])/rng5>=0.65)
                elif confirm=="engulf":
                    ok=j>0 and (cl[j]>op[j]) and (cl[j]>hi[j-1]) and (op[j]<=cl[j-1])
                else: # reclaim
                    ok=(cl[j]>level) and (cl[j]>op[j]) and ((cl[j]-lo[j])/rng5>=0.65)
            else:
                upper=hi[j]-max(op[j],cl[j])
                if confirm=="pin":
                    ok=(cl[j]<op[j]) and (upper/max(body,1e-12)>=1.2) and ((hi[j]-cl[j])/rng5>=0.65)
                elif confirm=="engulf":
                    ok=j>0 and (cl[j]<op[j]) and (cl[j]<lo[j-1]) and (op[j]>=cl[j-1])
                else:
                    ok=(cl[j]<level) and (cl[j]<op[j]) and ((hi[j]-cl[j])/rng5>=0.65)
            if ok:
                cpos=j; break
        if cpos is None: continue
        entry_pos=cpos+1
        if entry_pos>=len(idx) or idx[entry_pos]>=DEV_END: continue
        # Micro invalidation: pullback extreme from first touch through confirmation, with small ATR buffer.
        a=float(s.atr15)
        if d==1:
            stop=float(np.min(lo[touch:cpos+1])-0.03*a)
        else:
            stop=float(np.max(hi[touch:cpos+1])+0.03*a)
        entry=float(op[entry_pos])
        risk=(entry-stop) if d==1 else (stop-entry)
        if not np.isfinite(risk) or risk<=0 or risk/a<0.05 or risk/a>1.5: continue
        rows.append({"signal_time":s.signal_time,"entry_time":idx[entry_pos],"entry_pos":entry_pos,
                     "direction":d,"entry":entry,"stop":stop,"level":level,
                     "confirm":confirm,"risk":risk})
    return pd.DataFrame(rows)

def replay(m5,setups):
    if setups.empty:return pd.DataFrame()
    idx=m5.index; hi=m5.high.to_numpy(float); lo=m5.low.to_numpy(float)
    rows=[]; busy=None
    for s in setups.sort_values("entry_time").itertuples(index=False):
        et=pd.Timestamp(s.entry_time)
        if et<START or et>=DEV_END: continue
        if busy is not None and et<=busy: continue
        d=int(s.direction); entry=float(s.entry); stop=float(s.stop); risk=float(s.risk)
        target=entry+d*RR*risk; xp=xt=reason=None
        for j in range(int(s.entry_pos),len(idx)):
            t=idx[j]
            if t>=DEV_END:break
            hs=lo[j]<=stop if d==1 else hi[j]>=stop
            ht=hi[j]>=target if d==1 else lo[j]<=target
            if hs:
                xp=stop;xt=t+pd.Timedelta(minutes=5);reason="SL_same_bar" if ht else "SL";break
            if ht:
                xp=target;xt=t+pd.Timedelta(minutes=5);reason="TP";break
        if xp is None:continue
        gross=(xp-entry)/risk if d==1 else (entry-xp)/risk
        cost=(entry*COST_BPS/10000)/risk
        nr=float(gross-cost)
        rows.append({"signal_time":s.signal_time,"entry_time":et,"exit_time":xt,
                     "direction":"BUY" if d==1 else "SELL","net_r":nr,"r_multiple":nr,
                     "result":"WIN" if nr>0 else "LOSS","exit_reason":reason})
        busy=xt
    return pd.DataFrame(rows)

def run(data_path,output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path);m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy()
    m15=prep(m5)
    rows=[];yrs=[];alltr=[]
    specs=[]
    for session in ["PRIMARY","ALL"]:
      for disp in [0.4,0.6,0.8]:
       sig=base_signals(m15,disp,session)
       for rt in [0.705,0.79,0.886,0.90]:
        for wait in [30,60,120]:
         for conf in ["pin","engulf","reclaim"]:
          specs.append((session,disp,rt,wait,conf,sig))
    for session,disp,rt,wait,conf,sig in specs:
        name=f"2STAGE__{session}__D{disp}__R{rt}__W{wait}__{conf}"
        tr=replay(m5,confirm_setup(m5,sig,rt,wait,conf))
        if not tr.empty:alltr.append(tr.assign(strategy=name))
        ov=metrics(tr);ms=month_stats(tr);y=yearly(tr)
        rows.append({"strategy":name,"session":session,"disp":disp,"retrace":rt,"wait":wait,"confirm":conf,
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
    lines=["# Two-Stage M15 Retrace + M5 Confirmation","",
           "2017-2020 only. M15 HTF-aligned breakout impulse -> deep retrace zone -> completed M5 pin/engulf/reclaim -> next-M5-open entry.",
           "SL beyond actual M5 pullback extreme; fixed 3R; 1bp cost; 5% risk; same-bar stop-first. 2021+ sealed.","",
           f"Specs: {len(specs)}; strict passes: {len(strict)}.","",
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
    (out/"summary.json").write_text(json.dumps({"strict_count":int(len(strict)),
      "strict":strict.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records"),
      "closest":ranked.head(30).replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")},indent=2))
    print(report)

def main():
    p=argparse.ArgumentParser();p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output",default="reports/historical-first-two-stage");a=p.parse_args();run(a.data,a.output)
if __name__=="__main__":main()
