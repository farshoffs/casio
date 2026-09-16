from __future__ import annotations

from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .v3_asymmetry_challenger import prepare_asymmetry_features


MILESTONES = [2.0, 3.0, 3.5, 4.0, 5.0]


def _safe(x):
    if isinstance(x, dict): return {str(k): _safe(v) for k, v in x.items()}
    if isinstance(x, list): return [_safe(v) for v in x]
    if isinstance(x, (np.bool_, bool)): return bool(x)
    if isinstance(x, (np.integer,)): return int(x)
    if isinstance(x, (np.floating, float)):
        v = float(x); return v if math.isfinite(v) else None
    if isinstance(x, pd.Timestamp): return x.isoformat()
    return x


def _session(idx: pd.DatetimeIndex) -> np.ndarray:
    mins = idx.hour * 60 + idx.minute
    return np.select(
        [(mins >= 0) & (mins < 360), (mins >= 420) & (mins < 660), (mins >= 750) & (mins < 990)],
        ["ASIA", "LONDON", "NEW YORK"], default="TRANSITION",
    )


def _external_runway(entry: pd.Series, direction: pd.Series, risk: pd.Series, f: pd.DataFrame) -> pd.Series:
    e = entry.to_numpy(float)
    r = risk.to_numpy(float)
    d = direction.to_numpy(int)
    levels = np.column_stack([
        pd.to_numeric(f.prev_day_high, errors="coerce").to_numpy(float),
        pd.to_numeric(f.prev_day_low, errors="coerce").to_numpy(float),
        pd.to_numeric(f.h1_high20, errors="coerce").to_numpy(float),
        pd.to_numeric(f.h1_low20, errors="coerce").to_numpy(float),
        pd.to_numeric(f.m15_range_high30, errors="coerce").to_numpy(float),
        pd.to_numeric(f.m15_range_low30, errors="coerce").to_numpy(float),
    ])
    out = np.full(len(e), np.nan)
    for i in range(len(e)):
        if not np.isfinite(e[i]) or not np.isfinite(r[i]) or r[i] <= 0 or d[i] == 0:
            continue
        if d[i] == 1:
            valid = levels[i][levels[i] > e[i]]
            if len(valid): out[i] = (valid.min() - e[i]) / r[i]
        else:
            valid = levels[i][levels[i] < e[i]]
            if len(valid): out[i] = (e[i] - valid.max()) / r[i]
    return pd.Series(out, index=entry.index)


