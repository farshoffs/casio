from __future__ import annotations

from pathlib import Path
import json
import math
import numpy as np
import pandas as pd

from .v3_core import _atr, _resample, load_m5_csv

START_BALANCE = 2500.0
RISK = 0.005
COST_R = 0.05


def safe(x):
    if isinstance(x, dict): return {str(k): safe(v) for k,v in x.items()}
    if isinstance(x, list): return [safe(v) for v in x]
    if isinstance(x, pd.Timestamp): return x.isoformat()
    if isinstance(x, (np.integer,)): return int(x)
    if isinstance(x, (np.floating,float)):
        y=float(x); return y if math.isfinite(y) else None
    if isinstance(x, (np.bool_,bool)): return bool(x)
    return x


def trade_day(ts):
    ny=pd.Timestamp(ts).tz_convert("America/New_York")
    return (ny-pd.Timedelta(hours=17)).strftime("%Y-%m-%d")


def metrics(tr,a,b):
    if tr is None or tr.empty: return {"trades":0,"exp":None,"pf":None,"wr":None}
    t=pd.to_datetime(tr.entry_time,utc=True)
    r=pd.to_numeric(tr.loc[(t>=pd.Timestamp(a,tz="UTC"))&(t<pd.Timestamp(b,tz="UTC")),"net_r"],errors="coerce").dropna()
    if r.empty: return {"trades":0,"exp":None,"pf":None,"wr":None}
    w=r[r>0]; l=r[r<0]
    return {"trades":int(len(r)),"exp":float(r.mean()),"pf":float(w.sum()/(-l.sum())) if len(l) else 999.0,"wr":float((r>0).mean()*100)}


def pre2026_ok(tr):
    d=metrics(tr,"2020-01-01","2023-01-01")
    v=metrics(tr,"2023-01-01","2026-01-01")
    ok=(d["trades"]>=30 and v["trades"]>=30 and (d["exp"] or -99)>0.04 and (v["exp"] or -99)>0.04 and (d["pf"] or 0)>1.05 and (v["pf"] or 0)>1.05)
    return ok,d,v


def ny_cash_groups(m5):
    ny=m5.index.tz_convert("America/New_York")
    date=pd.Series(ny.date,index=m5.index)
    mins=ny.hour*60+ny.minute
    return ny,date,mins


def market_close_momentum(symbol,m5,min_signal_atr=0.0):
    ny,date,mins=ny_cash_groups(m5)
    h1=_resample(m5,"1h"); h1atr=_atr(h1,14).reindex(m5.index,method="ffill")
    pos=pd.Series(np.arange(len(m5)),index=m5.index)
    dates=sorted(set(date[(mins>=9*60+30)&(mins<16*60)]))
    prev_close={}
    for d in dates:
        idx=m5.index[(date==d)&(mins>=15*60+55)&(mins<16*60)]
        if len(idx): prev_close[d]=float(m5.loc[idx[-1],"close"])
    rows=[]
    for k,d in enumerate(dates):
        if k==0: continue
        pdate=dates[k-1]
        if pdate not in prev_close: continue
        first_idx=m5.index[(date==d)&(mins>=9*60+30)&(mins<10*60)]
        last_idx=m5.index[(date==d)&(mins>=15*60+30)&(mins<16*60)]
        if len(first_idx)<4 or len(last_idx)<4: continue
        first_last=first_idx[-1]
        move=float(m5.loc[first_last,"close"]-prev_close[pdate])
        a=float(h1atr.loc[first_last]) if np.isfinite(h1atr.loc[first_last]) else np.nan
        if not np.isfinite(a) or a<=0 or abs(move)/a < min_signal_atr or move==0: continue
        direction=1 if move>0 else -1
        entry_ts=last_idx[0]; i=int(pos.loc[entry_ts])
        entry=float(m5.open.iat[i])
        dist=max(.60*a, float(m5.loc[first_idx,"high"].max()-m5.loc[first_idx,"low"].min())*.75)
        stop=entry-direction*dist
        exit_i=int(pos.loc[last_idx[-1]])
        r=None; reason="cash_close"
        for j in range(i,exit_i+1):
            lo=float(m5.low.iat[j]); hi=float(m5.high.iat[j])
            hs=lo<=stop if direction==1 else hi>=stop
            if hs:
                r=-1.0; reason="stop"; exit_i=j; break
        if r is None:
            px=float(m5.close.iat[exit_i]); r=(px-entry)/dist*direction
        rows.append({"symbol":symbol,"engine":f"{symbol}_CLOSE_MOM_A{min_signal_atr:g}","entry_time":m5.index[i],"exit_time":m5.index[exit_i]+pd.Timedelta(minutes=5),"direction":direction,"net_r":float(r-COST_R),"reason":reason})
    return pd.DataFrame(rows)


