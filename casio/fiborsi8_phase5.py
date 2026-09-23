from __future__ import annotations
from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd

from .fiborsi8_backtest import load_m5
from .fiborsi8_phase3 import V, signals_for

CANDIDATES=(
    V("T22_78_HTF32.5_67.5","15min",15,"30min",30,22,78,32.5,67.5),
    V("T23_77_HTF30_70","15min",15,"30min",30,23,77,30,70),
    V("T23_77_HTF32.5_67.5","15min",15,"30min",30,23,77,32.5,67.5),
    V("T23_77_HTF35_65","15min",15,"30min",30,23,77,35,65),
    V("T24_76_HTF32.5_67.5","15min",15,"30min",30,24,76,32.5,67.5),
)
YEARS=(2024,2025,2026)
RISK=.05

def max_streak(vals,wanted):
    b=c=0
    for v in vals:
        if v==wanted: c+=1; b=max(b,c)
        else: c=0
    return b

def replay_window(m5,sig,v,start,end):
    idx=m5.index; rows=[]; busy=None
    for s in sig.itertuples(index=False):
        st=pd.Timestamp(s.signal_time)
        if st<start or st>=end: continue
        pos=idx.searchsorted(pd.Timestamp(s.signal_close_time),side="left")
        if pos>=len(idx): continue
        et=idx[pos]
        if et>=end: continue
        if busy is not None and et<=busy: continue
        entry=float(m5.iloc[pos].open); d=int(s.direction)
        stop=float(s.low if d==1 else s.high); risk=abs(entry-stop)
        if risk<=0 or (d==1 and entry<=stop) or (d==-1 and entry>=stop): continue
        target=entry+d*3*risk; ep=xt=None; reason=None
        for j in range(pos,len(idx)):
            t=idx[j]
            if t>=end: break
            lo=float(m5.iloc[j].low); hi=float(m5.iloc[j].high)
            hs=(lo<=stop) if d==1 else (hi>=stop)
            ht=(hi>=target) if d==1 else (lo<=target)
            if hs: ep=stop; xt=t+pd.Timedelta(minutes=5); reason="SL_same_bar" if ht else "SL"; break
            if ht: ep=target; xt=t+pd.Timedelta(minutes=5); reason="TP"; break
        if ep is None: continue
        r=(ep-entry)/risk if d==1 else (entry-ep)/risk
        rows.append({"variant":v.name,"signal_time":st,"entry_time":et,"exit_time":xt,
                     "direction":"BUY" if d==1 else "SELL","r_multiple":float(r),"result":"WIN" if r>0 else "LOSS",
                     "entry":entry,"stop":stop,"target":target,"exit_reason":reason})
        busy=xt
    return pd.DataFrame(rows)

def metrics(tr,year,data_end):
    if tr.empty:
        return {"trades":0,"wins":0,"losses":0,"wr":0.0,"expectancy_r":0.0,"pf":0.0,
                "max_dd_pct":0.0,"w_streak":0,"l_streak":0,"avg_month":0.0,"min_month":0,
                "end_rm":100.0,"return_pct":0.0}
    r=tr.r_multiple.astype(float); wins=int((r>0).sum()); losses=int((r<0).sum())
    gw=float(r[r>0].sum()); gl=float(-r[r<0].sum()); pf=gw/gl if gl else math.inf
    bal=100.; peak=100.; mdd=0.
    for rv in r:
        bal*=1+RISK*rv; peak=max(peak,bal); mdd=max(mdd,(peak-bal)/peak)
    outcomes=[x>0 for x in r]
    periods=pd.to_datetime(tr.entry_time,utc=True).dt.to_period("M")
    first=pd.Period(f"{year}-01",freq="M")
    last=pd.Period(f"{year}-12",freq="M")
    if year==data_end.year: last=data_end.to_period("M")-1
    ms=pd.period_range(first,last,freq="M") if last>=first else []
    counts=[int((periods==p).sum()) for p in ms]
    return {"trades":len(tr),"wins":wins,"losses":losses,"wr":wins*100/len(tr),"expectancy_r":float(r.mean()),
            "pf":pf,"max_dd_pct":mdd*100,"w_streak":max_streak(outcomes,True),"l_streak":max_streak(outcomes,False),
            "avg_month":float(np.mean(counts)) if counts else 0.0,"min_month":min(counts) if counts else 0,
            "end_rm":bal,"return_pct":(bal/100-1)*100}

