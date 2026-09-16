from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .v3_m5_engine import V3M5Config, prepare_m5_features, replay_execution, signals_for_m5_features


def metrics(trades: pd.DataFrame, start: pd.Timestamp | None = None, end: pd.Timestamp | None = None) -> dict:
    x = trades.copy()
    if not x.empty and start is not None:
        x = x[pd.to_datetime(x["entry_time"], utc=True) >= start]
    if not x.empty and end is not None:
        x = x[pd.to_datetime(x["entry_time"], utc=True) < end]
    r = pd.to_numeric(x.get("net_r", pd.Series(dtype=float)), errors="coerce").dropna()
    if r.empty:
        return {"trades": 0, "wins": 0, "losses": 0, "win_rate": None, "expectancy_r": None,
                "profit_factor": None, "max_drawdown_r": None, "avg_win_r": None,
                "avg_loss_r": None, "payoff_ratio": None, "trades_per_30d": None}
    wins, losses = r[r > 0], r[r < 0]
    gw, gl = float(wins.sum()), float(-losses.sum())
    pf = gw / gl if gl > 0 else (999.0 if gw > 0 else None)
    curve = r.cumsum()
    dd = curve.cummax() - curve
    aw = float(wins.mean()) if len(wins) else None
    al = float(-losses.mean()) if len(losses) else None
    days = ((end - start).total_seconds() / 86400) if start is not None and end is not None else None
    return {
        "trades": int(len(r)), "wins": int(len(wins)), "losses": int(len(losses)),
        "win_rate": float(len(wins) * 100 / len(r)), "expectancy_r": float(r.mean()),
        "profit_factor": float(pf) if pf is not None else None,
        "max_drawdown_r": float(dd.max()) if len(dd) else 0.0,
        "avg_win_r": aw, "avg_loss_r": al,
        "payoff_ratio": (aw / al) if aw is not None and al not in (None, 0) else None,
        "trades_per_30d": float(len(r) * 30 / days) if days and days > 0 else None,
    }


def configs(base: V3M5Config) -> list[tuple[str, V3M5Config]]:
    """Curated quality experiments. Live defaults are never changed here."""
    rows: list[tuple[str, V3M5Config]] = [("baseline", base)]
    rows += [(f"primary_score_{v}", replace(base, m5_trend_min_score_primary=v)) for v in [68, 70, 72, 75]]
    rows += [(f"other_score_{v}", replace(base, m5_trend_min_score_other=v)) for v in [78, 80, 82, 85]]
    rows += [(f"adx_{v}", replace(base, m5_trend_min_adx=float(v))) for v in [18, 20, 22]]
    rows += [
        ("rsi_53_47", replace(base, m5_rsi_long=53, m5_rsi_short=47)),
        ("rsi_54_46", replace(base, m5_rsi_long=54, m5_rsi_short=46)),
        ("rsi_55_45", replace(base, m5_rsi_long=55, m5_rsi_short=45)),
    ]
    rows += [(f"range_rr_{v:.1f}", replace(base, m5_range_min_rr=v)) for v in [1.3, 1.4, 1.5]]
    rows += [
        ("range_edge_025", replace(base, range_edge_fraction=0.25)),
        ("trend_only", replace(base, enable_m5_range=False)),
        ("m5_only", replace(base, enable_classic=False)),
        ("m5_trend_only", replace(base, enable_classic=False, enable_m5_range=False)),
    ]
    rows += [
        ("quality_70_80_adx18", replace(base, m5_trend_min_score_primary=70, m5_trend_min_score_other=80, m5_trend_min_adx=18)),
        ("quality_70_80_rsi54", replace(base, m5_trend_min_score_primary=70, m5_trend_min_score_other=80, m5_rsi_long=54, m5_rsi_short=46)),
        ("quality_70_80_adx18_rsi54", replace(base, m5_trend_min_score_primary=70, m5_trend_min_score_other=80, m5_trend_min_adx=18, m5_rsi_long=54, m5_rsi_short=46)),
        ("quality_72_82_adx18_rsi54", replace(base, m5_trend_min_score_primary=72, m5_trend_min_score_other=82, m5_trend_min_adx=18, m5_rsi_long=54, m5_rsi_short=46)),
        ("quality_70_80_adx20_rsi54", replace(base, m5_trend_min_score_primary=70, m5_trend_min_score_other=80, m5_trend_min_adx=20, m5_rsi_long=54, m5_rsi_short=46)),
        ("quality_70_80_adx18_range13", replace(base, m5_trend_min_score_primary=70, m5_trend_min_score_other=80, m5_trend_min_adx=18, m5_range_min_rr=1.3)),
    ]
    return rows


