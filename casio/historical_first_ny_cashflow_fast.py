from __future__ import annotations
from pathlib import Path
import argparse,json,math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import DEV_END
from .historical_first_ny_strict import prep,signal_rows,replay,Spec
from .historical_first_ny_cashflow import cashflow_metrics

def specs():
    out=[]
    # Prioritize promising NY families; keep the grid intentionally compact.
    for fam in ["displacement","rsi2_trend","ema20_pullback","vwap_trend_reclaim","orb_break","overnight_break"]:
        for b in ["h4","h4d1","triple"]:
            for w in ["NY_FULL","NY_CORE","NY_CASH_AM"]:
                for e in ["market","half","deep705","deep886"]:
                    for a in [22,28]:
                        for v in [0.0,1.15]:
                            lbs=[12,24,48] if fam=="displacement" else [24]
                            for lb in lbs:
                                out.append(Spec(f"NYCFAST__{fam}__{b}__{w}__{e}__A{a}__V{v}__L{lb}",fam,b,w,e,a,v,45,lb))
    return out

def run(data_path,output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path)
    m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy()
    f=prep(m5); rows=[]; mrows=[]; yrows=[]
    for s in specs():
        tr=replay(m5,signal_rows(f,s),s.name)
        cf,md,yd=cashflow_metrics(tr)
        wr=float((tr.net_r>0).mean()*100) if not tr.empty else 0.0
        ex=float(tr.net_r.mean()) if not tr.empty else 0.0
        gw=float(tr.loc[tr.net_r>0,"net_r"].sum()) if not tr.empty else 0
        gl=float(-tr.loc[tr.net_r<0,"net_r"].sum()) if not tr.empty else 0
        pf=gw/gl if gl>0 else (math.inf if gw>0 else 0.0)
        rows.append({"strategy":s.name,"family":s.family,"bias":s.bias,"window":s.window,"entry":s.entry_mode,
                     "trades":len(tr),"wr":wr,"expectancy_r":ex,"pf":pf,**cf,
                     "profitable_years":int((yd.net_month_pnl_rm>0).sum()),"years_12_withdraw":int((yd.withdrawal_months==12).sum())})
        md.insert(0,"strategy",s.name);mrows.append(md)
        yd.insert(0,"strategy",s.name);yrows.append(yd)
    rd=pd.DataFrame(rows)
    rd["risk_pass"]=rd.cashflow_max_dd_pct<=25
    rd["annual_pass"]=rd.profitable_years.eq(4)
    rd["wr60"]=rd.wr>=60
    rd["monthly48"]=rd.withdrawal_months.eq(48)
    rd["strict_all"]=rd.risk_pass&rd.annual_pass&rd.wr60&rd.monthly48
    rd=rd.sort_values(["withdrawal_months","max_no_withdraw_streak","risk_pass","annual_pass","total_withdraw_rm","wr","expectancy_r"],
                      ascending=[False,True,False,False,False,False,False])
    md=pd.concat(mrows,ignore_index=True);yd=pd.concat(yrows,ignore_index=True)
    rd.to_csv(out/"ranked.csv",index=False);md.to_csv(out/"monthly.csv",index=False);yd.to_csv(out/"yearly.csv",index=False)
    lines=["# Fast NY Monthly Cashflow Search — 2017-2020","",
           "RM100 retained-capital model: risk 5%, fixed 3R, real SL, DST-aware NY only. Month-end excess above RM100 withdrawn; losses carried, no top-up.","",
           f"Specs {len(rd)}; strict all-pass {int(rd.strict_all.sum())}.","",
           "| Strategy | Trades | WR | ExpR | PF | DD | Withdraw months | Dry streak | Total withdraw | Median withdraw | Worst month | Prof years |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rd.head(25).itertuples(index=False):
        pf="inf" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(f"| {r.strategy} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.cashflow_max_dd_pct:.2f}% | {r.withdrawal_months}/48 | {r.max_no_withdraw_streak} | RM{r.total_withdraw_rm:.2f} | RM{r.median_positive_withdraw_rm:.2f} | RM{r.worst_month_pnl_rm:.2f} | {r.profitable_years}/4 |")
    for name in rd.head(5).strategy:
        lines+=["",f"## {name}","",
                "| Month | Start | Trades | W | L | P/L | Withdraw | Carry |",
                "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for r in md[md.strategy==name].itertuples(index=False):
            lines.append(f"| {r.month} | RM{r.start_rm:.2f} | {r.trades} | {r.wins} | {r.losses} | RM{r.month_pnl_rm:+.2f} | RM{r.withdrawal_rm:.2f} | RM{r.carry_rm:.2f} |")
    report="\n".join(lines)+"\n";(out/"REPORT.md").write_text(report)
    (out/"summary.json").write_text(json.dumps({"top":rd.head(25).replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")},indent=2))
    print(report)

def main():
    p=argparse.ArgumentParser();p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output",default="reports/historical-first-ny-cashflow-fast");a=p.parse_args();run(a.data,a.output)
if __name__=="__main__":main()
