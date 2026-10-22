from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd

START = pd.Timestamp("2024-01-01T00:00:00Z")
END = pd.Timestamp("2026-01-31T00:00:00Z")
OUT = Path("reports/bbma-robustness")
OUT.mkdir(parents=True, exist_ok=True)

@dataclass(frozen=True)
class Params:
    min_stop_atr: float = 1.5
    max_stop_atr: float = 2.5
    stop_buffer_atr: float = 0.15
    cooldown_bars: int = 36
    max_trades_day: int = 3
    tp_r: float = 3.0

def rma(s,n=14): return s.ewm(alpha=1/n,adjust=False,min_periods=n).mean()
def atr(df,n=14):
    pc=df.close.shift()
    tr=pd.concat([(df.high-df.low),(df.high-pc).abs(),(df.low-pc).abs()],axis=1).max(axis=1)
    return rma(tr,n)
def wma(s,n):
    out=0.0; d=n*(n+1)/2.0
    for j in range(n): out += (j+1)*s.shift(n-1-j)
    return out/d
def bars_since(event):
    ev=event.fillna(False).to_numpy(bool); idx=np.arange(len(ev)); last=np.where(ev,idx,-1)
    last=np.maximum.accumulate(last); out=idx-last; out[last<0]=100000
    return pd.Series(out,index=event.index)
def read_csv(path):
    df=pd.read_csv(path)
    t="timestamp" if "timestamp" in df.columns else "time_utc"
    df[t]=pd.to_datetime(df[t],utc=True,errors="coerce")
    df=df.rename(columns={t:"timestamp"})[["timestamp","open","high","low","close"]]
    for c in ["open","high","low","close"]: df[c]=pd.to_numeric(df[c],errors="coerce")
    return df.dropna().drop_duplicates("timestamp").sort_values("timestamp").set_index("timestamp")
def ohlc(df,rule):
    return df[["open","high","low","close"]].resample(rule,label="left",closed="left").agg(
        {"open":"first","high":"max","low":"min","close":"last"}).dropna()
def tf_features(x):
    z=x.copy(); z["atr"]=atr(z); z["mid"]=z.close.rolling(20).mean()
    sd=z.close.rolling(20).std(ddof=0); z["upper"]=z.mid+2*sd; z["lower"]=z.mid-2*sd
    z["ema20"]=z.close.ewm(span=20,adjust=False,min_periods=20).mean()
    z["ema50"]=z.close.ewm(span=50,adjust=False,min_periods=50).mean()
    z["ma5h"]=wma(z.high,5); z["ma5l"]=wma(z.low,5); z["ma10h"]=wma(z.high,10); z["ma10l"]=wma(z.low,10)
    z["trend_long"]=(z.ema20>z.ema50)&(z.close>z.ema20)
    z["trend_short"]=(z.ema20<z.ema50)&(z.close<z.ema20)
    extL=z.low<z.lower; extS=z.high>z.upper
    z["ext_long_age"]=bars_since(extL); z["ext_short_age"]=bars_since(extS)
    z["re_long"]=(z.ext_long_age<=4)&(z.close>z.ma5h)&(z.close>z.lower)&(z.close>z.open)&(z.ema20>=z.ema50)
    z["re_short"]=(z.ext_short_age<=4)&(z.close<z.ma5l)&(z.close<z.upper)&(z.close<z.open)&(z.ema20<=z.ema50)
    z["zl_long"]=(z.ma5l>z.mid)&(z.ma10l>z.mid)&(z.mid>z.ema50)
    z["zl_short"]=(z.ma5h<z.mid)&(z.ma10h<z.mid)&(z.mid<z.ema50)
    return z
def add_context(df):
    m5=tf_features(df)
    for p,z in {"m15":tf_features(ohlc(df,"15min")),"h1":tf_features(ohlc(df,"1h")),"h4":tf_features(ohlc(df,"4h"))}.items():
        zz=z.shift(1).reindex(m5.index,method="ffill")
        for c in ["trend_long","trend_short","zl_long","zl_short"]: m5[f"{p}_{c}"]=zz[c]
    return m5.dropna(subset=["atr","h4_trend_long","h1_trend_long","m15_trend_long"])

def masks(x,name):
    m5L=x.re_long.fillna(False).astype(bool); m5S=x.re_short.fillna(False).astype(bool)
    h1L=x.h1_trend_long.fillna(False).astype(bool); h1S=x.h1_trend_short.fillna(False).astype(bool)
    m15L=x.m15_trend_long.fillna(False).astype(bool); m15S=x.m15_trend_short.fillna(False).astype(bool)
    h4L=x.h4_trend_long.fillna(False).astype(bool); h4S=x.h4_trend_short.fillna(False).astype(bool)
    if name=="strict_trend":
        return m5L&h1L&m15L&h4L, m5S&h1S&m15S&h4S
    h1zlL=x.h1_zl_long.fillna(False).astype(bool); h1zlS=x.h1_zl_short.fillna(False).astype(bool)
    m15zlL=x.m15_zl_long.fillna(False).astype(bool); m15zlS=x.m15_zl_short.fillna(False).astype(bool)
    baseL=m5L&~h1S&~m15S&h4L; baseS=m5S&~h1L&~m15L&h4S
    if name=="h1_zero_loss":
        return baseL&h1zlL, baseS&h1zlS
    if name=="m15_zero_loss":
        return baseL&m15zlL, baseS&m15zlS
    if name=="h1_m15_zero_loss":
        return baseL&h1zlL&m15zlL, baseS&h1zlS&m15zlS
    raise ValueError(name)

