from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .historical_first_2017_2020 import (
    DEV_END, atr, di_adx, resample, align_completed, rsi,
    replay, combine_setups, metrics, month_stats, yearly,
)

START = pd.Timestamp("2017-01-01", tz="UTC")


@dataclass(frozen=True)
class Card:
    name: str
    family: str
    bias: str = "align"  # align | h4 | d1 | none
    lookback: int = 10
    adx_min: float = 18.0
    body_min: float = 0.25
    wick_ratio: float = 1.5
    vol_min: float = 0.0
    cooldown: int = 2


def prep(m5: pd.DataFrame) -> pd.DataFrame:
    f = resample(m5, "15min")
    f["atr14"] = atr(f, 14)
    pdi, mdi, adx = di_adx(f, 14)
    f["pdi"], f["mdi"], f["adx"] = pdi, mdi, adx
    f["rsi8"] = rsi(f.close, 8)
    f["ema8"] = f.close.ewm(span=8, adjust=False).mean()
    f["ema20"] = f.close.ewm(span=20, adjust=False).mean()
    f["ema50"] = f.close.ewm(span=50, adjust=False).mean()
    f["ema100"] = f.close.ewm(span=100, adjust=False).mean()
    f["body"] = (f.close - f.open).abs()
    f["body_atr"] = f.body / f.atr14.replace(0, np.nan)
    f["range"] = f.high - f.low
    f["upper_wick"] = f.high - f[["open","close"]].max(axis=1)
    f["lower_wick"] = f[["open","close"]].min(axis=1) - f.low
    f["upper_wick_body"] = f.upper_wick / f.body.replace(0, np.nan)
    f["lower_wick_body"] = f.lower_wick / f.body.replace(0, np.nan)
    f["vol_med20"] = f.volume.rolling(20, min_periods=10).median()
    f["vol_ratio"] = f.volume / f.vol_med20.replace(0, np.nan)

    for lb in [5, 8, 10, 12, 20]:
        f[f"ph{lb}"] = f.high.shift(1).rolling(lb).max()
        f[f"pl{lb}"] = f.low.shift(1).rolling(lb).min()

    # Bollinger/Keltner compression.
    sma20 = f.close.rolling(20).mean()
    std20 = f.close.rolling(20).std(ddof=0)
    f["bb_up"] = sma20 + 2.0 * std20
    f["bb_dn"] = sma20 - 2.0 * std20
    f["kc_up"] = f.ema20 + 1.5 * f.atr14
    f["kc_dn"] = f.ema20 - 1.5 * f.atr14
    f["squeeze"] = (f.bb_up < f.kc_up) & (f.bb_dn > f.kc_dn)

    # Daily/session reference levels.
    f["day"] = f.index.floor("D")
    mins = f.index.hour * 60 + f.index.minute
    asia = (mins >= 0) & (mins < 6*60)
    nyor = (mins >= 12*60+30) & (mins < 13*60+30)
    daily = f.groupby("day").agg(day_high=("high","max"), day_low=("low","min"))
    prev = daily.shift(1)
    f["prev_day_high"] = f.day.map(prev.day_high)
    f["prev_day_low"] = f.day.map(prev.day_low)
    ast = f.loc[asia].groupby("day").agg(asia_high=("high","max"), asia_low=("low","min"))
    f["asia_high"] = f.day.map(ast.asia_high)
    f["asia_low"] = f.day.map(ast.asia_low)
    nst = f.loc[nyor].groupby("day").agg(ny_high=("high","max"), ny_low=("low","min"))
    f["ny_high"] = f.day.map(nst.ny_high)
    f["ny_low"] = f.day.map(nst.ny_low)
    f["mins"] = mins

    # Higher timeframes, completed only.
    h4 = resample(m5, "4h")
    d1 = resample(m5, "1D")
    for x in (h4, d1):
        x["ema20"] = x.close.ewm(span=20, adjust=False).mean()
        x["ema50"] = x.close.ewm(span=50, adjust=False).mean()
        x["ema100"] = x.close.ewm(span=100, adjust=False).mean()
        x["slope20"] = x.ema20.diff(3)
        x["slope50"] = x.ema50.diff(3)
        x["atr14"] = atr(x, 14)
    ct = f.index + pd.Timedelta(minutes=15)
    for p, x, period in [("h4",h4,pd.Timedelta(hours=4)),("d1",d1,pd.Timedelta(days=1))]:
        for col in ["ema20","ema50","ema100","slope20","slope50","close","atr14"]:
            f[f"{p}_{col}"] = align_completed(x[col], ct, period).to_numpy()

    f["h4_up"] = (f.h4_ema20 > f.h4_ema50) & (f.h4_slope20 > 0)
    f["h4_dn"] = (f.h4_ema20 < f.h4_ema50) & (f.h4_slope20 < 0)
    f["d1_up"] = (f.d1_ema20 > f.d1_ema50) & (f.d1_slope20 > 0)
    f["d1_dn"] = (f.d1_ema20 < f.d1_ema50) & (f.d1_slope20 < 0)
    f["align_up"] = f.h4_up & f.d1_up
    f["align_dn"] = f.h4_dn & f.d1_dn

    # Simple 3-candle imbalance / FVG proxy.
    f["bull_fvg"] = f.low > f.high.shift(2)
    f["bear_fvg"] = f.high < f.low.shift(2)

    # Inside bars.
    f["inside"] = (f.high < f.high.shift(1)) & (f.low > f.low.shift(1))

    # Engulfing.
    f["bull_engulf"] = (
        (f.close > f.open) & (f.close.shift(1) < f.open.shift(1))
        & (f.open <= f.close.shift(1)) & (f.close >= f.open.shift(1))
    )
    f["bear_engulf"] = (
        (f.close < f.open) & (f.close.shift(1) > f.open.shift(1))
        & (f.open >= f.close.shift(1)) & (f.close <= f.open.shift(1))
    )
    return f