def _slice(trades: pd.DataFrame, a: pd.Timestamp, b: pd.Timestamp) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    t = pd.to_datetime(trades["entry_time"], utc=True)
    return trades[(t >= a) & (t < b)].copy()


def _safe(x):
    if isinstance(x, dict):
        return {str(k): _safe(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_safe(v) for v in x]
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        v = float(x)
        return v if math.isfinite(v) else None
    if isinstance(x, pd.Timestamp):
        return x.isoformat()
    return x


def _group_rows(trades: pd.DataFrame, sample: str, cols: list[str]) -> list[dict]:
    if trades.empty:
        return []
    out = []
    for key, group in trades.groupby(cols, dropna=False):
        values = key if isinstance(key, tuple) else (key,)
        row = {"sample": sample}
        row.update(dict(zip(cols, values)))
        row.update(metrics(group))
        out.append(row)
    return out


def run_tuning(data_path: str | Path = "data/xauusd_m5.csv",
               output_dir: str | Path = "reports/v3-m5-tuning",
               holdout_fraction: float = 0.25) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    m5 = load_m5_csv(data_path)
    features = prepare_m5_features(m5)
    base = V3M5Config()

    start = features.index.min() + pd.Timedelta(days=30)
    finish = features.index.max() + pd.Timedelta(minutes=5)
    cutoff = start + (finish - start) * (1 - holdout_fraction)
    dev_span = cutoff - start
    folds = [(start + dev_span*a, start + dev_span*b) for a, b in [(0, .34), (.34, .67), (.67, 1)]]

    candidates = []
    trade_cache: dict[str, pd.DataFrame] = {}
    for name, cfg in configs(base):
        raw = signals_for_m5_features(features, cfg)
        trades = replay_execution(m5, raw, cfg)
        trade_cache[name] = trades
        dev = _slice(trades, start, cutoff)
        m = metrics(dev, start, cutoff)
        fold_m = [metrics(_slice(trades, a, b), a, b) for a, b in folds]
        positive_slices = sum((x["expectancy_r"] if x["expectancy_r"] is not None else -999) > 0 for x in fold_m) / 3
        candidates.append({
            "variant": name, **asdict(cfg), **m,
            "positive_dev_slice_ratio": positive_slices,
            "slice_expectancy_1": fold_m[0]["expectancy_r"],
            "slice_expectancy_2": fold_m[1]["expectancy_r"],
            "slice_expectancy_3": fold_m[2]["expectancy_r"],
        })

    frame = pd.DataFrame(candidates)
    base_row = frame[frame.variant.eq("baseline")].iloc[0]
    min_trades = max(30, int(float(base_row.trades) * .60))

    eligible = frame[
        frame.trades.ge(min_trades)
        & frame.expectancy_r.fillna(-999).gt(0)
        & frame.profit_factor.fillna(0).ge(1.15)
        & frame.positive_dev_slice_ratio.ge(2/3)
    ].copy()

    if len(eligible) and pd.notna(base_row.expectancy_r) and base_row.expectancy_r > 0:
        guarded = eligible[eligible.expectancy_r.ge(base_row.expectancy_r * .90)]
        if len(guarded):
            eligible = guarded
    if len(eligible) and pd.notna(base_row.profit_factor) and base_row.profit_factor > 1:
        guarded = eligible[eligible.profit_factor.ge(base_row.profit_factor * .80)]
        if len(guarded):
            eligible = guarded

    if len(eligible):
        eligible = eligible.sort_values(["win_rate", "expectancy_r", "profit_factor", "max_drawdown_r"],
                                        ascending=[False, False, False, True])
        selected = str(eligible.iloc[0].variant)
    else:
        selected = "baseline"

    base_all = trade_cache["baseline"]
    selected_all = trade_cache[selected]
    base_dev, base_oos = _slice(base_all, start, cutoff), _slice(base_all, cutoff, finish)
    sel_dev, sel_oos = _slice(selected_all, start, cutoff), _slice(selected_all, cutoff, finish)
    bm_dev, bm_oos = metrics(base_dev, start, cutoff), metrics(base_oos, cutoff, finish)
    sm_dev, sm_oos = metrics(sel_dev, start, cutoff), metrics(sel_oos, cutoff, finish)

    win_delta = (sm_oos["win_rate"] - bm_oos["win_rate"]) if sm_oos["win_rate"] is not None and bm_oos["win_rate"] is not None else None
    freq_ratio = sm_oos["trades"] / max(1, bm_oos["trades"])
    holdout_ok = (
        selected != "baseline"
        and sm_oos["trades"] >= max(15, int(bm_oos["trades"] * .50))
        and (sm_oos["expectancy_r"] or -999) > 0
        and (sm_oos["profit_factor"] or 0) >= 1.30
        and freq_ratio >= .50
        and win_delta is not None and win_delta > 0
    )
    verdict = "QUALITY_FILTER_CANDIDATE" if holdout_ok else "KEEP_LIVE_BASELINE"

    frame.sort_values(["win_rate", "expectancy_r"], ascending=[False, False]).to_csv(out / "development_candidates.csv", index=False)
    base_oos.to_csv(out / "baseline_holdout_trades.csv", index=False)
    sel_oos.to_csv(out / "selected_holdout_trades.csv", index=False)

    groups = []
    groups += _group_rows(base_dev, "baseline_dev", ["playbook"])
    groups += _group_rows(base_oos, "baseline_holdout", ["playbook"])
    groups += _group_rows(sel_dev, "selected_dev", ["playbook"])
    groups += _group_rows(sel_oos, "selected_holdout", ["playbook"])
    pd.DataFrame(groups).to_csv(out / "playbook_performance.csv", index=False)

    sessions = []
    sessions += _group_rows(base_dev, "baseline_dev", ["session", "playbook"])
    sessions += _group_rows(base_oos, "baseline_holdout", ["session", "playbook"])
    sessions += _group_rows(sel_dev, "selected_dev", ["session", "playbook"])
    sessions += _group_rows(sel_oos, "selected_holdout", ["session", "playbook"])
    pd.DataFrame(sessions).to_csv(out / "session_playbook_performance.csv", index=False)

    selected_cfg = dict(frame[frame.variant.eq(selected)].iloc[0][list(asdict(base).keys())])
    summary = {
        "data": {"rows": len(m5), "start": m5.index.min(), "end": m5.index.max(),
                 "development_start": start, "development_end": cutoff, "holdout_end": finish},
        "baseline_dev": bm_dev, "baseline_holdout": bm_oos,
        "selected_variant": selected, "selected_config": selected_cfg,
        "selected_dev": sm_dev, "selected_holdout": sm_oos,
        "holdout_win_rate_delta_pp": win_delta, "holdout_frequency_ratio": freq_ratio,
        "verdict": verdict, "auto_deploy": False,
        "note": "Research-only. Data backfill is incomplete and currently covers 2020 only. Live canonical parameters remain frozen.",
    }
    (out / "summary.json").write_text(json.dumps(_safe(summary), indent=2), encoding="utf-8")
    (out / "REPORT.md").write_text(
        "# CASIO v3 M5 tuning\n\n"
        f"Data: {m5.index.min().isoformat()} -> {m5.index.max().isoformat()} ({len(m5):,} M5 rows)\n\n"
        f"Selected on development only: **{selected}**\n\n"
        f"Verdict: **{verdict}**\n\n"
        f"Baseline holdout: {bm_oos}\n\nSelected holdout: {sm_oos}\n\n"
        "No live parameters are changed by this run.\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Tune quality thresholds for CASIO v3 canonical M5 without touching live defaults")
    p.add_argument("--data", default="data/xauusd_m5.csv")
    p.add_argument("--output", default="reports/v3-m5-tuning")
    p.add_argument("--holdout-fraction", type=float, default=.25)
    a = p.parse_args()
    print(json.dumps(_safe(run_tuning(a.data, a.output, a.holdout_fraction)), indent=2))


if __name__ == "__main__":
    main()
