#!/usr/bin/env python3
from __future__ import annotations
import json, math, pathlib
import numpy as np
import pandas as pd

from casio.v3_core import load_m5_csv, _resample, _atr

ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/"data/xauusd_m5.csv"
OUT=ROOT/"reports/bermula-baseline"
OUT.mkdir(parents=True,exist_ok=True)

def pivot_flags(df, left=2, right=2):
    hi=df.high
    lo=df.low
    ph=pd.Series(False,index=df.index)
    pl=pd.Series(False,index=df.index)
    for k in range(1,left+1):
        ph &= True
    # confirmed pivots, marked only after right bars have elapsed
    ph0=(hi.shift(right) > hi.shift(right+1)) & (hi.shift(right) > hi.shift(right-1))
    pl0=(lo.shift(right) < lo.shift(right+1)) & (lo.shift(right) < lo.shift(right-1))
    if left>=2:
        ph0 &= (hi.shift(right) >= hi.shift(right+2))
        pl0 &= (lo.shift(right) <= lo.shift(right+2))
    return ph0.fillna(False), pl0.fillna(False)

def make_zones(h1:pd.DataFrame):
    atr=_atr(h1,14)
    prior_hi=h1.high.shift(1).rolling(10,min_periods=10).max()
    prior_lo=h1.low.shift(1).rolling(10,min_periods=10).min()
    body=(h1.close-h1.open).abs()
    bull_disp=(h1.close>prior_hi)&(h1.close>h1.open)&(body>=0.75*atr)&((h1.high-h1.low)>=0.9*atr)
    bear_disp=(h1.close<prior_lo)&(h1.close<h1.open)&(body>=0.75*atr)&((h1.high-h1.low)>=0.9*atr)
    zones=[]
    zid=0
    for i in range(12,len(h1)):
        side=None
        if bull_disp.iloc[i]: side="demand"
        elif bear_disp.iloc[i]: side="supply"
        if not side: continue
        want_bear = side=="demand"
        origin=None
        for j in range(i-1,max(-1,i-5),-1):
            is_bear=h1.close.iloc[j] < h1.open.iloc[j]
            if is_bear==want_bear:
                origin=j; break
        if origin is None: origin=i-1
        zid+=1
        zones.append(dict(
            zone_id=zid, side=side, created_time=h1.index[i]+pd.Timedelta(hours=1),
            origin_time=h1.index[origin], low=float(h1.low.iloc[origin]), high=float(h1.high.iloc[origin]),
            displacement_atr=float((h1.high.iloc[i]-h1.low.iloc[i])/atr.iloc[i]) if np.isfinite(atr.iloc[i]) and atr.iloc[i]>0 else np.nan,
            broken_level=float(prior_hi.iloc[i] if side=="demand" else prior_lo.iloc[i]),
            break_bar_low=float(h1.low.iloc[i]), break_bar_high=float(h1.high.iloc[i]),
        ))
    return pd.DataFrame(zones)

def nearest_opposing_target(zones, t, direction, entry):
    hist=zones[zones.created_time<=t]
    if direction==1:
        c=hist[(hist.side=="supply") & (hist.low>entry)]
        if c.empty: return None
        return float(c.sort_values("low").iloc[0].low)
    c=hist[(hist.side=="demand") & (hist.high<entry)]
    if c.empty: return None
    return float(c.sort_values("high",ascending=False).iloc[0].high)

def m5_confirm_long(m5, i):
    if i<4:return False
    return (m5.close.iloc[i] > m5.open.iloc[i] and
            m5.close.iloc[i] > m5.high.iloc[i-3:i].max())

def m5_confirm_short(m5, i):
    if i<4:return False
    return (m5.close.iloc[i] < m5.open.iloc[i] and
            m5.close.iloc[i] < m5.low.iloc[i-3:i].min())

def simulate_trade(m5,start_i,direction,entry,stop,target,max_bars=12*24*7):
    risk=abs(entry-stop)
    if risk<=0 or not np.isfinite(risk): return None
    end=min(len(m5),start_i+max_bars)
    for j in range(start_i+1,end):
        lo=float(m5.low.iloc[j]); hi=float(m5.high.iloc[j])
        hs=(lo<=stop) if direction==1 else (hi>=stop)
        ht=(hi>=target) if direction==1 else (lo<=target)
        if hs and ht:
            px=stop; reason="stop_same_bar"
        elif hs:
            px=stop; reason="stop"
        elif ht:
            px=target; reason="target"
        else:
            continue
        r=(px-entry)/risk if direction==1 else (entry-px)/risk
        return dict(exit_time=m5.index[j]+pd.Timedelta(minutes=5),exit_price=px,gross_r=float(r),exit_reason=reason,bars_held=j-start_i)
    # structural time stop at one week
    j=end-1
    px=float(m5.close.iloc[j])
    r=(px-entry)/risk if direction==1 else (entry-px)/risk
    return dict(exit_time=m5.index[j]+pd.Timedelta(minutes=5),exit_price=px,gross_r=float(r),exit_reason="time_exit",bars_held=j-start_i)

