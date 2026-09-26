from __future__ import annotations

from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

from .v3_core import _atr, _resample, load_m5_csv


START_BALANCE = 2500.0
RISK = 0.005
MONTHLY_FLOOR = 5.0
COST_R = 0.05


def _safe(x):
    if isinstance(x, dict):
        return {str(k): _safe(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_safe(v) for v in x]
    if isinstance(x, pd.Timestamp):
        return x.isoformat()
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, (np.floating, float)):
        y=float(x); return y if math.isfinite(y) else None
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    return x


def _pip(symbol: str) -> float:
    return 0.01 if symbol.endswith("JPY") else 0.0001


def _trade_day(ts: pd.Timestamp) -> str:
    ny = pd.Timestamp(ts).tz_convert("America/New_York")
    return (ny - pd.Timedelta(hours=17)).strftime("%Y-%m-%d")


def _m5_exit(m5: pd.DataFrame, start_i: int, direction: int, entry: float, stop: float, target: float | None, bars: int) -> tuple[int,float,str]:
    end=min(len(m5), start_i+bars)
    risk=abs(entry-stop)
    for j in range(start_i,end):
        lo=float(m5.low.iat[j]); hi=float(m5.high.iat[j]); close=float(m5.close.iat[j])
        hs=lo<=stop if direction==1 else hi>=stop
        ht=False if target is None else (hi>=target if direction==1 else lo<=target)
        if hs and ht:
            return j,-1.0,"stop_same_bar"
        if hs:
            return j,-1.0,"stop"
        if ht:
            return j,abs(target-entry)/risk,"target"
        if j==end-1:
            return j,(close-entry)/risk*direction,"time_exit"
    return end-1,0.0,"time_exit"


def daily_gap_events(symbol: str, m5: pd.DataFrame, threshold_pips: float=2.0) -> pd.DataFrame:
    # FX trading day begins at 17:00 New York. Fade the discontinuity at the first
    # bar of the new trading day and exit within one hour. A real 1x-gap hard stop
    # is added; the prior close is the natural 1R full-gap target.
    ny=m5.index.tz_convert("America/New_York")
    keys=pd.Series([(x-pd.Timedelta(hours=17)).date() for x in ny],index=m5.index)
    starts=m5.groupby(keys).head(1).index
    pos=pd.Series(np.arange(len(m5)),index=m5.index)
    rows=[]
    pip=_pip(symbol)
    for ts in starts:
        i=int(pos.loc[ts])
        if i<1 or i+12>=len(m5):
            continue
        # Ignore weekend reopen; it is a separate regime and can interact with
        # weekend-holding/add-on conditions. Research only Mon-Fri daily auctions.
        nydow=ts.tz_convert("America/New_York").dayofweek
        if nydow>=4:
            continue
        entry=float(m5.open.iat[i]); prev=float(m5.close.iat[i-1])
        gap=entry-prev
        gp=abs(gap)/pip
        if gp < threshold_pips:
            continue
        d=-1 if gap>0 else 1
        dist=abs(gap)
        stop=entry-d*dist
        target=prev
        j,r,reason=_m5_exit(m5,i,d,entry,stop,target,12)
        rows.append({
            "symbol":symbol,"engine":f"GAP_FADE_{threshold_pips:g}P",
            "entry_time":m5.index[i],"exit_time":m5.index[j]+pd.Timedelta(minutes=5),
            "direction":d,"gap_pips":gp,"net_r":float(r-COST_R),"reason":reason,
        })
    return pd.DataFrame(rows)


def gap_selector(events: list[pd.DataFrame]) -> pd.DataFrame:
    xs=[x for x in events if x is not None and not x.empty]
    if not xs:
        return pd.DataFrame()
    x=pd.concat(xs,ignore_index=True)
    x["td"]=x.entry_time.map(_trade_day)
    x=x.sort_values(["td","gap_pips"],ascending=[True,False]).drop_duplicates("td",keep="first")
    x["engine"]="FX_GAP_SELECTOR"
    return x.drop(columns=["td"]).sort_values("entry_time").reset_index(drop=True)


