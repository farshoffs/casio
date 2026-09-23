from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import DEV_END, atr, di_adx, resample, align_completed, rsi, metrics, month_stats, yearly

START = pd.Timestamp("2017-01-01", tz="UTC")
RR = 3.0
RISK_FRAC = 0.05
COST_BPS = 1.0


@dataclass(frozen=True)
class Spec:
    name: str
    family: str
    bias: str
    window: str
    entry_mode: str
    adx_min: float
    vol_min: float
    wait_min: int
    lookback: int = 24


def add_local_session_fields(f: pd.DataFrame) -> pd.DataFrame:
    out = f.copy()
    local = out.index.tz_convert("America/New_York")
    out["ny_date"] = pd.Index(local.date)
    out["ny_min"] = local.hour * 60 + local.minute

    # All allowed windows are subsets of New York session.
    m = out.ny_min
    out["NY_FULL"] = (m >= 8*60) & (m < 17*60)
    out["NY_CORE"] = (m >= 8*60+30) & (m < 12*60+30)
    out["NY_CASH_AM"] = (m >= 9*60+30) & (m < 12*60+30)

    # Overnight / premarket / cash opening range in New York local time.
    overnight = (m >= 0) & (m < 8*60+30)
    premarket = (m >= 7*60) & (m < 9*60+30)
    orb30 = (m >= 9*60+30) & (m < 10*60)
    ib60 = (m >= 9*60+30) & (m < 10*60+30)
    ny_session = (m >= 8*60) & (m < 17*60)

    def levels(mask, hp, lp):
        st = out.loc[mask].groupby("ny_date").agg(**{hp:("high","max"), lp:("low","min")})
        out[hp] = out.ny_date.map(st[hp])
        out[lp] = out.ny_date.map(st[lp])

    levels(overnight, "on_h", "on_l")
    levels(premarket, "pm_h", "pm_l")
    levels(orb30, "or_h", "or_l")
    levels(ib60, "ib_h", "ib_l")

    nyday = out.loc[ny_session].groupby("ny_date").agg(ny_h=("high","max"), ny_l=("low","min"))
    prev = nyday.shift(1)
    out["prev_ny_h"] = out.ny_date.map(prev.ny_h)
    out["prev_ny_l"] = out.ny_date.map(prev.ny_l)

    # NY-session anchored VWAP from 08:00 ET; values outside session are irrelevant.
    pv = (out.close * out.volume).where(ny_session)
    vv = out.volume.where(ny_session)
    out["ny_vwap"] = pv.groupby(out.ny_date).cumsum() / vv.groupby(out.ny_date).cumsum().replace(0, np.nan)
    return out


def prep(m5: pd.DataFrame) -> pd.DataFrame:
    f = m5[["open","high","low","close","volume"]].copy()
    f["atr14"] = atr(f,14)
    pdi,mdi,adx = di_adx(f,14)
    f["pdi"],f["mdi"],f["adx"] = pdi,mdi,adx
    f["rsi2"] = rsi(f.close,2)
    f["rsi8"] = rsi(f.close,8)
    f["ema8"] = f.close.ewm(span=8,adjust=False).mean()
    f["ema20"] = f.close.ewm(span=20,adjust=False).mean()
    f["ema50"] = f.close.ewm(span=50,adjust=False).mean()

    f["body"]=(f.close-f.open).abs()
    f["range"]=f.high-f.low
    f["body_atr"]=f.body/f.atr14.replace(0,np.nan)
    f["body_frac"]=f.body/f.range.replace(0,np.nan)
    f["upper_wick"]=f.high-f[["open","close"]].max(axis=1)
    f["lower_wick"]=f[["open","close"]].min(axis=1)-f.low
    f["uwb"]=f.upper_wick/f.body.replace(0,np.nan)
    f["lwb"]=f.lower_wick/f.body.replace(0,np.nan)
    f["vol_med20"]=f.volume.rolling(20,min_periods=10).median()
    f["vol_ratio"]=f.volume/f.vol_med20.replace(0,np.nan)

    for lb in [12,24,36,48,72]:
        f[f"ph{lb}"]=f.high.shift(1).rolling(lb).max()
        f[f"pl{lb}"]=f.low.shift(1).rolling(lb).min()

    # Completed H1/H4/D1 state.
    h1=resample(m5,"1h"); h4=resample(m5,"4h"); d1=resample(m5,"1D")
    for x in (h1,h4,d1):
        x["atr14"]=atr(x,14)
        xp,xm,xa=di_adx(x,14)
        x["adx"]=xa
        x["ema20"]=x.close.ewm(span=20,adjust=False).mean()
        x["ema50"]=x.close.ewm(span=50,adjust=False).mean()
        x["ema100"]=x.close.ewm(span=100,adjust=False).mean()
        x["s20"]=x.ema20.diff(3)
    ct=f.index+pd.Timedelta(minutes=5)
    for p,x,period in [("h1",h1,pd.Timedelta(hours=1)),("h4",h4,pd.Timedelta(hours=4)),("d1",d1,pd.Timedelta(days=1))]:
        for col in ["adx","ema20","ema50","ema100","s20","atr14"]:
            f[f"{p}_{col}"]=align_completed(x[col],ct,period).to_numpy()
        f[f"{p}_up"]=(f[f"{p}_ema20"]>f[f"{p}_ema50"])&(f[f"{p}_s20"]>0)
        f[f"{p}_dn"]=(f[f"{p}_ema20"]<f[f"{p}_ema50"])&(f[f"{p}_s20"]<0)

    f["h4d1_up"]=f.h4_up&f.d1_up
    f["h4d1_dn"]=f.h4_dn&f.d1_dn
    f["triple_up"]=f.h1_up&f.h4_up&f.d1_up
    f["triple_dn"]=f.h1_dn&f.h4_dn&f.d1_dn

    # 3-candle FVG, mechanically defined on completed M5 candles.
    f["bull_fvg"]=f.low>f.high.shift(2)
    f["bear_fvg"]=f.high<f.low.shift(2)
    f["bull_fvg_mid"]=(f.low+f.high.shift(2))/2
    f["bear_fvg_mid"]=(f.high+f.low.shift(2))/2

    return add_local_session_fields(f)