def replay(x,L,S,p,cost_bps_side):
    idx=x.index; n=len(x)
    hi=x.high.to_numpy(float); lo=x.low.to_numpy(float); cl=x.close.to_numpy(float); at=x.atr.to_numpy(float)
    L=L.to_numpy(bool); S=S.to_numpy(bool)
    rlow=pd.Series(lo,index=idx).shift(1).rolling(7).min().to_numpy(float)
    rhigh=pd.Series(hi,index=idx).shift(1).rolling(7).max().to_numpy(float)
    out=[]; pos=0; entry=risk=stop=0.0; last=-10**9; cur=None; dayn=0; et=-1
    for i in range(n):
        d=idx[i].date()
        if d!=cur: cur=d; dayn=0
        if pos:
            hs=lo[i]<=stop if pos==1 else hi[i]>=stop
            ht=hi[i]>=entry+p.tp_r*risk if pos==1 else lo[i]<=entry-p.tp_r*risk
            if hs or ht:
                gross=-1.0 if hs else p.tp_r
                cost=2*cost_bps_side*1e-4*entry/risk
                out.append((idx[et],idx[i],gross-cost,gross,cost))
                pos=0
            continue
        if dayn>=p.max_trades_day or i-last<p.cooldown_bars: continue
        if not L[i] and not S[i]: continue
        side=1 if L[i] and not S[i] else -1 if S[i] and not L[i] else 0
        if side==0 or not np.isfinite(rlow[i]) or not np.isfinite(rhigh[i]) or not np.isfinite(at[i]) or at[i]<=0: continue
        st=(rlow[i]-p.stop_buffer_atr*at[i]) if side==1 else (rhigh[i]+p.stop_buffer_atr*at[i])
        rk=(cl[i]-st) if side==1 else (st-cl[i]); ra=rk/at[i]
        if rk<=0 or not (p.min_stop_atr<=ra<=p.max_stop_atr): continue
        pos=side; entry=cl[i]; risk=rk; stop=st; last=i; dayn+=1; et=i
    return pd.DataFrame(out,columns=["entry_time","exit_time","r","gross_r","cost_r"])

def metrics(t):
    if t.empty: return dict(trades=0,trades_month=0,win_rate=0,avg_r=0,pf=0,net_r=0,max_dd_r=0)
    r=t.r.astype(float); gp=r[r>0].sum(); gl=-r[r<0].sum()
    eq=r.cumsum(); peak=np.maximum.accumulate(np.r_[0,eq.values]); dd=peak[1:]-eq.values
    months=max((t.entry_time.max()-t.entry_time.min()).total_seconds()/(86400*30.4375),1)
    return dict(trades=len(t),trades_month=len(t)/months,win_rate=100*(r>0).mean(),avg_r=r.mean(),
                pf=gp/gl if gl>0 else float("inf"),net_r=r.sum(),max_dd_r=float(dd.max(initial=0)))
def money(t):
    eq=100.; peak=100.; mdd=0.
    for rr in t.sort_values("entry_time").r.astype(float):
        eq*=1+0.05*rr; peak=max(peak,eq); mdd=max(mdd,(peak-eq)/peak)
    return eq,100*mdd

feeds={
 "dukascopy":Path("data/xauusd_m5_dukascopy_research.csv"),
 "octafx":Path("data/xauusd_m5_secondary_octafx_mt4.csv"),
}
p=Params()
rows=[]
for feed,path in feeds.items():
    d=read_csv(path)
    d=d[(d.index>=START)&(d.index<END)]
    x=add_context(d)
    for variant in ["strict_trend","h1_zero_loss","m15_zero_loss","h1_m15_zero_loss"]:
        L,S=masks(x,variant)
        for cost in [0.0,0.10,0.25,0.50]:
            t=replay(x,L,S,p,cost)
            m=metrics(t); end_rm,dd=money(t)
            rows.append(dict(feed=feed,variant=variant,cost_bps_side=cost,data_start=str(x.index.min()),
                             data_end=str(x.index.max()),end_rm=end_rm,max_dd_pct=dd,**m))
res=pd.DataFrame(rows)
res.to_csv(OUT/"cross_feed.csv",index=False)
summary=OUT/"REPORT.md"
summary.write_text("# BBMA robustness cross-feed\n\nCommon window: 2024-01-01 to 2026-01-30 UTC.\n\n"+res.to_markdown(index=False)+"\n")
print(res.to_string(index=False))