def backtest_reversal(m5,h1,zones):
    trades=[]; busy_until=None
    atr_h1=_atr(h1,14)
    atr_asof=pd.Series(atr_h1.values,index=h1.index+pd.Timedelta(hours=1))
    # first touch only after zone creation, invalidate if price crosses fully through zone before confirmation
    for _,z in zones.iterrows():
        direction=1 if z.side=="demand" else -1
        start=m5.index.searchsorted(pd.Timestamp(z.created_time))
        touched=False
        touch_i=None
        invalid=False
        # limit active life to 20 days
        end=min(len(m5),start+20*24*12)
        for i in range(start,end):
            t=m5.index[i]
            if busy_until is not None and t<=busy_until: continue
            lo=float(m5.low.iloc[i]); hi=float(m5.high.iloc[i]); close=float(m5.close.iloc[i])
            if direction==1 and close < float(z.low): invalid=True; break
            if direction==-1 and close > float(z.high): invalid=True; break
            overlap=(lo<=float(z.high) and hi>=float(z.low))
            if not touched and overlap:
                touched=True; touch_i=i
            if touched and i-touch_i<=12: # confirmation within 60 minutes
                ok=m5_confirm_long(m5,i) if direction==1 else m5_confirm_short(m5,i)
                if not ok: continue
                entry=close
                h1pos=atr_asof.index.searchsorted(t,side="right")-1
                a=float(atr_asof.iloc[h1pos]) if h1pos>=0 and np.isfinite(atr_asof.iloc[h1pos]) else max(0.1,abs(float(z.high)-float(z.low)))
                stop=float(z.low)-0.10*a if direction==1 else float(z.high)+0.10*a
                target=nearest_opposing_target(zones,t,direction,entry)
                if target is None: break
                risk=abs(entry-stop)
                rr=((target-entry)/risk) if direction==1 else ((entry-target)/risk)
                if rr<=0: break
                sim=simulate_trade(m5,i,direction,entry,stop,target)
                if sim:
                    trades.append(dict(setup="REVERSAL",zone_id=int(z.zone_id),entry_time=t+pd.Timedelta(minutes=5),
                        direction=direction,entry=entry,stop=stop,target=target,planned_rr=float(rr),
                        zone_low=float(z.low),zone_high=float(z.high),fresh_touch=True,**sim))
                    busy_until=sim["exit_time"]
                break
            if touched and i-touch_i>12: break
    return trades

def backtest_continuation(m5,h1,zones):
    trades=[]; busy_until=None
    atr=_atr(h1,14)
    prior_hi=h1.high.shift(1).rolling(20,min_periods=20).max()
    prior_lo=h1.low.shift(1).rolling(20,min_periods=20).min()
    body=(h1.close-h1.open).abs()
    bull=(h1.close>prior_hi)&(h1.close>h1.open)&(body>=0.75*atr)
    bear=(h1.close<prior_lo)&(h1.close<h1.open)&(body>=0.75*atr)
    for k in range(20,len(h1)):
        if not (bull.iloc[k] or bear.iloc[k]): continue
        direction=1 if bull.iloc[k] else -1
        level=float(prior_hi.iloc[k] if direction==1 else prior_lo.iloc[k])
        a=float(atr.iloc[k])
        if not np.isfinite(a) or a<=0: continue
        ready=h1.index[k]+pd.Timedelta(hours=1)
        start=m5.index.searchsorted(ready)
        end=min(len(m5),start+12*12) # 12h for pullback
        touch=None
        for i in range(start,end):
            t=m5.index[i]
            if busy_until is not None and t<=busy_until: continue
            lo=float(m5.low.iloc[i]); hi=float(m5.high.iloc[i]); close=float(m5.close.iloc[i])
            # failed breakout invalidation
            if direction==1 and close < level-0.15*a: break
            if direction==-1 and close > level+0.15*a: break
            in_retest=(lo<=level+0.15*a and hi>=level-0.15*a)
            if touch is None and in_retest: touch=i
            if touch is not None and i-touch<=12:
                ok=m5_confirm_long(m5,i) if direction==1 else m5_confirm_short(m5,i)
                if not ok: continue
                entry=close
                # structural stop beyond retest swing and level
                span=m5.iloc[touch:i+1]
                stop=min(float(span.low.min()),level-0.10*a) if direction==1 else max(float(span.high.max()),level+0.10*a)
                target=nearest_opposing_target(zones,t,direction,entry)
                if target is None: break
                risk=abs(entry-stop)
                rr=((target-entry)/risk) if direction==1 else ((entry-target)/risk)
                if rr<=0: break
                sim=simulate_trade(m5,i,direction,entry,stop,target)
                if sim:
                    trades.append(dict(setup="CONTINUATION",zone_id=np.nan,entry_time=t+pd.Timedelta(minutes=5),
                        direction=direction,entry=entry,stop=stop,target=target,planned_rr=float(rr),
                        zone_low=level-0.15*a,zone_high=level+0.15*a,fresh_touch=np.nan,**sim))
                    busy_until=sim["exit_time"]
                break
            if touch is not None and i-touch>12: break
    return trades

