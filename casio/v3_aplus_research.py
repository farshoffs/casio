from __future__ import annotations

from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .v3_edge_map import candidate_frame
from .v3_m5_engine import V3M5Config, prepare_m5_features, replay_execution, signals_for_m5_features


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
    pullback_core = (
        c.candidate
        & c.playbook.eq("PULLBACK_CONTINUATION")
        & c.session.eq("LONDON")
        & c.htf_alignment.eq("BOTH_ALIGNED")
        & c.extension_atr.le(1.10)
    )
    if profile == "APLUS_CORE":
        sweep = (
            c.candidate
            & c.playbook.eq("LIQUIDITY_SWEEP")
            & c.session.eq("LONDON")
            & c.body_fraction.ge(.55)
            & c.body_fraction.lt(.65)
        )
    elif profile == "FREQUENCY":
        sweep = (
            c.candidate
            & c.playbook.eq("LIQUIDITY_SWEEP")
            & c.session.eq("LONDON")
            & c.htf_alignment.eq("ONE_ALIGNED")
        )
    else:
        raise ValueError(profile)
    return pullback_core | sweep


def _cost_r(entry: float, risk: float, bps: float=1.0) -> float:
    return (entry*bps/10000.0)/risk


def replay_profile(m5: pd.DataFrame, c: pd.DataFrame, profile: str, management: str,
                   cooldown: int=6, max_hold_bars: int=72, bps: float=1.0) -> pd.DataFrame:
    mask=profile_mask(c,profile)
    events=[]; active=None; last_entry=-999

    for i,(t,bar) in enumerate(m5.iterrows()):
        if active is not None and i>active["entry_pos"]:
            d=active["direction"]; ent=active["entry"]; risk=active["risk"]; stop=active["stop"]
            lo=float(bar.low); hi=float(bar.high); close=float(bar.close)
            stopped = lo<=stop if d==1 else hi>=stop
            elapsed=i-active["entry_pos"]

            if management=="FULL_3R":
                target=ent+d*risk*3.0
                hit_target = hi>=target if d==1 else lo<=target
                if stopped and hit_target:
                    active["gross_r"]=-1.0; active["reason"]="stop_same_bar"
                elif stopped:
                    active["gross_r"]=-1.0; active["reason"]="stop"
                elif hit_target:
                    active["gross_r"]=3.0; active["reason"]="target_3r"
                elif elapsed>=max_hold_bars:
                    active["gross_r"]=(close-ent)/risk*d; active["reason"]="time_exit"
                else:
                    continue
            elif management=="SCALE_2R_RUN4R":
                tp1=ent+d*risk*2.0; tp2=ent+d*risk*4.0
                hit1 = hi>=tp1 if d==1 else lo<=tp1
                hit2 = hi>=tp2 if d==1 else lo<=tp2
                if not active["partial"]:
                    if stopped and (hit1 or hit2):
                        active["gross_r"]=-1.0; active["reason"]="stop_same_bar"
                    elif stopped:
                        active["gross_r"]=-1.0; active["reason"]="stop"
                    elif hit2:
                        active["gross_r"]=3.6; active["reason"]="runner_4r"
                    elif hit1:
                        active["partial"]=True
                        active["realized_r"]=0.4
                        active["stop"]=ent
                        if elapsed>=max_hold_bars:
                            active["gross_r"]=0.4; active["reason"]="partial_time_exit"
                        else:
                            continue
                    elif elapsed>=max_hold_bars:
                        active["gross_r"]=(close-ent)/risk*d; active["reason"]="time_exit"
                    else:
                        continue
                else:
                    stopped_be = lo<=ent if d==1 else hi>=ent
                    if stopped_be and hit2:
                        active["gross_r"]=active["realized_r"]; active["reason"]="be_same_bar"
                    elif stopped_be:
                        active["gross_r"]=active["realized_r"]; active["reason"]="runner_be"
                    elif hit2:
                        active["gross_r"]=3.6; active["reason"]="runner_4r"
                    elif elapsed>=max_hold_bars:
                        runner_r=(close-ent)/risk*d
                        active["gross_r"]=active["realized_r"] + .8*runner_r
                        active["reason"]="partial_time_exit"
                    else:
                        continue
            else:
                raise ValueError(management)

            active["exit_time"]=t+pd.Timedelta(minutes=5)
            active["net_r"]=active["gross_r"]-_cost_r(ent,risk,bps)
            events.append({k:v for k,v in active.items() if k not in {"entry_pos","partial","realized_r"}})
            active=None
            continue

        if active is not None or i-last_entry<cooldown or not bool(mask.iloc[i]):
            continue
        row=c.iloc[i]
        risk=float(row.risk); ent=float(row.entry); d=int(row.direction)
        if not np.isfinite(risk) or risk<=0 or d==0: continue
        active={
            "signal_time":t, "entry_time":t+pd.Timedelta(minutes=5), "entry_pos":i,
            "profile":profile, "management":management, "playbook":row.playbook,
            "session":row.session, "htf_alignment":row.htf_alignment,
            "direction":d, "entry":ent, "risk":risk, "stop":ent-d*risk,
            "efficiency":row.efficiency, "extension_atr":row.extension_atr,
            "body_fraction":row.body_fraction, "runway_r":row.runway_r,
            "partial":False, "realized_r":0.0,
        }
        last_entry=i
    return pd.DataFrame(events)


