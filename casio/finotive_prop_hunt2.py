from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

from .v3_core import load_m5_csv, _atr, _resample


START_BALANCE = 2500.0
TARGET_R = 3.0
RISKS = (0.004, 0.005)


@dataclass(frozen=True)
class HuntConfig:
    target_r: float = 3.0
    cost_bps: float = 1.0
    max_hold_bars: int = 144
    min_risk_atr: float = 0.30
    max_risk_atr: float = 2.50


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def _align_closed(ctx: pd.DataFrame, index: pd.DatetimeIndex, delta: pd.Timedelta) -> pd.DataFrame:
    x = ctx.copy()
    x.index = x.index + delta
    return x.reindex(index, method="ffill")


def features(m5: pd.DataFrame) -> pd.DataFrame:
    f = m5.copy()
    f["atr"] = _atr(m5, 14)
    f["e20"] = _ema(f.close, 20)
    f["e50"] = _ema(f.close, 50)
    f["vol_med20"] = f.volume.shift(1).rolling(20, min_periods=20).median()
    f["vol_ratio"] = f.volume / f.vol_med20.replace(0, np.nan)
    cr = (f.high - f.low).replace(0, np.nan)
    f["body_frac"] = (f.close - f.open).abs() / cr
    f["close_loc"] = (f.close - f.low) / cr
    f["range_atr"] = cr / f.atr.replace(0, np.nan)
    f["prior_hi12"] = f.high.shift(1).rolling(12, min_periods=12).max()
    f["prior_lo12"] = f.low.shift(1).rolling(12, min_periods=12).min()
    f["prior_hi24"] = f.high.shift(1).rolling(24, min_periods=24).max()
    f["prior_lo24"] = f.low.shift(1).rolling(24, min_periods=24).min()
    f["recent_lo5"] = f.low.rolling(5, min_periods=5).min()
    f["recent_hi5"] = f.high.rolling(5, min_periods=5).max()
    f["recent_lo8"] = f.low.rolling(8, min_periods=8).min()
    f["recent_hi8"] = f.high.rolling(8, min_periods=8).max()

    m15 = _resample(m5, "15min")
    m15c = pd.DataFrame(index=m15.index)
    m15c["m15_e20"] = _ema(m15.close, 20)
    m15c["m15_e50"] = _ema(m15.close, 50)
    m15c["m15_close"] = m15.close
    m15c["m15_atr"] = _atr(m15, 14)
    f = f.join(_align_closed(m15c, f.index, pd.Timedelta(minutes=15)))

    h1 = _resample(m5, "1h")
    h1c = pd.DataFrame(index=h1.index)
    h1c["h1_e20"] = _ema(h1.close, 20)
    h1c["h1_e50"] = _ema(h1.close, 50)
    h1c["h1_close"] = h1.close
    h1c["h1_atr"] = _atr(h1, 14)
    f = f.join(_align_closed(h1c, f.index, pd.Timedelta(hours=1)))

    d = _resample(m5, "1D")
    dctx = pd.DataFrame({"prev_day_high": d.high, "prev_day_low": d.low}, index=d.index)
    f = f.join(_align_closed(dctx, f.index, pd.Timedelta(days=1)))

    day = f.index.floor("D")
    asia_src = f[f.index.hour < 6]
    asia = asia_src.groupby(asia_src.index.floor("D")).agg(asia_high=("high","max"), asia_low=("low","min"))
    ds = pd.Series(day, index=f.index)
    f["asia_high"] = ds.map(asia.asia_high)
    f["asia_low"] = ds.map(asia.asia_low)
    f.loc[f.index.hour < 6, ["asia_high","asia_low"]] = np.nan

    lon = f.index.tz_convert("Europe/London")
    ny = f.index.tz_convert("America/New_York")
    f["london"] = (lon.hour >= 8) & (lon.hour < 12)
    nymins = ny.hour * 60 + ny.minute
    f["new_york"] = (nymins >= 8*60+30) & (nymins < 12*60+30)
    f["primary"] = f.london | f.new_york

    f["h1_long"] = (f.h1_e20 > f.h1_e50) & (f.h1_close > f.h1_e20)
    f["h1_short"] = (f.h1_e20 < f.h1_e50) & (f.h1_close < f.h1_e20)
    f["m15_long"] = (f.m15_e20 > f.m15_e50) & (f.m15_close > f.m15_e20)
    f["m15_short"] = (f.m15_e20 < f.m15_e50) & (f.m15_close < f.m15_e20)
    return f


