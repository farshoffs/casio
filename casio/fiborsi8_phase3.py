from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd

from .fiborsi8_backtest import (
    START_CAPITAL, RISK_FRACTION, YEAR_START, YEAR_END,
    load_m5, resample_ohlc, rsi_wilder, summarize_variant,
)


@dataclass(frozen=True)
class V:
    name: str
    signal_tf: str
    signal_min: int
    htf_tf: str
    htf_min: int
    buy_level: float
    sell_level: float
    htf_buy_min: float
    htf_sell_max: float


VARIANTS = (
    V("M5_M15_20_80_HTF30_70", "5min", 5, "15min", 15, 20, 80, 30, 70),
    V("M5_M15_20_80_HTF35_65", "5min", 5, "15min", 15, 20, 80, 35, 65),
    V("M5_M15_20_80_HTF40_60", "5min", 5, "15min", 15, 20, 80, 40, 60),
    V("M5_M15_22_78_HTF30_70", "5min", 5, "15min", 15, 22, 78, 30, 70),
    V("M5_M15_22_78_HTF35_65", "5min", 5, "15min", 15, 22, 78, 35, 65),
    V("M15_M30_20_80_HTF30_70", "15min", 15, "30min", 30, 20, 80, 30, 70),
    V("M15_M30_20_80_HTF35_65", "15min", 15, "30min", 30, 20, 80, 35, 65),
    V("M30_H1_20_80_HTF30_70", "30min", 30, "1h", 60, 20, 80, 30, 70),
)


def frame(m5: pd.DataFrame, rule: str) -> pd.DataFrame:
    if rule == "5min":
        x = m5[["open","high","low","close"]].copy()
    else:
        x = resample_ohlc(m5, rule)
    x["rsi8"] = rsi_wilder(x["close"], 8)
    return x


def signals_for(m5: pd.DataFrame, v: V) -> pd.DataFrame:
    s = frame(m5, v.signal_tf)
    h = frame(m5, v.htf_tf)

    h_avail = h["rsi8"].copy()
    h_avail.index = h_avail.index + pd.Timedelta(minutes=v.htf_min)
    sig_close = s.index + pd.Timedelta(minutes=v.signal_min)
    htf = h_avail.reindex(sig_close, method="ffill")
    htf.index = s.index
    s["htf_rsi8"] = htf

    prev = s["rsi8"].shift(1)
    buy = (
        (prev > v.buy_level) & (s["rsi8"] <= v.buy_level)
        & (s["close"] < s["open"])
        & (s["htf_rsi8"] >= v.htf_buy_min)
    )
    sell = (
        (prev < v.sell_level) & (s["rsi8"] >= v.sell_level)
        & (s["close"] > s["open"])
        & (s["htf_rsi8"] <= v.htf_sell_max)
    )

    rows=[]
    for t in s.index[buy|sell]:
        d = 1 if bool(buy.loc[t]) else -1
        r=s.loc[t]
        rows.append({
            "signal_time":t,
            "signal_close_time":t+pd.Timedelta(minutes=v.signal_min),
            "direction":d,
            "high":float(r.high),"low":float(r.low),
            "rsi8":float(r.rsi8),"htf_rsi8":float(r.htf_rsi8),
        })
    return pd.DataFrame(rows)


def replay(m5: pd.DataFrame, sig: pd.DataFrame, v: V) -> pd.DataFrame:
    if sig.empty: return pd.DataFrame()
    idx=m5.index
    rows=[]; busy=None
    for s in sig.itertuples(index=False):
        st=pd.Timestamp(s.signal_time)
        if st<YEAR_START or st>=YEAR_END: continue
        pos=idx.searchsorted(pd.Timestamp(s.signal_close_time), side="left")
        if pos>=len(idx): continue
        et=idx[pos]
        if et>=YEAR_END: continue
        if busy is not None and et<=busy: continue
        entry=float(m5.iloc[pos].open); d=int(s.direction)
        stop=float(s.low if d==1 else s.high)
        risk=abs(entry-stop)
        if risk<=0 or (d==1 and entry<=stop) or (d==-1 and entry>=stop): continue
        target=entry+d*3.0*risk
        ep=None; xt=None; reason=None
        for j in range(pos,len(idx)):
            t=idx[j]
            if t>=YEAR_END: break
            lo=float(m5.iloc[j].low); hi=float(m5.iloc[j].high)
            hs=(lo<=stop) if d==1 else (hi>=stop)
            ht=(hi>=target) if d==1 else (lo<=target)
            if hs:
                ep=stop; xt=t+pd.Timedelta(minutes=5); reason="SL_same_bar" if ht else "SL"; break
            if ht:
                ep=target; xt=t+pd.Timedelta(minutes=5); reason="TP"; break
        if ep is None:
            rows.append({
                "variant":v.name,"signal_time":st,"entry_time":et,"exit_time":pd.NaT,
                "direction":"BUY" if d==1 else "SELL","signal_tf":v.signal_tf,"htf_tf":v.htf_tf,
                "rsi8":float(s.rsi8),"htf_rsi8":float(s.htf_rsi8),"entry":entry,"stop":stop,
                "target":target,"risk_distance":risk,"exit_price":np.nan,"r_multiple":np.nan,
                "result":"OPEN","exit_reason":"unresolved",
            }); busy=idx[-1]; break
        r=(ep-entry)/risk if d==1 else (entry-ep)/risk
        rows.append({
            "variant":v.name,"signal_time":st,"entry_time":et,"exit_time":xt,
            "direction":"BUY" if d==1 else "SELL","signal_tf":v.signal_tf,"htf_tf":v.htf_tf,
            "rsi8":float(s.rsi8),"htf_rsi8":float(s.htf_rsi8),"entry":entry,"stop":stop,
            "target":target,"risk_distance":risk,"exit_price":ep,"r_multiple":float(r),
            "result":"WIN" if r>0 else "LOSS","exit_reason":reason,
        }); busy=xt
    return pd.DataFrame(rows)


