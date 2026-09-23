from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import DEV_END, atr, di_adx, resample, align_completed, rsi, replay, metrics, month_stats, yearly


@dataclass(frozen=True)
class Card:
    name: str
    family: str
    bias: str
    session: str
    adx_min: float = 18.0
    wick: float = 1.5
    lookback: int = 24
    cooldown: int = 3


def prep(m5):
    f=m5[["open","high","low","close","volume"]].copy()
    f["atr14"]=atr(f,14)
    pdi,mdi,adx=di_adx(f,14); f["pdi"],f["mdi"],f["adx"]=pdi,mdi,adx
    f["rsi8"]=rsi(f.close,8); f["rsi2"]=rsi(f.close,2)
    f["ema8"]=f.close.ewm(span=8,adjust=False).mean()
    f["ema20"]=f.close.ewm(span=20,adjust=False).mean()
    f["ema50"]=f.close.ewm(span=50,adjust=False).mean()
    f["body"]=(f.close-f.open).abs()
    f["body_atr"]=f.body/f.atr14.replace(0,np.nan)
    f["uw"]=f.high-f[["open","close"]].max(axis=1)
    f["lw"]=f[["open","close"]].min(axis=1)-f.low
    f["uwb"]=f.uw/f.body.replace(0,np.nan); f["lwb"]=f.lw/f.body.replace(0,np.nan)
    f["vol_med20"]=f.volume.rolling(20,min_periods=10).median()
    f["vol_ratio"]=f.volume/f.vol_med20.replace(0,np.nan)
    f["macd"]=f.close.ewm(span=12,adjust=False).mean()-f.close.ewm(span=26,adjust=False).mean()
    f["macds"]=f.macd.ewm(span=9,adjust=False).mean()
    f["mach"]=f.macd-f.macds
    ll14=f.low.rolling(14).min(); hh14=f.high.rolling(14).max()
    f["stoch"]=100*(f.close-ll14)/(hh14-ll14).replace(0,np.nan)

    for lb in [12,24,36,48,72]:
        f[f"ph{lb}"]=f.high.shift(1).rolling(lb).max()
        f[f"pl{lb}"]=f.low.shift(1).rolling(lb).min()

    f["bull_engulf"]=(f.close>f.open)&(f.close.shift(1)<f.open.shift(1))&(f.open<=f.close.shift(1))&(f.close>=f.open.shift(1))
    f["bear_engulf"]=(f.close<f.open)&(f.close.shift(1)>f.open.shift(1))&(f.open>=f.close.shift(1))&(f.close<=f.open.shift(1))

    # Anchored daily VWAP from tick volume.
    day=f.index.floor("D")
    f["vwap"]=(f.close*f.volume).groupby(day).cumsum()/f.volume.groupby(day).cumsum().replace(0,np.nan)
    f["day"]=day
    mins=f.index.hour*60+f.index.minute; f["mins"]=mins

    # Asia and NY opening range.
    asia=(mins>=0)&(mins<6*60)
    nyor=(mins>=12*60+30)&(mins<13*60+30)
    ast=f.loc[asia].groupby("day").agg(asia_h=("high","max"),asia_l=("low","min"))
    nst=f.loc[nyor].groupby("day").agg(ny_h=("high","max"),ny_l=("low","min"))
    f["asia_h"]=f.day.map(ast.asia_h); f["asia_l"]=f.day.map(ast.asia_l)
    f["ny_h"]=f.day.map(nst.ny_h); f["ny_l"]=f.day.map(nst.ny_l)

    # Completed H1/H4/D1 bias.
    h1=resample(m5,"1h"); h4=resample(m5,"4h"); d1=resample(m5,"1D")
    for x in (h1,h4,d1):
        x["ema20"]=x.close.ewm(span=20,adjust=False).mean()
        x["ema50"]=x.close.ewm(span=50,adjust=False).mean()
        x["ema100"]=x.close.ewm(span=100,adjust=False).mean()
        x["s20"]=x.ema20.diff(3); x["s50"]=x.ema50.diff(3)
    ct=f.index+pd.Timedelta(minutes=5)
    for p,x,period in [("h1",h1,pd.Timedelta(hours=1)),("h4",h4,pd.Timedelta(hours=4)),("d1",d1,pd.Timedelta(days=1))]:
        for col in ["ema20","ema50","ema100","s20","s50"]:
            f[f"{p}_{col}"]=align_completed(x[col],ct,period).to_numpy()
    for p in ["h1","h4","d1"]:
        f[f"{p}_up"]=(f[f"{p}_ema20"]>f[f"{p}_ema50"])&(f[f"{p}_s20"]>0)
        f[f"{p}_dn"]=(f[f"{p}_ema20"]<f[f"{p}_ema50"])&(f[f"{p}_s20"]<0)
    f["h4d1_up"]=f.h4_up&f.d1_up; f["h4d1_dn"]=f.h4_dn&f.d1_dn
    f["h1h4_up"]=f.h1_up&f.h4_up; f["h1h4_dn"]=f.h1_dn&f.h4_dn
    f["triple_up"]=f.h1_up&f.h4_up&f.d1_up; f["triple_dn"]=f.h1_dn&f.h4_dn&f.d1_dn
    return f