def _rows(f: pd.DataFrame, mask_l: pd.Series, mask_s: pd.Series, name: str, recent: int = 8, cfg: HuntConfig | None = None) -> pd.DataFrame:
    cfg = cfg or HuntConfig()
    rows = []
    for i in np.flatnonzero((mask_l.fillna(False) | mask_s.fillna(False)).to_numpy()):
        if i + 1 >= len(f):
            continue
        d = 1 if bool(mask_l.iat[i]) and not bool(mask_s.iat[i]) else -1 if bool(mask_s.iat[i]) and not bool(mask_l.iat[i]) else 0
        if not d:
            continue
        row = f.iloc[i]
        atr = float(row.atr)
        if not np.isfinite(atr) or atr <= 0:
            continue
        entry = float(row.close)
        if recent == 5:
            stop = float(row.recent_lo5) - 0.08*atr if d == 1 else float(row.recent_hi5) + 0.08*atr
        else:
            stop = float(row.recent_lo8) - 0.08*atr if d == 1 else float(row.recent_hi8) + 0.08*atr
        risk = abs(entry - stop)
        ratr = risk / atr
        if not np.isfinite(risk) or risk <= 0 or not (cfg.min_risk_atr <= ratr <= cfg.max_risk_atr):
            continue
        rows.append({
            "signal_i": i, "signal_time": f.index[i], "direction": d, "engine": name,
            "entry_ref": entry, "stop_ref": stop, "risk_ref": risk, "risk_atr": ratr,
        })
    return pd.DataFrame(rows)