def candidate_frame(m5: pd.DataFrame) -> pd.DataFrame:
    f = prepare_asymmetry_features(m5)
    entry = f.close.astype(float)

    long_disp = (
        (f.close > f.open)
        & f.m5_body_fraction.ge(0.50)
        & f.m5_close_location.ge(0.68)
        & f.m5_range_atr.ge(0.65)
        & (f.close > f.m5_prior_high3)
    )
    short_disp = (
        (f.close < f.open)
        & f.m5_body_fraction.ge(0.50)
        & f.m5_close_location.le(0.32)
        & f.m5_range_atr.ge(0.65)
        & (f.close < f.m5_prior_low3)
    )

    pb_long = (
        (f.h4_bias.ne(-1) & f.h1_bias.ne(-1))
        & (f.h4_bias.eq(1) | f.h1_bias.eq(1))
        & f.m15_trend_long.fillna(False)
        & f.m5_long_pullback_age.le(8)
        & long_disp
    )
    pb_short = (
        (f.h4_bias.ne(1) & f.h1_bias.ne(1))
        & (f.h4_bias.eq(-1) | f.h1_bias.eq(-1))
        & f.m15_trend_short.fillna(False)
        & f.m5_short_pullback_age.le(8)
        & short_disp
    )
    sw_long = (
        f.m5_sell_sweep_age.le(4)
        & ~((f.h4_bias.eq(-1)) & (f.h1_bias.eq(-1)))
        & long_disp
    )
    sw_short = (
        f.m5_buy_sweep_age.le(4)
        & ~((f.h4_bias.eq(1)) & (f.h1_bias.eq(1)))
        & short_disp
    )

    direction = np.select([sw_long, sw_short, pb_long, pb_short], [1, -1, 1, -1], default=0)
    playbook = np.select(
        [sw_long | sw_short, pb_long | pb_short],
        ["LIQUIDITY_SWEEP", "PULLBACK_CONTINUATION"], default="NONE",
    )

    pb_long_risk = np.maximum(entry - (f.recent_low6 - f.m5_atr*0.10), f.m5_atr*0.50)
    pb_short_risk = np.maximum((f.recent_high6 + f.m5_atr*0.10) - entry, f.m5_atr*0.50)
    sw_long_risk = np.maximum(entry - (f.recent_low4 - f.m5_atr*0.10), f.m5_atr*0.50)
    sw_short_risk = np.maximum((f.recent_high4 + f.m5_atr*0.10) - entry, f.m5_atr*0.50)
    risk = pd.Series(np.select(
        [sw_long, sw_short, pb_long, pb_short],
        [sw_long_risk, sw_short_risk, pb_long_risk, pb_short_risk], default=np.nan,
    ).astype(float), index=f.index)
    direction_s = pd.Series(direction, index=f.index)

    both = ((f.h4_bias == direction_s) & (f.h1_bias == direction_s) & direction_s.ne(0))
    one = (((f.h4_bias == direction_s) | (f.h1_bias == direction_s)) & ~both & direction_s.ne(0))
    htf = np.select([both, one], ["BOTH_ALIGNED", "ONE_ALIGNED"], default="NEUTRAL")

    out = pd.DataFrame(index=f.index)
    out["candidate"] = direction_s.ne(0)
    out["direction"] = direction_s
    out["playbook"] = playbook
    out["entry"] = entry
    out["risk"] = risk
    out["session"] = _session(f.index)
    out["htf_alignment"] = htf
    out["efficiency"] = f.m5_efficiency12
    out["extension_atr"] = f.m5_extension_atr
    out["body_fraction"] = f.m5_body_fraction
    out["range_atr"] = f.m5_range_atr
    out["m15_adx"] = f.m15_adx
    out["runway_r"] = _external_runway(entry, direction_s, risk, f)

    out["eff_bin"] = pd.cut(out.efficiency, [-np.inf,.20,.35,.50,.70,np.inf], labels=["<.20",".20-.35",".35-.50",".50-.70",">.70"])
    out["ext_bin"] = pd.cut(out.extension_atr, [-np.inf,.50,.80,1.10,1.50,np.inf], labels=["<.50",".50-.80",".80-1.10","1.10-1.50",">1.50"])
    out["body_bin"] = pd.cut(out.body_fraction, [-np.inf,.55,.65,.75,np.inf], labels=["<.55",".55-.65",".65-.75",">.75"])
    out["runway_bin"] = pd.cut(out.runway_r, [-np.inf,2,3,4,5,np.inf], labels=["<2R","2-3R","3-4R","4-5R",">5R"])

    # Prevent a burst of nearly identical bars from dominating the study.
    keep = np.zeros(len(out), dtype=bool)
    last = {("LIQUIDITY_SWEEP",1):-999, ("LIQUIDITY_SWEEP",-1):-999,
            ("PULLBACK_CONTINUATION",1):-999, ("PULLBACK_CONTINUATION",-1):-999}
    for i, row in enumerate(out.itertuples()):
        if not row.candidate: continue
        key = (row.playbook, int(row.direction))
        if i - last[key] >= 6:
            keep[i] = True; last[key] = i
    out["candidate"] = out.candidate & keep
    return out


def evaluate_candidates(m5: pd.DataFrame, c: pd.DataFrame, horizon_bars: int = 72) -> pd.DataFrame:
    rows = []
    idx = m5.index
    for i in np.flatnonzero(c.candidate.to_numpy()):
        if i + 1 >= len(m5): continue
        row = c.iloc[i]
        risk = float(row.risk); entry = float(row.entry); direction = int(row.direction)
        if not np.isfinite(risk) or risk <= 0: continue
        stop = entry - risk if direction == 1 else entry + risk
        hit = {m: False for m in MILESTONES}
        mfe = 0.0; stop_hit = False; stop_bar = None
        end = min(len(m5), i + 1 + horizon_bars)
        for j in range(i+1, end):
            bar = m5.iloc[j]
            lo, hi = float(bar.low), float(bar.high)
            adverse = lo <= stop if direction == 1 else hi >= stop
            favorable_r = (hi-entry)/risk if direction == 1 else (entry-lo)/risk
            mfe = max(mfe, favorable_r)
            # Conservative same-bar ordering: if stop and a milestone are both touched, stop wins.
            if adverse:
                stop_hit = True; stop_bar = j; break
            for m in MILESTONES:
                if favorable_r >= m: hit[m] = True
        rows.append({
            "signal_time": idx[i], "playbook": row.playbook, "direction": direction,
            "session": row.session, "htf_alignment": row.htf_alignment,
            "efficiency": row.efficiency, "eff_bin": row.eff_bin,
            "extension_atr": row.extension_atr, "ext_bin": row.ext_bin,
            "body_fraction": row.body_fraction, "body_bin": row.body_bin,
            "range_atr": row.range_atr, "m15_adx": row.m15_adx,
            "runway_r": row.runway_r, "runway_bin": row.runway_bin,
            "risk": risk, "mfe_r_before_stop_or_horizon": mfe,
            "stop_hit": stop_hit, "bars_to_stop": (stop_bar-i) if stop_bar is not None else None,
            **{f"hit_{str(m).replace('.','_')}r_before_stop": hit[m] for m in MILESTONES},
        })
    return pd.DataFrame(rows)


