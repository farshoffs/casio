from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json, math
import numpy as np
import pandas as pd

from .v3_core import _atr, _ema, _resample, load_m5_csv
from .v3_m5_engine import _align_completed


@dataclass(frozen=True)
class StructuralAPlusConfig:
    min_runway_r: float = 3.5
    retrace_fraction: float = 0.50
    retrace_bars: int = 6
    displacement_body_min: float = 0.50
    displacement_range_atr_min: float = 0.65
    stop_buffer_atr: float = 0.10
    min_stop_atr: float = 0.50
    cooldown_bars: int = 6
    max_hold_bars: int = 96
    management: str = "SCALE_25_2R_RUN4R"  # or FULL_3_5R
    round_trip_cost_bps: float = 1.0


TARGET = {
    "trades_per_30d": 8.0,
    "win_rate_low": 42.0,
    "win_rate_high": 50.0,
    "avg_win_r": 3.5,
    "expectancy_r": 0.70,
    "profit_factor": 2.0,
}


def _safe(x):
    if isinstance(x, dict): return {str(k): _safe(v) for k, v in x.items()}
    if isinstance(x, list): return [_safe(v) for v in x]
    if isinstance(x, (np.bool_, bool)): return bool(x)
    if isinstance(x, np.integer): return int(x)
    if isinstance(x, (np.floating, float)):
        v = float(x); return v if math.isfinite(v) else None
    if isinstance(x, pd.Timestamp): return x.isoformat()
    return x


def _confirmed_structure(frame: pd.DataFrame) -> pd.DataFrame:
    """Causal 5-bar fractal structure, available only after two confirming bars."""
    a = _atr(frame, 14)
    ph = frame.high.shift(2).where(frame.high.shift(2).eq(frame.high.rolling(5, min_periods=5).max()))
    pl = frame.low.shift(2).where(frame.low.shift(2).eq(frame.low.rolling(5, min_periods=5).min()))
    n = len(frame)
    last_ph = np.full(n, np.nan); prev_ph = np.full(n, np.nan)
    last_pl = np.full(n, np.nan); prev_pl = np.full(n, np.nan)
    eqh = np.full(n, np.nan); eql = np.full(n, np.nan); bias = np.zeros(n, dtype=np.int8)
    cph = pph = cpl = ppl = np.nan
    for i in range(n):
        if np.isfinite(ph.iat[i]): pph, cph = cph, float(ph.iat[i])
        if np.isfinite(pl.iat[i]): ppl, cpl = cpl, float(pl.iat[i])
        last_ph[i], prev_ph[i], last_pl[i], prev_pl[i] = cph, pph, cpl, ppl
        aa = float(a.iat[i]) if np.isfinite(a.iat[i]) else np.nan
        if np.isfinite(cph) and np.isfinite(pph) and np.isfinite(aa) and abs(cph-pph) <= .18*aa:
            eqh[i] = (cph+pph)/2
        if np.isfinite(cpl) and np.isfinite(ppl) and np.isfinite(aa) and abs(cpl-ppl) <= .18*aa:
            eql[i] = (cpl+ppl)/2
        if all(np.isfinite(v) for v in (cph,pph,cpl,ppl)):
            if cph > pph and cpl > ppl: bias[i] = 1
            elif cph < pph and cpl < ppl: bias[i] = -1
    return pd.DataFrame({
        "atr": a, "last_ph": last_ph, "last_pl": last_pl,
        "equal_high": eqh, "equal_low": eql, "structure_bias": bias,
    }, index=frame.index)


