from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd

OUT = Path("reports/casio-hybrid-core-v1-independent")
OUT.mkdir(parents=True, exist_ok=True)
COST_BPS = 1.0
TARGET_R = 3.0

def rma(s, n=14):
    return s.ewm(alpha=1/n, adjust=False, min_periods=n).mean()

def atr(df, n=14):
    pc=df.close.shift(1)
    tr=pd.concat([df.high-df.low,(df.high-pc).abs(),(df.low-pc).abs()],axis=1).max(axis=1)
    return rma(tr,n)

def adx(df,n=14):
    up=df.high.diff(); dn=-df.low.diff()
    p=pd.Series(np.where((up>dn)&(up>0),up,0.0),index=df.index)
    m=pd.Series(np.where((dn>up)&(dn>0),dn,0.0),index=df.index)
    a=atr(df,n)
    pdi=100*rma(p,n)/a.replace(0,np.nan); mdi=100*rma(m,n)/a.replace(0,np.nan)
    dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)
    return rma(dx,n)

def rs(df, rule):
    return df.resample(rule,label="left",closed="left",origin="epoch").agg(
        open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last"),volume=("volume","sum")
    ).dropna(subset=["open","high","low","close"])

def bias(df):
    e20=df.close.ewm(span=20,adjust=False,min_periods=1).mean()
    e50=df.close.ewm(span=50,adjust=False,min_periods=1).mean()
    return pd.Series(np.select([(e20>e50)&(df.close>e20),(e20<e50)&(df.close<e20)],[1,-1],0),index=df.index)

def align_closed(s, target_index, period):
    x=s.copy(); x.index=x.index+period
    ev=pd.DatetimeIndex(target_index+pd.Timedelta(minutes=15))
    y=x.reindex(ev,method="ffill"); y.index=target_index
    return y

def bars_since(flag):
    out=[]; age=None
    for x in flag.fillna(False).to_numpy(bool):
        age=0 if x else (None if age is None else age+1)
        out.append(np.nan if age is None else age)
    return pd.Series(out,index=flag.index,dtype=float)

def load_m5(path, start=None, end=None):
    df=pd.read_csv(path)
    tc="timestamp" if "timestamp" in df.columns else "time_utc"
    vc="volume" if "volume" in df.columns else "tick_volume"
    df[tc]=pd.to_datetime(df[tc],utc=True,errors="raise")
    df=df.sort_values(tc).drop_duplicates(tc,keep="last")
    for c in ["open","high","low","close",vc]:
        df[c]=pd.to_numeric(df[c],errors="coerce")
    df=df.set_index(tc)[["open","high","low","close",vc]].rename(columns={vc:"volume"}).dropna()
    if start is not None: df=df[df.index>=pd.Timestamp(start,tz="UTC")]
    if end is not None: df=df[df.index<pd.Timestamp(end,tz="UTC")]
    return df

def build_context(m5):
    m15=rs(m5,"15min"); h1=rs(m5,"1h"); h4=rs(m5,"4h")
    A=atr(m15)
    h1b=align_closed(bias(h1),m15.index,pd.Timedelta(hours=1))
    h4b=align_closed(bias(h4),m15.index,pd.Timedelta(hours=4))
    h4ad=align_closed(adx(h4),m15.index,pd.Timedelta(hours=4))
    e20=m15.close.ewm(span=20,adjust=False,min_periods=1).mean()
    e50=m15.close.ewm(span=50,adjust=False,min_periods=1).mean()
    rng=(m15.high-m15.low).replace(0,np.nan)
    bf=(m15.close-m15.open).abs()/rng
    loc=(m15.close-m15.low)/rng
    ra=rng/A.replace(0,np.nan)
    hh5=m15.high.shift(1).rolling(5,min_periods=5).max(); ll5=m15.low.shift(1).rolling(5,min_periods=5).min()
    hh10=m15.high.shift(1).rolling(10,min_periods=10).max(); ll10=m15.low.shift(1).rolling(10,min_periods=10).min()
    hh20=m15.high.shift(1).rolling(20,min_periods=20).max(); ll20=m15.low.shift(1).rolling(20,min_periods=20).min()
    bull=m15.close>m15.open; bear=m15.close<m15.open
    vL=(e20>e50)&(m15.close>hh10)&bull&bf.ge(.45)
    vS=(e20<e50)&(m15.close<ll10)&bear&bf.ge(.45)
    fvgL=m15.low>m15.high.shift(2); fvgS=m15.high<m15.low.shift(2)
    dispL=bull&bf.ge(.55)&loc.ge(.68)&ra.ge(.80)&(m15.close>hh5)
    dispS=bear&bf.ge(.55)&loc.le(.32)&ra.ge(.80)&(m15.close<ll5)
    swL=(m15.low<ll20)&(m15.close>ll20); swS=(m15.high>hh20)&(m15.close<hh20)
    saL=bars_since(swL); saS=bars_since(swS)
    mins=m15.index.hour*60+m15.index.minute
    primary=((mins>=420)&(mins<720))|((mins>=750)&(mins<1020))
    htfL=(h1b>=0)&(h4b>=0); htfS=(h1b<=0)&(h4b<=0)
    sfL=pd.Series(primary,index=m15.index)&htfL&saL.le(6)&(dispL|fvgL)
    sfS=pd.Series(primary,index=m15.index)&htfS&saS.le(6)&(dispS|fvgS)
    return m15,A,h1b,h4b,h4ad,vL,vS,sfL,sfS