def bias_masks(f: pd.DataFrame, bias: str):
    if bias == "align":
        return f.align_up.fillna(False), f.align_dn.fillna(False)
    if bias == "h4":
        return f.h4_up.fillna(False), f.h4_dn.fillna(False)
    if bias == "d1":
        return f.d1_up.fillna(False), f.d1_dn.fillna(False)
    if bias == "none":
        return pd.Series(True,index=f.index), pd.Series(True,index=f.index)
    raise ValueError(bias)


def signal_masks(f: pd.DataFrame, c: Card):
    up, dn = bias_masks(f, c.bias)
    ph = f[f"ph{c.lookback}"]
    pl = f[f"pl{c.lookback}"]
    volok = (f.vol_ratio >= c.vol_min) if c.vol_min > 0 else pd.Series(True,index=f.index)
    trend_long = (f.pdi > f.mdi)
    trend_short = (f.mdi > f.pdi)

    if c.family == "ema20_rejection":
        lo = up & (f.low <= f.ema20) & (f.close > f.ema20) & (f.close > f.open) & (f.lower_wick_body >= c.wick_ratio) & trend_long & (f.adx >= c.adx_min)
        sh = dn & (f.high >= f.ema20) & (f.close < f.ema20) & (f.close < f.open) & (f.upper_wick_body >= c.wick_ratio) & trend_short & (f.adx >= c.adx_min)

    elif c.family == "ema50_rejection":
        lo = up & (f.low <= f.ema50) & (f.close > f.ema50) & (f.close > f.open) & (f.lower_wick_body >= c.wick_ratio) & trend_long
        sh = dn & (f.high >= f.ema50) & (f.close < f.ema50) & (f.close < f.open) & (f.upper_wick_body >= c.wick_ratio) & trend_short

    elif c.family == "engulf_pullback":
        lo = up & f.bull_engulf & (f.low <= f.ema20) & (f.close > f.ema20) & (f.adx >= c.adx_min)
        sh = dn & f.bear_engulf & (f.high >= f.ema20) & (f.close < f.ema20) & (f.adx >= c.adx_min)

    elif c.family == "sweep_continuation":
        # Sweep against the HTF trend, then reject back with trend.
        lo = up & (f.low < pl) & (f.close > pl) & (f.close > f.open) & (f.lower_wick_body >= c.wick_ratio)
        sh = dn & (f.high > ph) & (f.close < ph) & (f.close < f.open) & (f.upper_wick_body >= c.wick_ratio)

    elif c.family == "break_retest":
        # Current bar retests a level broken by the prior bar and closes back through it.
        prev_break_up = f.close.shift(1) > ph.shift(1)
        prev_break_dn = f.close.shift(1) < pl.shift(1)
        lo = up & prev_break_up & (f.low <= ph.shift(1)) & (f.close > ph.shift(1)) & (f.close > f.open) & (f.adx >= c.adx_min)
        sh = dn & prev_break_dn & (f.high >= pl.shift(1)) & (f.close < pl.shift(1)) & (f.close < f.open) & (f.adx >= c.adx_min)

    elif c.family == "inside_break":
        mother_hi = f.high.shift(1)
        mother_lo = f.low.shift(1)
        was_inside = f.inside.shift(1)
        lo = up & was_inside & (f.close > mother_hi) & (f.body_atr >= c.body_min) & (f.adx >= c.adx_min)
        sh = dn & was_inside & (f.close < mother_lo) & (f.body_atr >= c.body_min) & (f.adx >= c.adx_min)

    elif c.family == "squeeze_break":
        prev_sq = f["squeeze"].shift(1)
        lo = up & prev_sq & (f.close > f.bb_up) & (f.body_atr >= c.body_min) & volok
        sh = dn & prev_sq & (f.close < f.bb_dn) & (f.body_atr >= c.body_min) & volok

    elif c.family == "fvg_continuation":
        # Impulse creates FVG, next bar retraces but preserves directional structure.
        lo = up & f.bull_fvg.shift(1) & (f.low <= f.low.shift(1)) & (f.close > f.open) & (f.close > f.ema20) & (f.adx >= c.adx_min)
        sh = dn & f.bear_fvg.shift(1) & (f.high >= f.high.shift(1)) & (f.close < f.open) & (f.close < f.ema20) & (f.adx >= c.adx_min)

    elif c.family == "two_bar_momentum":
        lo = up & (f.close > f.open) & (f.close.shift(1) > f.open.shift(1)) & (f.body_atr >= c.body_min) & (f.body_atr.shift(1) >= c.body_min) & (f.close > ph) & volok
        sh = dn & (f.close < f.open) & (f.close.shift(1) < f.open.shift(1)) & (f.body_atr >= c.body_min) & (f.body_atr.shift(1) >= c.body_min) & (f.close < pl) & volok

    elif c.family == "ny_or_retest":
        mins=f.mins
        session=(mins>=13*60+30)&(mins<16*60+30)
        prev_up = f.close.shift(1) > f.ny_high.shift(1)
        prev_dn = f.close.shift(1) < f.ny_low.shift(1)
        lo = up & session & prev_up & (f.low <= f.ny_high) & (f.close > f.ny_high) & (f.close > f.open)
        sh = dn & session & prev_dn & (f.high >= f.ny_low) & (f.close < f.ny_low) & (f.close < f.open)

    elif c.family == "prev_day_retest":
        mins=f.mins
        session=((mins>=7*60)&(mins<11*60))|((mins>=12*60+30)&(mins<16*60+30))
        prev_up = f.close.shift(1) > f.prev_day_high.shift(1)
        prev_dn = f.close.shift(1) < f.prev_day_low.shift(1)
        lo = up & session & prev_up & (f.low <= f.prev_day_high) & (f.close > f.prev_day_high) & (f.close > f.open)
        sh = dn & session & prev_dn & (f.high >= f.prev_day_low) & (f.close < f.prev_day_low) & (f.close < f.open)

    else:
        raise ValueError(c.family)

    return (lo & volok).fillna(False), (sh & volok).fillna(False)