def prepare_structural_features(m5: pd.DataFrame) -> pd.DataFrame:
    f = m5.copy()
    f["m5_atr"] = _atr(m5, 14)
    f["m5_ema20"] = _ema(m5.close, 20)
    rng = (m5.high-m5.low).replace(0, np.nan)
    f["body_fraction"] = (m5.close-m5.open).abs()/rng
    f["close_location"] = (m5.close-m5.low)/rng
    f["range_atr"] = rng/f.m5_atr.replace(0, np.nan)
    f["prior_high5"] = m5.high.shift(1).rolling(5, min_periods=5).max()
    f["prior_low5"] = m5.low.shift(1).rolling(5, min_periods=5).min()
    f["recent_low8"] = m5.low.rolling(8, min_periods=8).min()
    f["recent_high8"] = m5.high.rolling(8, min_periods=8).max()

    for name, rule, delta in [("h1","1h",pd.Timedelta(hours=1)), ("h4","4h",pd.Timedelta(hours=4))]:
        h = _resample(m5, rule)
        s = _confirmed_structure(h).add_prefix(name+"_")
        f = f.join(_align_completed(s, m5.index, delta))

    m15 = _resample(m5, "15min")
    e20, e50 = _ema(m15.close,20), _ema(m15.close,50)
    m15f = pd.DataFrame(index=m15.index)
    m15f["m15_trend_long"] = (e20 > e50) & (m15.close > e20)
    m15f["m15_trend_short"] = (e20 < e50) & (m15.close < e20)
    f = f.join(_align_completed(m15f, m5.index, pd.Timedelta(minutes=15)))

    day = _resample(m5, "1D")
    d = pd.DataFrame({"prev_day_high":day.high, "prev_day_low":day.low}, index=day.index)
    f = f.join(_align_completed(d, m5.index, pd.Timedelta(days=1)))

    # Current day's Asia range becomes tradable information only from 06:00 UTC onward.
    asia_src = m5[m5.index.hour < 6]
    asia = asia_src.groupby(asia_src.index.floor("D")).agg(asia_high=("high","max"), asia_low=("low","min"))
    days = pd.Series(m5.index.floor("D"), index=m5.index)
    f["asia_high"] = days.map(asia.asia_high)
    f["asia_low"] = days.map(asia.asia_low)
    f.loc[m5.index.hour < 6, ["asia_high","asia_low"]] = np.nan
    return f


def _nearest_liquidity(row: pd.Series, direction: int, entry: float) -> tuple[float,str]:
    if direction == 1:
        levels = [("PDH",row.prev_day_high),("ASIA_H",row.asia_high),("H1_SWING_H",row.h1_last_ph),("EQUAL_H",row.h1_equal_high)]
        valid = [(n,float(v)) for n,v in levels if np.isfinite(v) and float(v) > entry]
        return min(valid, key=lambda x:x[1])[1::-1] if False else ((min(valid,key=lambda x:x[1])[1], min(valid,key=lambda x:x[1])[0]) if valid else (np.nan,"NONE"))
    levels = [("PDL",row.prev_day_low),("ASIA_L",row.asia_low),("H1_SWING_L",row.h1_last_pl),("EQUAL_L",row.h1_equal_low)]
    valid = [(n,float(v)) for n,v in levels if np.isfinite(v) and float(v) < entry]
    if not valid: return np.nan,"NONE"
    name, level = max(valid, key=lambda x:x[1]); return level,name