def metrics(trades: pd.DataFrame, a: pd.Timestamp, b: pd.Timestamp) -> dict:
    if trades.empty: x=trades
    else:
        t=pd.to_datetime(trades.entry_time,utc=True); x=trades[(t>=a)&(t<b)].copy()
    r=pd.to_numeric(x.get("net_r",pd.Series(dtype=float)),errors="coerce").dropna()
    if r.empty:
        return {"trades":0,"wins":0,"losses":0,"breakeven":0,"win_rate":None,"expectancy_r":None,"profit_factor":None,"avg_win_r":None,"avg_loss_r":None,"max_drawdown_r":None,"trades_per_30d":0.0}
    wins=r[r>0.05]; losses=r[r<-0.05]; be=r[(r>=-.05)&(r<=.05)]
    gw=float(wins.sum()); gl=float(-losses.sum())
    curve=r.cumsum(); dd=curve.cummax()-curve; days=(b-a).total_seconds()/86400
    return {
        "trades":int(len(r)),"wins":int(len(wins)),"losses":int(len(losses)),"breakeven":int(len(be)),
        "win_rate":float(len(wins)*100/len(r)),"expectancy_r":float(r.mean()),
        "profit_factor":float(gw/gl) if gl>0 else (999.0 if gw>0 else None),
        "avg_win_r":float(wins.mean()) if len(wins) else None,"avg_loss_r":float(-losses.mean()) if len(losses) else None,
        "max_drawdown_r":float(dd.max()) if len(dd) else 0.0,"trades_per_30d":float(len(r)*30/days),
    }


def run(data_path: str|Path="data/xauusd_m5.csv", output_dir: str|Path="reports/v3-aplus") -> dict:
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    m5=load_m5_csv(data_path); c=candidate_frame(m5)
    start=m5.index.min()+pd.Timedelta(days=30); finish=m5.index.max()+pd.Timedelta(minutes=5); cutoff=start+(finish-start)*.75

    base_cfg=V3M5Config(); base_f=prepare_m5_features(m5); base=replay_execution(m5,signals_for_m5_features(base_f,base_cfg),base_cfg)
    def base_metrics(a,b):
        if base.empty: return metrics(pd.DataFrame(),a,b)
        x=base.copy(); x=x.rename(columns={"risk_distance":"risk"})
        return metrics(x,a,b)

    variants=[]; caches={}
    for profile in ["APLUS_CORE","FREQUENCY"]:
        for mgmt in ["FULL_3R","SCALE_2R_RUN4R"]:
            name=f"{profile}_{mgmt}"; tr=replay_profile(m5,c,profile,mgmt); caches[name]=tr
            variants.append({"variant":name,"sample":"DEV",**metrics(tr,start,cutoff)})
            variants.append({"variant":name,"sample":"HOLDOUT",**metrics(tr,cutoff,finish)})
    pd.DataFrame(variants).to_csv(out/"variant_metrics.csv",index=False)
    for name,tr in caches.items(): tr.to_csv(out/f"{name.lower()}_trades.csv",index=False)

    summary={
        "data":{"rows":len(m5),"start":m5.index.min(),"end":m5.index.max(),"dev_end":cutoff},
        "canonical_dev":base_metrics(start,cutoff),"canonical_holdout":base_metrics(cutoff,finish),
        "variants":variants,
        "auto_deploy":False,
        "note":"Research-only A+ London profiles derived from the 2020 edge map. 2020 validation is now hypothesis-building data; future backfilled years must be used as untouched OOS before any promotion.",
    }
    (out/"summary.json").write_text(json.dumps(_safe(summary),indent=2),encoding="utf-8")
    lines=["# CASIO A+ Asymmetry Execution Research","",f"Coverage: {m5.index.min().isoformat()} -> {m5.index.max().isoformat()}","",f"Canonical dev: `{summary['canonical_dev']}`",f"Canonical holdout: `{summary['canonical_holdout']}`",""]
    for v in variants: lines.append(f"- {v['variant']} / {v['sample']}: `{v}`")
    lines += ["","No live parameters were modified."]
    (out/"REPORT.md").write_text("\n".join(lines),encoding="utf-8")
    return summary


def main():
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("--data",default="data/xauusd_m5.csv"); p.add_argument("--output",default="reports/v3-aplus"); a=p.parse_args()
    print(json.dumps(_safe(run(a.data,a.output)),indent=2))

if __name__=="__main__": main()
