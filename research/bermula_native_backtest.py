#!/usr/bin/env python3
from __future__ import annotations
import json, math, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data/xauusd_m5.csv"
OUT = ROOT / "reports/bermula-native"
OUT.mkdir(parents=True, exist_ok=True)

PARAMS = {
    "h4_pivot_left": 2,
    "h4_pivot_right": 2,
    "origin_displacement_atr": 1.5,
    "origin_displacement_bars": 3,
    "breakout_body_atr": 0.8,
    "breakout_close_buffer_atr": 0.05,
    "pullback_expiry_hours": 24,
    "pullback_touch_tolerance_atr": 0.05,
    "confirmation_window_m5_bars": 12,
    "confirmation_lookback_m5_bars": 5,
    "confirmation_body_atr": 0.40,
    "stop_buffer_h1_atr": 0.10,
    "round_trip_cost_bps": 1.0,
    "require_h4_structure_bias": True,
}

def rma(s, n):
    return s.ewm(alpha=1/n, adjust=False, min_periods=n).mean()

def atr(df, n=14):
    pc=df.close.shift(1)
    tr=pd.concat([(df.high-df.low),(df.high-pc).abs(),(df.low-pc).abs()],axis=1).max(axis=1)
    return rma(tr,n)

def resample(df, rule):
    return df.resample(rule,label="left",closed="left",origin="epoch").agg(
        {"open":"first","high":"max","low":"min","close":"last","volume":"sum"}
    ).dropna()

def load():
    x=pd.read_csv(DATA)
    x["timestamp"]=pd.to_datetime(x.timestamp,utc=True)
    x=x.sort_values("timestamp").drop_duplicates("timestamp",keep="last").set_index("timestamp")
    for c in ["open","high","low","close","volume"]:
        x[c]=pd.to_numeric(x[c],errors="coerce")
    return x.dropna(subset=["open","high","low","close"])

def build_zones(h4):
    a=atr(h4)
    zones=[]
    L=PARAMS["h4_pivot_left"]; R=PARAMS["h4_pivot_right"]; D=PARAMS["origin_displacement_bars"]
    for i in range(max(L,14), len(h4)-max(R,D)-1):
        lo=float(h4.low.iloc[i]); hi=float(h4.high.iloc[i]); av=float(a.iloc[i])
        if not np.isfinite(av) or av<=0: continue
        # Meaningful origin = confirmed swing plus strong departure in the expected direction.
        is_low = lo < float(h4.low.iloc[i-L:i].min()) and lo <= float(h4.low.iloc[i+1:i+R+1].min())
        is_high = hi > float(h4.high.iloc[i-L:i].max()) and hi >= float(h4.high.iloc[i+1:i+R+1].max())
        future=h4.iloc[i+1:i+D+1]
        confirm_i=i+max(R,D)+1
        if confirm_i>=len(h4): continue
        confirm_time=h4.index[confirm_i]
        if is_low and float(future.close.max())-hi >= PARAMS["origin_displacement_atr"]*av:
            zones.append({"id":len(zones),"kind":"support","origin_time":h4.index[i],"confirm_time":confirm_time,
                          "low":lo,"high":hi,"mid":(lo+hi)/2,"atr":av})
        if is_high and lo-float(future.close.min()) >= PARAMS["origin_displacement_atr"]*av:
            zones.append({"id":len(zones),"kind":"resistance","origin_time":h4.index[i],"confirm_time":confirm_time,
                          "low":lo,"high":hi,"mid":(lo+hi)/2,"atr":av})
    return pd.DataFrame(zones)

def h4_bias_series(zones,h1_index):
    zs=zones.sort_values("confirm_time").to_dict("records")
    out=[]; p=0; highs=[]; lows=[]
    for t in h1_index + pd.Timedelta(hours=1):
        while p<len(zs) and zs[p]["confirm_time"]<=t:
            z=zs[p]
            (highs if z["kind"]=="resistance" else lows).append(float(z["mid"]))
            p+=1
        bias=0
        if len(highs)>=2 and len(lows)>=2:
            if highs[-1]>highs[-2] and lows[-1]>lows[-2]: bias=1
            elif highs[-1]<highs[-2] and lows[-1]<lows[-2]: bias=-1
        out.append(bias)
    return pd.Series(out,index=h1_index,dtype=int)

