from __future__ import annotations
from pathlib import Path
import argparse,json,math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import DEV_END
from .historical_first_ny_strict import prep,signal_rows,replay
from .historical_first_ny_cashflow_fast import specs as base_specs

START_RM=100.0
RISK=0.05
WITHDRAW_SHARE=0.50

def rolling_metrics(tr: pd.DataFrame,target_pct:float,max_losses:int|None):
    months=pd.period_range("2017-01","2020-12",freq="M")
    bal=START_RM
    peak=bal
    max_dd=0.0
    total_withdraw=0.0
    rows=[]
    if tr.empty:
        groups={}
    else:
        t=tr.copy()
        t["month"]=pd.to_datetime(t.entry_time,utc=True).dt.to_period("M")
        groups={m:g.sort_values("entry_time") for m,g in t.groupby("month")}

    dry=0;max_dry=0
    for m in months:
        start=bal
        target=start*(1.0+target_pct)
        losses=0
        used=0
        wins=0
        locked=False
        g=groups.get(m,pd.DataFrame())
        if not g.empty:
            for rv in g.net_r.astype(float):
                if locked:
                    continue
                used+=1
                if rv>0:wins+=1
                elif rv<0:losses+=1
                bal*=max(0.0,1.0+RISK*rv)
                peak=max(peak,bal)
                if peak>0:
                    max_dd=max(max_dd,(peak-bal)/peak)
                if bal>target:
                    locked=True
                if max_losses is not None and losses>=max_losses:
                    locked=True
        pre=bal
        pnl=pre-start
        withdrawal=0.0
        if pnl>0:
            withdrawal=pnl*WITHDRAW_SHARE
            bal-=withdrawal
            peak=max(bal,peak-withdrawal)
            total_withdraw+=withdrawal
            dry=0
        else:
            dry+=1;max_dry=max(max_dry,dry)
        rows.append({"month":str(m),"start_rm":start,"available_trades":int(len(g)),"used_trades":used,
                     "wins":wins,"losses":losses,"month_pnl_rm":pnl,"withdrawal_rm":withdrawal,"carry_rm":bal})
    md=pd.DataFrame(rows)
    md["year"]=md.month.str[:4].astype(int)
    yd=md.groupby("year").agg(
        withdrawal_months=("withdrawal_rm",lambda x:int((x>0).sum())),
        withdrawal_rm=("withdrawal_rm","sum"),
        month_pnl_rm=("month_pnl_rm","sum"),
        used_trades=("used_trades","sum"),
    ).reset_index()
    w=md.loc[md.withdrawal_rm>0,"withdrawal_rm"]
    return {
        "withdrawal_months":int((md.withdrawal_rm>0).sum()),
        "max_no_withdraw_streak":int(max_dry),
        "total_withdraw_rm":float(total_withdraw),
        "median_withdraw_rm":float(w.median()) if len(w) else 0.0,
        "min_withdraw_rm":float(w.min()) if len(w) else 0.0,
        "worst_month_pnl_rm":float(md.month_pnl_rm.min()),
        "dd_pct":float(max_dd*100),
        "ending_carry_rm":float(bal),
        "profitable_years":int((yd.month_pnl_rm>0).sum()),
        "years_12_withdraw":int((yd.withdrawal_months==12).sum()),
        "used_trades":int(md.used_trades.sum()),
    },md,yd