def london_open_events(symbol: str, m5: pd.DataFrame, reverse: bool=False) -> pd.DataFrame:
    # Literature-inspired London-open sign test. The paper reports GBPUSD with
    # reversed direction and USDJPY as the only cost-positive spot instrument.
    lon=m5.index.tz_convert("Europe/London")
    date=pd.Series(lon.date,index=m5.index)
    minute=lon.hour*60+lon.minute
    first=(minute>=8*60)&(minute<8*60+30)
    groups=m5[first].groupby(date[first])
    pos=pd.Series(np.arange(len(m5)),index=m5.index)
    h1=_resample(m5,"1h")
    h1atr=_atr(h1,14)
    atr_aligned=h1atr.reindex(m5.index,method="ffill")
    rows=[]
    for d,g in groups:
        if len(g)<4:
            continue
        end_ts=g.index[-1]
        i=int(pos.loc[end_ts])+1
        if i>=len(m5):
            continue
        move=float(g.close.iloc[-1]-g.open.iloc[0])
        if move==0:
            continue
        direction=1 if move>0 else -1
        if reverse:
            direction*=-1
        entry=float(m5.open.iat[i])
        orng=float(g.high.max()-g.low.min())
        a=float(atr_aligned.iat[i]) if np.isfinite(atr_aligned.iat[i]) else np.nan
        dist=max(orng, .30*a if np.isfinite(a) else 0.0)
        if not np.isfinite(dist) or dist<=0:
            continue
        stop=entry-direction*dist
        target=entry+direction*2.0*dist
        # through 12:00 London = at most 42 M5 bars after 08:30
        j,r,reason=_m5_exit(m5,i,direction,entry,stop,target,42)
        rows.append({
            "symbol":symbol,
            "engine":f"{symbol}_LO30_{'REV' if reverse else 'MOM'}",
            "entry_time":m5.index[i],"exit_time":m5.index[j]+pd.Timedelta(minutes=5),
            "direction":direction,"net_r":float(r-COST_R),"reason":reason,
        })
    return pd.DataFrame(rows)


def xau_asia_momentum(m5: pd.DataFrame) -> pd.DataFrame:
    # Post-2022 literature reports gold momentum concentrated into Asia and a
    # surviving long-only variant after costs. Use prior completed Asia return as
    # the signal and only take positive continuation.
    utc=m5.index
    day=pd.Series(utc.floor("D"),index=utc)
    asia=(utc.hour>=0)&(utc.hour<8)
    sessions=m5[asia].groupby(day[asia]).agg(
        open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last")
    )
    sessions["ret"]=sessions.close/sessions.open-1.0
    sessions["prev_ret"]=sessions.ret.shift(1)
    pos=pd.Series(np.arange(len(m5)),index=m5.index)
    h1=_resample(m5,"1h"); h1atr=_atr(h1,14).reindex(m5.index,method="ffill")
    rows=[]
    for d,s in sessions.iterrows():
        if not np.isfinite(s.prev_ret) or s.prev_ret<=0:
            continue
        idx=m5.index[(m5.index.floor("D")==d)&(m5.index.hour>=0)&(m5.index.hour<8)]
        if len(idx)<10:
            continue
        i=int(pos.loc[idx[0]])
        entry=float(m5.open.iat[i])
        a=float(h1atr.iat[i]) if np.isfinite(h1atr.iat[i]) else np.nan
        if not np.isfinite(a) or a<=0:
            continue
        dist=.75*a
        stop=entry-dist
        target=entry+1.5*dist
        j,r,reason=_m5_exit(m5,i,1,entry,stop,target,min(96,len(m5)-i))
        rows.append({
            "symbol":"XAUUSD","engine":"XAU_ASIA_LONG_MOM",
            "entry_time":m5.index[i],"exit_time":m5.index[j]+pd.Timedelta(minutes=5),
            "direction":1,"net_r":float(r-COST_R),"reason":reason,
        })
    return pd.DataFrame(rows)


def metrics(tr: pd.DataFrame, a: str, b: str) -> dict:
    if tr is None or tr.empty:
        return {"trades":0,"exp_r":None,"pf":None,"wr":None}
    t=pd.to_datetime(tr.entry_time,utc=True)
    r=pd.to_numeric(tr.loc[(t>=pd.Timestamp(a,tz="UTC"))&(t<pd.Timestamp(b,tz="UTC")),"net_r"],errors="coerce").dropna()
    if r.empty:
        return {"trades":0,"exp_r":None,"pf":None,"wr":None}
    w=r[r>0]; l=r[r<0]
    return {"trades":int(len(r)),"exp_r":float(r.mean()),"pf":float(w.sum()/(-l.sum())) if len(l) else 999.0,"wr":float((r>0).mean()*100)}


