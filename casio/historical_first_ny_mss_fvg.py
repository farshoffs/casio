from __future__ import annotations
from pathlib import Path
import argparse,json,math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import DEV_END,metrics,month_stats,yearly
from .historical_first_ny_strict import prep

START=pd.Timestamp("2017-01-01",tz="UTC");RR=3.0;COST=1.0

def window_mask(f,w):
    m=f.ny_min
    if w=="OPEN": return ((m>=8*60+30)&(m<10*60+30)).to_numpy(bool)
    if w=="AM_SB": return ((m>=10*60)&(m<11*60)).to_numpy(bool)
    if w=="PM_SB": return ((m>=14*60)&(m<15*60)).to_numpy(bool)
    if w=="CORE": return ((m>=8*60+30)&(m<12*60+30)).to_numpy(bool)
    raise ValueError(w)

def find_setups(f,source,bias,w,slb,mlb,smw,disp,fgw,ew):
    n=len(f);o=f.open.to_numpy(float);h=f.high.to_numpy(float);l=f.low.to_numpy(float);cl=f.close.to_numpy(float)
    at=f.atr14.to_numpy(float);ba=f.body_atr.to_numpy(float);bf=f.body_frac.to_numpy(float)
    ph=f[f"ph{slb}"].to_numpy(float);pl=f[f"pl{slb}"].to_numpy(float)
    phm=f[f"ph{mlb}"].to_numpy(float);plm=f[f"pl{mlb}"].to_numpy(float)
    bfg=f.bull_fvg.fillna(False).to_numpy(bool);sfg=f.bear_fvg.fillna(False).to_numpy(bool)
    bmid=f.bull_fvg_mid.to_numpy(float);smid=f.bear_fvg_mid.to_numpy(float)
    win=window_mask(f,w)
    if bias=="none":
        up=np.ones(n,bool);dn=np.ones(n,bool)
    elif bias=="h4d1":
        up=f.h4d1_up.fillna(False).to_numpy(bool);dn=f.h4d1_dn.fillna(False).to_numpy(bool)
    else:
        up=f.triple_up.fillna(False).to_numpy(bool);dn=f.triple_dn.fillna(False).to_numpy(bool)

    if source=="rolling":
        swl=win&up&(l<pl)&(cl>pl);sws=win&dn&(h>ph)&(cl<ph)
    elif source=="overnight":
        onl=f.on_l.to_numpy(float);onh=f.on_h.to_numpy(float)
        swl=win&up&(l<onl)&(cl>onl);sws=win&dn&(h>onh)&(cl<onh)
    elif source=="prevny":
        pdl=f.prev_ny_l.to_numpy(float);pdh=f.prev_ny_h.to_numpy(float)
        swl=win&up&(l<pdl)&(cl>pdl);sws=win&dn&(h>pdh)&(cl<pdh)
    elif source=="or":
        orl=f.or_l.to_numpy(float);orh=f.or_h.to_numpy(float)
        after=f.ny_min.to_numpy(int)>=10*60
        swl=win&after&up&(l<orl)&(cl>orl);sws=win&after&dn&(h>orh)&(cl<orh)
    else: raise ValueError(source)

    idxs=np.flatnonzero(swl|sws);rows=[]
    for i in idxs:
        d=1 if swl[i] else -1;sweep_ext=l[i] if d==1 else h[i]
        mss=None
        for j in range(i+1,min(n,i+1+smw)):
            if not win[j]: break
            if d==1 and np.isfinite(phm[j]) and cl[j]>phm[j] and ba[j]>=disp and bf[j]>=0.55:
                mss=j;break
            if d==-1 and np.isfinite(plm[j]) and cl[j]<plm[j] and ba[j]>=disp and bf[j]>=0.55:
                mss=j;break
        if mss is None:continue
        fg=None;entry=None
        for k in range(mss+1,min(n,mss+1+fgw)):
            if not win[k]:break
            if d==1 and bfg[k]:
                fg=k;entry=bmid[k];break
            if d==-1 and sfg[k]:
                fg=k;entry=smid[k];break
        if fg is None or not np.isfinite(entry):continue
        stop=sweep_ext-0.04*at[fg] if d==1 else sweep_ext+0.04*at[fg]
        risk=(entry-stop) if d==1 else (stop-entry)
        if not np.isfinite(risk) or risk<=0 or risk/at[fg]<0.10 or risk/at[fg]>3.0:continue
        fill=None
        for q in range(fg+1,min(n,fg+1+ew)):
            if not win[q]:break
            if l[q]<=entry<=h[q]:fill=q;break
        if fill is None:continue
        rows.append({"signal_time":f.index[i],"entry_time":f.index[fill],"fill_pos":fill,"ny_date":f.ny_date.iat[i],
                     "direction":d,"entry":float(entry),"stop":float(stop),"risk":float(risk)})
    return pd.DataFrame(rows)

