from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
from numba import njit

from casio.bbma_cleaner_robustness import FEEDS, NS_DAY, load_feed, metric
from casio.bbma_crossfeed_grid import prepare_base, signals, VARIANTS

OUT = Path("reports/bbma-lifecycle-grid")
OUT.mkdir(parents=True, exist_ok=True)

ENTRY_NAMES = ["CSM_STRICT", "CSM_MED", "CSM_WIDE", "UNION_MED", "STATE_TREND"]
ENTRY_SPECS = {v[0]: v for v in VARIANTS if v[0] in ENTRY_NAMES}

EXIT_SPECS = [
    # name, t1, t2, first_weight, be_trigger, be_lock, max_hold_bars, reverse_exit
    ("FULL_3R_24H", 3.0, 3.0, 1.0, 0.50, 0.25, 288, True),
    ("SPLIT_3R4R_24H", 3.0, 4.0, 0.50, 0.50, 0.25, 288, True),
    ("SPLIT_4R5R_24H", 4.0, 5.0, 0.25, 1.00, 0.25, 288, True),
    ("RUN_4R8R_24H", 4.0, 8.0, 0.20, 1.25, 0.25, 288, True),
    ("FULL_3R_48H", 3.0, 3.0, 1.0, 0.50, 0.25, 576, True),
    ("SPLIT_3R4R_48H", 3.0, 4.0, 0.50, 0.50, 0.25, 576, True),
    ("RUN_4R8R_48H", 4.0, 8.0, 0.20, 1.25, 0.25, 576, True),
]


def prepare_lifecycle(frame: pd.DataFrame) -> pd.DataFrame:
    f = prepare_base(frame)
    # Rebuild M5 native opposite-signal exits from the same feature definitions already
    # present in prepare_base's source frame via lightweight local calculations.
    close = f["close"]
    mid = close.rolling(20).mean()
    sd = close.rolling(20).std(ddof=0)
    bbu, bbl = mid + 2.0 * sd, mid - 2.0 * sd
    # For lifecycle emergency exit, Momentum/CSM alone is sufficient and BBMA-native.
    f["opp_for_long"] = close < bbl
    f["opp_for_short"] = close > bbu
    return f


@njit
def replay_lifecycle_np(
    o,h,l,c,atr,long_signal,short_signal,long_stop,short_stop,opp_long,opp_short,daycodes,
    t1r,t2r,w1,be_trigger,be_lock,max_hold,reverse_exit,min_risk_atr,max_risk_atr,cooldown,max_per_day,
):
    n=len(o)
    cap=n//4+1000
    rs=np.empty(cap,np.float64); entries=np.empty(cap,np.int64); exits=np.empty(cap,np.int64); sides=np.empty(cap,np.int8)
    reasons=np.empty(cap,np.int8)
    cnt=0
    pos=0; entry=stop=risk=t1=t2=0.0; rem=realized=0.0; entry_i=-1
    pending_i=-1; pending_side=0; pending_stop=0.0
    last_entry=-10**9; cur_day=-10**9; day_count=0
    for i in range(1,n):
        d=daycodes[i]
        if d!=cur_day:
            cur_day=d; day_count=0

        if pos==0 and pending_i==i:
            side=pending_side; e=o[i]; st=pending_stop; a=atr[i-1]
            rrisk=(e-st) if side==1 else (st-e)
            ratr=rrisk/a if a>0 else 1e9
            if rrisk>0 and min_risk_atr<=ratr<=max_risk_atr and day_count<max_per_day and i-last_entry>=cooldown:
                pos=side; entry=e; stop=st; risk=rrisk
                t1=entry+side*t1r*risk; t2=entry+side*t2r*risk
                rem=1.0; realized=0.0; entry_i=i; last_entry=i; day_count+=1
            pending_i=-1

        if pos!=0:
            hit_stop=(l[i]<=stop) if pos==1 else (h[i]>=stop)
            hit_t1=(h[i]>=t1) if pos==1 else (l[i]<=t1)
            hit_t2=(h[i]>=t2) if pos==1 else (l[i]<=t2)

            if hit_stop:
                sr=(stop-entry)/risk if pos==1 else (entry-stop)/risk
                realized+=rem*sr
                rs[cnt]=realized; entries[cnt]=entry_i; exits[cnt]=i; sides[cnt]=pos; reasons[cnt]=1; cnt+=1
                pos=0; rem=0.0
                continue

            if rem==1.0 and hit_t1:
                if w1>=0.999999 or t2r<=t1r:
                    realized+=t1r
                    rs[cnt]=realized; entries[cnt]=entry_i; exits[cnt]=i; sides[cnt]=pos; reasons[cnt]=2; cnt+=1
                    pos=0; rem=0.0
                    continue
                realized+=w1*t1r; rem=1.0-w1
                if hit_t2:
                    realized+=rem*t2r
                    rs[cnt]=realized; entries[cnt]=entry_i; exits[cnt]=i; sides[cnt]=pos; reasons[cnt]=3; cnt+=1
                    pos=0; rem=0.0
                    continue
            elif 0.0<rem<1.0 and hit_t2:
                realized+=rem*t2r
                rs[cnt]=realized; entries[cnt]=entry_i; exits[cnt]=i; sides[cnt]=pos; reasons[cnt]=3; cnt+=1
                pos=0; rem=0.0
                continue

            # BBMA-native opposite Momentum/CSM emergency exit, evaluated at bar close.
            reverse_now = (opp_long[i] if pos==1 else opp_short[i]) if reverse_exit else False
            timed_out = i-entry_i>=max_hold
            if reverse_now or timed_out:
                cr=(c[i]-entry)/risk if pos==1 else (entry-c[i])/risk
                realized+=rem*cr
                rs[cnt]=realized; entries[cnt]=entry_i; exits[cnt]=i; sides[cnt]=pos
                reasons[cnt]=4 if reverse_now else 5
                cnt+=1; pos=0; rem=0.0
                continue

            excursion=(h[i]-entry)/risk if pos==1 else (entry-l[i])/risk
            if excursion>=be_trigger:
                ns=entry+pos*be_lock*risk
                if pos==1:
                    if ns>stop: stop=ns
                else:
                    if ns<stop: stop=ns

        if pos==0 and pending_i==-1 and i+1<n:
            if day_count<max_per_day and i+1-last_entry>=cooldown:
                lb=long_signal[i]; sb=short_signal[i]
                if lb or sb:
                    side=1 if (lb and not sb) else -1 if (sb and not lb) else (1 if c[i]>=o[i] else -1)
                    pending_i=i+1; pending_side=side; pending_stop=long_stop[i] if side==1 else short_stop[i]

    # Force-close any final open trade at final close, so no lifecycle survives data end.
    if pos!=0:
        i=n-1
        cr=(c[i]-entry)/risk if pos==1 else (entry-c[i])/risk
        realized+=rem*cr
        rs[cnt]=realized; entries[cnt]=entry_i; exits[cnt]=i; sides[cnt]=pos; reasons[cnt]=6; cnt+=1
    return rs[:cnt],entries[:cnt],exits[:cnt],sides[:cnt],reasons[:cnt]