def pre2026_ok(tr: pd.DataFrame) -> tuple[bool,dict,dict]:
    disc=metrics(tr,"2020-01-01","2023-01-01")
    val=metrics(tr,"2023-01-01","2026-01-01")
    ok=(disc["trades"]>=20 and val["trades"]>=20 and (disc["exp_r"] or -99)>0 and (val["exp_r"] or -99)>0 and (disc["pf"] or 0)>1 and (val["pf"] or 0)>1)
    return ok,disc,val


def portfolio_sim(trades: pd.DataFrame, month: pd.Timestamp) -> dict:
    b=month+pd.offsets.MonthBegin(1)
    t=pd.to_datetime(trades.entry_time,utc=True) if not trades.empty else pd.Series(dtype="datetime64[ns, UTC]")
    x=trades[(t>=month)&(t<b)].sort_values(["entry_time","engine"]).copy() if not trades.empty else trades.copy()

    eq=START_BALANCE; peak=eq; free=pd.Timestamp("1900-01-01",tz="UTC")
    cur=None; day_start=eq; day_pnl=0.0; day_losses=0; mpd=0; worstday=0.0; maxdd=0.0; used=0; breach=False

    def finish():
        nonlocal mpd,worstday
        if cur is None: return
        p0=day_pnl/START_BALANCE*100
        pd_=day_pnl/day_start*100 if day_start else 0.0
        worstday=min(worstday,pd_)
        if p0>=.5: mpd+=1

    for r in x.itertuples(index=False):
        et=pd.Timestamp(r.entry_time); xt=pd.Timestamp(r.exit_time)
        if et<free: continue
        td=_trade_day(et)
        if td!=cur:
            finish()
            if (eq/START_BALANCE-1)*100>=MONTHLY_FLOOR and mpd>=5:
                break
            cur=td; day_start=eq; day_pnl=0.0; day_losses=0
        if day_losses>=2: continue
        pnl=eq*RISK*float(r.net_r)
        eq+=pnl; day_pnl+=pnl; used+=1; free=xt
        if float(r.net_r)<0: day_losses+=1
        peak=max(peak,eq); maxdd=max(maxdd,(peak-eq)/peak*100)
        dd_day=(day_start-eq)/day_start*100
        dd_static=(START_BALANCE-eq)/START_BALANCE*100
        if dd_day>=3 or dd_static>=6:
            breach=True; break
    finish()
    ret=(eq/START_BALANCE-1)*100
    return {"month":month.strftime("%Y-%m"),"return_pct":ret,"mpd":mpd,"trades":used,"max_dd_pct":maxdd,"worst_day_pct":worstday,"breach":breach,"pass5":ret>=5 and mpd>=5 and not breach}


