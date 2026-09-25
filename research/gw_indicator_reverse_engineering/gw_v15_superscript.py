import pandas as pd, numpy as np
from numba import njit

CSV='/mnt/data/xau2024_2026.csv'
m1=pd.read_csv(CSV,parse_dates=['time_utc']).set_index('time_utc').sort_index()

def rs(rule):
    return m1.resample(rule,label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),tick_volume=('tick_volume','sum')).dropna()

def rma(s,n): return s.ewm(alpha=1/n,adjust=False).mean()
def ema(s,n): return s.ewm(span=n,adjust=False).mean()

def gd(s,n,a=.7):
    e1=ema(s,n);e2=ema(e1,n);return e1*(1+a)-e2*a

def t3(s,n,a=.7): return gd(gd(gd(s,n,a),n,a),n,a)

def tsi(src, short=5, long=25):
    d=src.diff(); num=ema(ema(d,short),long); den=ema(ema(d.abs(),short),long)
    return 100*num/den.replace(0,np.nan)

def ha_open_close(d):
    hc=(d.open+d.high+d.low+d.close)/4
    ho=np.empty(len(d),float)
    if len(d): ho[0]=(d.open.iloc[0]+d.close.iloc[0])/2
    for i in range(1,len(d)): ho[i]=(ho[i-1]+hc.iloc[i-1])/2
    return pd.Series(ho,index=d.index),hc

def psar(d, start=0.02, inc=0.02, maxaf=0.2):
    h=d.high.to_numpy(float); l=d.low.to_numpy(float); n=len(d)
    sar=np.full(n,np.nan); bull=np.ones(n,bool)
    if n<2:return pd.Series(sar,index=d.index),pd.Series(bull,index=d.index)
    bull[1]=d.close.iloc[1]>=d.close.iloc[0]
    ep=h[0] if bull[1] else l[0]; af=start; sar[0]=l[0] if bull[1] else h[0]; sar[1]=sar[0]
    for i in range(2,n):
        prev_bull=bull[i-1]; s=sar[i-1]+af*(ep-sar[i-1])
        if prev_bull:
            s=min(s,l[i-1],l[i-2])
            if l[i] < s:
                bull[i]=False; s=ep; ep=l[i]; af=start
            else:
                bull[i]=True
                if h[i]>ep: ep=h[i]; af=min(maxaf,af+inc)
        else:
            s=max(s,h[i-1],h[i-2])
            if h[i] > s:
                bull[i]=True; s=ep; ep=h[i]; af=start
            else:
                bull[i]=False
                if l[i]<ep: ep=l[i]; af=min(maxaf,af+inc)
        sar[i]=s
    return pd.Series(sar,index=d.index),pd.Series(bull,index=d.index)

def feat(d):
    z=d[['open','high','low','close']].copy()
    basis=d.close.rolling(20).mean(); sd=d.close.rolling(20).std(ddof=0)
    z['bbB']=d.close>basis;z['bbS']=d.close<basis
    z['bbRetB']=(d.low<=basis)&(d.close>basis);z['bbRetS']=(d.high>=basis)&(d.close<basis)
    z['bbXB']=z.bbB&~z.bbB.shift(1).fillna(False);z['bbXS']=z.bbS&~z.bbS.shift(1).fillna(False)
    fast=t3(d.close,6,.7);slow=t3(d.close,8,.7)
    z['bjB']=(d.close>slow)&(fast>=slow);z['bjS']=(d.close<slow)&(fast<=slow)
    z['bjYellowB']=(d.close>slow)&(fast<slow);z['bjYellowS']=(d.close<slow)&(fast>slow)
    z['bjXB']=z.bjB&~z.bjB.shift(1).fillna(False);z['bjXS']=z.bjS&~z.bjS.shift(1).fillna(False)
    tv=tsi(d.close,5,25); tsl=ema(tv,14); rsi_delta=d.close.diff(); up=rma(rsi_delta.clip(lower=0),14);dn=rma((-rsi_delta.clip(upper=0)),14);rsi=100-100/(1+up/dn.replace(0,np.nan))
    z['tsiB']=tv>tsl;z['tsiS']=tv<tsl;z['tsiSigUp']=tsl>tsl.shift(1);z['tsiSigDn']=tsl<tsl.shift(1)
    z['trmB']=(tv>tsl)&(rsi>50);z['trmS']=(tv<tsl)&(rsi<50)
    z['curlB']=(tv<tsl)&(tv>tv.shift(1));z['curlS']=(tv>tsl)&(tv<tv.shift(1))
    ho,hc=ha_open_close(d);e5=ema(ho,5);e9=ema(ho,9);e21=ema(ho,21)
    z['hemaB']=(d.close>e5)&(e5>e9)&(e9>e21);z['hemaS']=(d.close<e5)&(e5<e9)&(e9<e21)
    sar,pbull=psar(d);z['psarB']=pbull&(d.close>sar);z['psarS']=(~pbull)&(d.close<sar)
    z['bull']=d.close>d.open;z['bear']=d.close<d.open
    return z