def breakout_events(h1,zones):
    h1=h1.copy()
    h1["atr"]=atr(h1)
    h1["bias"]=h4_bias_series(zones,h1.index)
    n=len(zones)
    broken_up=np.array([False]*n)
    broken_dn=np.array([False]*n)
    break_up_time=np.array([np.datetime64("NaT")]*n,dtype="datetime64[ns]")
    break_dn_time=np.array([np.datetime64("NaT")]*n,dtype="datetime64[ns]")
    zkind=zones.kind.to_numpy()
    zhi=zones.high.to_numpy(float); zlo=zones.low.to_numpy(float)
    zconf=pd.to_datetime(zones.confirm_time,utc=True).astype("int64").to_numpy()
    events=[]
    prev_close=float(h1.close.iloc[0])
    for i in range(1,len(h1)):
        row=h1.iloc[i]; t=h1.index[i]+pd.Timedelta(hours=1)
        tns=t.value
        active=zconf<=tns
        close=float(row.close); op=float(row.open); av=float(row.atr) if np.isfinite(row.atr) else np.nan
        if not np.isfinite(av) or av<=0:
            prev_close=close; continue
        body=abs(close-op)
        # resistance broken upward for first time
        cross_up=active & (zkind=="resistance") & (~broken_up) & (prev_close<=zhi) & (close>zhi)
        idx_up=np.flatnonzero(cross_up)
        if idx_up.size:
            for j in idx_up:
                broken_up[j]=True; break_up_time[j]=np.datetime64(t.tz_convert(None))
            j=idx_up[np.argmax(zhi[idx_up])]
            strong=(close>op and body>=PARAMS["breakout_body_atr"]*av and close>=zhi[j]+PARAMS["breakout_close_buffer_atr"]*av)
            bias_ok=(int(row.bias)==1) if PARAMS["require_h4_structure_bias"] else True
            if strong and bias_ok:
                events.append({"break_time":t,"direction":1,"zone_id":int(j),"zone_low":zlo[j],"zone_high":zhi[j],
                               "h1_atr":av,"h4_bias":int(row.bias),"breakout_body_atr":body/av})
        # support broken downward for first time
        cross_dn=active & (zkind=="support") & (~broken_dn) & (prev_close>=zlo) & (close<zlo)
        idx_dn=np.flatnonzero(cross_dn)
        if idx_dn.size:
            for j in idx_dn:
                broken_dn[j]=True; break_dn_time[j]=np.datetime64(t.tz_convert(None))
            j=idx_dn[np.argmin(zlo[idx_dn])]
            strong=(close<op and body>=PARAMS["breakout_body_atr"]*av and close<=zlo[j]-PARAMS["breakout_close_buffer_atr"]*av)
            bias_ok=(int(row.bias)==-1) if PARAMS["require_h4_structure_bias"] else True
            if strong and bias_ok:
                events.append({"break_time":t,"direction":-1,"zone_id":int(j),"zone_low":zlo[j],"zone_high":zhi[j],
                               "h1_atr":av,"h4_bias":int(row.bias),"breakout_body_atr":body/av})
        prev_close=close
    zones=zones.copy()
    zones["break_up_time"]=pd.to_datetime(break_up_time,utc=True)
    zones["break_down_time"]=pd.to_datetime(break_dn_time,utc=True)
    return pd.DataFrame(events), zones, h1

def nearest_target(zones, entry_time, direction, entry, own_zone_id):
    known=zones[(zones.confirm_time<=entry_time) & (zones.id!=own_zone_id)]
    if direction==1:
        # nearest still-unbroken resistance above entry; target its near edge.
        x=known[(known.kind=="resistance") & (known.low>entry)]
        x=x[x.break_up_time.isna() | (x.break_up_time>entry_time)]
        if x.empty: return None,None
        z=x.sort_values("low").iloc[0]
        return float(z.low), int(z.id)
    x=known[(known.kind=="support") & (known.high<entry)]
    x=x[x.break_down_time.isna() | (x.break_down_time>entry_time)]
    if x.empty: return None,None
    z=x.sort_values("high",ascending=False).iloc[0]
    return float(z.high), int(z.id)

