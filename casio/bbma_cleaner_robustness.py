from __future__ import annotations
import argparse, json
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class Params:
    min_risk_atr: float = 0.8
    max_risk_atr: float = 1.8
    stop_buffer_atr: float = 0.15
    be_trigger_r: float = 0.5
    be_lock_r: float = 0.25
    tp1_r: float = 3.0
    tp2_r: float = 4.0
    tp1_fraction: float = 0.5
    cooldown_bars: int = 60
    max_trades_per_day: int = 2
    h1_valid_bars: int = 1
    m15_valid_bars: int = 1
    cost_usd: float = 0.0
    next_open_entry: bool = False

def rma(s,n): return s.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
def atr(df,n=14):
    pc=df.close.shift(1)
    tr=pd.concat([(df.high-df.low),(df.high-pc).abs(),(df.low-pc).abs()],axis=1).max(axis=1)
    return rma(tr,n)
def wma(s,n):
    w=np.arange(1,n+1,dtype=float); d=w.sum()
    return s.rolling(n).apply(lambda x: float(np.dot(x,w)/d),raw=True)
def bars_since(ev):
    a=ev.fillna(False).to_numpy(bool); idx=np.arange(len(a)); last=np.where(a,idx,-1); last=np.maximum.accumulate(last); age=idx-last; age[last<0]=10000
    return pd.Series(age,index=ev.index,dtype='int32')

def normalize(path):
    df=pd.read_csv(path)
    tcol='timestamp' if 'timestamp' in df.columns else 'time_utc'
    df[tcol]=pd.to_datetime(df[tcol],utc=True,errors='coerce')
    df=df.rename(columns={tcol:'timestamp'}).dropna(subset=['timestamp','open','high','low','close'])
    df=df.drop_duplicates('timestamp').sort_values('timestamp').set_index('timestamp')
    for c in ['open','high','low','close']: df[c]=pd.to_numeric(df[c],errors='coerce')
    return df.dropna(subset=['open','high','low','close'])[['open','high','low','close']]

def tf_features(ohlc):
    x=ohlc.copy()
    x['atr']=atr(x)
    x['ema50']=x.close.ewm(span=50,adjust=False,min_periods=50).mean()
    x['ema50_slope']=x.ema50-x.ema50.shift(2)
    x['mid']=x.close.rolling(20).mean()
    sd=x.close.rolling(20).std(ddof=0)
    x['upper']=x['mid']+2*sd; x['lower']=x['mid']-2*sd
    x['ma5h']=wma(x.high,5); x['ma5l']=wma(x.low,5); x['ma10h']=wma(x.high,10); x['ma10l']=wma(x.low,10)
    x['csm_long']=x.close>x.upper; x['csm_short']=x.close<x.lower
    x['csak_long']=(x.close>x.ma5h)&(x.close>x.ma10h)&(x.close>x['mid'])
    x['csak_short']=(x.close<x.ma5l)&(x.close<x.ma10l)&(x.close<x['mid'])
    prior_long=(x.csm_long|x.csak_long).shift(1).fillna(False)
    prior_short=(x.csm_short|x.csak_short).shift(1).fillna(False)
    ageL=bars_since(prior_long); ageS=bars_since(prior_short)
    long_zone=pd.concat([x.ma5l,x.ma10l],axis=1).max(axis=1)
    short_zone=pd.concat([x.ma5h,x.ma10h],axis=1).min(axis=1)
    x['re_long']=(ageL<=12)&(x.low<=long_zone)&(x.close>long_zone)&(x.close>x.open)&(x.close>=x['mid'])
    x['re_short']=(ageS<=12)&(x.high>=short_zone)&(x.close<short_zone)&(x.close<x.open)&(x.close<=x['mid'])
    x['zl_long']=(x.ma5l>x['mid'])&(x.ma10l>x['mid'])&(x['mid']>x.ema50)
    x['zl_short']=(x.ma5h<x['mid'])&(x.ma10h<x['mid'])&(x['mid']<x.ema50)
    x['major_long']=(x.close>x.ema50)&(x.ema50_slope>0)
    x['major_short']=(x.close<x.ema50)&(x.ema50_slope<0)
    x['re_long_age']=bars_since(x.re_long); x['re_short_age']=bars_since(x.re_short)
    x['csm_long_age']=bars_since(x.csm_long); x['csm_short_age']=bars_since(x.csm_short)
    return x

def resample(df,rule):
    return df.resample(rule,label='left',closed='left').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()

