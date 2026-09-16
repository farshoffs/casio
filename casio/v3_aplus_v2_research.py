from __future__ import annotations

from pathlib import Path
import json
import math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .v3_edge_map import candidate_frame


def _safe(x):
    if isinstance(x, dict): return {str(k): _safe(v) for k,v in x.items()}
    if isinstance(x, list): return [_safe(v) for v in x]
    if isinstance(x, (np.bool_, bool)): return bool(x)
    if isinstance(x, (np.integer,)): return int(x)
    if isinstance(x, (np.floating, float)):
        v=float(x); return v if math.isfinite(v) else None
    if isinstance(x,pd.Timestamp): return x.isoformat()
    return x


def profile_mask(c: pd.DataFrame, profile: str) -> pd.Series:
    if profile == "ROBUST":
        pb = c.candidate & c.playbook.eq("PULLBACK_CONTINUATION") & c.session.eq("LONDON") & c.extension_atr.le(1.10)
        sw = c.candidate & c.playbook.eq("LIQUIDITY_SWEEP") & c.session.eq("LONDON") & c.body_fraction.ge(.55) & c.body_fraction.lt(.65) & c.efficiency.ge(.10)
    elif profile == "ROBUST_EFF20":
        pb = c.candidate & c.playbook.eq("PULLBACK_CONTINUATION") & c.session.eq("LONDON") & c.extension_atr.le(1.10)
        sw = c.candidate & c.playbook.eq("LIQUIDITY_SWEEP") & c.session.eq("LONDON") & c.body_fraction.ge(.55) & c.body_fraction.lt(.65) & c.efficiency.ge(.20)
    elif profile == "FREQ16":
        pb = c.candidate & c.playbook.eq("PULLBACK_CONTINUATION") & c.session.eq("LONDON") & c.htf_alignment.eq("BOTH_ALIGNED") & c.extension_atr.le(1.80)
        sw = c.candidate & c.playbook.eq("LIQUIDITY_SWEEP") & c.session.eq("LONDON") & c.body_fraction.ge(.55) & c.body_fraction.lt(.65) & c.efficiency.ge(.10)
    else:
        raise ValueError(profile)
    return pb | sw


def replay(m5: pd.DataFrame, c: pd.DataFrame, profile: str, target_r: float, cooldown: int=6, max_hold_bars: int=72, bps: float=1.0) -> pd.DataFrame:
    mask=profile_mask(c,profile)
    events=[]; active=None; last_entry=-999
    for i,(t,bar) in enumerate(m5.iterrows()):
        if active is not None and i>active["entry_pos"]:
            d=active["direction"]; ent=active["entry"]; risk=active["risk"]; stop=active["stop"]
            target=ent+d*risk*target_r; lo=float(bar.low); hi=float(bar.high); close=float(bar.close)
            hit_stop = lo<=stop if d==1 else hi>=stop
            hit_target = hi>=target if d==1 else lo<=target
            elapsed=i-active["entry_pos"]
            if hit_stop and hit_target: gross=-1.0; reason="stop_same_bar"
            elif hit_stop: gross=-1.0; reason="stop"
            elif hit_target: gross=target_r; reason=f"target_{target_r}r"
            elif elapsed>=max_hold_bars: gross=(close-ent)/risk*d; reason="time_exit"
            else: continue
            cost=(ent*bps/10000.0)/risk
            active["exit_time"]=t+pd.Timedelta(minutes=5); active["gross_r"]=gross; active["net_r"]=gross-cost; active["reason"]=reason
            events.append({k:v for k,v in active.items() if k!="entry_pos"}); active=None
            continue
        if active is not None or i-last_entry<cooldown or not bool(mask.iloc[i]): continue
        row=c.iloc[i]; risk=float(row.risk); ent=float(row.entry); d=int(row.direction)
        if not np.isfinite(risk) or risk<=0 or d==0: continue
        active={"signal_time":t,"entry_time":t+pd.Timedelta(minutes=5),"entry_pos":i,"profile":profile,"target_r":target_r,
                "playbook":row.playbook,"session":row.session,"htf_alignment":row.htf_alignment,"direction":d,"entry":ent,
                "risk":risk,"stop":ent-d*risk,"efficiency":row.efficiency,"extension_atr":row.extension_atr,
                "body_fraction":row.body_fraction,"runway_r":row.runway_r}
        last_entry=i
    return pd.DataFrame(events)


