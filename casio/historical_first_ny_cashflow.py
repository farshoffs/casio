from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import DEV_END
from .historical_first_ny_strict import prep, signal_rows, replay, Spec

START_RM=100.0
RISK=0.05
BASE_RM=100.0

@dataclass(frozen=True)
class CashSpec:
    spec: Spec
    tag: str


def cashflow_metrics(tr: pd.DataFrame):
    months=pd.period_range("2017-01","2020-12",freq="M")
    bal=START_RM
    peak=bal
    max_dd=0.0
    rows=[]
    zero_streak=0
    max_zero_streak=0
    total_withdraw=0.0

    if tr.empty:
        groups={}
    else:
        tt=tr.copy()
        tt["month"]=pd.to_datetime(tt.entry_time,utc=True).dt.to_period("M")
        groups={m:g.sort_values("entry_time") for m,g in tt.groupby("month")}

    for m in months:
        start_bal=bal
        g=groups.get(m,pd.DataFrame())
        wins=losses=0
        month_r=0.0
        if not g.empty:
            for rv in g.net_r.astype(float):
                month_r+=rv
                if rv>0:wins+=1
                elif rv<0:losses+=1
                bal*=max(0.0,1.0+RISK*rv)
                peak=max(peak,bal)
                if peak>0:max_dd=max(max_dd,(peak-bal)/peak)
        pre_withdraw=bal
        month_pnl=pre_withdraw-start_bal
        trading_positive=month_pnl>1e-9
        withdrawal=max(0.0,pre_withdraw-BASE_RM)
        if withdrawal>0:
            bal-=withdrawal
            peak=max(bal, peak-withdrawal)
            total_withdraw+=withdrawal
            zero_streak=0
        else:
            zero_streak+=1
            max_zero_streak=max(max_zero_streak,zero_streak)

        rows.append({
            "month":str(m),"start_rm":start_bal,"trades":int(len(g)),"wins":wins,"losses":losses,
            "month_sum_r":month_r,"pre_withdraw_rm":pre_withdraw,"month_pnl_rm":month_pnl,
            "trading_positive":trading_positive,"withdrawal_rm":withdrawal,"carry_rm":bal,
        })

    md=pd.DataFrame(rows)
    pos_months=int(md.trading_positive.sum())
    withdraw_months=int((md.withdrawal_rm>0).sum())
    all_months=withdraw_months==48
    worst_pnl=float(md.month_pnl_rm.min())
    min_withdraw=float(md.loc[md.withdrawal_rm>0,"withdrawal_rm"].min()) if withdraw_months else 0.0
    median_withdraw=float(md.loc[md.withdrawal_rm>0,"withdrawal_rm"].median()) if withdraw_months else 0.0
    avg_withdraw=float(md.withdrawal_rm.mean())
    total_return_cash=(total_withdraw+bal-START_RM)/START_RM*100.0

    # Calendar-year cashflow requirements: at least one withdrawal each month means 12/12.
    md["year"]=md.month.str[:4].astype(int)
    y=md.groupby("year").agg(
        profitable_months=("trading_positive","sum"),
        withdrawal_months=("withdrawal_rm",lambda x:int((x>0).sum())),
        withdrawal_rm=("withdrawal_rm","sum"),
        net_month_pnl_rm=("month_pnl_rm","sum"),
        trades=("trades","sum"),
    ).reset_index()

    return {
        "positive_months":pos_months,
        "withdrawal_months":withdraw_months,
        "all_48_withdraw":all_months,
        "max_no_withdraw_streak":int(max_zero_streak),
        "total_withdraw_rm":float(total_withdraw),
        "avg_withdraw_rm":avg_withdraw,
        "median_positive_withdraw_rm":median_withdraw,
        "min_positive_withdraw_rm":min_withdraw,
        "worst_month_pnl_rm":worst_pnl,
        "cashflow_max_dd_pct":max_dd*100.0,
        "ending_carry_rm":float(bal),
        "cash_plus_carry_return_pct":float(total_return_cash),
    },md,y


def make_specs():
    out=[]
    # Focused families based on prior NY results plus complementary cashflow styles.
    families=["displacement","rsi2_trend","ema20_pullback","vwap_trend_reclaim","orb_break","ib_break","overnight_break",
              "overnight_sweep","premarket_sweep","prev_ny_sweep","rolling_sweep"]
    for fam in families:
        biases=["h4","h4d1","triple"] if fam not in ["overnight_sweep","premarket_sweep","prev_ny_sweep","rolling_sweep"] else ["none","h4","h4d1"]
        windows=["NY_FULL","NY_CORE","NY_CASH_AM"]
        entries=["market","half","deep705","deep886"]
        adxs=[16,22,28]
        vols=[0.0,1.15]
        lbs=[12,24,48] if fam in ["displacement","rolling_sweep"] else [24]
        for b in biases:
            for w in windows:
                for e in entries:
                    for a in adxs:
                        for v in vols:
                            for lb in lbs:
                                name=f"NYCF__{fam}__{b}__{w}__{e}__A{a}__V{v}__L{lb}"
                                out.append(Spec(name,fam,b,w,e,a,v,45,lb))
    return out


