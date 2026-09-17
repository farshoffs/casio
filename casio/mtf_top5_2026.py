from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .m15_all_families_2026 import (
    DATA,
    START,
    END,
    START_RM,
    RISK_FRACTION,
    COST_BPS,
    prepare,
    build_strategies,
    replay,
    _summary,
    _monthly,
    _slice,
    _compound,
)

OUT = Path("reports/mtf-top5-2026")
TOP4 = {
    "Outcome First M15",
    "V1 Legacy M15",
    "Structural Frequency M15",
    "Structural Portfolio M15",
}


def _direction_target(base_target: pd.Series, f: pd.DataFrame, direction: int) -> tuple[pd.Series, pd.Series]:
    if direction == 1:
        h1_align = f.h1_bias.eq(1)
        h4_align = f.h4_bias.eq(1)
        h1_oppose = f.h1_bias.eq(-1)
        h4_oppose = f.h4_bias.eq(-1)
    else:
        h1_align = f.h1_bias.eq(-1)
        h4_align = f.h4_bias.eq(-1)
        h1_oppose = f.h1_bias.eq(1)
        h4_oppose = f.h4_bias.eq(1)

    blocked = h1_oppose & h4_oppose
    base_grade = pd.Series(
        np.select([base_target.ge(4.0), base_target.ge(3.0)], [2, 1], default=0),
        index=f.index,
        dtype=float,
    )
    align_count = h1_align.astype(int) + h4_align.astype(int)
    strong_context = (h1_align & h4_align & f.h4_adx.ge(18)).astype(int)
    score = base_grade + align_count + strong_context
    target = pd.Series(
        np.select([score.ge(3), score.ge(1)], [4.0, 3.0], default=2.0),
        index=f.index,
        dtype=float,
    )
    return target, blocked


def _mtf_wrap(spec: dict, f: pd.DataFrame) -> dict:
    base_target = spec["target"].reindex(f.index).astype(float)
    t_long, block_long = _direction_target(base_target, f, 1)
    t_short, block_short = _direction_target(base_target, f, -1)

    long = spec["long"].reindex(f.index).fillna(False) & ~block_long
    short = spec["short"].reindex(f.index).fillna(False) & ~block_short
    target = pd.Series(base_target, index=f.index)
    target.loc[long] = t_long.loc[long]
    target.loc[short] = t_short.loc[short]

    out = dict(spec)
    out["name"] = spec["name"].replace(" M15", " MTF")
    out["long"] = long
    out["short"] = short
    out["target"] = target
    out["note"] = spec["note"] + " M15 setup; completed H1/H4 context blocks only double-opposition and grades target 2R/3R/4R."
    return out


def _scalar_mtf_decision(f: pd.DataFrame, i: int, direction: int, base_target: float = 3.0) -> tuple[bool, float]:
    row = f.iloc[i]
    h1 = int(row.h1_bias) if pd.notna(row.h1_bias) else 0
    h4 = int(row.h4_bias) if pd.notna(row.h4_bias) else 0
    wanted = 1 if direction == 1 else -1
    blocked = (h1 == -wanted) and (h4 == -wanted)
    if blocked:
        return False, 2.0

    base_grade = 2 if base_target >= 4 else (1 if base_target >= 3 else 0)
    align = int(h1 == wanted) + int(h4 == wanted)
    strong = int(align == 2 and pd.notna(row.h4_adx) and float(row.h4_adx) >= 18.0)
    score = base_grade + align + strong
    target = 4.0 if score >= 3 else (3.0 if score >= 1 else 2.0)
    return True, target