def metrics(tr: pd.DataFrame, a: pd.Timestamp, b: pd.Timestamp) -> dict:
    if tr.empty: x=tr
    else:
        t=pd.to_datetime(tr.entry_time,utc=True); x=tr[(t>=a)&(t<b)].copy()
    r=pd.to_numeric(x.get("net_r",pd.Series(dtype=float)),errors="coerce").dropna()
    if r.empty: return {"trades":0,"wins":0,"losses":0,"win_rate":None,"expectancy_r":None,"profit_factor":None,"avg_win_r":None,"avg_loss_r":None,"max_drawdown_r":None,"trades_per_30d":0.0}
    w=r[r>0.05]; l=r[r<-.05]; gw=float(w.sum()); gl=float(-l.sum()); curve=r.cumsum(); dd=curve.cummax()-curve
    days=max((b-a).total_seconds()/86400,1e-9)
    return {"trades":int(len(r)),"wins":int(len(w)),"losses":int(len(l)),"win_rate":float(len(w)*100/len(r)),
            "expectancy_r":float(r.mean()),"profit_factor":float(gw/gl) if gl>0 else (999.0 if gw>0 else None),
            "avg_win_r":float(w.mean()) if len(w) else None,"avg_loss_r":float(-l.mean()) if len(l) else None,
            "max_drawdown_r":float(dd.max()) if len(dd) else 0.0,"trades_per_30d":float(len(r)*30/days)}


def run(data_path: str|Path="data/xauusd_m5.csv", output_dir: str|Path="reports/v3-aplus-v2") -> dict:
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    m5=load_m5_csv(data_path); c=candidate_frame(m5)
    start=m5.index.min()+pd.Timedelta(days=30); finish=m5.index.max()+pd.Timedelta(minutes=5)
    cut=start+(finish-start)*.70
    rows=[]
    for profile in ["ROBUST","ROBUST_EFF20","FREQ16"]:
        for target in [3.0,3.5,4.0]:
            tr=replay(m5,c,profile,target)
            tr.to_csv(out/f"{profile.lower()}_{str(target).replace('.','_')}r_trades.csv",index=False)
            rows.append({"profile":profile,"target_r":target,"sample":"EARLY70",**metrics(tr,start,cut)})
            rows.append({"profile":profile,"target_r":target,"sample":"LATE30",**metrics(tr,cut,finish)})
            rows.append({"profile":profile,"target_r":target,"sample":"FULL",**metrics(tr,start,finish)})
    frame=pd.DataFrame(rows); frame.to_csv(out/"metrics.csv",index=False)
    summary={"data":{"rows":len(m5),"start":m5.index.min(),"end":m5.index.max(),"cut":cut},"results":rows,"auto_deploy":False,
             "note":"Research-only. Profile was informed by 2020 diagnostics and Sep 1-15 2026 user-supplied data, so neither period is untouched OOS. Live CASIO remains unchanged."}
    (out/"summary.json").write_text(json.dumps(_safe(summary),indent=2),encoding="utf-8")
    (out/"REPORT.md").write_text("# CASIO A+ v2 Research\n\n"+frame.to_markdown(index=False)+"\n\nLive strategy unchanged.\n",encoding="utf-8")
    return summary


def main():
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("--data",default="data/xauusd_m5.csv"); p.add_argument("--output",default="reports/v3-aplus-v2"); a=p.parse_args()
    print(json.dumps(_safe(run(a.data,a.output)),indent=2))

if __name__=="__main__": main()
