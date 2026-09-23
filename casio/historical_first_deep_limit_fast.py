from __future__ import annotations
from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd
from .v3_core import load_m5_csv
from .historical_first_2017_2020 import DEV_END, metrics, month_stats, yearly
from .historical_first_deep_limit import prep, build
from .historical_first_displacement_retrace import replay_pending

def run(data_path,output_dir):
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path); m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy()
    f=prep(m5)
    specs=[]
    for session in ["PRIMARY","ALL"]:
      for disp in [0.4,0.6]:
       for rt in [0.79,0.886]:
        for wait in [30,60]:
         for br in [False,True]:
          specs.append((f"FASTIMP__{session}__D{disp}__R{rt}__W{wait}__B{int(br)}","impulse","h4d1",session,rt,wait,disp,0.0,br))
      for wick in [1.5,2.2]:
       for rt in [0.705,0.79]:
        for wait in [30,60]:
         specs.append((f"FASTPIN__{session}__K{wick}__R{rt}__W{wait}","ema20_pin","h4d1",session,rt,wait,0.0,wick,False))
    rows=[]; yrs=[]
    for name,fam,bias,session,rt,wait,disp,wick,br in specs:
        tr=replay_pending(m5,build(f,name,fam,bias,session,rt,wait,disp,wick,br))
        ov=metrics(tr); ms=month_stats(tr); y=yearly(tr)
        rows.append({"strategy":name,"family":fam,"trades":ov["trades"],"wr":ov["wr"],"expectancy_r":ov["expectancy_r"],
                     "pf":ov["pf"],"dd":ov["max_dd_pct"],"end_rm":ov["end_rm"],**ms,
                     "positive_years":int((y.expectancy_r>0).sum()),"pf_years":int((y.pf>1).sum())})
        for rr in y.itertuples(index=False): yrs.append({"strategy":name,**rr._asdict()})
    rd=pd.DataFrame(rows)
    rd["strict"]=(rd.wr>=60)&(rd.dd<=25)&(rd.min_month>=8)&(rd.positive_years.eq(4))&(rd.pf_years.eq(4))
    rd["dist"]=np.maximum(0,60-rd.wr)*3+np.maximum(0,rd.dd-25)+np.maximum(0,8-rd.min_month)*5+(4-rd.positive_years)*20
    ranked=rd.sort_values(["strict","dist","positive_years","min_month","wr","expectancy_r"],ascending=[False,True,False,False,False,False])
    yd=pd.DataFrame(yrs); ranked.to_csv(out/"ranked.csv",index=False); yd.to_csv(out/"yearly.csv",index=False)
    lines=["# Deep Limit Fast Shortlist","",f"Specs {len(specs)}; strict passes {int(ranked.strict.sum())}.","",
           "| Strategy | Trades | WR | ExpR | PF | DD | Avg/mo | Min/mo | Years |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in ranked.itertuples(index=False):
        pf="inf" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(f"| {r.strategy} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.dd:.2f}% | {r.avg_month:.2f} | {r.min_month} | {r.positive_years}/4 |")
    report="\n".join(lines)+"\n"; (out/"REPORT.md").write_text(report)
    (out/"summary.json").write_text(json.dumps({"strict":ranked[ranked.strict].replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records"),
      "ranked":ranked.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")},indent=2))
    print(report)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output",default="reports/historical-first-deep-limit-fast")
    a=p.parse_args(); run(a.data,a.output)
if __name__=="__main__": main()