def add_context(df):
    base=tf_features(df); out=base.copy()
    for p,rule in [('m15','15min'),('h1','1h'),('h4','4h')]:
        f=tf_features(resample(df,rule)).shift(1).reindex(df.index,method='ffill')
        keep=['re_long_age','re_short_age','csm_long_age','csm_short_age','zl_long','zl_short','major_long','major_short','re_long','re_short','csm_long','csm_short']
        for c in keep: out[f'{p}_{c}']=f[c]
    return out.dropna(subset=['atr','h4_major_long','h4_major_short','h1_re_long_age','m15_re_long_age'])

def signals(x,p):
    h1_re_L=x.h1_re_long_age<=p.h1_valid_bars
    h1_re_S=(x.h1_re_short_age<=p.h1_valid_bars)&x.h1_zl_short.astype(bool)
    h1_csm_L=x.h1_csm_long_age<=p.h1_valid_bars; h1_csm_S=x.h1_csm_short_age<=p.h1_valid_bars
    m15_re_L=x.m15_re_long_age<=p.m15_valid_bars; m15_re_S=x.m15_re_short_age<=p.m15_valid_bars
    m15_csm_L=x.m15_csm_long_age<=p.m15_valid_bars; m15_csm_S=x.m15_csm_short_age<=p.m15_valid_bars
    fam1L=h1_re_L&m15_re_L&x.csm_long; fam1S=h1_re_S&m15_re_S&x.csm_short
    fam2L=h1_csm_L&m15_csm_L&x.re_long; fam2S=h1_csm_S&m15_csm_S&x.re_short
    fam3L=h1_re_L&m15_csm_L&x.re_long; fam3S=h1_re_S&m15_csm_S&x.re_short
    long=(fam1L|fam2L|fam3L)&x.h4_major_long.astype(bool)
    short=(fam1S|fam2S|fam3S)&x.h4_major_short.astype(bool)
    fam=np.select([fam1L|fam1S,fam2L|fam2S,fam3L|fam3S],['RRR_CSM','CSM_CSM_RE','H1_RE_M15_CSM_M5_RE'],default='')
    return long.to_numpy(bool),short.to_numpy(bool),fam

def replay(x,p):
    L,S,F=signals(x,p)
    o=x.open.to_numpy(float); h=x.high.to_numpy(float); l=x.low.to_numpy(float); c=x.close.to_numpy(float); a=x.atr.to_numpy(float)
    revL=(x.csm_short|x.csak_short).to_numpy(bool); revS=(x.csm_long|x.csak_long).to_numpy(bool); idx=x.index
    rows=[]; pos=0; entry=stop=risk=np.nan; fam=''; et=None; tp1_done=False; last_entry_i=-10**9; day_count=0; curday=None; pending=None
    for i,ts in enumerate(idx):
        d=ts.date()
        if d!=curday: curday=d; day_count=0
        if pos==0 and pending is not None:
            side,pfam=pending; pending=None; ent=o[i]
            struct=(np.nanmin(l[max(0,i-6):i+1])-p.stop_buffer_atr*a[i]) if side==1 else (np.nanmax(h[max(0,i-6):i+1])+p.stop_buffer_atr*a[i])
            rr=(ent-struct) if side==1 else (struct-ent); rat=rr/a[i] if a[i]>0 else np.nan
            if p.min_risk_atr<=rat<=p.max_risk_atr and rr>0:
                pos=side; entry=ent; stop=struct; risk=rr; fam=pfam; et=ts; tp1_done=False; last_entry_i=i; day_count+=1
        if pos!=0:
            hitstop=(l[i]<=stop) if pos==1 else (h[i]>=stop)
            tp1=entry+pos*p.tp1_r*risk; tp2=entry+pos*p.tp2_r*risk
            hittp2=(h[i]>=tp2) if pos==1 else (l[i]<=tp2)
            hittp1=(h[i]>=tp1) if pos==1 else (l[i]<=tp1)
            if hitstop:
                rs=(stop-entry)/risk if pos==1 else (entry-stop)/risk
                r=(p.tp1_fraction*p.tp1_r+(1-p.tp1_fraction)*rs) if tp1_done else rs
                rows.append((et,ts,pos,fam,r-p.cost_usd/risk,'STOP',risk)); pos=0; continue
            if hittp2:
                r=p.tp1_fraction*p.tp1_r+(1-p.tp1_fraction)*p.tp2_r
                rows.append((et,ts,pos,fam,r-p.cost_usd/risk,'TP2',risk)); pos=0; continue
            if (not tp1_done) and hittp1: tp1_done=True
            reverse=revL[i] if pos==1 else revS[i]
            if reverse:
                rr=(c[i]-entry)/risk if pos==1 else (entry-c[i])/risk
                r=(p.tp1_fraction*p.tp1_r+(1-p.tp1_fraction)*rr) if tp1_done else rr
                rows.append((et,ts,pos,fam,r-p.cost_usd/risk,'REVERSE',risk)); pos=0; continue
            trigger=entry+pos*p.be_trigger_r*risk
            reached=(h[i]>=trigger) if pos==1 else (l[i]<=trigger)
            if reached:
                new=entry+pos*p.be_lock_r*risk
                stop=max(stop,new) if pos==1 else min(stop,new)
            continue
        if day_count>=p.max_trades_per_day or i-last_entry_i<p.cooldown_bars or not (L[i] or S[i]): continue
        side=1 if L[i] and not S[i] else -1 if S[i] and not L[i] else (1 if c[i]>=o[i] else -1); pfam=F[i]
        if p.next_open_entry: pending=(side,pfam); continue
        ent=c[i]
        struct=(np.nanmin(l[max(0,i-6):i+1])-p.stop_buffer_atr*a[i]) if side==1 else (np.nanmax(h[max(0,i-6):i+1])+p.stop_buffer_atr*a[i])
        rr=(ent-struct) if side==1 else (struct-ent); rat=rr/a[i] if a[i]>0 else np.nan
        if not (p.min_risk_atr<=rat<=p.max_risk_atr and rr>0): continue
        pos=side; entry=ent; stop=struct; risk=rr; fam=pfam; et=ts; tp1_done=False; last_entry_i=i; day_count+=1
    return pd.DataFrame(rows,columns=['entry_time','exit_time','side','family','r','exit_reason','risk_usd'])