def recent(s,k):
    out=s.copy()
    for j in range(1,k): out|=s.shift(j).fillna(False)
    return out

@njit
def sim(hi,lo,op,st,sd):
    n=len(st);out=np.zeros(n,np.int8);ex=np.zeros(n,np.int64);N=len(hi)
    for q in range(n):
        i=st[q];e=op[i];sl=e-4 if sd[q]>0 else e+4;tp=e+12 if sd[q]>0 else e-12
        for j in range(i,N):
            if sd[q]>0:
                if lo[j]<=sl:out[q]=-1;ex[q]=j;break
                if hi[j]>=tp:out[q]=1;ex[q]=j;break
            else:
                if hi[j]>=sl:out[q]=-1;ex[q]=j;break
                if lo[j]<=tp:out[q]=1;ex[q]=j;break
    return out,ex

hi=m1.high.to_numpy();lo=m1.low.to_numpy();op=m1.open.to_numpy();ns=m1.index.view('int64')
F={tf:feat(rs(tf)) for tf in ['3min','5min','15min','1h']}
for tf,mins in [('15min',15),('1h',60)]: F[tf].index=F[tf].index+pd.Timedelta(minutes=mins)
rows=[]
for tf,bm in [('3min',3),('5min',5)]:
    d=F[tf].copy(); end=d.index+pd.Timedelta(minutes=bm)
    a15=F['15min'].reindex(end,method='ffill');a15.index=d.index
    ah1=F['1h'].reindex(end,method='ffill');ah1.index=d.index
    pos=np.searchsorted(ns,end.view('int64'),'left');valid=pos<len(m1);ets=m1.index[np.minimum(pos,len(m1)-1)]
    loc=ets.tz_convert('Asia/Kuala_Lumpur');mins=loc.hour*60+loc.minute
    timing=((mins>=530)&(mins<=570))|((mins>=630)&(mins<=675))|((mins>=810)&(mins<=870))
    base_opts={
      'bj':(d.bjB,d.bjS),
      'bj_bb':(d.bjB&d.bbB,d.bjS&d.bbS),
      'bj_bb_trm':(d.bjB&d.bbB&d.trmB,d.bjS&d.bbS&d.trmS),
      'bj_bb_psar':(d.bjB&d.bbB&d.psarB,d.bjS&d.bbS&d.psarS),
      'bj_bb_hema':(d.bjB&d.bbB&d.hemaB,d.bjS&d.bbS&d.hemaS),
      'bj_all':(d.bjB&d.bbB&d.trmB&d.psarB&d.hemaB,d.bjS&d.bbS&d.trmS&d.psarS&d.hemaS),
    }
    mtf_opts={
      'none':(pd.Series(True,index=d.index),pd.Series(True,index=d.index)),
      'M15_bj':(a15.bjB,a15.bjS),
      'M15_bjbb':(a15.bjB&a15.bbB,a15.bjS&a15.bbS),
      'M15_trm':(a15.trmB,a15.trmS),
      'M15H1_bj':(a15.bjB&ah1.bjB,a15.bjS&ah1.bjS),
      'M15H1_bjtrm':(a15.bjB&a15.trmB&ah1.bjB&ah1.trmB,a15.bjS&a15.trmS&ah1.bjS&ah1.trmS),
      'M15H1_all':(a15.bjB&a15.bbB&a15.trmB&a15.psarB&ah1.bjB&ah1.bbB&ah1.trmB&ah1.psarB,
                    a15.bjS&a15.bbS&a15.trmS&a15.psarS&ah1.bjS&ah1.bbS&ah1.trmS&ah1.psarS),
    }
    trig_opts={
      'state':(pd.Series(True,index=d.index),pd.Series(True,index=d.index)),
      'bjx2':(recent(d.bjXB,2),recent(d.bjXS,2)),
      'bbx2':(recent(d.bbXB,2),recent(d.bbXS,2)),
      'bbret':(d.bbRetB,d.bbRetS),
      'curl':(d.curlB,d.curlS),
      'yellow_to_confirm':(d.bjB&d.bjYellowB.shift(1).fillna(False),d.bjS&d.bjYellowS.shift(1).fillna(False)),
    }
    for bn,(B0,S0) in base_opts.items():
      for mn,(MB,MS) in mtf_opts.items():
       for tn,(TB,TS) in trig_opts.items():
        for candle in [0,1]:
         B=B0&MB&TB;S=S0&MS&TS
         if candle:B&=d.bull;S&=d.bear
         for use_time in [0,1]:
          tm=timing if use_time else np.ones(len(d),bool)
          ids=np.flatnonzero((B|S).to_numpy()&valid&tm)
          if len(ids)<20: continue
          st=pos[ids].astype(np.int64);sd=np.where(B.to_numpy()[ids],1,-1).astype(np.int8)
          oo,ex=sim(hi,lo,op,st,sd);keep=[];busy=-1
          for q in range(len(st)):
            if st[q]>busy and oo[q]!=0:keep.append(q);busy=ex[q]
          if len(keep)<10:continue
          kk=np.asarray(keep);tt=m1.index[st[kk]];out=oo[kk]
          for yr in [2024,2025,2026]:
            y=np.array([x.year==yr for x in tt]);n=int(y.sum())
            if not n:continue
            w=int((out[y]==1).sum());months=12 if yr<2026 else 9
            cnt=pd.Series(1,index=tt[y]).groupby(tt[y].month).sum().reindex(range(1,months+1),fill_value=0)
            rows.append(dict(tf=tf,base=bn,mtf=mn,trig=tn,candle=candle,timing=use_time,year=yr,trades=n,wins=w,wr=w/n,netR=3*w-(n-w),min_month=int(cnt.min())))

r=pd.DataFrame(rows);r.to_csv('/mnt/data/gw_v15_superscript_summary.csv',index=False)
keys=['tf','base','mtf','trig','candle','timing'];rank=[]
for key,g in r.groupby(keys):
    if set(g.year)=={2024,2025,2026}:
      q={int(x.year):x for _,x in g.iterrows()};row=dict(zip(keys,key))
      for y in [2024,2025,2026]:row|={f'wr{str(y)[2:]}':q[y].wr,f'tr{str(y)[2:]}':int(q[y].trades),f'net{str(y)[2:]}':int(q[y].netR),f'min{str(y)[2:]}':int(q[y].min_month)}
      row['worst_wr']=min(row['wr24'],row['wr25'],row['wr26']);row['avg_wr']=np.mean([row['wr24'],row['wr25'],row['wr26']]);row['freqok']=row['min24']>=8 and row['min25']>=8 and row['min26']>=8;rank.append(row)
o=pd.DataFrame(rank);o=o.sort_values(['freqok','worst_wr','avg_wr'],ascending=False);o.to_csv('/mnt/data/gw_v15_superscript_ranked.csv',index=False)
print(o[o.freqok].head(30).to_string(index=False))