def engines(f: pd.DataFrame) -> dict[str, pd.DataFrame]:
    bull = (f.close > f.open)
    bear = (f.close < f.open)

    # 1) MTF EMA pullback/rejection during active sessions.
    pb_l = f.primary & f.h1_long & f.m15_long & (f.low <= f.e20) & (f.close > f.e20) & bull & f.body_frac.ge(.42)
    pb_s = f.primary & f.h1_short & f.m15_short & (f.high >= f.e20) & (f.close < f.e20) & bear & f.body_frac.ge(.42)

    # 2) Tick-volume momentum continuation. Breakout plus unusually active M5 bar.
    vol_l = f.primary & f.h1_long & f.m15_long & bull & f.body_frac.ge(.55) & f.close_loc.ge(.70) & f.range_atr.ge(.75) & f.vol_ratio.ge(1.20) & (f.close > f.prior_hi12)
    vol_s = f.primary & f.h1_short & f.m15_short & bear & f.body_frac.ge(.55) & f.close_loc.le(.30) & f.range_atr.ge(.75) & f.vol_ratio.ge(1.20) & (f.close < f.prior_lo12)

    # 3) Stronger 24-bar momentum, looser volume; designed to add independent trend days.
    mom_l = f.primary & f.h1_long & bull & f.body_frac.ge(.60) & f.close_loc.ge(.75) & f.range_atr.ge(.90) & f.vol_ratio.ge(1.05) & (f.close > f.prior_hi24)
    mom_s = f.primary & f.h1_short & bear & f.body_frac.ge(.60) & f.close_loc.le(.25) & f.range_atr.ge(.90) & f.vol_ratio.ge(1.05) & (f.close < f.prior_lo24)

    # 4) Asia range liquidity sweep/reclaim, traded during London.
    as_l = f.london & f.asia_low.notna() & (f.low < f.asia_low) & (f.close > f.asia_low) & (~f.h1_short) & bull & f.body_frac.ge(.30)
    as_s = f.london & f.asia_high.notna() & (f.high > f.asia_high) & (f.close < f.asia_high) & (~f.h1_long) & bear & f.body_frac.ge(.30)

    # 5) Previous-day liquidity sweep/reclaim during either primary session.
    pd_l = f.primary & f.prev_day_low.notna() & (f.low < f.prev_day_low) & (f.close > f.prev_day_low) & (~f.h1_short) & bull & f.body_frac.ge(.30)
    pd_s = f.primary & f.prev_day_high.notna() & (f.high > f.prev_day_high) & (f.close < f.prev_day_high) & (~f.h1_long) & bear & f.body_frac.ge(.30)

    # 6) Session breakout continuation: Asia breakout in H1 direction with displacement.
    br_l = f.london & f.h1_long & f.asia_high.notna() & (f.close > f.asia_high) & (f.close.shift(1) <= f.asia_high.shift(1)) & bull & f.body_frac.ge(.50) & f.range_atr.ge(.70)
    br_s = f.london & f.h1_short & f.asia_low.notna() & (f.close < f.asia_low) & (f.close.shift(1) >= f.asia_low.shift(1)) & bear & f.body_frac.ge(.50) & f.range_atr.ge(.70)

    return {
        "EMA_PULLBACK": _rows(f, pb_l, pb_s, "EMA_PULLBACK", 8),
        "VOL_CONT": _rows(f, vol_l, vol_s, "VOL_CONT", 5),
        "MOM24": _rows(f, mom_l, mom_s, "MOM24", 5),
        "ASIA_SWEEP": _rows(f, as_l, as_s, "ASIA_SWEEP", 5),
        "PD_SWEEP": _rows(f, pd_l, pd_s, "PD_SWEEP", 5),
        "ASIA_BREAK": _rows(f, br_l, br_s, "ASIA_BREAK", 5),
    }


def _combine(parts: list[pd.DataFrame]) -> pd.DataFrame:
    xs = [x for x in parts if x is not None and not x.empty]
    if not xs:
        return pd.DataFrame()
    x = pd.concat(xs, ignore_index=True).sort_values(["signal_i","engine"])
    x = x.drop_duplicates(["signal_i","direction"], keep="first")
    return x.reset_index(drop=True)


def replay(f: pd.DataFrame, setups: pd.DataFrame, cfg: HuntConfig | None = None) -> pd.DataFrame:
    cfg = cfg or HuntConfig()
    if setups.empty:
        return pd.DataFrame()
    events = []
    next_free = -1
    for s in setups.sort_values("signal_i").itertuples(index=False):
        sig = int(s.signal_i)
        fill = sig + 1
        if fill < next_free or fill >= len(f):
            continue
        d = int(s.direction)
        entry = float(f.open.iat[fill])
        ref_stop = float(s.stop_ref)
        atr = float(f.atr.iat[sig])
        # If next-open gaps beyond the reference stop, skip rather than assume a magical fill.
        if (d == 1 and entry <= ref_stop) or (d == -1 and entry >= ref_stop):
            continue
        stop = ref_stop
        risk = abs(entry - stop)
        ratr = risk / atr if atr > 0 else np.nan
        if not np.isfinite(ratr) or not (cfg.min_risk_atr <= ratr <= cfg.max_risk_atr):
            continue
        target = entry + d * cfg.target_r * risk
        end = min(len(f), fill + 1 + cfg.max_hold_bars)
        result = None
        reason = None
        exit_i = None
        for j in range(fill, end):
            lo = float(f.low.iat[j]); hi = float(f.high.iat[j]); close = float(f.close.iat[j])
            hs = lo <= stop if d == 1 else hi >= stop
            ht = hi >= target if d == 1 else lo <= target
            if hs and ht:
                result, reason = -1.0, "stop_same_bar"
            elif hs:
                result, reason = -1.0, "stop"
            elif ht:
                result, reason = cfg.target_r, "target"
            elif j == end - 1:
                result, reason = (close-entry)/risk*d, "time_exit"
            else:
                continue
            exit_i = j
            break
        if result is None:
            continue
        cost_r = (entry * cfg.cost_bps / 10000.0) / risk
        events.append({
            "engine": s.engine, "entry_time": f.index[fill] + pd.Timedelta(minutes=5),
            "exit_time": f.index[exit_i] + pd.Timedelta(minutes=5), "direction": d,
            "entry": entry, "stop": stop, "target": target, "gross_r": result,
            "net_r": result - cost_r, "reason": reason,
        })
        next_free = exit_i + 1
    return pd.DataFrame(events)