def run(data_path,output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path)
    m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy()
    f=prep(m5)
    rows=[];monthly=[];yearly=[]
    pol=[(0.0,None),(0.0,2),(0.0,3),(0.05,None),(0.05,2),(0.05,3)]
    for s in base_specs():
        tr=replay(m5,signal_rows(f,s),s.name)
        base_wr=float((tr.net_r>0).mean()*100) if not tr.empty else 0.0
        exp=float(tr.net_r.mean()) if not tr.empty else 0.0
        gw=float(tr.loc[tr.net_r>0,"net_r"].sum()) if not tr.empty else 0.0
        gl=float(-tr.loc[tr.net_r<0,"net_r"].sum()) if not tr.empty else 0.0
        pf=gw/gl if gl>0 else (math.inf if gw>0 else 0.0)
        for tp,ml in pol:
            met,md,yd=rolling_metrics(tr,tp,ml)
            name=f"{s.name}__ROLL_T{tp}__ML{ml if ml is not None else 0}"
            rows.append({"strategy":name,"base_strategy":s.name,"family":s.family,"bias":s.bias,"window":s.window,
                         "entry":s.entry_mode,"target_pct":tp,"max_losses":0 if ml is None else ml,
                         "base_trades":int(len(tr)),"wr":base_wr,"expectancy_r":exp,"pf":pf,**met})
            md.insert(0,"strategy",name);monthly.append(md)
            yd.insert(0,"strategy",name);yearly.append(yd)
    rd=pd.DataFrame(rows)
    rd["strict"]=(rd.wr>=60)&(rd.dd_pct<=25)&(rd.withdrawal_months.eq(48))&(rd.profitable_years.eq(4))
    rd=rd.sort_values(["strict","withdrawal_months","max_no_withdraw_streak","dd_pct","profitable_years","total_withdraw_rm","wr","expectancy_r"],
                      ascending=[False,False,True,True,False,False,False,False])
    md=pd.concat(monthly,ignore_index=True);yd=pd.concat(yearly,ignore_index=True)
    rd.to_csv(out/"ranked.csv",index=False);md.to_csv(out/"monthly.csv",index=False);yd.to_csv(out/"yearly.csv",index=False)

    lines=["# NY Rolling Monthly Withdrawal Search — 2017-2020","",
           "Start RM100; 5% current-equity risk; fixed RR3; real SL; DST-aware New York only.",
           "Monthly rolling policy: stop trading once the month reaches the selected positive target; at month-end withdraw 50% of positive monthly P/L and retain 50% to grow/repair capital. Losing months withdraw RM0. No top-up.",
           "Cash withdrawals are removed from both balance and high-water mark; losses carry across months for DD.",
           "2021+ sealed.","",
           f"Strategy-policy combinations: {len(rd)}. Strict all-pass: {int(rd.strict.sum())}.","",
           "| Strategy | Base trades | Used | WR | ExpR | PF | DD | Withdraw months | Dry streak | Total withdraw | Median withdraw | Ending carry | Prof years |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rd.head(30).itertuples(index=False):
        pf="inf" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(f"| {r.strategy} | {r.base_trades} | {r.used_trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.dd_pct:.2f}% | {r.withdrawal_months}/48 | {r.max_no_withdraw_streak} | RM{r.total_withdraw_rm:.2f} | RM{r.median_withdraw_rm:.2f} | RM{r.ending_carry_rm:.2f} | {r.profitable_years}/4 |")
    for name in rd.head(5).strategy:
        lines+=["",f"## {name}","",
                "| Month | Start | Avail | Used | W | L | P/L | Withdraw | Carry |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for r in md[md.strategy==name].itertuples(index=False):
            lines.append(f"| {r.month} | RM{r.start_rm:.2f} | {r.available_trades} | {r.used_trades} | {r.wins} | {r.losses} | RM{r.month_pnl_rm:+.2f} | RM{r.withdrawal_rm:.2f} | RM{r.carry_rm:.2f} |")
    report="\n".join(lines)+"\n";(out/"REPORT.md").write_text(report)
    (out/"summary.json").write_text(json.dumps({"withdraw_share":WITHDRAW_SHARE,"top":rd.head(30).replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")},indent=2))
    print(report)

def main():
    p=argparse.ArgumentParser();p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output",default="reports/historical-first-ny-rolling-cashflow");a=p.parse_args();run(a.data,a.output)
if __name__=="__main__":main()