def bias(f,b):
    if b=="h4d1": return f.h4d1_up.fillna(False),f.h4d1_dn.fillna(False)
    if b=="h1h4": return f.h1h4_up.fillna(False),f.h1h4_dn.fillna(False)
    if b=="triple": return f.triple_up.fillna(False),f.triple_dn.fillna(False)
    raise ValueError(b)


def sess(f,s):
    m=f.mins
    if s=="ALL": return pd.Series(True,index=f.index)
    if s=="LONDON": return pd.Series((m>=7*60)&(m<11*60),index=f.index)
    if s=="NY": return pd.Series((m>=12*60+30)&(m<16*60+30),index=f.index)
    if s=="PRIMARY": return pd.Series(((m>=7*60)&(m<11*60))|((m>=12*60+30)&(m<16*60+30)),index=f.index)
    raise ValueError(s)


def masks(f,c):
    up,dn=bias(f,c.bias); ss=sess(f,c.session)
    ph=f[f"ph{c.lookback}"]; pl=f[f"pl{c.lookback}"]
    if c.family=="ema20_pin":
        lo=up&ss&(f.low<=f.ema20)&(f.close>f.ema20)&(f.close>f.open)&(f.lwb>=c.wick)&(f.pdi>f.mdi)&(f.adx>=c.adx_min)
        sh=dn&ss&(f.high>=f.ema20)&(f.close<f.ema20)&(f.close<f.open)&(f.uwb>=c.wick)&(f.mdi>f.pdi)&(f.adx>=c.adx_min)
    elif c.family=="ema50_pin":
        lo=up&ss&(f.low<=f.ema50)&(f.close>f.ema50)&(f.close>f.open)&(f.lwb>=c.wick)&(f.pdi>f.mdi)
        sh=dn&ss&(f.high>=f.ema50)&(f.close<f.ema50)&(f.close<f.open)&(f.uwb>=c.wick)&(f.mdi>f.pdi)
    elif c.family=="ema20_engulf":
        lo=up&ss&f.bull_engulf&(f.low<=f.ema20)&(f.close>f.ema20)&(f.adx>=c.adx_min)
        sh=dn&ss&f.bear_engulf&(f.high>=f.ema20)&(f.close<f.ema20)&(f.adx>=c.adx_min)
    elif c.family=="vwap_reject":
        lo=up&ss&(f.low<=f.vwap)&(f.close>f.vwap)&(f.close>f.open)&(f.lwb>=c.wick)&(f.adx>=c.adx_min)
        sh=dn&ss&(f.high>=f.vwap)&(f.close<f.vwap)&(f.close<f.open)&(f.uwb>=c.wick)&(f.adx>=c.adx_min)
    elif c.family=="sweep":
        lo=up&ss&(f.low<pl)&(f.close>pl)&(f.close>f.open)&(f.lwb>=c.wick)
        sh=dn&ss&(f.high>ph)&(f.close<ph)&(f.close<f.open)&(f.uwb>=c.wick)
    elif c.family=="break_retest":
        pu=f.close.shift(1)>ph.shift(1); pdn=f.close.shift(1)<pl.shift(1)
        lo=up&ss&pu&(f.low<=ph.shift(1))&(f.close>ph.shift(1))&(f.close>f.open)&(f.adx>=c.adx_min)
        sh=dn&ss&pdn&(f.high>=pl.shift(1))&(f.close<pl.shift(1))&(f.close<f.open)&(f.adx>=c.adx_min)
    elif c.family=="rsi8_reclaim":
        lo=up&ss&(f.rsi8.shift(1)<=30)&(f.rsi8>35)&(f.close>f.ema20)&(f.close>f.open)&(f.adx>=c.adx_min)
        sh=dn&ss&(f.rsi8.shift(1)>=70)&(f.rsi8<65)&(f.close<f.ema20)&(f.close<f.open)&(f.adx>=c.adx_min)
    elif c.family=="stoch_reclaim":
        lo=up&ss&(f.stoch.shift(1)<=15)&(f.stoch>25)&(f.close>f.ema20)&(f.close>f.open)
        sh=dn&ss&(f.stoch.shift(1)>=85)&(f.stoch<75)&(f.close<f.ema20)&(f.close<f.open)
    elif c.family=="macd_turn":
        lo=up&ss&(f.mach.shift(1)<=0)&(f.mach>0)&(f.close>f.ema20)&(f.adx>=c.adx_min)
        sh=dn&ss&(f.mach.shift(1)>=0)&(f.mach<0)&(f.close<f.ema20)&(f.adx>=c.adx_min)
    elif c.family=="ny_retest":
        win=(f.mins>=13*60+30)&(f.mins<16*60+30)
        pu=f.close.shift(1)>f.ny_h.shift(1); pdn=f.close.shift(1)<f.ny_l.shift(1)
        lo=up&win&pu&(f.low<=f.ny_h)&(f.close>f.ny_h)&(f.close>f.open)
        sh=dn&win&pdn&(f.high>=f.ny_l)&(f.close<f.ny_l)&(f.close<f.open)
    elif c.family=="asia_retest":
        win=(f.mins>=7*60)&(f.mins<11*60)
        pu=f.close.shift(1)>f.asia_h.shift(1); pdn=f.close.shift(1)<f.asia_l.shift(1)
        lo=up&win&pu&(f.low<=f.asia_h)&(f.close>f.asia_h)&(f.close>f.open)
        sh=dn&win&pdn&(f.high>=f.asia_l)&(f.close<f.asia_l)&(f.close<f.open)
    else: raise ValueError(c.family)
    return lo.fillna(False),sh.fillna(False)