def _build_0591_setups(m15: pd.DataFrame, f: pd.DataFrame, use_mtf: bool) -> pd.DataFrame:
    # Exact frozen M15-0591 setup parameters from the prior untouched-2026 test.
    lookback = 20
    impulse_atr = 1.20
    body_min = 0.55
    pullback_bars = 4
    retrace_max = 0.50
    stop_buffer_atr = 0.12
    min_risk_atr = 0.35
    max_risk_atr = 2.8

    ph = f[f"hh{lookback}"]
    pl = f[f"ll{lookback}"]
    long_imp = (
        f.atr.notna()
        & f.range_atr.ge(impulse_atr)
        & f.body_frac.ge(body_min)
        & f.close_loc.ge(0.72)
        & f.close.gt(ph)
    ).to_numpy()
    short_imp = (
        f.atr.notna()
        & f.range_atr.ge(impulse_atr)
        & f.body_frac.ge(body_min)
        & f.close_loc.le(0.28)
        & f.close.lt(pl)
    ).to_numpy()

    rows: list[dict] = []
    last_signal = -999
    for i in np.flatnonzero(long_imp | short_imp):
        if i - last_signal < 2:
            continue
        d = 1 if long_imp[i] else -1
        imp = f.iloc[i]
        a = float(imp.atr)
        if not np.isfinite(a) or a <= 0:
            continue
        imp_open = float(imp.open)
        imp_close = float(imp.close)
        imp_high = float(imp.high)
        imp_low = float(imp.low)
        imp_body = abs(imp_close - imp_open)
        if imp_body <= 0:
            continue
        broken = float(ph.iat[i] if d == 1 else pl.iat[i])
        if not np.isfinite(broken):
            continue

        if d == 1:
            zone_near = imp_close - 0.18 * imp_body
            zone_far = imp_close - retrace_max * imp_body
        else:
            zone_near = imp_close + 0.18 * imp_body
            zone_far = imp_close + retrace_max * imp_body

        confirm_j = None
        pull_extreme = imp_low if d == 1 else imp_high
        for j in range(i + 1, min(len(f) - 1, i + 1 + pullback_bars)):
            r = f.iloc[j]
            if d == 1:
                pull_extreme = min(pull_extreme, float(r.low))
                invalid = float(r.low) < imp_low - 0.30 * a
                touched = float(r.low) <= zone_near and float(r.high) >= zone_far
                confirm = float(r.close) > float(r.open) and float(r.close) > broken
            else:
                pull_extreme = max(pull_extreme, float(r.high))
                invalid = float(r.high) > imp_high + 0.30 * a
                touched = float(r.high) >= zone_near and float(r.low) <= zone_far
                confirm = float(r.close) < float(r.open) and float(r.close) < broken
            if invalid:
                break
            if touched and confirm:
                confirm_j = j
                break
        if confirm_j is None or confirm_j + 1 >= len(f):
            continue

        allowed, target_r = (True, 3.0)
        if use_mtf:
            allowed, target_r = _scalar_mtf_decision(f, confirm_j, d, 3.0)
        if not allowed:
            continue

        entry_i = confirm_j + 1
        entry = float(f.open.iat[entry_i])
        if d == 1:
            stop = pull_extreme - stop_buffer_atr * a
            risk = entry - stop
        else:
            stop = pull_extreme + stop_buffer_atr * a
            risk = stop - entry
        if not np.isfinite(risk) or risk <= 0:
            continue
        risk_atr = risk / a
        if risk_atr < min_risk_atr or risk_atr > max_risk_atr:
            continue

        rows.append({
            "signal_i": int(confirm_j),
            "entry_i": int(entry_i),
            "entry_time": f.index[entry_i],
            "direction": d,
            "entry": entry,
            "stop": stop,
            "risk": risk,
            "target_r": target_r,
            "target": entry + d * target_r * risk,
        })
        last_signal = confirm_j
    return pd.DataFrame(rows)


def _replay_0591(m15: pd.DataFrame, setups: pd.DataFrame, name: str) -> pd.DataFrame:
    if setups.empty:
        return pd.DataFrame()
    out: list[dict] = []
    next_free = -1
    for s in setups.sort_values("entry_i").itertuples(index=False):
        ei = int(s.entry_i)
        if ei < next_free:
            continue
        d = int(s.direction)
        entry = float(s.entry)
        stop = float(s.stop)
        risk = float(s.risk)
        target = float(s.target)
        target_r = float(s.target_r)
        end = min(len(m15), ei + 1 + 40)
        gross = None
        reason = None
        exit_i = None
        for j in range(ei, end):
            lo = float(m15.low.iat[j])
            hi = float(m15.high.iat[j])
            close = float(m15.close.iat[j])
            hs = lo <= stop if d == 1 else hi >= stop
            ht = hi >= target if d == 1 else lo <= target
            if hs and ht:
                gross, reason = -1.0, "stop_same_bar"
            elif hs:
                gross, reason = -1.0, "stop"
            elif ht:
                gross, reason = target_r, "target"
            elif j == end - 1:
                gross, reason = ((close - entry) / risk) * d, "time_exit"
            else:
                continue
            exit_i = j
            break
        if gross is None or exit_i is None:
            continue
        cost_r = (entry * COST_BPS / 10000.0) / risk
        out.append({
            "strategy": name,
            "family": "M15-0591",
            "entry_time": m15.index[ei],
            "exit_time": m15.index[exit_i] + pd.Timedelta(minutes=15),
            "direction": d,
            "entry": entry,
            "stop": stop,
            "target_r": target_r,
            "gross_r": float(gross),
            "net_r": float(gross - cost_r),
            "reason": reason,
        })
        next_free = exit_i + 1
    return pd.DataFrame(out)