def bias_mask(f,bias):
    if bias=="none":
        return pd.Series(True,index=f.index),pd.Series(True,index=f.index)
    if bias=="h4":
        return f.h4_up.fillna(False),f.h4_dn.fillna(False)
    if bias=="h4d1":
        return f.h4d1_up.fillna(False),f.h4d1_dn.fillna(False)
    if bias=="triple":
        return f.triple_up.fillna(False),f.triple_dn.fillna(False)
    raise ValueError(bias)


def window_mask(f,w):
    return f[w].fillna(False)


def signal_rows(f: pd.DataFrame, s: Spec) -> pd.DataFrame:
    up,dn=bias_mask(f,s.bias)
    win=window_mask(f,s.window)
    volok=(f.vol_ratio>=s.vol_min) if s.vol_min>0 else pd.Series(True,index=f.index)
    adxok=f.adx>=s.adx_min
    ph=f[f"ph{s.lookback}"]; pl=f[f"pl{s.lookback}"]

    bull_rej=(f.close>f.open)&(f.lwb>=1.2)
    bear_rej=(f.close<f.open)&(f.uwb>=1.2)
    bull_disp=(f.close>f.open)&(f.body_atr>=0.55)&(f.body_frac>=0.65)
    bear_disp=(f.close<f.open)&(f.body_atr>=0.55)&(f.body_frac>=0.65)

    fam=s.family
    if fam=="ema20_pullback":
        lo=win&up&volok&adxok&bull_rej&(f.low<=f.ema20)&(f.close>f.ema20)&(f.pdi>f.mdi)
        sh=win&dn&volok&adxok&bear_rej&(f.high>=f.ema20)&(f.close<f.ema20)&(f.mdi>f.pdi)
    elif fam=="ema50_pullback":
        lo=win&up&volok&bull_rej&(f.low<=f.ema50)&(f.close>f.ema50)
        sh=win&dn&volok&bear_rej&(f.high>=f.ema50)&(f.close<f.ema50)
    elif fam=="vwap_trend_reclaim":
        lo=win&up&volok&adxok&bull_rej&(f.low<=f.ny_vwap)&(f.close>f.ny_vwap)
        sh=win&dn&volok&adxok&bear_rej&(f.high>=f.ny_vwap)&(f.close<f.ny_vwap)
    elif fam=="vwap_fade":
        dev=(f.close-f.ny_vwap)/f.atr14.replace(0,np.nan)
        rangegate=f.h1_adx<=22
        lo=win&rangegate&volok&bull_rej&(dev<=-1.25)&(f.rsi2<=20)
        sh=win&rangegate&volok&bear_rej&(dev>=1.25)&(f.rsi2>=80)
    elif fam=="rolling_sweep":
        lo=win&volok&bull_rej&(f.low<pl)&(f.close>pl)
        sh=win&volok&bear_rej&(f.high>ph)&(f.close<ph)
    elif fam=="overnight_sweep":
        lo=win&volok&bull_rej&(f.low<f.on_l)&(f.close>f.on_l)
        sh=win&volok&bear_rej&(f.high>f.on_h)&(f.close<f.on_h)
    elif fam=="premarket_sweep":
        lo=win&volok&bull_rej&(f.low<f.pm_l)&(f.close>f.pm_l)
        sh=win&volok&bear_rej&(f.high>f.pm_h)&(f.close<f.pm_h)
    elif fam=="prev_ny_sweep":
        lo=win&volok&bull_rej&(f.low<f.prev_ny_l)&(f.close>f.prev_ny_l)
        sh=win&volok&bear_rej&(f.high>f.prev_ny_h)&(f.close<f.prev_ny_h)
    elif fam=="orb_break":
        eligible=f.ny_min>=10*60
        lo=win&eligible&up&volok&bull_disp&(f.close>f.or_h)&(f.close.shift(1)<=f.or_h.shift(1))
        sh=win&eligible&dn&volok&bear_disp&(f.close<f.or_l)&(f.close.shift(1)>=f.or_l.shift(1))
    elif fam=="ib_break":
        eligible=f.ny_min>=10*60+30
        lo=win&eligible&up&volok&bull_disp&(f.close>f.ib_h)&(f.close.shift(1)<=f.ib_h.shift(1))
        sh=win&eligible&dn&volok&bear_disp&(f.close<f.ib_l)&(f.close.shift(1)>=f.ib_l.shift(1))
    elif fam=="overnight_break":
        eligible=f.ny_min>=8*60+30
        lo=win&eligible&up&volok&bull_disp&(f.close>f.on_h)&(f.close.shift(1)<=f.on_h.shift(1))
        sh=win&eligible&dn&volok&bear_disp&(f.close<f.on_l)&(f.close.shift(1)>=f.on_l.shift(1))
    elif fam=="rsi2_trend":
        lo=win&up&volok&(f.rsi2.shift(1)<=8)&(f.rsi2>=25)&(f.close>f.ema20)&(f.close>f.open)
        sh=win&dn&volok&(f.rsi2.shift(1)>=92)&(f.rsi2<=75)&(f.close<f.ema20)&(f.close<f.open)
    elif fam=="fvg_trend":
        lo=win&up&volok&f.bull_fvg&(f.close>f.ema20)&(f.adx>=s.adx_min)
        sh=win&dn&volok&f.bear_fvg&(f.close<f.ema20)&(f.adx>=s.adx_min)
    elif fam=="displacement":
        lo=win&up&volok&adxok&bull_disp&(f.close>ph)
        sh=win&dn&volok&adxok&bear_disp&(f.close<pl)
    else:
        raise ValueError(fam)

    rows=[]
    for i in np.flatnonzero((lo.fillna(False)|sh.fillna(False)).to_numpy()):
        row=f.iloc[i]; d=1 if bool(lo.iat[i]) else -1
        a=float(row.atr14)
        if not np.isfinite(a) or a<=0: continue

        # Pending entry modes based only on the completed signal candle/known level.
        if s.entry_mode=="market":
            entry=np.nan
        elif s.entry_mode=="half":
            entry=float((row.open+row.close)/2.0)
        elif s.entry_mode=="deep705":
            entry=float(row.high-0.705*(row.high-row.low)) if d==1 else float(row.low+0.705*(row.high-row.low))
        elif s.entry_mode=="deep886":
            entry=float(row.high-0.886*(row.high-row.low)) if d==1 else float(row.low+0.886*(row.high-row.low))
        elif s.entry_mode=="fvgmid":
            if fam!="fvg_trend": continue
            entry=float(row.bull_fvg_mid) if d==1 else float(row.bear_fvg_mid)
        else:
            raise ValueError(s.entry_mode)

        # True signal-structure stop; no BE/protected SL.
        stop=float(row.low-0.04*a) if d==1 else float(row.high+0.04*a)
        rows.append({
            "signal_time":f.index[i],
            "available":f.index[i]+pd.Timedelta(minutes=5),
            "ny_date":row.ny_date,
            "direction":d,
            "entry_limit":entry,
            "stop":stop,
            "atr":a,
            "wait_min":s.wait_min,
        })
    return pd.DataFrame(rows)