def setup_frame(f: pd.DataFrame, cfg: StructuralAPlusConfig) -> pd.DataFrame:
    idx = f.index
    london = (idx.hour >= 7) & (idx.hour < 11)
    long_structure = ((f.h4_structure_bias == 1) | (f.h1_structure_bias == 1)) & ~((f.h4_structure_bias == -1) & (f.h1_structure_bias == -1))
    short_structure = ((f.h4_structure_bias == -1) | (f.h1_structure_bias == -1)) & ~((f.h4_structure_bias == 1) & (f.h1_structure_bias == 1))
    disp_long = (f.close > f.open) & f.body_fraction.ge(cfg.displacement_body_min) & f.close_location.ge(.68) & f.range_atr.ge(cfg.displacement_range_atr_min) & (f.close > f.prior_high5)
    disp_short = (f.close < f.open) & f.body_fraction.ge(cfg.displacement_body_min) & f.close_location.le(.32) & f.range_atr.ge(cfg.displacement_range_atr_min) & (f.close < f.prior_low5)

    long_levels = ["prev_day_low","asia_low","h1_last_pl","h1_equal_low"]
    short_levels = ["prev_day_high","asia_high","h1_last_ph","h1_equal_high"]
    swl = pd.Series(False,index=idx); sws = pd.Series(False,index=idx)
    swl_level = pd.Series(np.nan,index=idx); sws_level = pd.Series(np.nan,index=idx)
    for c in long_levels:
        hit = (f.low < f[c]) & (f.close > f[c]); swl |= hit.fillna(False); swl_level = swl_level.where(~hit, f[c])
    for c in short_levels:
        hit = (f.high > f[c]) & (f.close < f[c]); sws |= hit.fillna(False); sws_level = sws_level.where(~hit, f[c])

    pb_long = ((f.low <= f.m5_ema20 + .20*f.m5_atr) & (f.close >= f.m5_ema20 - .25*f.m5_atr)).rolling(9,min_periods=1).max().astype(bool)
    pb_short = ((f.high >= f.m5_ema20 - .20*f.m5_atr) & (f.close <= f.m5_ema20 + .25*f.m5_atr)).rolling(9,min_periods=1).max().astype(bool)

    long_ok = london & disp_long & long_structure & (swl | (f.m15_trend_long.fillna(False) & pb_long))
    short_ok = london & disp_short & short_structure & (sws | (f.m15_trend_short.fillna(False) & pb_short))

    rows=[]; last={1:-999,-1:-999}
    for i in np.flatnonzero((long_ok|short_ok).to_numpy()):
        direction = 1 if bool(long_ok.iat[i]) else -1
        if i-last[direction] < cfg.cooldown_bars: continue
        last[direction] = i; row=f.iloc[i]
        candle_range=float(row.high-row.low)
        entry = float(row.high - cfg.retrace_fraction*candle_range) if direction==1 else float(row.low + cfg.retrace_fraction*candle_range)
        swept = bool(swl.iat[i] if direction==1 else sws.iat[i])
        if direction==1:
            base = float(swl_level.iat[i]) if swept and np.isfinite(swl_level.iat[i]) else float(row.recent_low8)
            stop = base - cfg.stop_buffer_atr*float(row.m5_atr); risk = entry-stop
        else:
            base = float(sws_level.iat[i]) if swept and np.isfinite(sws_level.iat[i]) else float(row.recent_high8)
            stop = base + cfg.stop_buffer_atr*float(row.m5_atr); risk = stop-entry
        if not np.isfinite(risk) or risk < cfg.min_stop_atr*float(row.m5_atr): continue
        liq, liq_name = _nearest_liquidity(row,direction,entry)
        if not np.isfinite(liq): continue
        runway = (liq-entry)/risk if direction==1 else (entry-liq)/risk
        if runway < cfg.min_runway_r: continue
        rows.append({
            "signal_i":i,"signal_time":idx[i],"direction":direction,"entry":entry,"stop":stop,"risk":risk,
            "runway_r":runway,"liquidity_target":liq,"liquidity_type":liq_name,"sweep":swept,
            "h4_structure":int(row.h4_structure_bias),"h1_structure":int(row.h1_structure_bias),
            "body_fraction":float(row.body_fraction),"range_atr":float(row.range_atr),
        })
    return pd.DataFrame(rows)