def _month(trades: pd.DataFrame, a: pd.Timestamp, b: pd.Timestamp, risk: float) -> dict:
    if trades.empty:
        x = trades.copy()
    else:
        t = pd.to_datetime(trades.entry_time, utc=True)
        x = trades[(t >= a) & (t < b)].sort_values("entry_time").copy()
    eq = START_BALANCE
    peak = eq
    maxdd = 0.0
    loss_streak = max_streak = 0
    wins = losses = 0
    daily = {}
    for r in x.itertuples(index=False):
        day = pd.Timestamp(r.entry_time).floor("D")
        daily.setdefault(day, {"start":eq,"pnl":0.0})
        pnl = eq * risk * float(r.net_r)
        eq += pnl
        daily[day]["pnl"] += pnl
        peak = max(peak, eq)
        maxdd = max(maxdd, (peak-eq)/peak*100.0)
        if r.net_r > .05:
            wins += 1; loss_streak = 0
        elif r.net_r < -.05:
            losses += 1; loss_streak += 1; max_streak = max(max_streak,loss_streak)
    dailyp = [v["pnl"]/v["start"]*100 for v in daily.values()]
    profdays = sum(v["pnl"]/START_BALANCE*100 >= .5 for v in daily.values())
    ret = (eq/START_BALANCE-1)*100
    worstday = min(dailyp) if dailyp else 0.0
    breach = maxdd >= 6.0 or worstday <= -3.0
    return {
        "month":a.strftime("%Y-%m"),"trades":len(x),"wins":wins,"losses":losses,
        "win_rate":wins/max(1,len(x))*100,"return_pct":ret,"max_dd_pct":maxdd,
        "worst_daily_pct":worstday,"max_loss_streak":max_streak,
        "profitable_days_0_5":profdays,"hard_breach":breach,
        "passes_8pct":ret>=8.0 and not breach,
    }