def build(f,c):
    lo,sh=masks(f,c); rows=[]; last={1:-10**9,-1:-10**9}
    for i in np.flatnonzero((lo|sh).to_numpy()):
        d=1 if bool(lo.iat[i]) else -1
        if i-last[d]<c.cooldown: continue
        row=f.iloc[i]; a=float(row.atr14)
        if not np.isfinite(a) or a<=0: continue
        stop=float(row.low-0.04*a) if d==1 else float(row.high+0.04*a)
        risk=(float(row.close)-stop) if d==1 else (stop-float(row.close))
        if risk/a<0.10 or risk/a>1.50: continue
        rows.append({"card":c.name,"signal_i":i,"signal_time":f.index[i],"signal_close_time":f.index[i]+pd.Timedelta(minutes=5),
                     "direction":d,"stop":stop,"atr14":a,"adx":float(row.adx) if np.isfinite(row.adx) else np.nan,
                     "vol_ratio":float(row.vol_ratio) if np.isfinite(row.vol_ratio) else np.nan})
        last[d]=i
    return pd.DataFrame(rows)


def cards():
    out=[]
    for b in ["h4d1","h1h4","triple"]:
      for s in ["ALL","PRIMARY","LONDON","NY"]:
        for a in [18,22,26]:
          for w in [1.5,2.2]:
            out.append(Card(f"EMA20PIN_{b}_{s}_A{a}_W{w}","ema20_pin",b,s,a,w,24,3))
            out.append(Card(f"VWAP_{b}_{s}_A{a}_W{w}","vwap_reject",b,s,a,w,24,3))
          out.append(Card(f"ENGULF_{b}_{s}_A{a}","ema20_engulf",b,s,a,1.5,24,3))
          out.append(Card(f"RSI8_{b}_{s}_A{a}","rsi8_reclaim",b,s,a,1.5,24,3))
          out.append(Card(f"MACD_{b}_{s}_A{a}","macd_turn",b,s,a,1.5,24,3))
        out.append(Card(f"STOCH_{b}_{s}","stoch_reclaim",b,s,18,1.5,24,3))
      for lb in [12,24,36,48,72]:
        for w in [1.5,2.2,3.0]:
          out.append(Card(f"SWEEP{lb}_{b}_W{w}","sweep",b,"PRIMARY",18,w,lb,4))
        for a in [18,22,26]:
          out.append(Card(f"RETEST{lb}_{b}_A{a}","break_retest",b,"PRIMARY",a,1.5,lb,4))
      out.append(Card(f"NYRETEST_{b}","ny_retest",b,"NY",18,1.5,24,12))
      out.append(Card(f"ASIARETEST_{b}","asia_retest",b,"LONDON",18,1.5,24,12))
    return out