def overnight_first30(symbol,m5,reverse=False,min_gap_atr=0.0):
    ny,date,mins=ny_cash_groups(m5)
    h1=_resample(m5,"1h"); h1atr=_atr(h1,14).reindex(m5.index,method="ffill")
    pos=pd.Series(np.arange(len(m5)),index=m5.index)
    dates=sorted(set(date[(mins>=9*60+30)&(mins<16*60)]))
    closes={}
    for d in dates:
        idx=m5.index[(date==d)&(mins>=15*60+55)&(mins<16*60)]
        if len(idx): closes[d]=float(m5.loc[idx[-1],"close"])
    rows=[]
    for k,d in enumerate(dates):
        if k==0 or dates[k-1] not in closes: continue
        idx=m5.index[(date==d)&(mins>=9*60+30)&(mins<10*60)]
        if len(idx)<4: continue
        i=int(pos.loc[idx[0]])
        entry=float(m5.open.iat[i]); gap=entry-closes[dates[k-1]]
        a=float(h1atr.iat[i]) if np.isfinite(h1atr.iat[i]) else np.nan
        if not np.isfinite(a) or a<=0 or abs(gap)/a<min_gap_atr or gap==0: continue
        direction=1 if gap>0 else -1
        if reverse: direction*=-1
        dist=max(.50*a,abs(gap)*.75)
        stop=entry-direction*dist
        exit_i=int(pos.loc[idx[-1]])
        r=None; reason="first30_exit"
        for j in range(i,exit_i+1):
            lo=float(m5.low.iat[j]); hi=float(m5.high.iat[j])
            hs=lo<=stop if direction==1 else hi>=stop
            if hs: r=-1.0; reason="stop"; exit_i=j; break
        if r is None:
            r=(float(m5.close.iat[exit_i])-entry)/dist*direction
        rows.append({"symbol":symbol,"engine":f"{symbol}_OVN_{'REV' if reverse else 'MOM'}_A{min_gap_atr:g}","entry_time":m5.index[i],"exit_time":m5.index[exit_i]+pd.Timedelta(minutes=5),"direction":direction,"net_r":float(r-COST_R),"reason":reason})
    return pd.DataFrame(rows)


def structural_exit(xau,i,direction,dist,target_r=2.5,bars=36):
    entry=float(xau.open.iat[i]); stop=entry-direction*dist; target=entry+direction*target_r*dist
    end=min(len(xau),i+bars)
    for j in range(i,end):
        lo=float(xau.low.iat[j]); hi=float(xau.high.iat[j])
        hs=lo<=stop if direction==1 else hi>=stop
        ht=hi>=target if direction==1 else lo<=target
        if hs and ht: return j,-1.0,"stop_same_bar"
        if hs: return j,-1.0,"stop"
        if ht: return j,target_r,"target"
    j=end-1
    return j,(float(xau.close.iat[j])-entry)/dist*direction,"time_exit"


def xau_spx_flight(xau,spx,shock_atr=.8):
    common=xau.index.intersection(spx.index)
    if len(common)<100: return pd.DataFrame()
    sx=spx.reindex(common).copy(); gx=xau.reindex(common).copy()
    satr=_atr(sx,14); gatr=_atr(gx,14)
    shock=(sx.close-sx.open)/satr.replace(0,np.nan)
    ny=common.tz_convert("America/New_York"); mins=ny.hour*60+ny.minute
    active=(mins>=9*60+30)&(mins<15*60+30)
    pos=pd.Series(np.arange(len(gx)),index=common)
    rows=[]; used_day=None
    for ts in common[(shock<=-shock_atr)&active]:
        day=ts.tz_convert("America/New_York").date()
        if day==used_day: continue
        k=int(pos.loc[ts])
        if k+1>=len(gx): continue
        # Literature-supported direction: equity shock -> flight to gold.
        if float(gx.close.iat[k]) <= float(gx.open.iat[k]): continue
        a=float(gatr.iat[k])
        if not np.isfinite(a) or a<=0: continue
        i=k+1; recent=float(gx.low.iloc[max(0,k-5):k+1].min())
        entry=float(gx.open.iat[i]); dist=max(entry-recent+.10*a,.55*a)
        if dist<=0: continue
        j,r,reason=structural_exit(gx,i,1,dist,2.5,36)
        rows.append({"symbol":"XAUUSD","engine":f"XAU_SPX_FLIGHT_A{shock_atr:g}","entry_time":gx.index[i],"exit_time":gx.index[j]+pd.Timedelta(minutes=5),"direction":1,"net_r":float(r-COST_R),"reason":reason})
        used_day=day
    return pd.DataFrame(rows)