def run(data_path: str|Path, output_dir: str|Path) -> dict:
    out = Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    m5 = load_m5_csv(data_path)
    f = features(m5)
    e = engines(f)

    portfolios = {
        **e,
        "TREND_CORE": _combine([e["EMA_PULLBACK"],e["VOL_CONT"],e["MOM24"]]),
        "LIQ_CORE": _combine([e["ASIA_SWEEP"],e["PD_SWEEP"],e["ASIA_BREAK"]]),
        "TREND_LIQ": _combine([e["EMA_PULLBACK"],e["VOL_CONT"],e["ASIA_SWEEP"],e["PD_SWEEP"]]),
        "ALL_6": _combine(list(e.values())),
        "VOL_MOM_SWEEP": _combine([e["VOL_CONT"],e["MOM24"],e["ASIA_SWEEP"],e["PD_SWEEP"]]),
        "PB_BREAK_SWEEP": _combine([e["EMA_PULLBACK"],e["ASIA_BREAK"],e["ASIA_SWEEP"],e["PD_SWEEP"]]),
    }

    end = m5.index.max()+pd.Timedelta(minutes=5)
    cur = end.floor("D").replace(day=1)
    starts = list(pd.date_range(pd.Timestamp("2026-01-01",tz="UTC"),cur,freq="MS",inclusive="left"))

    allm=[]; ranks=[]; trade_cache={}
    for name,setups in portfolios.items():
        tr = replay(f,setups)
        trade_cache[name]=tr
        for risk in RISKS:
            rows=[]
            for a in starts:
                mm=_month(tr,a,a+pd.offsets.MonthBegin(1),risk); rows.append(mm)
                allm.append({"candidate":name,"risk_pct":risk*100,"complete_month":True,**mm})
            part=_month(tr,cur,end,risk)
            allm.append({"candidate":name,"risk_pct":risk*100,"complete_month":False,**part})
            rets=[x["return_pct"] for x in rows]
            ranks.append({
                "candidate":name,"risk_pct":risk*100,"months_tested":len(rows),
                "months_ge_8pct":sum(x["passes_8pct"] for x in rows),
                "breach_months":sum(x["hard_breach"] for x in rows),
                "worst_month_pct":min(rets),"avg_month_pct":float(np.mean(rets)),
                "median_month_pct":float(np.median(rets)),"best_month_pct":max(rets),
                "avg_trades_month":float(np.mean([x["trades"] for x in rows])),
                "aggregate_wr":sum(x["wins"] for x in rows)/max(1,sum(x["trades"] for x in rows))*100,
                "worst_month_dd_pct":max(x["max_dd_pct"] for x in rows),
                "worst_daily_pct":min(x["worst_daily_pct"] for x in rows),
                "max_loss_streak":max(x["max_loss_streak"] for x in rows),
                "all_months_pass":all(x["passes_8pct"] for x in rows),
                "sep_partial_return_pct":part["return_pct"],"sep_partial_trades":part["trades"],
            })

    mf=pd.DataFrame(allm)
    rf=pd.DataFrame(ranks).sort_values(
        ["all_months_pass","months_ge_8pct","breach_months","worst_month_pct","avg_month_pct"],
        ascending=[False,False,True,False,False]).reset_index(drop=True)
    mf.to_csv(out/"monthly_results.csv",index=False)
    rf.to_csv(out/"ranking.csv",index=False)
    for n,tr in trade_cache.items():
        tr.to_csv(out/f"trades_{n}.csv",index=False)

    top=rf.head(12)
    best=top.iloc[0].to_dict() if len(top) else None
    summary={"data_start":m5.index.min().isoformat(),"data_end":m5.index.max().isoformat(),
             "completed_months":[x.strftime("%Y-%m") for x in starts],
             "candidate_count":len(portfolios),"best":best,
             "accepted_count":int(rf.all_months_pass.sum())}
    (out/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")

    lines=["# Finotive Prop Hunt 2","","New independent engines: EMA pullback, tick-volume continuation, 24-bar momentum, Asia sweep, previous-day sweep, Asia breakout, plus portfolios.","",
           "Acceptance: every completed 2026 month >=8%, risk 0.4/0.5%, fixed 3R, one active trade, real SL, no BE.","",
           f"Accepted: **{summary['accepted_count']}**","","## Ranking","~~~text",top.to_string(index=False),"~~~",""]
    if best:
        n=str(best["candidate"]); rp=float(best["risk_pct"])
        wm=mf[(mf.candidate==n)&(mf.risk_pct==rp)].sort_values("month")
        lines += [f"## Best: {n} @ {rp:.1f}%","~~~text",wm[["month","complete_month","trades","win_rate","return_pct","max_dd_pct","worst_daily_pct","max_loss_streak","profitable_days_0_5","hard_breach","passes_8pct"]].to_string(index=False),"~~~"]
    report="\n".join(lines)
    (out/"REPORT.md").write_text(report,encoding="utf-8")
    print(report)
    return summary


def main():
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("--data",required=True); p.add_argument("--output",default="reports/finotive-prop-hunt2")
    a=p.parse_args(); run(a.data,a.output)


if __name__=="__main__":
    main()