def make_trades(m5, events, zones):
    x=m5.copy()
    x["atr"]=atr(x)
    prior_hi=x.high.shift(1).rolling(PARAMS["confirmation_lookback_m5_bars"],min_periods=PARAMS["confirmation_lookback_m5_bars"]).max()
    prior_lo=x.low.shift(1).rolling(PARAMS["confirmation_lookback_m5_bars"],min_periods=PARAMS["confirmation_lookback_m5_bars"]).min()
    idx=x.index
    rows=[]; busy_until=None
    for _,e in events.sort_values("break_time").iterrows():
        bt=pd.Timestamp(e.break_time)
        if busy_until is not None and bt<=busy_until: continue
        start=idx.searchsorted(bt,side="left")
        expiry=bt+pd.Timedelta(hours=PARAMS["pullback_expiry_hours"])
        end=min(len(idx),idx.searchsorted(expiry,side="right"))
        touched=None
        direction=int(e.direction); zl=float(e.zone_low); zh=float(e.zone_high); h1atr=float(e.h1_atr)
        tol=PARAMS["pullback_touch_tolerance_atr"]*h1atr
        # First post-break pullback into/onto the broken zone.
        for j in range(start,end):
            bar=x.iloc[j]
            if direction==1:
                if float(bar.low) < zl-PARAMS["stop_buffer_h1_atr"]*h1atr: break
                if float(bar.low)<=zh+tol:
                    touched=j; break
            else:
                if float(bar.high) > zh+PARAMS["stop_buffer_h1_atr"]*h1atr: break
                if float(bar.high)>=zl-tol:
                    touched=j; break
        if touched is None: continue
        # Lower-TF confirmation: directional micro breakout after the touch.
        c_end=min(len(idx),touched+PARAMS["confirmation_window_m5_bars"]+1)
        cj=None
        for j in range(touched,c_end):
            bar=x.iloc[j]; av=float(bar.atr) if np.isfinite(bar.atr) else np.nan
            if not np.isfinite(av) or av<=0: continue
            body=abs(float(bar.close)-float(bar.open))
            if direction==1:
                if float(bar.low)<zl-PARAMS["stop_buffer_h1_atr"]*h1atr: break
                if float(bar.close)>float(prior_hi.iloc[j]) and float(bar.close)>float(bar.open) and body>=PARAMS["confirmation_body_atr"]*av:
                    cj=j; break
            else:
                if float(bar.high)>zh+PARAMS["stop_buffer_h1_atr"]*h1atr: break
                if float(bar.close)<float(prior_lo.iloc[j]) and float(bar.close)<float(bar.open) and body>=PARAMS["confirmation_body_atr"]*av:
                    cj=j; break
        if cj is None: continue
        entry=float(x.close.iloc[cj]); entry_time=idx[cj]+pd.Timedelta(minutes=5)
        stop=(zl-PARAMS["stop_buffer_h1_atr"]*h1atr) if direction==1 else (zh+PARAMS["stop_buffer_h1_atr"]*h1atr)
        risk=(entry-stop) if direction==1 else (stop-entry)
        if risk<=0: continue
        target,target_zone=nearest_target(zones,entry_time,direction,entry,int(e.zone_id))
        if target is None: continue
        reward=(target-entry) if direction==1 else (entry-target)
        if reward<=0: continue
        planned_rr=reward/risk
        # Resolve at M5. Conservative if SL and TP occur in same bar.
        exit_time=None; exit_price=None; reason=None
        for k in range(cj+1,len(idx)):
            lo=float(x.low.iloc[k]); hi=float(x.high.iloc[k])
            hs=(lo<=stop) if direction==1 else (hi>=stop)
            ht=(hi>=target) if direction==1 else (lo<=target)
            if hs and ht:
                exit_price=stop; reason="stop_same_bar"
            elif hs:
                exit_price=stop; reason="stop"
            elif ht:
                exit_price=target; reason="target_structure"
            if reason:
                exit_time=idx[k]+pd.Timedelta(minutes=5); break
        if reason is None: continue
        gross_r=((exit_price-entry)/risk) if direction==1 else ((entry-exit_price)/risk)
        cost_r=(entry*PARAMS["round_trip_cost_bps"]/10000.0)/risk
        net_r=gross_r-cost_r
        rows.append({
            "break_time":bt,"touch_time":idx[touched],"entry_time":entry_time,"exit_time":exit_time,
            "direction":"LONG" if direction==1 else "SHORT","zone_id":int(e.zone_id),"target_zone_id":target_zone,
            "entry":entry,"stop":stop,"target":target,"risk_distance":risk,"planned_rr":planned_rr,
            "breakout_body_atr":float(e.breakout_body_atr),"gross_r":gross_r,"cost_r":cost_r,"net_r":net_r,
            "exit_reason":reason
        })
        busy_until=exit_time
    return pd.DataFrame(rows)

def streaks(vals):
    maxw=maxl=curw=curl=0
    for v in vals:
        if v>0: curw+=1; curl=0; maxw=max(maxw,curw)
        elif v<0: curl+=1; curw=0; maxl=max(maxl,curl)
        else: curw=curl=0
    return maxw,maxl