def replay(f,spec,exit_spec):
    lb,sb=signals(f,spec)
    name,t1,t2,w1,bet,bel,mh,rev=exit_spec
    idx_ns=f.index.view("int64"); days=(idx_ns//NS_DAY).astype(np.int64)
    o=f.open.to_numpy(float); h=f.high.to_numpy(float); l=f.low.to_numpy(float); c=f.close.to_numpy(float); a=f.atr.to_numpy(float)
    ls=f.long_stop.to_numpy(float); ss=f.short_stop.to_numpy(float)
    r,ei,xi,side,reason=replay_lifecycle_np(
        o,h,l,c,a,lb.to_numpy(bool),sb.to_numpy(bool),ls,ss,
        f.opp_for_long.to_numpy(bool),f.opp_for_short.to_numpy(bool),days,
        t1,t2,w1,bet,bel,mh,rev,1.0,2.0,36,3
    )
    sig=ei-1; entry=o[ei]; risk=np.where(side==1,entry-ls[sig],ss[sig]-entry)
    t=pd.DataFrame({"entry_time":f.index[ei],"exit_time":f.index[xi],"side":side,"entry":entry,"risk":risk,"gross_r":r,"reason":reason})
    t["net_r"]=t["gross_r"]-(0.1714+0.00007*t["entry"])/t["risk"]
    return t


def summarize(feed,entry_name,exit_name,t,coverage_start,coverage_end):
    months=max(1.0,(coverage_end-coverage_start).total_seconds()/(365.25/12*86400))
    gm=metric(t.gross_r); nm=metric(t.net_r)
    return {
        "feed":feed,"entry":entry_name,"exit":exit_name,"trades":len(t),"trades_per_month":len(t)/months,
        "gross_avg_r":gm["avg_r"],"gross_pf":gm["pf"],"net_avg_r":nm["avg_r"],"net_pf":nm["pf"],
        "median_hold_h":float(((t.exit_time-t.entry_time).dt.total_seconds()/3600).median()) if len(t) else 0.0,
        "p90_hold_h":float(((t.exit_time-t.entry_time).dt.total_seconds()/3600).quantile(.9)) if len(t) else 0.0,
    }


def main():
    rows=[]
    for feed,path in FEEDS.items():
        raw=load_feed(path)
        f=prepare_lifecycle(raw)
        start=max(pd.Timestamp("2017-01-01",tz="UTC"),f.index.min()); end=f.index.max()+pd.Timedelta(minutes=5)
        f=f[f.index>=start]
        for ename,spec in ENTRY_SPECS.items():
            for ex in EXIT_SPECS:
                t=replay(f,spec,ex)
                rows.append(summarize(feed,ename,ex[0],t,start,end))
    df=pd.DataFrame(rows)
    df.to_csv(OUT/"grid.csv",index=False)

    # Rank combinations on the weaker feed.
    rank=[]
    for (entry,ex),g in df.groupby(["entry","exit"]):
        rec={"entry":entry,"exit":ex}
        for feed in FEEDS:
            r=g[g.feed==feed].iloc[0]
            rec[f"{feed}_tpm"]=float(r.trades_per_month)
            rec[f"{feed}_avg"]=float(r.net_avg_r)
            rec[f"{feed}_pf"]=float(r.net_pf)
        rec["min_avg"]=min(rec[f"{f}_avg"] for f in FEEDS)
        rec["min_tpm"]=min(rec[f"{f}_tpm"] for f in FEEDS)
        rank.append(rec)
    rk=pd.DataFrame(rank).sort_values(["min_avg","min_tpm"],ascending=False)
    rk.to_csv(OUT/"rank.csv",index=False)
    print("# TOP CROSS-FEED LIFECYCLE COMBINATIONS")
    print(rk.head(25).to_string(index=False))
    print("\n# ALL FEED RESULTS")
    print(df.to_string(index=False))


if __name__=="__main__":
    main()