def _summary(x: pd.DataFrame) -> dict:
    if x.empty: return {"n":0}
    result = {"n": int(len(x)), "median_mfe_r": float(x.mfe_r_before_stop_or_horizon.median()), "mean_mfe_r": float(x.mfe_r_before_stop_or_horizon.mean())}
    for m in MILESTONES:
        col = f"hit_{str(m).replace('.','_')}r_before_stop"
        result[f"hit_{m}r_pct"] = float(x[col].mean()*100)
    return result


def _group(df: pd.DataFrame, cols: list[str], min_n: int = 12) -> pd.DataFrame:
    rows = []
    for key, g in df.groupby(cols, observed=True, dropna=False):
        vals = key if isinstance(key, tuple) else (key,)
        if len(g) < min_n: continue
        row = dict(zip(cols, vals)); row.update(_summary(g)); rows.append(row)
    if not rows: return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["hit_3.0r_pct","hit_4.0r_pct","n"], ascending=[False,False,False])


def run(data_path: str | Path = "data/xauusd_m5.csv", output_dir: str | Path = "reports/v3-edge-map") -> dict:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    m5 = load_m5_csv(data_path)
    c = candidate_frame(m5)
    ev = evaluate_candidates(m5, c)

    start = m5.index.min() + pd.Timedelta(days=30)
    finish = m5.index.max() + pd.Timedelta(minutes=5)
    cutoff = start + (finish-start)*.75
    t = pd.to_datetime(ev.signal_time, utc=True)
    dev = ev[(t>=start)&(t<cutoff)].copy(); hold = ev[(t>=cutoff)&(t<finish)].copy()

    ev.to_csv(out/"all_candidates.csv", index=False)
    for name, cols in {
        "playbook_session": ["playbook","session"],
        "alignment_playbook": ["htf_alignment","playbook"],
        "efficiency_playbook": ["eff_bin","playbook"],
        "extension_playbook": ["ext_bin","playbook"],
        "runway_playbook": ["runway_bin","playbook"],
        "body_playbook": ["body_bin","playbook"],
        "session_alignment_playbook": ["session","htf_alignment","playbook"],
    }.items():
        _group(dev, cols).to_csv(out/f"dev_{name}.csv", index=False)
        _group(hold, cols).to_csv(out/f"holdout_{name}.csv", index=False)

    # Multi-factor cells: only report cells with enough observations; never optimize on holdout.
    dev_cells = _group(dev, ["playbook","session","htf_alignment","eff_bin","ext_bin"], min_n=8)
    dev_cells.to_csv(out/"dev_multifactor_cells.csv", index=False)

    summary = {
        "data": {"rows":len(m5), "start":m5.index.min(), "end":m5.index.max(), "dev_end":cutoff},
        "development": _summary(dev), "holdout": _summary(hold),
        "dev_candidates": len(dev), "holdout_candidates": len(hold),
        "note": "Diagnostic edge map only. Milestones are first-passage outcomes before a structural 1R stop, with stop-first ordering on ambiguous bars. Not a deployable strategy.",
    }
    (out/"summary.json").write_text(json.dumps(_safe(summary), indent=2), encoding="utf-8")
    (out/"REPORT.md").write_text(
        "# CASIO High-Asymmetry Edge Map\n\n"
        f"Coverage: {m5.index.min().isoformat()} -> {m5.index.max().isoformat()} ({len(m5):,} M5 rows)\n\n"
        f"Development candidates: {len(dev):,}; Holdout candidates: {len(hold):,}\n\n"
        f"Development: `{_summary(dev)}`\n\nHoldout: `{_summary(hold)}`\n\n"
        "This is a setup-potential study, not a backtest or live model.\n",
        encoding="utf-8",
    )
    return summary


def main():
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("--data",default="data/xauusd_m5.csv"); p.add_argument("--output",default="reports/v3-edge-map"); a=p.parse_args()
    print(json.dumps(_safe(run(a.data,a.output)),indent=2))


if __name__ == "__main__": main()