def replay(m5: pd.DataFrame, ss: pd.DataFrame, name: str) -> pd.DataFrame:
    if ss.empty:return pd.DataFrame()
    idx=m5.index
    hi=m5.high.to_numpy(float); lo=m5.low.to_numpy(float); op=m5.open.to_numpy(float)
    rows=[]; busy=None; traded_dates=set()

    for s in ss.sort_values("available").itertuples(index=False):
        st=pd.Timestamp(s.signal_time)
        if st<START or st>=DEV_END: continue
        if s.ny_date in traded_dates: continue  # max one entry per NY trading day
        avail=pd.Timestamp(s.available)
        if busy is not None and avail<=busy: continue
        pos=idx.searchsorted(avail,side="left")
        if pos>=len(idx):continue

        if np.isnan(float(s.entry_limit)):
            fill=pos; entry=float(op[fill])
        else:
            expiry=avail+pd.Timedelta(minutes=int(s.wait_min))
            fill=None; entry=float(s.entry_limit)
            for j in range(pos,len(idx)):
                if idx[j]>=expiry or idx[j]>=DEV_END: break
                if lo[j]<=entry<=hi[j]:
                    fill=j;break
            if fill is None:continue

        et=idx[fill]
        d=int(s.direction); stop=float(s.stop)
        risk=(entry-stop) if d==1 else (stop-entry)
        a=float(s.atr)
        if not np.isfinite(risk) or risk<=0 or risk/a<0.08 or risk/a>2.0:continue
        target=entry+d*RR*risk

        xp=xt=reason=None
        for j in range(fill,len(idx)):
            if idx[j]>=DEV_END:break
            hs=lo[j]<=stop if d==1 else hi[j]>=stop
            ht=hi[j]>=target if d==1 else lo[j]<=target
            if hs:
                xp=stop;xt=idx[j]+pd.Timedelta(minutes=5);reason="SL_same_bar" if ht else "SL";break
            if ht:
                xp=target;xt=idx[j]+pd.Timedelta(minutes=5);reason="TP";break
        if xp is None:continue

        gross=(xp-entry)/risk if d==1 else (entry-xp)/risk
        cost=(entry*COST_BPS/10000.0)/risk
        nr=float(gross-cost)
        rows.append({
            "strategy":name,"signal_time":st,"entry_time":et,"exit_time":xt,
            "direction":"BUY" if d==1 else "SELL","entry":entry,"stop":stop,"target":target,
            "net_r":nr,"r_multiple":nr,"result":"WIN" if nr>0 else "LOSS","exit_reason":reason,
            "ny_date":str(s.ny_date),
        })
        traded_dates.add(s.ny_date)
        busy=xt
    return pd.DataFrame(rows)