def build(f: pd.DataFrame, c: Card):
    lo, sh = signal_masks(f,c)
    rows=[]; last={1:-10**9,-1:-10**9}
    for i in np.flatnonzero((lo|sh).to_numpy()):
        d=1 if bool(lo.iat[i]) else -1
        if i-last[d] < c.cooldown:
            continue
        row=f.iloc[i]; a=float(row.atr14)
        if not np.isfinite(a) or a<=0:
            continue

        # Signal-candle structural stop: tighter than 5-8 bar swing, but still real.
        stop=float(row.low-0.05*a) if d==1 else float(row.high+0.05*a)
        entry=float(row.close)
        risk=(entry-stop) if d==1 else (stop-entry)
        if not np.isfinite(risk) or risk <= 0:
            continue
        # Reject pathological micro/tall stops.
        rr_atr=risk/a
        if rr_atr < 0.12 or rr_atr > 1.60:
            continue

        rows.append({
            "card":c.name,"signal_i":i,"signal_time":f.index[i],
            "signal_close_time":f.index[i]+pd.Timedelta(minutes=15),
            "direction":d,"stop":stop,"atr14":a,
            "adx":float(row.adx) if np.isfinite(row.adx) else np.nan,
            "vol_ratio":float(row.vol_ratio) if np.isfinite(row.vol_ratio) else np.nan,
        })
        last[d]=i
    return pd.DataFrame(rows)