def event_stream(m15,vL,vS,sfL,sfS):
    raw=[]; last={("V1",1):-99,("V1",-1):-99,("SF",1):-99,("SF",-1):-99}
    for i in range(60,len(m15)):
        for tech,l,s in [("V1",vL,vS),("SF",sfL,sfS)]:
            d=1 if bool(l.iat[i]) and not bool(s.iat[i]) else -1 if bool(s.iat[i]) and not bool(l.iat[i]) else 0
            if not d: continue
            cur=l if d==1 else s
            if bool(cur.iat[i-1]): continue
            if i-last[(tech,d)]<2: continue
            last[(tech,d)]=i
            raw.append((i,m15.index[i]+pd.Timedelta(minutes=15),tech,d))
    return pd.DataFrame(raw,columns=["i","signal_time","tech","direction"]).sort_values("signal_time").reset_index(drop=True)

def shadow_outcomes(m5,m15,A,ev):
    idx=m5.index
    ns=idx.view("int64")
    O=m5.open.to_numpy(float); H=m5.high.to_numpy(float); L=m5.low.to_numpy(float)
    out=[]
    for r in ev.itertuples(index=False):
        i=int(r.i); d=int(r.direction)
        ei=int(np.searchsorted(ns,r.signal_time.value,side="left"))
        if ei>=len(idx): continue
        entry=float(O[ei]); aa=float(A.iat[i])
        if not np.isfinite(aa) or aa<=0: continue
        lo=float(m15.low.iloc[max(0,i-5):i+1].min()); hi=float(m15.high.iloc[max(0,i-5):i+1].max())
        stop=lo-.1*aa if d==1 else hi+.1*aa
        risk=entry-stop if d==1 else stop-entry
        if not np.isfinite(risk) or risk<=0 or risk/aa<.35 or risk/aa>3.0: continue
        target=entry+d*TARGET_R*risk
        xi=None; gr=None; reason=None
        for j in range(ei,len(idx)):
            hs=L[j]<=stop if d==1 else H[j]>=stop
            ht=H[j]>=target if d==1 else L[j]<=target
            if hs:
                xi=j; gr=-1.0; reason="stop_same_m5" if ht else "stop"; break
            if ht:
                xi=j; gr=TARGET_R; reason="target"; break
        if xi is None: continue
        nr=gr-(entry*COST_BPS/10000.0)/risk
        out.append((i,r.signal_time,r.tech,d,idx[ei],idx[xi]+pd.Timedelta(minutes=5),entry,stop,gr,nr,reason))
    return pd.DataFrame(out,columns=["i","signal_time","tech","direction","entry_time","exit_time","entry","stop","gross_r","net_r","reason"])