def run(xau_path: str|Path, gbp_path: str|Path, eur_path: str|Path, jpy_path: str|Path, aud_path: str|Path, output: str|Path) -> dict:
    out=Path(output); out.mkdir(parents=True,exist_ok=True)
    data={
        "XAUUSD":load_m5_csv(xau_path),
        "GBPUSD":load_m5_csv(gbp_path),
        "EURUSD":load_m5_csv(eur_path),
        "USDJPY":load_m5_csv(jpy_path),
        "AUDUSD":load_m5_csv(aud_path),
    }

    sleeves={}
    gaps=[]
    for s in ("GBPUSD","EURUSD","USDJPY","AUDUSD"):
        g=daily_gap_events(s,data[s],2.0); sleeves[f"{s}_GAP2"]=g; gaps.append(g)
    sleeves["FX_GAP_SELECTOR"]=gap_selector(gaps)
    sleeves["USDJPY_LO30_MOM"]=london_open_events("USDJPY",data["USDJPY"],False)
    sleeves["GBPUSD_LO30_REV"]=london_open_events("GBPUSD",data["GBPUSD"],True)
    sleeves["XAU_ASIA_LONG_MOM"]=xau_asia_momentum(data["XAUUSD"])

    valrows=[]; valid=[]
    for n,tr in sleeves.items():
        ok,d,v=pre2026_ok(tr)
        valrows.append({"sleeve":n,"valid":ok,**{f"disc_{k}":x for k,x in d.items()},**{f"val_{k}":x for k,x in v.items()}})
        if ok: valid.append(n)
    vf=pd.DataFrame(valrows).sort_values(["valid","val_exp_r"],ascending=[False,False],na_position="last")
    vf.to_csv(out/"sleeve_validation.csv",index=False)

    portfolios={
        "GAP_SELECTOR_ONLY":["FX_GAP_SELECTOR"] if "FX_GAP_SELECTOR" in valid else [],
        "ALL_VALIDATED":valid,
        "GAP_PLUS_SESSION":list(dict.fromkeys((["FX_GAP_SELECTOR"] if "FX_GAP_SELECTOR" in valid else [])+[x for x in ["USDJPY_LO30_MOM","XAU_ASIA_LONG_MOM","GBPUSD_LO30_REV"] if x in valid])),
    }

    starts=list(pd.date_range(pd.Timestamp("2026-01-01",tz="UTC"),pd.Timestamp("2026-09-01",tz="UTC"),freq="MS"))
    monthly=[]; ranks=[]
    for pname,names in portfolios.items():
        xs=[sleeves[n] for n in names if n in sleeves and not sleeves[n].empty]
        pt=pd.concat(xs,ignore_index=True).sort_values("entry_time") if xs else pd.DataFrame(columns=["entry_time","exit_time","net_r","engine"])
        pt.to_csv(out/f"{pname}_trades.csv",index=False)
        ms=[portfolio_sim(pt,m) for m in starts]
        for z in ms: monthly.append({"portfolio":pname,"sleeves":"|".join(names),**z})
        ranks.append({
            "portfolio":pname,"sleeves":"|".join(names),"months_pass5":sum(z["pass5"] for z in ms),
            "all_months_pass":all(z["pass5"] for z in ms) if ms else False,
            "worst_month":min(z["return_pct"] for z in ms) if ms else None,
            "avg_month":float(np.mean([z["return_pct"] for z in ms])) if ms else None,
            "min_mpd":min(z["mpd"] for z in ms) if ms else 0,
            "max_dd":max(z["max_dd_pct"] for z in ms) if ms else None,
            "breach_months":sum(z["breach"] for z in ms),
        })
    mf=pd.DataFrame(monthly); rf=pd.DataFrame(ranks).sort_values(["all_months_pass","months_pass5","worst_month","avg_month"],ascending=[False,False,False,False])
    mf.to_csv(out/"monthly_2026.csv",index=False); rf.to_csv(out/"ranking.csv",index=False)

    summary={"validated_sleeves":valid,"ranking":rf.to_dict(orient="records")}
    (out/"summary.json").write_text(json.dumps(_safe(summary),indent=2),encoding="utf-8")
    lines=[
        "# CASIO Phase 3 — New Edge Families",
        "",
        "Families: FX daily-reopen gap fade, USDJPY London-open momentum, GBPUSD reversed London-open signal, XAU Asia long-session momentum.",
        "Selection uses only 2020-2022 discovery + 2023-2025 validation. Jan-Aug 2026 is holdout.",
        "",
        "## Sleeve validation","~~~text",vf.to_string(index=False),"~~~",
        "","## 2026 5% floor ranking","~~~text",rf.to_string(index=False),"~~~","",
    ]
    if len(rf):
        best=rf.iloc[0]
        b=mf[mf.portfolio.eq(best.portfolio)]
        lines += ["## Best monthly detail","~~~text",b.to_string(index=False),"~~~"]
    (out/"REPORT.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))
    return summary


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--xau",required=True); p.add_argument("--gbp",required=True); p.add_argument("--eur",required=True); p.add_argument("--jpy",required=True); p.add_argument("--aud",required=True)
    p.add_argument("--output",default="reports/finotive-phase3")
    a=p.parse_args(); run(a.xau,a.gbp,a.eur,a.jpy,a.aud,a.output)


if __name__=="__main__":
    main()