def xau_dxy_impulse(xau,dxy,threshold=.65):
    # 15m dollar impulse; trade gold opposite only when gold confirms the direction.
    g15=_resample(xau,"15min"); d15=_resample(dxy,"15min")
    common=g15.index.intersection(d15.index)
    if len(common)<100: return pd.DataFrame()
    gg=g15.reindex(common); dd=d15.reindex(common)
    da=_atr(dd,14); ga=_atr(gg,14)
    impulse=(dd.close-dd.open)/da.replace(0,np.nan)
    ny=common.tz_convert("America/New_York"); mins=ny.hour*60+ny.minute
    active=(mins>=8*60)&(mins<14*60)
    xau_pos=pd.Series(np.arange(len(xau)),index=xau.index)
    rows=[]; used_day=None
    for ts in common[(impulse.abs()>=threshold)&active]:
        day=ts.tz_convert("America/New_York").date()
        if day==used_day: continue
        d=-1 if impulse.loc[ts]>0 else 1
        gc=float(gg.loc[ts,"close"]-gg.loc[ts,"open"])
        if gc*d<=0: continue
        signal_close=ts+pd.Timedelta(minutes=15)
        future=xau.index[xau.index>=signal_close]
        if len(future)==0: continue
        i=int(xau_pos.loc[future[0]])
        a=float(ga.loc[ts])
        if not np.isfinite(a) or a<=0: continue
        recent=xau.iloc[max(0,i-6):i]
        entry=float(xau.open.iat[i])
        structural=(entry-float(recent.low.min())) if d==1 else (float(recent.high.max())-entry)
        dist=max(structural+.10*a,.55*a)
        if dist<=0: continue
        j,r,reason=structural_exit(xau,i,d,dist,2.5,36)
        rows.append({"symbol":"XAUUSD","engine":f"XAU_DXY_INV_A{threshold:g}","entry_time":xau.index[i],"exit_time":xau.index[j]+pd.Timedelta(minutes=5),"direction":d,"net_r":float(r-COST_R),"reason":reason})
        used_day=day
    return pd.DataFrame(rows)


def sim_month(tr,month):
    end=month+pd.offsets.MonthBegin(1)
    t=pd.to_datetime(tr.entry_time,utc=True) if not tr.empty else pd.Series(dtype="datetime64[ns, UTC]")
    x=tr[(t>=month)&(t<end)].sort_values(["entry_time","engine"]) if not tr.empty else tr.copy()
    eq=START_BALANCE; peak=eq; free=pd.Timestamp("1900-01-01",tz="UTC")
    cur=None; ds=eq; dp=0.; dl=0; mpd=0; maxdd=0.; worst=0.; used=0; breach=False
    def finish():
        nonlocal mpd,worst
        if cur is None:return
        worst=min(worst,dp/ds*100 if ds else 0)
        if dp/START_BALANCE*100>=.5: mpd+=1
    for r in x.itertuples(index=False):
        et=pd.Timestamp(r.entry_time); xt=pd.Timestamp(r.exit_time)
        if et<free: continue
        td=trade_day(et)
        if td!=cur:
            finish()
            if (eq/START_BALANCE-1)*100>=5 and mpd>=5: break
            cur=td; ds=eq; dp=0.; dl=0
        if dl>=2: continue
        pnl=eq*RISK*float(r.net_r); eq+=pnl; dp+=pnl; used+=1; free=xt
        if float(r.net_r)<0: dl+=1
        peak=max(peak,eq); maxdd=max(maxdd,(peak-eq)/peak*100)
        if (ds-eq)/ds*100>=3 or (START_BALANCE-eq)/START_BALANCE*100>=6:
            breach=True; break
    finish(); ret=(eq/START_BALANCE-1)*100
    return {"month":month.strftime("%Y-%m"),"return_pct":ret,"mpd":mpd,"trades":used,"max_dd":maxdd,"breach":breach,"pass5":ret>=5 and mpd>=5 and not breach}