def enrich_and_route(sh,h1b,h4b,h4ad):
    sh=sh.sort_values(["signal_time","tech"]).reset_index(drop=True).copy()
    inds=sh.i.to_numpy(int)
    sh["h1"]=h1b.iloc[inds].fillna(0).astype(int).to_numpy()
    sh["h4"]=h4b.iloc[inds].fillna(0).astype(int).to_numpy()
    sh["h4adx"]=h4ad.iloc[inds].fillna(0).to_numpy(float)
    sh["gate"]=False
    for tech in sh.tech.unique():
        allg=sh[sh.tech==tech].sort_values("exit_time")
        ext=allg.exit_time.astype("int64").to_numpy()
        vals=allg.net_r.to_numpy(float)
        cs=np.concatenate([[0.0],np.cumsum(vals)])
        rows=sh.index[sh.tech==tech]
        sig=sh.loc[rows,"signal_time"].astype("int64").to_numpy()
        low=(sh.loc[rows,"signal_time"]-pd.Timedelta(days=180)).astype("int64").to_numpy()
        right=np.searchsorted(ext,sig,side="left"); left=np.searchsorted(ext,low,side="left")
        cnt=right-left; sums=cs[right]-cs[left]
        sh.loc[rows,"gate"]=(cnt>=20)&(sums>0)
    sh["sf_support"]=False
    for d in [1,-1]:
        sf=np.sort(sh.loc[(sh.tech=="SF")&(sh.direction==d),"signal_time"].astype("int64").to_numpy())
        rows=sh.index[sh.direction==d]
        sig=sh.loc[rows,"signal_time"].astype("int64").to_numpy()
        lo=sig-int(pd.Timedelta(minutes=30).value)
        right=np.searchsorted(sf,sig,side="right"); left=np.searchsorted(sf,lo,side="left")
        sh.loc[rows,"sf_support"]=(right-left)>0
    out=[]; active=pd.Timestamp("1900-01-01",tz="UTC")
    for t,g in sh.groupby("signal_time",sort=True):
        if t<active: continue
        elig=[]
        for r in g.itertuples(index=False):
            if not bool(r.gate): continue
            d=int(r.direction); h1=int(r.h1); h4=int(r.h4)
            if h1==-d and h4==-d: continue
            strong=h1!=0 and h1==h4 and float(r.h4adx)>=18.0
            if strong:
                if d!=h1: continue
                rank=0 if r.tech=="V1" else 1
            else:
                if r.tech=="V1" and not bool(r.sf_support): continue
                rank=0 if r.tech=="SF" else 1
            elig.append((rank,r.tech,r))
        if not elig: continue
        elig.sort(key=lambda x:(x[0],x[1]))
        r=elig[0][2]; out.append(r._asdict()); active=r.exit_time+pd.Timedelta(minutes=1)
    return pd.DataFrame(out),sh

def summarize(t,start,end,label):
    if t.empty:
        return {"feed":label,"trades":0}
    x=t[(t.entry_time>=start)&(t.entry_time<end)].sort_values("entry_time").copy()
    rr=x.net_r.to_numpy(float)
    pf=rr[rr>0].sum()/abs(rr[rr<0].sum()) if (rr<0).any() else np.inf
    bal=100.; peak=100.; dd=0.0
    for z in rr:
        bal*=1+.01*z; peak=max(peak,bal); dd=max(dd,(peak-bal)/peak)
    return {
        "feed":label,"start":str(start),"end":str(end),"trades":len(x),
        "wr_pct":100*(x.gross_r>0).mean(),"net_r_1bp":rr.sum(),
        "expectancy_r":rr.mean(),"pf_1bp":pf,"rm100_1pct":bal,"maxdd_1pct":100*dd
    }

def run_one(path,label,start=None,end=None):
    m5=load_m5(path,start,end)
    m15,A,h1b,h4b,h4ad,vL,vS,sfL,sfS=build_context(m5)
    ev=event_stream(m15,vL,vS,sfL,sfS)
    sh=shadow_outcomes(m5,m15,A,ev)
    rt,en=enrich_and_route(sh,h1b,h4b,h4ad)
    startx=m5.index.min(); endx=m5.index.max()+pd.Timedelta(minutes=5)
    s=summarize(rt,startx,endx,label)
    rt.to_csv(OUT/f"{label}_trades.csv",index=False)
    en.to_csv(OUT/f"{label}_shadow.csv",index=False)
    yr=[]
    for y,g in rt.groupby(rt.entry_time.dt.year):
        r=g.net_r.to_numpy(float)
        pf=r[r>0].sum()/abs(r[r<0].sum()) if (r<0).any() else np.inf
        yr.append({"feed":label,"year":int(y),"trades":len(g),"wr_pct":100*(g.gross_r>0).mean(),"net_r":r.sum(),"pf":pf})
    pd.DataFrame(yr).to_csv(OUT/f"{label}_yearly.csv",index=False)
    return s

def main():
    rows=[]
    rows.append(run_one("data/xauusd_m5_dukascopy_research.csv","dukascopy_research"))
    rows.append(run_one("data/xauusd_m5_secondary_octafx_mt4.csv","octafx_2017_2025","2016-07-01","2026-01-31"))
    summary=pd.DataFrame(rows)
    summary.to_csv(OUT/"summary.csv",index=False)
    (OUT/"summary.json").write_text(json.dumps(rows,indent=2),encoding="utf-8")
    print(summary.to_string(index=False))

if __name__=="__main__":
    main()