def replay(m5: pd.DataFrame, setups: pd.DataFrame, cfg: StructuralAPlusConfig) -> pd.DataFrame:
    if setups.empty: return pd.DataFrame()
    events=[]; next_free=-1
    for s in setups.sort_values("signal_i").itertuples(index=False):
        sig=int(s.signal_i)
        if sig < next_free: continue
        d=int(s.direction); ent=float(s.entry); stop=float(s.stop); risk=float(s.risk)
        fill=None
        for j in range(sig+1, min(len(m5),sig+1+cfg.retrace_bars)):
            lo,hi=float(m5.low.iat[j]),float(m5.high.iat[j])
            if (lo<=stop if d==1 else hi>=stop): break
            if lo<=ent<=hi: fill=j; break
        if fill is None: continue
        partial=False; cur_stop=stop; gross=None; reason=None; exit_i=None
        for j in range(fill+1,min(len(m5),fill+1+cfg.max_hold_bars)):
            lo,hi,cl=float(m5.low.iat[j]),float(m5.high.iat[j]),float(m5.close.iat[j]); elapsed=j-fill
            if cfg.management=="FULL_3_5R":
                tp=ent+d*3.5*risk; hs=lo<=stop if d==1 else hi>=stop; ht=hi>=tp if d==1 else lo<=tp
                if hs and ht: gross,reason=-1.,"stop_same_bar"
                elif hs: gross,reason=-1.,"stop"
                elif ht: gross,reason=3.5,"target_3_5r"
                elif elapsed>=cfg.max_hold_bars-1: gross,reason=(cl-ent)/risk*d,"time_exit"
                else: continue
            else:
                tp1=ent+d*2*risk; tp2=ent+d*4*risk
                hs=lo<=cur_stop if d==1 else hi>=cur_stop; h1=hi>=tp1 if d==1 else lo<=tp1; h2=hi>=tp2 if d==1 else lo<=tp2
                if not partial:
                    if hs and (h1 or h2): gross,reason=-1.,"stop_same_bar"
                    elif hs: gross,reason=-1.,"stop"
                    elif h2: gross,reason=3.5,"runner_4r"
                    elif h1: partial=True; cur_stop=ent; continue
                    elif elapsed>=cfg.max_hold_bars-1: gross,reason=(cl-ent)/risk*d,"time_exit"
                    else: continue
                else:
                    hsbe=lo<=ent if d==1 else hi>=ent
                    if hsbe and h2: gross,reason=.5,"be_same_bar"
                    elif hsbe: gross,reason=.5,"runner_be"
                    elif h2: gross,reason=3.5,"runner_4r"
                    elif elapsed>=cfg.max_hold_bars-1: gross,reason=.5+.75*((cl-ent)/risk*d),"partial_time_exit"
                    else: continue
            exit_i=j; break
        if gross is None: continue
        cost=(ent*cfg.round_trip_cost_bps/10000.0)/risk
        e=s._asdict(); e.update(entry_time=m5.index[fill]+pd.Timedelta(minutes=5), exit_time=m5.index[exit_i]+pd.Timedelta(minutes=5), gross_r=gross, net_r=gross-cost, reason=reason)
        events.append(e); next_free=exit_i+1
    return pd.DataFrame(events)


def metrics(tr: pd.DataFrame, a: pd.Timestamp, b: pd.Timestamp) -> dict:
    if tr.empty: return {"trades":0,"trades_per_30d":0.0}
    tt=pd.to_datetime(tr.entry_time,utc=True); r=pd.to_numeric(tr.loc[(tt>=a)&(tt<b),"net_r"],errors="coerce").dropna()
    if r.empty: return {"trades":0,"trades_per_30d":0.0}
    w=r[r>.05]; l=r[r<-.05]; curve=r.cumsum(); dd=curve.cummax()-curve; days=max((b-a).total_seconds()/86400,1e-9)
    return {
        "trades":int(len(r)),"trades_per_30d":float(len(r)*30/days),"win_rate":float(len(w)*100/len(r)),
        "avg_win_r":float(w.mean()) if len(w) else None,"avg_loss_r":float(-l.mean()) if len(l) else None,
        "expectancy_r":float(r.mean()),"profit_factor":float(w.sum()/(-l.sum())) if len(l) else 999.0,
        "max_drawdown_r":float(dd.max()) if len(dd) else 0.0,
    }


