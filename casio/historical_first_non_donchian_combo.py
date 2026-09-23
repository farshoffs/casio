from __future__ import annotations
from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import DEV_END, replay, combine_setups, metrics, month_stats, yearly
from .historical_first_alternative_systems import prepare as alt_prepare, build as alt_build, CARDS as ALT_CARDS
from .historical_first_session import prep as session_prep, setups as session_setups, CARDS as SESSION_CARDS


def run(data_path, output_dir):
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    raw = load_m5_csv(data_path)
    m5 = raw[(raw.index >= pd.Timestamp("2016-01-01", tz="UTC")) & (raw.index < DEV_END)].copy()

    af = alt_prepare(m5)
    wanted_alt = {
        "EMA_RIBBON_BREAK","MACD_CONTINUATION","ICHIMOKU_CONTINUATION",
        "RSI2_PULLBACK","BB_TREND_BREAK","KELTNER_BREAK","ATR_EXPANSION"
    }
    alt = {c.name: alt_build(af, c) for c in ALT_CARDS if c.name in wanted_alt}

    sf = session_prep(m5)
    sess = {c.name: session_setups(sf, c) for c in SESSION_CARDS if c.name in ["ASIA_BREAK_RAW","NY_OR_BREAK_RAW"]}

    trend_alt = combine_setups(
        [alt["MACD_CONTINUATION"], alt["ICHIMOKU_CONTINUATION"], alt["EMA_RIBBON_BREAK"]],
        "TREND_ALT_CORE"
    )

    cache = {
        "EMA_RIBBON_PLUS_NY": combine_setups([alt["EMA_RIBBON_BREAK"], sess["NY_OR_BREAK_RAW"]], "EMA_RIBBON_PLUS_NY"),
        "EMA_RIBBON_PLUS_ASIA": combine_setups([alt["EMA_RIBBON_BREAK"], sess["ASIA_BREAK_RAW"]], "EMA_RIBBON_PLUS_ASIA"),
        "EMA_RIBBON_PLUS_SESSION": combine_setups([alt["EMA_RIBBON_BREAK"], sess["ASIA_BREAK_RAW"], sess["NY_OR_BREAK_RAW"]], "EMA_RIBBON_PLUS_SESSION"),
        "EMA_RIBBON_PLUS_RSI2": combine_setups([alt["EMA_RIBBON_BREAK"], alt["RSI2_PULLBACK"]], "EMA_RIBBON_PLUS_RSI2"),
        "EMA_RIBBON_RSI2_NY": combine_setups([alt["EMA_RIBBON_BREAK"], alt["RSI2_PULLBACK"], sess["NY_OR_BREAK_RAW"]], "EMA_RIBBON_RSI2_NY"),
        "EMA_RIBBON_BB_NY": combine_setups([alt["EMA_RIBBON_BREAK"], alt["BB_TREND_BREAK"], sess["NY_OR_BREAK_RAW"]], "EMA_RIBBON_BB_NY"),
        "TREND_ALT_PLUS_NY": combine_setups([trend_alt, sess["NY_OR_BREAK_RAW"]], "TREND_ALT_PLUS_NY"),
        "TREND_ALT_PLUS_SESSION": combine_setups([trend_alt, sess["ASIA_BREAK_RAW"], sess["NY_OR_BREAK_RAW"]], "TREND_ALT_PLUS_SESSION"),
        "BREAK_ALT_PLUS_NY": combine_setups([alt["KELTNER_BREAK"], alt["ATR_EXPANSION"], sess["NY_OR_BREAK_RAW"]], "BREAK_ALT_PLUS_NY"),
    }

    rows=[]; yrs=[]; months=[]; alltr=[]
    for name, ss in cache.items():
        tr = replay(m5, ss)
        if not tr.empty: alltr.append(tr.assign(strategy=name))
        ov=metrics(tr); ms=month_stats(tr); y=yearly(tr)
        rows.append({"strategy":name, **ov, **ms,
                     "positive_years":int((y.expectancy_r>0).sum()),
                     "pf_gt1_years":int((y.pf>1).sum()),
                     "worst_year_exp_r":float(y.expectancy_r.min()),
                     "worst_year_dd_pct":float(y.max_dd_pct.max())})
        for rr in y.itertuples(index=False):
            yrs.append({"strategy":name, **rr._asdict()})
        pp = pd.to_datetime(tr.entry_time, utc=True).dt.to_period("M") if not tr.empty else pd.Series([],dtype="period[M]")
        for p in pd.period_range("2017-01","2020-12",freq="M"):
            g=tr[pp==p] if not tr.empty else tr
            months.append({"strategy":name,"month":str(p),**metrics(g)})

    ranked=pd.DataFrame(rows).sort_values(
        ["positive_years","pf_gt1_years","min_month","avg_month","worst_year_exp_r","expectancy_r","pf","worst_year_dd_pct"],
        ascending=[False,False,False,False,False,False,False,True]
    )
    yd=pd.DataFrame(yrs); md=pd.DataFrame(months); td=pd.concat(alltr,ignore_index=True) if alltr else pd.DataFrame()
    ranked.to_csv(out/"ranked.csv",index=False); yd.to_csv(out/"yearly.csv",index=False)
    md.to_csv(out/"monthly.csv",index=False); td.to_csv(out/"trades.csv",index=False)

    lines=[
        "# Historical-First Phase 8 — Non-Donchian selective combinations","",
        "2017-2020 development only. Donchian excluded from every candidate.",
        "RR3, RM100, 5% risk, 1bp cost, one position at a time.","",
        "| Strategy | Trades | Avg/mo | Min/mo | >=8 | Pos years | WR | ExpR | PF | Worst ExpR | Worst DD | End RM |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in ranked.itertuples(index=False):
        pf="∞" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(
            f"| {r.strategy} | {r.trades} | {r.avg_month:.2f} | {r.min_month} | {r.months_ge8}/48 | "
            f"{r.positive_years}/4 | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | "
            f"{r.worst_year_exp_r:+.3f} | {r.worst_year_dd_pct:.2f}% | RM{r.end_rm:.2f} |"
        )
    for strategy in ranked.strategy:
        lines += ["",f"## {strategy}","","| Year | Trades | WR | ExpR | PF | DD | RM100 → |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for r in yd[yd.strategy==strategy].itertuples(index=False):
            pf="∞" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
            lines.append(f"| {r.year} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.max_dd_pct:.2f}% | RM{r.end_rm:.2f} |")

    report="\n".join(lines)+"\n"; (out/"REPORT.md").write_text(report,encoding="utf-8")
    (out/"summary.json").write_text(json.dumps({"window":"2017-2020","donchian_used":False,
        "ranked":ranked.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records")},indent=2),encoding="utf-8")
    print(report)


def main():
    p=argparse.ArgumentParser(); p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output",default="reports/historical-first-non-donchian-combo")
    a=p.parse_args(); run(a.data,a.output)

if __name__=="__main__": main()