def run(data_path,output_dir):
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    m5=load_m5(data_path); data_end=m5.index.max()
    rows=[]; monthly=[]; trades=[]
    for v in CANDIDATES:
        sig=signals_for(m5,v)
        for year in YEARS:
            start=pd.Timestamp(f"{year}-01-01",tz="UTC")
            end=min(pd.Timestamp(f"{year+1}-01-01",tz="UTC"),data_end+pd.Timedelta(minutes=5))
            if end<=start: continue
            tr=replay_window(m5,sig,v,start,end); tr["year"]=year; trades.append(tr)
            m=metrics(tr,year,data_end); rows.append({"variant":v.name,"year":year,**m})
            if not tr.empty:
                x=tr.copy(); x["month"]=pd.to_datetime(x.entry_time,utc=True).dt.to_period("M")
                for p,g in x.groupby("month"):
                    rr=g.r_multiple.astype(float); monthly.append({"variant":v.name,"year":year,"month":str(p),
                        "trades":len(g),"wins":int((rr>0).sum()),"losses":int((rr<0).sum()),"wr":float((rr>0).mean()*100),
                        "net_r":float(rr.sum())})
    rd=pd.DataFrame(rows); md=pd.DataFrame(monthly); td=pd.concat(trades,ignore_index=True) if trades else pd.DataFrame()
    rd.to_csv(out/"yearly.csv",index=False); md.to_csv(out/"monthly.csv",index=False); td.to_csv(out/"trades.csv",index=False)
    # Stability summary across complete 2024/2025 and partial 2026.
    stab=[]
    for v in CANDIDATES:
        g=rd[rd.variant==v.name]
        pos=int((g.expectancy_r>0).sum()); pfs=int((g.pf>1).sum())
        stab.append({"variant":v.name,"positive_years":pos,"pf_gt1_years":pfs,
                     "mean_expectancy_r":float(g.expectancy_r.mean()),"worst_expectancy_r":float(g.expectancy_r.min()),
                     "worst_dd_pct":float(g.max_dd_pct.max()),"mean_wr":float(g.wr.mean()),
                     "min_avg_month":float(g.avg_month.min()),"min_month_across_years":int(g.min_month.min())})
    sd=pd.DataFrame(stab).sort_values(["positive_years","worst_expectancy_r","mean_expectancy_r"],ascending=[False,False,False])
    sd.to_csv(out/"stability.csv",index=False)
    lines=["# FiboRSI8 Phase 5 — frozen backward robustness","",
           f"Data coverage: {m5.index.min().isoformat()} -> {data_end.isoformat()}",
           "2026 threshold choice is frozen before checking 2024/2025. 2026 is partial through current data end.",
           "RM100 reset each year; risk 5%; fixed 3R; real wick SL; one position at a time; costs not modeled.","",
           "## Stability","",
           "| Variant | Positive years | Mean ExpR | Worst ExpR | Mean WR | Worst DD | Lowest avg/mo | Lowest month |",
           "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in sd.itertuples(index=False):
        lines.append(f"| {r.variant} | {r.positive_years}/3 | {r.mean_expectancy_r:+.3f} | {r.worst_expectancy_r:+.3f} | {r.mean_wr:.2f}% | {r.worst_dd_pct:.2f}% | {r.min_avg_month:.2f} | {r.min_month_across_years} |")
    lines+=["","## Year by year","",
            "| Variant | Year | Trades | Avg/mo | Min/mo | W | SL | WR | ExpR | PF | DD | End RM | Return |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rd.itertuples(index=False):
        pf="∞" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(f"| {r.variant} | {r.year} | {r.trades} | {r.avg_month:.2f} | {r.min_month} | {r.wins} | {r.losses} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.max_dd_pct:.2f}% | RM{r.end_rm:.2f} | {r.return_pct:+.2f}% |")
    report="\n".join(lines)+"\n"; (out/"REPORT.md").write_text(report)
    (out/"summary.json").write_text(json.dumps({"stability":sd.replace({np.nan:None,np.inf:None}).to_dict("records"),
                                                "yearly":rd.replace({np.nan:None,np.inf:None}).to_dict("records")},indent=2))
    print(report); return sd,rd

def main():
    p=argparse.ArgumentParser(); p.add_argument("--data",default="data/xauusd_m5_dukascopy_research.csv")
    p.add_argument("--output",default="reports/fiborsi8-phase5-robustness"); a=p.parse_args(); run(a.data,a.output)
if __name__=="__main__": main()