def make_specs():
    out=[]
    # Technique set deliberately mixes old and new families.
    families=[
        "ema20_pullback","ema50_pullback","vwap_trend_reclaim","vwap_fade",
        "rolling_sweep","overnight_sweep","premarket_sweep","prev_ny_sweep",
        "orb_break","ib_break","overnight_break","rsi2_trend","fvg_trend","displacement"
    ]
    for fam in families:
        biases = ["none","h4","h4d1","triple"] if fam in ["vwap_fade","rolling_sweep","overnight_sweep","premarket_sweep","prev_ny_sweep"] else ["h4","h4d1","triple"]
        windows = ["NY_FULL","NY_CORE","NY_CASH_AM"]
        entries = ["market","half","deep705","deep886"]
        if fam=="fvg_trend": entries += ["fvgmid"]
        for b in biases:
            for w in windows:
                for e in entries:
                    for adx in [16,22,28]:
                        for vol in [0.0,1.15]:
                            for lb in ([12,24,48] if fam in ["rolling_sweep","displacement"] else [24]):
                                # Deep limits need time to fill, market ignores wait but harmless.
                                wait=30 if e=="market" else 45
                                name=f"NY__{fam}__{b}__{w}__{e}__A{adx}__V{vol}__L{lb}"
                                out.append(Spec(name,fam,b,w,e,adx,vol,wait,lb))
    return out