def run(data_path, output_dir):
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    m5=load_m5(data_path); data_end=m5.index.max()
    ovs=[]; mons=[]; ats=[]
    for v in VARIANTS:
        sig=signals_for(m5,v); tr=replay(m5,sig,v)
        if tr.empty:
            tr=pd.DataFrame(columns=["variant","signal_time","entry_time","exit_time","direction","r_multiple","result"])
        ov,mo=summarize_variant(tr,data_end)
        ovs.append({"variant":v.name,"signal_tf":v.signal_tf,"htf_tf":v.htf_tf,
                    "buy_level":v.buy_level,"sell_level":v.sell_level,
                    "htf_buy_min":v.htf_buy_min,"htf_sell_max":v.htf_sell_max,**ov})
        if not mo.empty:
            mo.insert(0,"variant",v.name); mons.append(mo)
        ats.append(tr)
    od=pd.DataFrame(ovs)
    md=pd.concat(mons,ignore_index=True) if mons else pd.DataFrame()
    td=pd.concat(ats,ignore_index=True) if ats else pd.DataFrame()
    od["meets_avg8"]=od.avg_trades_per_month>=8
    od["meets_min8"]=od.min_trades_month>=8
    od["positive_edge"]=(od.expectancy_r>0)&(od.profit_factor>1)
    ranked=od.sort_values(["positive_edge","meets_min8","meets_avg8","expectancy_r","max_drawdown_pct"],
                          ascending=[False,False,False,False,True])
    od.to_csv(out/"overall.csv",index=False); md.to_csv(out/"monthly.csv",index=False)
    td.to_csv(out/"trades.csv",index=False); ranked.to_csv(out/"ranked.csv",index=False)
    lines=[
        "# FiboRSI8 Phase 3 — MTF frequency search","",
        f"Coverage: {m5.index.min().isoformat()} -> {data_end.isoformat()}",
        "2026 trades only; XAUUSD Dukascopy BID M5.",
        "RM100 start; 5% current-equity risk; fixed 3R; signal-wick SL; one position at a time.",
        "Same-M5 SL+TP = SL first. Costs not modeled.","",
        "| Variant | Trades | Avg/mo | Min/mo | W | SL | WR | Exp R | PF | DD | W/L streak | End RM | Return |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in ranked.itertuples(index=False):
        pf="∞" if math.isinf(float(r.profit_factor)) else f"{r.profit_factor:.2f}"
        lines.append(f"| {r.variant} | {r.trades} | {r.avg_trades_per_month:.2f} | {r.min_trades_month} | {r.wins} | {r.losses} | {r.win_rate_pct:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.max_drawdown_pct:.2f}% | {r.max_win_streak}/{r.max_loss_streak} | RM{r.end_balance_rm:.2f} | {r.return_pct:+.2f}% |")
    for variant in ranked.variant:
        lines += ["",f"## {variant}",""]
        g=md[md.variant==variant] if not md.empty else pd.DataFrame()
        lines += ["| Month | Trades | W | SL | WR | Net R | W/L | End RM |","|---|---:|---:|---:|---:|---:|---:|---:|"]
        for m in g.itertuples(index=False):
            lines.append(f"| {m.month} | {m.trades} | {m.wins} | {m.sl} | {m.win_rate_pct:.2f}% | {m.net_r:+.1f}R | {m.max_win_streak}/{m.max_loss_streak} | RM{m.end_balance_rm:.2f} |")
    report="\n".join(lines)+"\n"; (out/"REPORT.md").write_text(report)
    summary={"coverage":{"start":m5.index.min().isoformat(),"end":data_end.isoformat()},"variants":ranked.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")}
    (out/"summary.json").write_text(json.dumps(summary,indent=2))
    print(report); return summary


def main():
    p=argparse.ArgumentParser(); p.add_argument("--data",default="data/xauusd_m5_dukascopy_research.csv")
    p.add_argument("--output",default="reports/fiborsi8-phase3-2026"); a=p.parse_args(); run(a.data,a.output)
if __name__=="__main__": main()