def _compare_row(name: str, base_trades: pd.DataFrame, mtf_trades: pd.DataFrame, observed_end: pd.Timestamp) -> dict:
    b = _summary(base_trades, observed_end)
    m = _summary(mtf_trades, observed_end)
    return {
        "strategy": name,
        "m15_end_rm": b["ending_balance_rm"],
        "mtf_end_rm": m["ending_balance_rm"],
        "delta_rm": m["ending_balance_rm"] - b["ending_balance_rm"],
        "m15_trades": b["trades"],
        "mtf_trades": m["trades"],
        "m15_min_month": b["min_completed_month_trades"],
        "mtf_min_month": m["min_completed_month_trades"],
        "mtf_lowest_rm": m["lowest_balance_rm"],
        "mtf_frequency_pass": m["passes_frequency"],
        "mtf_growth_pass": m["passes_growth"],
        "mtf_requested_fit": m["requested_fit"],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    m5 = load_m5_csv(DATA)
    m5 = m5[m5.index >= pd.Timestamp("2025-10-01", tz="UTC")].copy()
    observed_end = min(END, m5.index.max() + pd.Timedelta(minutes=5))
    if observed_end <= START:
        raise RuntimeError("No 2026 Dukascopy data available")

    m15, f = prepare(m5)
    specs = {s["name"]: s for s in build_strategies(f) if s["name"] in TOP4}
    if set(specs) != TOP4:
        missing = sorted(TOP4 - set(specs))
        raise RuntimeError(f"Missing M15 strategy specs: {missing}")

    rows: list[dict] = []
    trades_out = []
    monthly_out = []

    for name in sorted(TOP4):
        base_spec = specs[name]
        mtf_spec = _mtf_wrap(base_spec, f)
        base_trades = replay(m15, f, base_spec)
        mtf_trades = replay(m15, f, mtf_spec)
        rows.append(_compare_row(name, base_trades, mtf_trades, observed_end))

        for label, t in [("M15", base_trades), ("MTF", mtf_trades)]:
            z = _slice(t, START, observed_end)
            if not z.empty:
                z, _, _ = _compound(z)
                z.insert(0, "variant", label)
                z.insert(0, "strategy_base", name)
                trades_out.append(z)
            mo = _monthly(t, observed_end)
            if not mo.empty:
                mo.insert(0, "variant", label)
                mo.insert(0, "strategy", name)
                monthly_out.append(mo)

    base_0591 = _replay_0591(m15, _build_0591_setups(m15, f, use_mtf=False), "M15-0591")
    mtf_0591 = _replay_0591(m15, _build_0591_setups(m15, f, use_mtf=True), "M15-0591 MTF")
    rows.append(_compare_row("M15-0591", base_0591, mtf_0591, observed_end))

    for label, t in [("M15", base_0591), ("MTF", mtf_0591)]:
        z = _slice(t, START, observed_end)
        if not z.empty:
            z, _, _ = _compound(z)
            z.insert(0, "variant", label)
            z.insert(0, "strategy_base", "M15-0591")
            trades_out.append(z)
        mo = _monthly(t, observed_end)
        if not mo.empty:
            mo.insert(0, "variant", label)
            mo.insert(0, "strategy", "M15-0591")
            monthly_out.append(mo)

    result = pd.DataFrame(rows).sort_values(
        ["mtf_requested_fit", "mtf_end_rm"], ascending=[False, False]
    ).reset_index(drop=True)
    result.to_csv(OUT / "comparison.csv", index=False)
    if trades_out:
        pd.concat(trades_out, ignore_index=True).to_csv(OUT / "all_trades.csv", index=False)
    if monthly_out:
        pd.concat(monthly_out, ignore_index=True).to_csv(OUT / "monthly.csv", index=False)

    lines = [
        "# CASIO Top Five M15 -> H1 -> H4 MTF Test — 2026",
        "",
        "## Test rule",
        "",
        "- Dukascopy 2026 only, through the latest available bar.",
        "- Start **RM100** independently for each strategy/variant.",
        "- Risk **5% of current balance** per filled trade.",
        "- Require **at least 8 filled trades in every completed month**.",
        "- Same **1 bp round-trip cost** and stop-first same-bar handling.",
        "- M15 still creates the setup. Only completed H1/H4 candles may influence the decision.",
        "- A trade is blocked only when **both H1 and H4 oppose** its direction.",
        "- Target is graded **2R / 3R / 4R** from original M15 setup quality plus H1/H4 alignment.",
        "",
        "## Side-by-side result",
        "",
        result.to_markdown(index=False),
        "",
        "## Interpretation rule",
        "",
        "MTF is useful only if it improves the RM100 path without breaking the >=8-trades-per-completed-month requirement. This test does not retune the original M15 entry rules.",
        "",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(result.to_string(index=False))
    print(f"Report: {OUT / 'REPORT.md'}")


if __name__ == "__main__":
    main()
