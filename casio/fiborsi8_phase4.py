from __future__ import annotations
from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd

from .fiborsi8_backtest import load_m5, summarize_variant
from .fiborsi8_phase3 import V, signals_for, replay

THRESHOLDS=[(20,80),(21,79),(22,78),(23,77),(24,76),(25,75)]
HTF_FILTERS=[(30,70),(32.5,67.5),(35,65)]

VARIANTS=[
    V(f"M15_T{b:g}_{s:g}_HTF{hb:g}_{hs:g}","15min",15,"30min",30,b,s,hb,hs)
    for b,s in THRESHOLDS for hb,hs in HTF_FILTERS
]

def full_month_stats(monthly: pd.DataFrame, data_end: pd.Timestamp) -> tuple[float,int]:
    if monthly.empty: return 0.0,0
    current_period=data_end.to_period("M")
    g=monthly[pd.PeriodIndex(monthly["month"],freq="M")<current_period]
    if g.empty: return 0.0,0
    return float(g["trades"].mean()), int(g["trades"].min())

def run(data_path,output_dir):
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    m5=load_m5(data_path); data_end=m5.index.max()
    ovs=[]; mons=[]; ats=[]
    for v in VARIANTS:
        sig=signals_for(m5,v); tr=replay(m5,sig,v)
        if tr.empty:
            tr=pd.DataFrame(columns=["variant","signal_time","entry_time","exit_time","direction","r_multiple","result"])
        ov,mo=summarize_variant(tr,data_end)
        avg_full,min_full=full_month_stats(mo,data_end)
        ovs.append({
            "variant":v.name,"buy_level":v.buy_level,"sell_level":v.sell_level,
            "htf_buy_min":v.htf_buy_min,"htf_sell_max":v.htf_sell_max,
            "avg_full_month":avg_full,"min_full_month":min_full,**ov
        })
        if not mo.empty:
            mo.insert(0,"variant",v.name); mons.append(mo)
        ats.append(tr)
    od=pd.DataFrame(ovs); md=pd.concat(mons,ignore_index=True); td=pd.concat(ats,ignore_index=True)
    od["meets_avg8_full"]=od.avg_full_month>=8
    od["meets_min8_full"]=od.min_full_month>=8
    od["positive_edge"]=(od.expectancy_r>0)&(od.profit_factor>1)
    ranked=od.sort_values(
        ["positive_edge","meets_min8_full","meets_avg8_full","expectancy_r","profit_factor","max_drawdown_pct"],
        ascending=[False,False,False,False,False,True]
    )
    od.to_csv(out/"overall.csv",index=False); md.to_csv(out/"monthly.csv",index=False)
    td.to_csv(out/"trades.csv",index=False); ranked.to_csv(out/"ranked.csv",index=False)
    lines=[
        "# FiboRSI8 Phase 4 — M15 threshold sweep","",
        f"Coverage: {m5.index.min().isoformat()} -> {data_end.isoformat()}",
        "2026 only; September is partial. Full-month frequency metrics use Jan-Aug only.",
        "RM100 start; 5% risk; fixed 3R; signal-wick SL; M30 completed RSI filter; one position at a time.",
        "Same-M5 SL+TP = SL first. Costs not modeled.","",
        "| Variant | Trades | Avg full-mo | Min full-mo | W | SL | WR | Exp R | PF | DD | End RM | Return |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in ranked.itertuples(index=False):
        pf="∞" if math.isinf(float(r.profit_factor)) else f"{r.profit_factor:.2f}"
        lines.append(
            f"| {r.variant} | {r.trades} | {r.avg_full_month:.2f} | {r.min_full_month} | {r.wins} | {r.losses} | "
            f"{r.win_rate_pct:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.max_drawdown_pct:.2f}% | "
            f"RM{r.end_balance_rm:.2f} | {r.return_pct:+.2f}% |"
        )
    for variant in ranked.variant:
        lines+=["",f"## {variant}","",
                "| Month | Trades | W | SL | WR | Net R | End RM |",
                "|---|---:|---:|---:|---:|---:|---:|"]
        g=md[md.variant==variant]
        for m in g.itertuples(index=False):
            lines.append(f"| {m.month} | {m.trades} | {m.wins} | {m.sl} | {m.win_rate_pct:.2f}% | {m.net_r:+.1f}R | RM{m.end_balance_rm:.2f} |")
    report="\n".join(lines)+"\n"; (out/"REPORT.md").write_text(report)
    summary={"coverage":{"start":m5.index.min().isoformat(),"end":data_end.isoformat()},
             "ranked":ranked.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")}
    (out/"summary.json").write_text(json.dumps(summary,indent=2))
    print(report); return summary

def main():
    p=argparse.ArgumentParser(); p.add_argument("--data",default="data/xauusd_m5_dukascopy_research.csv")
    p.add_argument("--output",default="reports/fiborsi8-phase4-2026"); a=p.parse_args(); run(a.data,a.output)
if __name__=="__main__": main()