def run(xau_current_path,xau_secondary_path,spx_path,nas_path,dxy_path,output):
    out=Path(output); out.mkdir(parents=True,exist_ok=True)
    xc=load_m5_csv(xau_current_path); xv=load_m5_csv(xau_secondary_path)
    spx=load_m5_csv(spx_path); nas=load_m5_csv(nas_path); dxy=load_m5_csv(dxy_path)

    val={}; cur={}
    for symbol,data in [("US500",spx),("US100",nas)]:
        for a in (0.0,.20,.35):
            tr=market_close_momentum(symbol,data,a); val[f"{symbol}_CLOSE_MOM_A{a:g}"]=tr; cur[f"{symbol}_CLOSE_MOM_A{a:g}"]=tr
        for reverse in (False,True):
            for a in (.10,.25):
                tr=overnight_first30(symbol,data,reverse,a)
                n=f"{symbol}_OVN_{'REV' if reverse else 'MOM'}_A{a:g}"
                val[n]=tr; cur[n]=tr

    for a in (.70,1.0,1.3):
        n=f"XAU_SPX_FLIGHT_A{a:g}"
        val[n]=xau_spx_flight(xv,spx,a); cur[n]=xau_spx_flight(xc,spx,a)
    for a in (.55,.80,1.05):
        n=f"XAU_DXY_INV_A{a:g}"
        val[n]=xau_dxy_impulse(xv,dxy,a); cur[n]=xau_dxy_impulse(xc,dxy,a)

    rows=[]; valid=[]
    # Avoid multiple thresholds from same family: choose best robust threshold pre-2026.
    fams={}
    for n,tr in val.items():
        ok,d,v=pre2026_ok(tr)
        robust=min(d["exp"] if d["exp"] is not None else -99,v["exp"] if v["exp"] is not None else -99)
        rows.append({"sleeve":n,"valid":ok,"robust_exp":robust,**{f"disc_{k}":z for k,z in d.items()},**{f"val_{k}":z for k,z in v.items()}})
        family=n.rsplit("_A",1)[0]
        if ok and (family not in fams or robust>fams[family][0]): fams[family]=(robust,n)
    valid=[z[1] for z in fams.values()]
    vf=pd.DataFrame(rows).sort_values(["valid","robust_exp"],ascending=[False,False],na_position="last")
    vf.to_csv(out/"validation.csv",index=False)

    xs=[cur[n] for n in valid if n in cur and not cur[n].empty]
    pt=pd.concat(xs,ignore_index=True).sort_values("entry_time") if xs else pd.DataFrame(columns=["entry_time","exit_time","net_r","engine"])
    data_end=min(spx.index.max(),nas.index.max(),dxy.index.max(),xc.index.max())+pd.Timedelta(minutes=5)
    current_month=data_end.floor("D").replace(day=1)
    starts=list(pd.date_range(pd.Timestamp("2026-01-01",tz="UTC"),current_month,freq="MS",inclusive="left"))
    ms=[sim_month(pt,m) for m in starts]
    mf=pd.DataFrame(ms); mf.to_csv(out/"monthly_2026.csv",index=False)
    summary={"validated_sleeves":valid,"months_pass5":sum(z["pass5"] for z in ms),"months_tested":len(ms),"all_months_pass":all(z["pass5"] for z in ms) if ms else False,"worst_month":min([z["return_pct"] for z in ms],default=None),"average_month":float(np.mean([z["return_pct"] for z in ms])) if ms else None}
    (out/"summary.json").write_text(json.dumps(safe(summary),indent=2),encoding="utf-8")
    lines=["# CASIO Phase 4 — Cross-Asset / Index Edge Hunt","",
           "Families: US500/US100 first-half-hour -> last-half-hour momentum, overnight -> first-30m continuation/reversal, XAU flight-to-safety after US500 shocks, and XAU inverse response to DXY impulses.",
           "Sleeve thresholds are selected only from 2020-2022 discovery + 2023-2025 validation. 2026 completed months are holdout.","",
           "## Validation","~~~text",vf.to_string(index=False),"~~~","",
           "## 2026","~~~text",mf.to_string(index=False),"~~~","",
           "## Verdict",json.dumps(safe(summary),indent=2)]
    (out/"REPORT.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--xau-current",required=True);p.add_argument("--xau-secondary",required=True)
    p.add_argument("--spx",required=True);p.add_argument("--nas",required=True);p.add_argument("--dxy",required=True)
    p.add_argument("--output",default="reports/finotive-phase4")
    a=p.parse_args();run(a.xau_current,a.xau_secondary,a.spx,a.nas,a.dxy,a.output)

if __name__=="__main__": main()