def run(data_path,output_dir):
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path)
    m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy()
    f=prep(m5)
    rows=[]; yrs=[]; alltr=[]
    cs=cards()
    for c in cs:
        tr=replay(m5,build(f,c))
        if not tr.empty: alltr.append(tr.assign(strategy=c.name))
        ov=metrics(tr); ms=month_stats(tr); y=yearly(tr)
        rows.append({"strategy":c.name,"family":c.family,"bias":c.bias,"session":c.session,
                     "trades":ov["trades"],"wr":ov["wr"],"expectancy_r":ov["expectancy_r"],"pf":ov["pf"],
                     "dd":ov["max_dd_pct"],"end_rm":ov["end_rm"],**ms,
                     "positive_years":int((y.expectancy_r>0).sum()),"pf_years":int((y.pf>1).sum()),
                     "worst_year_exp":float(y.expectancy_r.min()),"worst_year_dd":float(y.max_dd_pct.max())})
        for rr in y.itertuples(index=False): yrs.append({"strategy":c.name,**rr._asdict()})

    rd=pd.DataFrame(rows)
    rd["strict"]=(rd.wr>=60)&(rd.dd<=25)&(rd.min_month>=8)&(rd.positive_years.eq(4))&(rd.pf_years.eq(4))
    rd["dist"]=np.maximum(0,60-rd.wr)*3+np.maximum(0,rd.dd-25)+np.maximum(0,8-rd.min_month)*5+(4-rd.positive_years)*20
    ranked=rd.sort_values(["strict","dist","positive_years","min_month","wr","expectancy_r"],ascending=[False,True,False,False,False,False])
    yd=pd.DataFrame(yrs)
    ranked.to_csv(out/"ranked.csv",index=False); yd.to_csv(out/"yearly.csv",index=False)
    if alltr: pd.concat(alltr,ignore_index=True).to_csv(out/"trades.csv",index=False)

    strict=ranked[ranked.strict]
    lines=["# Historical-First Strict M5 Precision Search","",
           "2017-2020 only; 2021+ sealed.",
           "Hard target: RR3, WR>=60%, DD<=25%, min 8 trades every month, 4/4 profitable years.",
           "M5 signal, next-M5-open entry, real signal-candle SL + 0.04ATR, same-bar stop-first, 1bp cost, RM100, 5% risk.","",
           f"Cards tested: {len(cs)}. Strict passes: {len(strict)}.","",
           "## Strict passes",""]
    if strict.empty: lines.append("No candidate met all hard constraints.")
    else:
      lines+=["| Strategy | Trades | WR | ExpR | PF | DD | Avg/mo | Min/mo | Years |","|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
      for r in strict.itertuples(index=False):
        lines.append(f"| {r.strategy} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {r.pf:.2f} | {r.dd:.2f}% | {r.avg_month:.2f} | {r.min_month} | {r.positive_years}/4 |")
    lines+=["","## Closest","",
            "| Strategy | Family | Trades | WR | ExpR | PF | DD | Avg/mo | Min/mo | Years | Dist |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in ranked.head(20).itertuples(index=False):
      lines.append(f"| {r.strategy} | {r.family} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {r.pf:.2f} | {r.dd:.2f}% | {r.avg_month:.2f} | {r.min_month} | {r.positive_years}/4 | {r.dist:.1f} |")
    for strategy in (strict.strategy.tolist() if len(strict) else ranked.head(5).strategy.tolist()):
      lines+=["",f"## {strategy}","","| Year | Trades | WR | ExpR | PF | DD | RM100 -> |","|---|---:|---:|---:|---:|---:|---:|"]
      for r in yd[yd.strategy==strategy].itertuples(index=False):
        lines.append(f"| {r.year} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {r.pf:.2f} | {r.max_dd_pct:.2f}% | RM{r.end_rm:.2f} |")
    report="\n".join(lines)+"\n"; (out/"REPORT.md").write_text(report)
    (out/"summary.json").write_text(json.dumps({"cards":len(cs),"strict_passes":int(len(strict)),
      "strict":strict.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records"),
      "closest":ranked.head(20).replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")},indent=2))
    print(report)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output",default="reports/historical-first-strict-m5"); a=p.parse_args(); run(a.data,a.output)
if __name__=="__main__": main()