def metrics(df):
    if df.empty:return {}
    r=df.gross_r.astype(float)
    wins=(r>0); losses=(r<0)
    gp=float(r[wins].sum()); gl=float(-r[losses].sum())
    eq=r.cumsum(); dd=eq.cummax()-eq
    streak_w=streak_l=curw=curl=0
    for x in r:
        if x>0: curw+=1; curl=0; streak_w=max(streak_w,curw)
        elif x<0: curl+=1; curw=0; streak_l=max(streak_l,curl)
    return dict(trades=int(len(df)),wins=int(wins.sum()),losses=int(losses.sum()),win_rate=float(wins.mean()*100),
        expectancy_r=float(r.mean()),profit_factor=(gp/gl if gl else None),net_r=float(r.sum()),
        avg_win_r=float(r[wins].mean()) if wins.any() else None,avg_loss_r=float(r[losses].mean()) if losses.any() else None,
        median_planned_rr=float(df.planned_rr.median()),max_drawdown_r=float(dd.max() if len(dd) else 0),
        max_win_streak=streak_w,max_loss_streak=streak_l,target_hits=int((df.exit_reason=="target").sum()),
        stop_hits=int(df.exit_reason.str.startswith("stop").sum()),time_exits=int((df.exit_reason=="time_exit").sum()))

def monthly(df):
    x=df.copy()
    x["month"]=pd.to_datetime(x.entry_time,utc=True).dt.to_period("M").astype(str)
    rows=[]
    for m,g in x.groupby("month"):
        z=metrics(g); z["month"]=m; rows.append(z)
    return pd.DataFrame(rows)

def main():
    m5=load_m5_csv(DATA)
    h1=_resample(m5,"1h")
    zones=make_zones(h1)
    rev=backtest_reversal(m5,h1,zones)
    cont=backtest_continuation(m5,h1,zones)
    df=pd.DataFrame(rev+cont)
    if not df.empty:
        df=df.sort_values("entry_time").reset_index(drop=True)
    # combined one-position-at-a-time arbitration: earliest signal wins
    comb=[]
    busy=None
    for _,r in df.iterrows():
        if busy is not None and pd.Timestamp(r.entry_time)<=busy: continue
        comb.append(r.to_dict()); busy=pd.Timestamp(r.exit_time)
    combined=pd.DataFrame(comb)
    for name,x in [("reversal",pd.DataFrame(rev)),("continuation",pd.DataFrame(cont)),("combined",combined)]:
        x.to_csv(OUT/f"trades_{name}.csv",index=False)
        monthly(x).to_csv(OUT/f"monthly_{name}.csv",index=False)
    result={
        "data":{"source":str(DATA.relative_to(ROOT)),"rows":int(len(m5)),"start":str(m5.index.min()),"end":str(m5.index.max()),"h1_bars":int(len(h1)),"zones":int(len(zones))},
        "method":{
            "identity":"Paul-X Bermula/SNR faithful operational baseline",
            "creator_direct":["S/R foundation","Bermula origin zones","strong displacement","breakout -> pullback -> entry","lower-TF confirmation","role reversal","fresh zones preferred","reversal + continuation families","structural risk management"],
            "operational_assumptions":["H1 last opposite candle before structure-breaking displacement defines Bermula zone","full origin candle defines zone","strong displacement >=0.75 H1 ATR body","M5 close beyond previous 3 M5 bars is lower-TF confirmation","fresh reversal uses first zone touch","continuation retest band = +/-0.15 H1 ATR around broken H1 S/R","SL beyond structural zone/retest with 0.10 H1 ATR buffer","TP = nearest historically-known opposing H1 Bermula zone","no session filter","no fixed RR filter","one position at a time within each engine","same-bar stop+target resolves to stop","one-week time exit"],
        },
        "reversal":metrics(pd.DataFrame(rev)),
        "continuation":metrics(pd.DataFrame(cont)),
        "combined":metrics(combined),
    }
    (OUT/"summary.json").write_text(json.dumps(result,indent=2)+"\n")
    md=["# Bermula Backtest Report","",f"Data: {result['data']['start']} -> {result['data']['end']} ({result['data']['rows']:,} M5 bars)","",
        "## Important","This is a source-faithful **operational baseline**, not a claim that Paul-X numerically specified every threshold. Direct teachings and test assumptions are separated in summary.json.","",
        "## Results","",
        "| Engine | Trades | WR | Expectancy | PF | Net R | Max DD R | Median planned RR |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for n in ["reversal","continuation","combined"]:
        z=result[n]
        if z:
            md.append(f"| {n.title()} | {z['trades']} | {z['win_rate']:.2f}% | {z['expectancy_r']:.3f}R | {z['profit_factor']:.2f} | {z['net_r']:.2f}R | {z['max_drawdown_r']:.2f}R | {z['median_planned_rr']:.2f}R |")
    (OUT/"REPORT.md").write_text("\n".join(md)+"\n")
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