def target_score(m: dict) -> float:
    if m.get("trades",0) < 8: return -999.0
    tpm=float(m.get("trades_per_30d",0)); wr=float(m.get("win_rate",0)); aw=float(m.get("avg_win_r") or 0); ex=float(m.get("expectancy_r",-9)); pf=float(m.get("profit_factor",0))
    freq=min(tpm/TARGET["trades_per_30d"],1.0)
    wr_score=max(0.0,1-abs(wr-46.0)/20.0)
    return 1.2*ex + .35*min(pf/TARGET["profit_factor"],1.5) + .25*min(aw/TARGET["avg_win_r"],1.5) + .20*freq + .15*wr_score


def run(data_path: str|Path="data/xauusd_m5.csv", output_dir: str|Path="reports/v3-structural-aplus") -> dict:
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    m5=load_m5_csv(data_path); f=prepare_structural_features(m5)
    start=m5.index.min()+pd.Timedelta(days=30); finish=m5.index.max()+pd.Timedelta(minutes=5); cut=start+(finish-start)*.75
    rows=[]; cache={}
    for runway in [3.0,3.5,4.0]:
        for retrace_bars in [4,6,8]:
            for mgmt in ["FULL_3_5R","SCALE_25_2R_RUN4R"]:
                cfg=StructuralAPlusConfig(min_runway_r=runway,retrace_bars=retrace_bars,management=mgmt)
                setups=setup_frame(f,cfg); tr=replay(m5,setups,cfg)
                name=f"R{str(runway).replace('.','_')}_RB{retrace_bars}_{mgmt}"
                dev=metrics(tr,start,cut); val=metrics(tr,cut,finish)
                rows += [{"variant":name,"sample":"DEV","score":target_score(dev),**dev},{"variant":name,"sample":"VALIDATION","score":None,**val}]
                cache[name]=(cfg,setups,tr,dev,val)
    frame=pd.DataFrame(rows); frame.to_csv(out/"variant_metrics.csv",index=False)
    best=max(cache, key=lambda k: target_score(cache[k][3])); cfg,setups,tr,dev,val=cache[best]
    setups.to_csv(out/"best_setups.csv",index=False); tr.to_csv(out/"best_trades.csv",index=False)
    summary={
        "data":{"rows":len(m5),"start":m5.index.min(),"end":m5.index.max(),"dev_end":cut},
        "target":TARGET,"selected_on_development":best,"selected_config":cfg.__dict__,"development":dev,"validation":val,
        "target_met_development": bool(dev.get("trades_per_30d",0)>=8 and 42<=dev.get("win_rate",0)<=50 and (dev.get("avg_win_r") or 0)>=3.5 and dev.get("expectancy_r",-9)>=.7 and dev.get("profit_factor",0)>=2),
        "auto_deploy":False,
        "note":"Research only. Implements H4/H1 confirmed swing structure; PD/Asia/H1/equal-high-low liquidity; pullback/sweep; M5 displacement+micro-BOS; retracement entry; structural stop; liquidity runway; exceptional-R filter. Live CASIO remains unchanged. 2020 has already informed prior research and is not pristine OOS.",
    }
    (out/"summary.json").write_text(json.dumps(_safe(summary),indent=2),encoding="utf-8")
    (out/"REPORT.md").write_text("# CASIO Structural A+ Research\n\nTarget: `8 trades/month | 42-50% WR | 3.5R avg winner | +0.7R expectancy | PF 2+`\n\nSelected on DEV only: `"+best+"`\n\nDEV: `"+str(dev)+"`\n\nVALIDATION: `"+str(val)+"`\n\nNo live changes.\n",encoding="utf-8")
    print(json.dumps(_safe(summary),indent=2)); return summary


def main():
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("--data",default="data/xauusd_m5.csv"); p.add_argument("--output",default="reports/v3-structural-aplus"); a=p.parse_args(); run(a.data,a.output)

if __name__=="__main__": main()