def stats(t):
    if t.empty: return dict(trades=0,positive_rate=0,avg_r=0,pf=0,net_r=0,max_dd_r=0,trades_month=0)
    r=t.r.to_numpy(float); gains=r[r>0].sum(); losses=-r[r<0].sum(); eq=np.cumsum(r); peak=np.maximum.accumulate(np.r_[0,eq]); dd=peak[1:]-eq
    months=max(1,(t.entry_time.max().to_period('M')-t.entry_time.min().to_period('M')).n+1)
    return dict(trades=len(t),positive_rate=float((r>0).mean()*100),avg_r=float(r.mean()),pf=float(gains/losses if losses else np.inf),net_r=float(r.sum()),max_dd_r=float(dd.max(initial=0)),trades_month=float(len(t)/months))

def money_by_year(t,risk_pct=.05):
    rows=[]
    for y,g in t.groupby(t.entry_time.dt.year):
        eq=100.; peak=100.; maxdd=0.
        for r in g.sort_values('entry_time').r:
            eq*=1+risk_pct*float(r); peak=max(peak,eq); maxdd=max(maxdd,(peak-eq)/peak*100)
        st=stats(g)
        rows.append(dict(year=int(y),trades=len(g),positive_rate=st['positive_rate'],avg_r=st['avg_r'],pf=st['pf'],max_dd_pct=maxdd,end_rm=eq))
    return pd.DataFrame(rows)

def run(path,p=Params(),start=None,end=None):
    feat=add_context(normalize(path))
    if start: feat=feat[feat.index>=pd.Timestamp(start,tz='UTC')]
    if end: feat=feat[feat.index<pd.Timestamp(end,tz='UTC')]
    t=replay(feat,p)
    if not t.empty:
        t['entry_time']=pd.to_datetime(t.entry_time,utc=True); t['exit_time']=pd.to_datetime(t.exit_time,utc=True)
    return feat,t,stats(t),money_by_year(t)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('data'); ap.add_argument('--start'); ap.add_argument('--end'); ap.add_argument('--cost',type=float,default=0); ap.add_argument('--next-open',action='store_true')
    args=ap.parse_args(); p=Params(cost_usd=args.cost,next_open_entry=args.next_open)
    f,t,s,y=run(args.data,p,args.start,args.end)
    print(json.dumps({'data':args.data,'start':str(f.index.min()),'end':str(f.index.max()),'params':asdict(p),'stats':s},indent=2,default=str)); print(y.to_string(index=False))
if __name__=='__main__': main()