def replay(m5,ss,name):
    if ss.empty:return pd.DataFrame()
    idx=m5.index;h=m5.high.to_numpy(float);l=m5.low.to_numpy(float)
    rows=[];busy=None;days=set()
    for s in ss.sort_values("entry_time").itertuples(index=False):
        et=pd.Timestamp(s.entry_time)
        if et<START or et>=DEV_END or s.ny_date in days:continue
        if busy is not None and et<=busy:continue
        d=int(s.direction);entry=float(s.entry);stop=float(s.stop);risk=float(s.risk);target=entry+d*RR*risk
        xp=xt=reason=None
        for j in range(int(s.fill_pos),len(idx)):
            if idx[j]>=DEV_END:break
            hs=l[j]<=stop if d==1 else h[j]>=stop;ht=h[j]>=target if d==1 else l[j]<=target
            if hs:xp=stop;xt=idx[j]+pd.Timedelta(minutes=5);reason="SL_same_bar" if ht else "SL";break
            if ht:xp=target;xt=idx[j]+pd.Timedelta(minutes=5);reason="TP";break
        if xp is None:continue
        gross=(xp-entry)/risk if d==1 else (entry-xp)/risk;nr=float(gross-(entry*COST/10000)/risk)
        rows.append({"strategy":name,"signal_time":s.signal_time,"entry_time":et,"exit_time":xt,
                     "direction":"BUY" if d==1 else "SELL","net_r":nr,"r_multiple":nr,
                     "result":"WIN" if nr>0 else "LOSS","exit_reason":reason})
        days.add(s.ny_date);busy=xt
    return pd.DataFrame(rows)

def specs():
    out=[]
    for src in ["rolling","overnight","prevny","or"]:
      for b in ["none","h4d1","triple"]:
       for w in ["OPEN","AM_SB","PM_SB","CORE"]:
        for slb in ([12,24,48] if src=="rolling" else [24]):
         for mlb in [6,12]:
          for smw in [6,12]:
           for disp in [0.5,0.8]:
            for fgw in [6,12]:
             for ew in [6,12]:
              out.append((src,b,w,slb,mlb,smw,disp,fgw,ew))
    return out

def run(data_path,output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path);m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy()
    f=prep(m5)
    f["ph6"]=f.high.shift(1).rolling(6).max()
    f["pl6"]=f.low.shift(1).rolling(6).min()
    sp=specs();rows=[];yrs=[];alltr=[]
    for src,b,w,slb,mlb,smw,disp,fgw,ew in sp:
        name=f"NYSB__{src}__{b}__{w}__S{slb}__M{mlb}__SM{smw}__D{disp}__F{fgw}__E{ew}"
        tr=replay(m5,find_setups(f,src,b,w,slb,mlb,smw,disp,fgw,ew),name)
        if not tr.empty:alltr.append(tr)
        ov=metrics(tr);ms=month_stats(tr);y=yearly(tr)
        rows.append({"strategy":name,"source":src,"bias":b,"window":w,
                     "trades":ov["trades"],"wr":ov["wr"],"expectancy_r":ov["expectancy_r"],"pf":ov["pf"],
                     "dd":ov["max_dd_pct"],"end_rm":ov["end_rm"],**ms,
                     "positive_years":int((y.expectancy_r>0).sum()),"pf_years":int((y.pf>1).sum()),
                     "worst_year_exp":float(y.expectancy_r.min()),"worst_year_dd":float(y.max_dd_pct.max())})
        for rr in y.itertuples(index=False):yrs.append({"strategy":name,**rr._asdict()})
    rd=pd.DataFrame(rows);rd["strict"]=(rd.wr>=60)&(rd.dd<=25)&(rd.min_month>=8)&(rd.positive_years.eq(4))&(rd.pf_years.eq(4))
    rd["dist"]=np.maximum(0,60-rd.wr)*3+np.maximum(0,rd.dd-25)+np.maximum(0,8-rd.min_month)*6+(4-rd.positive_years)*25
    ranked=rd.sort_values(["strict","dist","positive_years","min_month","wr","expectancy_r"],ascending=[False,True,False,False,False,False])
    yd=pd.DataFrame(yrs);ranked.to_csv(out/"ranked.csv",index=False);yd.to_csv(out/"yearly.csv",index=False)
    if alltr:pd.concat(alltr,ignore_index=True).to_csv(out/"trades.csv",index=False)
    strict=ranked[ranked.strict]
    lines=["# DST-Aware New York Sweep -> MSS -> FVG Search","",
           "NY-local OPEN / 10-11 AM / 2-3 PM / core windows. Sweep rolling/overnight/previous-NY/opening-range liquidity, confirm MSS+displacement, FVG midpoint retrace.",
           "One entry max per NY date. Fixed RR3, sweep-extreme real SL, RM100, 5% risk, 1bp cost, same-bar stop-first. 2021+ sealed.","",
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
    p.add_argument("--output",default="reports/historical-first-ny-mss-fvg");a=p.parse_args();run(a.data,a.output)
if __name__=="__main__":main()