def run(data_path,output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path)
    m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy()
    f=prep(m5)
    specs=make_specs()
    rows=[]; monthly=[]; yearly=[]; trade_cache={}

    for s in specs:
        tr=replay(m5,signal_rows(f,s),s.name)
        cf,md,yd=cashflow_metrics(tr)
        wr=float((tr.net_r>0).mean()*100) if not tr.empty else 0.0
        exp=float(tr.net_r.mean()) if not tr.empty else 0.0
        gw=float(tr.loc[tr.net_r>0,"net_r"].sum()) if not tr.empty else 0.0
        gl=float(-tr.loc[tr.net_r<0,"net_r"].sum()) if not tr.empty else 0.0
        pf=gw/gl if gl>0 else (math.inf if gw>0 else 0.0)
        rows.append({
            "strategy":s.name,"family":s.family,"bias":s.bias,"window":s.window,"entry_mode":s.entry_mode,
            "adx_min":s.adx_min,"vol_min":s.vol_min,"lookback":s.lookback,
            "trades":int(len(tr)),"wr":wr,"expectancy_r":exp,"pf":pf,
            **cf,
            "profitable_years":int((yd.net_month_pnl_rm>0).sum()),
            "years_12_withdraw":int((yd.withdrawal_months==12).sum()),
        })
        md.insert(0,"strategy",s.name);monthly.append(md)
        yd.insert(0,"strategy",s.name);yearly.append(yd)
        trade_cache[s.name]=tr

    rd=pd.DataFrame(rows)
    # Hard risk/profit integrity, but monthly cashflow is the main target.
    rd["risk_pass"]=rd.cashflow_max_dd_pct<=25
    rd["annual_pass"]=rd.profitable_years.eq(4)
    rd["wr60"]=rd.wr>=60
    rd["monthly_withdraw_pass"]=rd.withdrawal_months.eq(48)
    rd["strict_all"] = rd.risk_pass & rd.annual_pass & rd.wr60 & rd.monthly_withdraw_pass

    # Rank for actual use: most withdrawal months, shorter dry spells, risk integrity, yearly profitability, then cash amount/quality.
    rd=rd.sort_values(
        ["strict_all","withdrawal_months","max_no_withdraw_streak","risk_pass","annual_pass","total_withdraw_rm","wr","expectancy_r"],
        ascending=[False,False,True,False,False,False,False,False]
    )

    # Build simple first-signal-per-day routers from top distinct families to increase monthly coverage.
    routers=[]
    top_unique=[]
    for r in rd.itertuples(index=False):
        if r.family not in [x.family for x in top_unique] and r.cashflow_max_dd_pct<=40 and r.expectancy_r>0:
            top_unique.append(r)
        if len(top_unique)>=8: break

    def union_trade_stream(names,router_name):
        parts=[]
        for n in names:
            tr=trade_cache.get(n,pd.DataFrame())
            if tr is not None and not tr.empty:
                x=tr.copy();x["source"]=n;parts.append(x)
        if not parts:return pd.DataFrame()
        x=pd.concat(parts,ignore_index=True).sort_values(["entry_time","source"])
        # Preserve one-trade-per-NY-day discipline across the router.
        local=pd.to_datetime(x.entry_time,utc=True).dt.tz_convert("America/New_York")
        x["ny_date"]=local.dt.date
        x=x.drop_duplicates("ny_date",keep="first").sort_values("entry_time")
        # Remove overlaps: keep next trade only after previous trade exited.
        keep=[];busy=None
        for i,row in x.iterrows():
            et=pd.Timestamp(row.entry_time);xt=pd.Timestamp(row.exit_time)
            if busy is not None and et<=busy:continue
            keep.append(i);busy=xt
        return x.loc[keep].reset_index(drop=True)

    for k in [2,3,4,5,6]:
        if len(top_unique)<k:continue
        names=[x.strategy for x in top_unique[:k]]
        rn=f"NYCF_ROUTER_TOP{k}"
        tr=union_trade_stream(names,rn)
        cf,md,yd=cashflow_metrics(tr)
        wr=float((tr.net_r>0).mean()*100) if not tr.empty else 0.0
        exp=float(tr.net_r.mean()) if not tr.empty else 0.0
        gw=float(tr.loc[tr.net_r>0,"net_r"].sum()) if not tr.empty else 0.0
        gl=float(-tr.loc[tr.net_r<0,"net_r"].sum()) if not tr.empty else 0.0
        pf=gw/gl if gl>0 else (math.inf if gw>0 else 0.0)
        row={"strategy":rn,"family":"router","bias":"mixed","window":"NY","entry_mode":"mixed",
             "adx_min":np.nan,"vol_min":np.nan,"lookback":np.nan,"trades":int(len(tr)),"wr":wr,
             "expectancy_r":exp,"pf":pf,**cf,"profitable_years":int((yd.net_month_pnl_rm>0).sum()),
             "years_12_withdraw":int((yd.withdrawal_months==12).sum())}
        row["risk_pass"]=row["cashflow_max_dd_pct"]<=25
        row["annual_pass"]=row["profitable_years"]==4
        row["wr60"]=row["wr"]>=60
        row["monthly_withdraw_pass"]=row["withdrawal_months"]==48
        row["strict_all"]=row["risk_pass"] and row["annual_pass"] and row["wr60"] and row["monthly_withdraw_pass"]
        routers.append(row)
        md.insert(0,"strategy",rn);monthly.append(md)
        yd.insert(0,"strategy",rn);yearly.append(yd)

    if routers:
        rd=pd.concat([rd,pd.DataFrame(routers)],ignore_index=True)
        rd=rd.sort_values(["strict_all","withdrawal_months","max_no_withdraw_streak","risk_pass","annual_pass","total_withdraw_rm","wr","expectancy_r"],
                          ascending=[False,False,True,False,False,False,False,False])

    mdall=pd.concat(monthly,ignore_index=True);ydall=pd.concat(yearly,ignore_index=True)
    rd.to_csv(out/"ranked_cashflow.csv",index=False)
    mdall.to_csv(out/"monthly_cashflow.csv",index=False)
    ydall.to_csv(out/"yearly_cashflow.csv",index=False)

    strict=rd[rd.strict_all]
    lines=[
        "# New York Monthly Withdrawal Research — 2017-2020","",
        "Objective: real monthly cashflow, not an arbitrary minimum trade count.",
        "Account starts RM100. Risk = 5% of current retained equity per entry. TP = fixed 3R. Real structural SL only.",
        "At each month-end: if equity > RM100, withdraw the excess and reset retained trading equity to RM100. If equity <= RM100, withdraw RM0 and carry the reduced balance forward; no top-up.",
        "Withdrawals are not counted as drawdown. Drawdown is measured trade-by-trade inside retained trading capital.",
        "New York session is DST-aware America/New_York. 2021+ remains sealed.","",
        f"Individual specs tested: {len(specs)}; routers tested: {len(routers)}; all-hard-passes (WR>=60, DD<=25, 48/48 withdrawal months, 4/4 profitable years): {len(strict)}.","",
        "## Best monthly-cashflow candidates","",
        "| Strategy | Trades | WR | ExpR | PF | DD | Withdraw months | Longest dry | Total withdrawn | Median +withdraw | Worst month P/L | Prof years |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in rd.head(30).itertuples(index=False):
        pf="inf" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(f"| {r.strategy} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.cashflow_max_dd_pct:.2f}% | {r.withdrawal_months}/48 | {r.max_no_withdraw_streak} | RM{r.total_withdraw_rm:.2f} | RM{r.median_positive_withdraw_rm:.2f} | RM{r.worst_month_pnl_rm:.2f} | {r.profitable_years}/4 |")

    detail=rd.head(8).strategy.tolist()
    for strategy in detail:
        lines+=["",f"## {strategy} — monthly","",
                "| Month | Start | Trades | W | L | Month P/L | Withdrawal | Carry |",
                "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for r in mdall[mdall.strategy==strategy].itertuples(index=False):
            lines.append(f"| {r.month} | RM{r.start_rm:.2f} | {r.trades} | {r.wins} | {r.losses} | RM{r.month_pnl_rm:+.2f} | RM{r.withdrawal_rm:.2f} | RM{r.carry_rm:.2f} |")

    report="\n".join(lines)+"\n";(out/"REPORT.md").write_text(report,encoding="utf-8")
    (out/"summary.json").write_text(json.dumps({
        "objective":"monthly withdrawals",
        "withdrawal_rule":"month-end withdraw equity above RM100; no top-up below RM100",
        "specs":len(specs),"routers":len(routers),"strict_count":int(len(strict)),
        "top":rd.head(30).replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")
    },indent=2),encoding="utf-8")
    print(report)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output",default="reports/historical-first-ny-cashflow")
    a=p.parse_args();run(a.data,a.output)

if __name__=="__main__":main()