def make_cards():
    cards=[]
    # Coarse, interpretable grid only. No year-specific parameters.
    for bias in ["align","h4"]:
        for adx in [18,22,26]:
            for wick in [1.2,1.8,2.5]:
                cards.append(Card(f"EMA20_REJ_{bias}_A{adx}_W{wick}", "ema20_rejection", bias, 10, adx, 0.25, wick, 0, 2))
                cards.append(Card(f"SWEEP10_{bias}_A{adx}_W{wick}", "sweep_continuation", bias, 10, adx, 0.25, wick, 0, 2))
        for adx in [18,22,26]:
            cards.append(Card(f"ENGULF_{bias}_A{adx}", "engulf_pullback", bias, 10, adx, 0.25, 1.5, 0, 2))
            for lb in [5,8,10,12,20]:
                cards.append(Card(f"RETEST{lb}_{bias}_A{adx}", "break_retest", bias, lb, adx, 0.25, 1.5, 0, 2))
            cards.append(Card(f"INSIDE_{bias}_A{adx}", "inside_break", bias, 10, adx, 0.35, 1.5, 0, 2))
            cards.append(Card(f"FVG_{bias}_A{adx}", "fvg_continuation", bias, 10, adx, 0.25, 1.5, 0, 2))
        for body in [0.35,0.5,0.7]:
            for vol in [0.0,1.15,1.35]:
                cards.append(Card(f"SQZ_{bias}_B{body}_V{vol}", "squeeze_break", bias, 10, 18, body, 1.5, vol, 2))
                cards.append(Card(f"MOM2_{bias}_B{body}_V{vol}", "two_bar_momentum", bias, 10, 18, body, 1.5, vol, 2))

    # Session/key-level retest techniques.
    for bias in ["align","h4","none"]:
        cards.append(Card(f"NY_RETEST_{bias}", "ny_or_retest", bias, 10, 18, 0.25, 1.5, 0, 8))
        cards.append(Card(f"PD_RETEST_{bias}", "prev_day_retest", bias, 10, 18, 0.25, 1.5, 0, 8))

    return cards


def strict_pass(row):
    return (
        row["win_rate_pct"] >= 60.0
        and row["max_drawdown_pct"] <= 25.0
        and row["min_month"] >= 8
        and row["positive_years"] == 4
        and row["pf_gt1_years"] == 4
    )