def run(data_path,output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path)
    m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy()
    f=prep(m5)
    specs=make_specs()
    rows=[];yrs=[];alltr=[]

    for s in specs:
        tr=replay(m5,signal_rows(f,s),s.name)
        if not tr.empty:alltr.append(tr)
        ov=metrics(tr);ms=month_stats(tr);y=yearly(tr)
        rows.append({
            "strategy":s.name,"family":s.family,"bias":s.bias,"window":s.window,"entry_mode":s.entry_mode,
            "adx_min":s.adx_min,"vol_min":s.vol_min,"lookback":s.lookback,
            "trades":ov["trades"],"wr":ov["wr"],"expectancy_r":ov["expectancy_r"],"pf":ov["pf"],
            "dd":ov["max_dd_pct"],"end_rm":ov["end_rm"],"return_pct":ov["return_pct"],**ms,
            "positive_years":int((y.expectancy_r>0).sum()),"pf_years":int((y.pf>1).sum()),
            "worst_year_exp":float(y.expectancy_r.min()),"worst_year_dd":float(y.max_dd_pct.max()),
        })
        for rr in y.itertuples(index=False):yrs.append({"strategy":s.name,**rr._asdict()})

    rd=pd.DataFrame(rows)
    rd["strict"]=(rd.wr>=60)&(rd.dd<=25)&(rd.min_month>=8)&(rd.positive_years.eq(4))&(rd.pf_years.eq(4))
    rd["dist"]=np.maximum(0,60-rd.wr)*3+np.maximum(0,rd.dd-25)+np.maximum(0,8-rd.min_month)*6+(4-rd.positive_years)*25
    ranked=rd.sort_values(["strict","dist","positive_years","min_month","wr","expectancy_r"],ascending=[False,True,False,False,False,False])
    yd=pd.DataFrame(yrs)
    ranked.to_csv(out/"ranked.csv",index=False);yd.to_csv(out/"yearly.csv",index=False)
    if alltr:pd.concat(alltr,ignore_index=True).to_csv(out/"trades.csv",index=False)

    strict=ranked[ranked.strict]
    lines=[
        "# New York Session Only — Strict Historical Search 2017-2020","",
        "Session clock is DST-aware America/New_York. No trade outside the selected NY-local window.",
        "Hard target: RM100 start; 5% risk; fixed RR3; WR>=60%; max DD<=25%; min 8 trades EVERY month; profitable in 2017,2018,2019,2020.",
        "Real signal-structure SL only; no BE/protected stop. M5 execution; one entry maximum per NY trading day; same-bar SL first; 1bp round-trip cost.",
        "2021+ remains sealed.","",
        f"Specs tested: {len(specs)}. Strict passes: {len(strict)}.","",
        "## Strict passes",""
    ]
    if strict.empty:
        lines.append("No strict pass.")
    else:
        lines+=["| Strategy | Trades | WR | ExpR | PF | DD | Avg/mo | Min/mo | Years | RM100 -> |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for r in strict.itertuples(index=False):
            pf="inf" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
            lines.append(f"| {r.strategy} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.dd:.2f}% | {r.avg_month:.2f} | {r.min_month} | {r.positive_years}/4 | RM{r.end_rm:.2f} |")

    lines+=["","## Closest candidates","",
            "| Strategy | Family | Trades | WR | ExpR | PF | DD | Avg/mo | Min/mo | Years | Dist |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in ranked.head(30).itertuples(index=False):
        pf="inf" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(f"| {r.strategy} | {r.family} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.dd:.2f}% | {r.avg_month:.2f} | {r.min_month} | {r.positive_years}/4 | {r.dist:.1f} |")

    detail=strict.strategy.tolist() if len(strict) else ranked.head(8).strategy.tolist()
    for strategy in detail:
        lines+=["",f"## {strategy}","","| Year | Trades | WR | ExpR | PF | DD | RM100 -> |",
                "|---|---:|---:|---:|---:|---:|---:|"]
        for r in yd[yd.strategy==strategy].itertuples(index=False):
            pf="inf" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
            lines.append(f"| {r.year} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.max_dd_pct:.2f}% | RM{r.end_rm:.2f} |")

    report="\n".join(lines)+"\n"
    (out/"REPORT.md").write_text(report,encoding="utf-8")
    (out/"summary.json").write_text(json.dumps({
        "timezone":"America/New_York",
        "constraints":{"start_rm":100,"risk_pct":5,"rr":3,"wr_min_pct":60,"dd_max_pct":25,"min_trades_month":8,"positive_years":4},
        "specs":len(specs),"strict_count":int(len(strict)),
        "strict":strict.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records"),
        "closest":ranked.head(30).replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")
    },indent=2),encoding="utf-8")
    print(report)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output",default="reports/historical-first-ny-strict")
    a=p.parse_args();run(a.data,a.output)

if __name__=="__main__":main()