def metrics(t):
    if t.empty: return {}
    r=t.net_r.astype(float)
    gw=float(r[r>0].sum()); gl=float(-r[r<0].sum())
    eq=r.cumsum(); dd=eq.cummax()-eq
    w,l=streaks(r.to_list())
    return {
        "trades":int(len(t)),"wins":int((r>0).sum()),"losses":int((r<0).sum()),
        "win_rate_pct":float((r>0).mean()*100),"expectancy_r":float(r.mean()),
        "profit_factor":float(gw/gl) if gl>0 else None,"net_r":float(r.sum()),
        "max_drawdown_r":float(dd.max()),"avg_planned_rr":float(t.planned_rr.mean()),
        "median_planned_rr":float(t.planned_rr.median()),"max_win_streak":w,"max_loss_streak":l,
        "long_trades":int((t.direction=="LONG").sum()),"short_trades":int((t.direction=="SHORT").sum())
    }

def main():
    m5=load(); h1=resample(m5,"1h"); h4=resample(m5,"4h")
    zones=build_zones(h4)
    events,zones,h1x=breakout_events(h1,zones)
    trades=make_trades(m5,events,zones)
    if not trades.empty:
        trades["year"]=pd.to_datetime(trades.entry_time,utc=True).dt.year
        trades["month"]=pd.to_datetime(trades.entry_time,utc=True).dt.strftime("%Y-%m")
    overall=metrics(trades)
    yearly={str(y):metrics(g) for y,g in trades.groupby("year")} if not trades.empty else {}
    monthly={str(m):metrics(g) for m,g in trades.groupby("month")} if not trades.empty else {}
    by_dir={str(d):metrics(g) for d,g in trades.groupby("direction")} if not trades.empty else {}
    report={
        "strategy":"Paul-X Bermula Breakout/Continuation — source-faithful prototype",
        "data":{"start":str(m5.index.min()),"end":str(m5.index.max()),"m5_bars":int(len(m5))},
        "parameters":PARAMS,
        "zones":int(len(zones)),"breakout_events":int(len(events)),"overall":overall,
        "yearly":yearly,"monthly":monthly,"by_direction":by_dir,
        "scope_note":"Reversal family excluded because the exact creator trigger remains unresolved. This test uses only the higher-confidence Breakout -> Pullback -> lower-TF confirmation sequence.",
        "assumption_note":"Full H4 pivot candle is used as the Bermula zone; H4 structural HH/HL or LH/LL is used for direction; strong breakout and M5 micro-BOS thresholds are deterministic operationalizations, not claimed verbatim creator parameters.",
    }
    trades.to_csv(OUT/"trades.csv",index=False)
    zones.to_csv(OUT/"zones.csv",index=False)
    events.to_csv(OUT/"breakout_events.csv",index=False)
    (OUT/"report.json").write_text(json.dumps(report,indent=2,default=str))
    md=["# Bermula Native Backtest Report","",
        f"Data: {report['data']['start']} to {report['data']['end']} ({report['data']['m5_bars']:,} M5 bars)","",
        "## Scope",report["scope_note"],"",report["assumption_note"],"",
        "## Overall",f"```json\n{json.dumps(overall,indent=2)}\n```","",
        "## Yearly","| Year | Trades | WR % | Net R | Exp R | PF | Max DD R | Avg planned RR |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for y,m in yearly.items():
        md.append(f"| {y} | {m.get('trades',0)} | {m.get('win_rate_pct',0):.2f} | {m.get('net_r',0):.2f} | {m.get('expectancy_r',0):.3f} | {(m.get('profit_factor') or 0):.2f} | {m.get('max_drawdown_r',0):.2f} | {m.get('avg_planned_rr',0):.2f} |")
    md+=["","## Monthly","| Month | Trades | WR % | Net R | Exp R | PF | Max DD R |","|---|---:|---:|---:|---:|---:|---:|"]
    for mo,m in monthly.items():
        md.append(f"| {mo} | {m.get('trades',0)} | {m.get('win_rate_pct',0):.2f} | {m.get('net_r',0):.2f} | {m.get('expectancy_r',0):.3f} | {(m.get('profit_factor') or 0):.2f} | {m.get('max_drawdown_r',0):.2f} |")
    (OUT/"REPORT.md").write_text("\n".join(md)+"\n")
    print(json.dumps(report,indent=2,default=str))

if __name__=="__main__":
    main()