def run(data_path, output_dir):
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    raw=load_m5_csv(data_path)
    m5=raw[(raw.index>=pd.Timestamp("2016-01-01",tz="UTC"))&(raw.index<DEV_END)].copy()
    f=prep(m5)

    cards=make_cards()
    rows=[]; yearly_rows=[]; trade_cache={}
    for c in cards:
        ss=build(f,c)
        tr=replay(m5,ss)
        trade_cache[c.name]=tr
        ov=metrics(tr); ms=month_stats(tr); y=yearly(tr)
        rows.append({
            "strategy":c.name,"family":c.family,"bias":c.bias,
            "trades":ov["trades"],"win_rate_pct":ov["wr"],"expectancy_r":ov["expectancy_r"],"pf":ov["pf"],
            "max_drawdown_pct":ov["max_dd_pct"],"end_rm":ov["end_rm"],"return_pct":ov["return_pct"],
            **ms,
            "positive_years":int((y.expectancy_r>0).sum()),
            "pf_gt1_years":int((y.pf>1).sum()),
            "worst_year_exp_r":float(y.expectancy_r.min()),
            "worst_year_dd_pct":float(y.max_dd_pct.max()),
        })
        for rr in y.itertuples(index=False):
            yearly_rows.append({"strategy":c.name,**rr._asdict()})

    ranked=pd.DataFrame(rows)

    # Build portfolios only from cards that already show useful precision or stability.
    seed_names = ranked[
        ((ranked.win_rate_pct >= 38) & (ranked.expectancy_r > 0))
        | ((ranked.positive_years >= 3) & (ranked.win_rate_pct >= 32))
    ].sort_values(["positive_years","win_rate_pct","expectancy_r"],ascending=[False,False,False]).head(16).strategy.tolist()

    portfolios={}
    # Pair/triple top independent families; keeps search coarse.
    seed_cards={c.name:c for c in cards}
    family_best=[]
    for fam,g in ranked[ranked.strategy.isin(seed_names)].groupby("family"):
        if not g.empty:
            family_best.append(g.sort_values(["positive_years","win_rate_pct","expectancy_r"],ascending=[False,False,False]).iloc[0].strategy)
    family_best=family_best[:8]
    for i in range(len(family_best)):
        for j in range(i+1,len(family_best)):
            a,b=family_best[i],family_best[j]
            name=f"PAIR__{a}__{b}"
            portfolios[name]=combine_setups([build(f,seed_cards[a]),build(f,seed_cards[b])],name)
    # A few broad routers from top family representatives.
    if len(family_best)>=3:
        for k in [3,4,5]:
            if len(family_best)>=k:
                mem=family_best[:k]
                name=f"ROUTER_TOP{k}"
                portfolios[name]=combine_setups([build(f,seed_cards[x]) for x in mem],name)

    for name,ss in portfolios.items():
        tr=replay(m5,ss)
        trade_cache[name]=tr
        ov=metrics(tr); ms=month_stats(tr); y=yearly(tr)
        rows.append({
            "strategy":name,"family":"portfolio","bias":"mixed",
            "trades":ov["trades"],"win_rate_pct":ov["wr"],"expectancy_r":ov["expectancy_r"],"pf":ov["pf"],
            "max_drawdown_pct":ov["max_dd_pct"],"end_rm":ov["end_rm"],"return_pct":ov["return_pct"],
            **ms,
            "positive_years":int((y.expectancy_r>0).sum()),
            "pf_gt1_years":int((y.pf>1).sum()),
            "worst_year_exp_r":float(y.expectancy_r.min()),
            "worst_year_dd_pct":float(y.max_dd_pct.max()),
        })
        for rr in y.itertuples(index=False):
            yearly_rows.append({"strategy":name,**rr._asdict()})

    ranked=pd.DataFrame(rows)
    ranked["strict_pass"]=ranked.apply(strict_pass,axis=1)

    # Distance to user's hard target, for diagnostics only.
    ranked["wr_gap"]=np.maximum(0,60-ranked.win_rate_pct)
    ranked["dd_gap"]=np.maximum(0,ranked.max_drawdown_pct-25)
    ranked["freq_gap"]=np.maximum(0,8-ranked.min_month)
    ranked["year_gap"]=4-ranked.positive_years
    ranked["target_distance"]=ranked.wr_gap*3 + ranked.dd_gap + ranked.freq_gap*5 + ranked.year_gap*20

    ranked=ranked.sort_values(
        ["strict_pass","target_distance","positive_years","min_month","win_rate_pct","expectancy_r"],
        ascending=[False,True,False,False,False,False]
    )
    yd=pd.DataFrame(yearly_rows)
    ranked.to_csv(out/"ranked.csv",index=False)
    yd.to_csv(out/"yearly.csv",index=False)
    alltr=[tr.assign(strategy=name) for name,tr in trade_cache.items() if not tr.empty]
    if alltr:
        pd.concat(alltr,ignore_index=True).to_csv(out/"trades.csv",index=False)

    strict=ranked[ranked.strict_pass]
    lines=[
        "# Historical-First Strict Search — User Hard Constraints","",
        "Development: 2017-2020 only. 2021+ sealed.",
        "Hard constraints: fixed RR3, WR>=60%, max DD<=25%, minimum 8 trades EVERY month, profitable in each of 2017/2018/2019/2020.",
        "Execution: M15 signals, next-M5-open entry, real signal-candle structural SL + 0.05ATR buffer, one position at a time, same-M5 stop-first, 1bp round-trip cost.",
        "",
        f"Cards tested: {len(cards)}; portfolio combinations: {len(portfolios)}; strict passes: {len(strict)}.",
        "",
        "## Strict passes",""
    ]
    if strict.empty:
        lines.append("No candidate met all hard constraints.")
    else:
        lines += ["| Strategy | Trades | WR | ExpR | PF | DD | Avg/mo | Min/mo | Pos years | End RM |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for r in strict.itertuples(index=False):
            lines.append(f"| {r.strategy} | {r.trades} | {r.win_rate_pct:.2f}% | {r.expectancy_r:+.3f} | {r.pf:.2f} | {r.max_drawdown_pct:.2f}% | {r.avg_month:.2f} | {r.min_month} | {r.positive_years}/4 | RM{r.end_rm:.2f} |")

    lines += ["","## Closest candidates","",
              "| Strategy | Family | Trades | WR | ExpR | PF | DD | Avg/mo | Min/mo | Pos years | Target distance |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in ranked.head(20).itertuples(index=False):
        pf="∞" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
        lines.append(f"| {r.strategy} | {r.family} | {r.trades} | {r.win_rate_pct:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.max_drawdown_pct:.2f}% | {r.avg_month:.2f} | {r.min_month} | {r.positive_years}/4 | {r.target_distance:.1f} |")

    # Yearly details for strict passes or top 5 if none.
    detail_names = strict.strategy.tolist() if not strict.empty else ranked.head(5).strategy.tolist()
    for strategy in detail_names:
        lines += ["",f"## {strategy}","","| Year | Trades | WR | ExpR | PF | DD | RM100 -> |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for r in yd[yd.strategy==strategy].itertuples(index=False):
            pf="∞" if math.isinf(float(r.pf)) else f"{r.pf:.2f}"
            lines.append(f"| {r.year} | {r.trades} | {r.wr:.2f}% | {r.expectancy_r:+.3f} | {pf} | {r.max_dd_pct:.2f}% | RM{r.end_rm:.2f} |")

    report="\n".join(lines)+"\n"
    (out/"REPORT.md").write_text(report,encoding="utf-8")
    (out/"summary.json").write_text(json.dumps({
        "window":"2017-2020",
        "constraints":{"rr":3,"wr_min_pct":60,"max_dd_pct":25,"min_month":8,"positive_years_required":4},
        "cards_tested":len(cards),"portfolios_tested":len(portfolios),
        "strict_pass_count":int(len(strict)),
        "strict_passes":strict.replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records"),
        "closest":ranked.head(20).replace({np.nan:None,np.inf:None,-np.inf:None}).to_dict("records"),
    },indent=2),encoding="utf-8")
    print(report)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data",default="data/xauusd_m5_secondary_octafx_mt4.csv")
    p.add_argument("--output",default="reports/historical-first-strict-search")
    a=p.parse_args(); run(a.data,a.output)

if __name__=="__main__":
    main()
