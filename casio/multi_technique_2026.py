from __future__ import annotations

from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .m15_all_families_2026 import (
    DATA, START, END, START_RM, RISK_FRACTION,
    prepare, build_strategies, replay, _summary, _monthly, _slice, _compound,
)
from .mtf_top5_2026 import _mtf_wrap, _build_0591_setups, _replay_0591

OUT = Path("reports/multi-technique-2026")
LOOKBACK = pd.Timedelta(minutes=30)
CORE = {"M15-0591 MTF", "Structural Portfolio MTF"}
BOOSTERS = {"Outcome First M15", "V1 Legacy M15", "Structural Frequency M15"}
PRIORITY = {
    "M15-0591 MTF": 0,
    "Structural Portfolio MTF": 1,
    "Outcome First M15": 2,
    "V1 Legacy M15": 3,
    "Structural Frequency M15": 4,
}


def _actualize(t: pd.DataFrame, technique: str, base_replay_clock: bool) -> pd.DataFrame:
    x = t.copy()
    if x.empty:
        return x
    x["entry_time"] = pd.to_datetime(x["entry_time"], utc=True)
    x["exit_time"] = pd.to_datetime(x["exit_time"], utc=True)
    # m15_all_families labels entry at the end of the entry bar even though the
    # fill price is that bar's open. Normalize to the actual M15 bar-open time.
    if base_replay_clock:
        x["entry_time"] = x["entry_time"] - pd.Timedelta(minutes=15)
    x["technique"] = technique
    keep = [
        "technique", "entry_time", "exit_time", "direction", "entry", "stop",
        "target_r", "gross_r", "net_r", "reason",
    ]
    return x[[c for c in keep if c in x.columns]].copy()


def _build_streams(m15: pd.DataFrame, f: pd.DataFrame) -> dict[str, pd.DataFrame]:
    wanted = {
        "Outcome First M15",
        "V1 Legacy M15",
        "Structural Frequency M15",
        "Structural Portfolio M15",
    }
    specs = {s["name"]: s for s in build_strategies(f) if s["name"] in wanted}
    missing = wanted - set(specs)
    if missing:
        raise RuntimeError(f"Missing source specs: {sorted(missing)}")

    streams: dict[str, pd.DataFrame] = {}
    for name in ["Outcome First M15", "V1 Legacy M15", "Structural Frequency M15"]:
        streams[name] = _actualize(replay(m15, f, specs[name]), name, True)

    sp_mtf = _mtf_wrap(specs["Structural Portfolio M15"], f)
    streams["Structural Portfolio MTF"] = _actualize(
        replay(m15, f, sp_mtf), "Structural Portfolio MTF", True
    )

    s0591 = _build_0591_setups(m15, f, use_mtf=True)
    streams["M15-0591 MTF"] = _actualize(
        _replay_0591(m15, s0591, "M15-0591 MTF"), "M15-0591 MTF", False
    )
    return streams


def _all_signals(streams: dict[str, pd.DataFrame], observed_end: pd.Timestamp) -> pd.DataFrame:
    parts = []
    for name, t in streams.items():
        if t.empty:
            continue
        x = t[(t.entry_time >= START) & (t.entry_time < observed_end)].copy()
        x["priority"] = PRIORITY[name]
        parts.append(x)
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True).sort_values(
        ["entry_time", "priority", "technique"]
    ).reset_index(drop=True)


def _recent(signals: pd.DataFrame, t: pd.Timestamp) -> pd.DataFrame:
    return signals[(signals.entry_time >= t - LOOKBACK) & (signals.entry_time <= t)]


def _flat_select(candidates: pd.DataFrame, next_free: pd.Timestamp | None) -> pd.Series | None:
    if candidates.empty:
        return None
    z = candidates.sort_values(["priority", "technique"])
    for _, row in z.iterrows():
        if next_free is None or row.entry_time >= next_free:
            return row
    return None


def _finalize(rows: list[pd.Series], name: str) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows).copy()
    out["strategy"] = name
    out = out.sort_values("entry_time").reset_index(drop=True)
    return out


def route_any_first(signals: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.Series] = []
    next_free = None
    for t, group in signals.groupby("entry_time", sort=True):
        pick = _flat_select(group, next_free)
        if pick is None:
            continue
        rows.append(pick)
        next_free = pick.exit_time
    return _finalize(rows, "Ensemble ANY-FIRST")


def route_priority_veto(signals: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.Series] = []
    next_free = None
    for t, group in signals.groupby("entry_time", sort=True):
        if next_free is not None and t < next_free:
            continue
        recent = _recent(signals, t)
        accepted = None
        for _, cand in group.sort_values(["priority", "technique"]).iterrows():
            higher_or_equal = recent[recent.priority <= cand.priority]
            opposite = higher_or_equal[higher_or_equal.direction == -int(cand.direction)]
            if len(opposite):
                continue
            accepted = cand
            break
        if accepted is not None:
            rows.append(accepted)
            next_free = accepted.exit_time
    return _finalize(rows, "Ensemble PRIORITY-VETO")


def route_consensus2(signals: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.Series] = []
    next_free = None
    for t, group in signals.groupby("entry_time", sort=True):
        if next_free is not None and t < next_free:
            continue
        recent = _recent(signals, t)
        eligible = []
        for _, cand in group.iterrows():
            same = recent[recent.direction == int(cand.direction)].technique.nunique()
            opp = recent[recent.direction == -int(cand.direction)].technique.nunique()
            if same >= 2 and same > opp:
                c = cand.copy()
                c["support_count"] = int(same)
                c["opposition_count"] = int(opp)
                eligible.append(c)
        if eligible:
            z = pd.DataFrame(eligible).sort_values(["priority", "technique"])
            pick = z.iloc[0]
            rows.append(pick)
            next_free = pick.exit_time
    return _finalize(rows, "Ensemble CONSENSUS-2")


def route_core_booster(signals: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.Series] = []
    next_free = None
    for t, group in signals.groupby("entry_time", sort=True):
        if next_free is not None and t < next_free:
            continue
        recent = _recent(signals, t)
        accepted = None
        for _, cand in group.sort_values(["priority", "technique"]).iterrows():
            d = int(cand.direction)
            if cand.technique in CORE:
                accepted = cand
                break
            # Booster trades need either recent core support or agreement from a
            # second booster. A recent opposite core signal vetoes them.
            core_recent = recent[recent.technique.isin(CORE)]
            if len(core_recent[core_recent.direction == -d]):
                continue
            core_support = core_recent[core_recent.direction == d].technique.nunique() >= 1
            booster_support = recent[
                recent.technique.isin(BOOSTERS) & (recent.direction == d)
            ].technique.nunique() >= 2
            if core_support or booster_support:
                accepted = cand
                break
        if accepted is not None:
            rows.append(accepted)
            next_free = accepted.exit_time
    return _finalize(rows, "Ensemble CORE+BOOSTER")


def _ctx(f: pd.DataFrame, t: pd.Timestamp) -> pd.Series:
    # Entry is at M15 bar open. Context must come only from features already
    # known by then, so use the previous completed M15 feature row.
    pos = f.index.searchsorted(t, side="left") - 1
    pos = max(0, min(pos, len(f) - 1))
    return f.iloc[pos]


def route_regime(signals: pd.DataFrame, f: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.Series] = []
    next_free = None
    trend_order = ["M15-0591 MTF", "V1 Legacy M15", "Outcome First M15", "Structural Portfolio MTF", "Structural Frequency M15"]
    mixed_order = ["Structural Portfolio MTF", "Outcome First M15", "Structural Frequency M15", "M15-0591 MTF", "V1 Legacy M15"]
    rank_trend = {n: i for i, n in enumerate(trend_order)}
    rank_mixed = {n: i for i, n in enumerate(mixed_order)}

    for t, group in signals.groupby("entry_time", sort=True):
        if next_free is not None and t < next_free:
            continue
        c = _ctx(f, t)
        h1 = int(c.h1_bias) if pd.notna(c.h1_bias) else 0
        h4 = int(c.h4_bias) if pd.notna(c.h4_bias) else 0
        h4_adx = float(c.h4_adx) if pd.notna(c.h4_adx) else 0.0
        strong_trend = h1 != 0 and h1 == h4 and h4_adx >= 18.0
        recent = _recent(signals, t)

        z = group.copy()
        if strong_trend:
            z = z[z.direction == h1].copy()
            z["route_rank"] = z.technique.map(rank_trend)
        else:
            # Mixed regime: structural techniques are first. Momentum/breakout
            # techniques need a second technique agreeing in the last 30m.
            ok = []
            for idx, cand in z.iterrows():
                if cand.technique in {"M15-0591 MTF", "V1 Legacy M15"}:
                    support = recent[recent.direction == int(cand.direction)].technique.nunique()
                    if support < 2:
                        continue
                ok.append(idx)
            z = z.loc[ok].copy()
            z["route_rank"] = z.technique.map(rank_mixed)
        if z.empty:
            continue
        pick = z.sort_values(["route_rank", "priority", "technique"]).iloc[0]
        rows.append(pick)
        next_free = pick.exit_time
    return _finalize(rows, "Ensemble REGIME-ROUTER")


def _compound_summary(trades: pd.DataFrame, observed_end: pd.Timestamp) -> dict:
    if trades.empty:
        return {
            "trades": 0, "trades_per_30d": 0.0, "min_completed_month_trades": 0,
            "ending_balance_rm": START_RM, "lowest_balance_rm": START_RM,
            "passes_frequency": False, "passes_growth": False, "requested_fit": False,
        }
    x = trades.copy()
    # _summary only needs entry_time/net_r; it compounds at the same 5% rule.
    return _summary(x, observed_end)


def _overlap_matrix(signals: pd.DataFrame) -> pd.DataFrame:
    names = sorted(PRIORITY, key=PRIORITY.get)
    rows = []
    for a in names:
        aa = signals[signals.technique == a]
        for b in names:
            if a == b:
                continue
            bb = signals[signals.technique == b]
            same = opp = 0
            for r in aa.itertuples(index=False):
                z = bb[(bb.entry_time >= r.entry_time - LOOKBACK) & (bb.entry_time <= r.entry_time + LOOKBACK)]
                same += int((z.direction == r.direction).any())
                opp += int((z.direction == -r.direction).any())
            rows.append({"technique_a": a, "technique_b": b, "same_direction_overlap": same, "opposite_direction_overlap": opp})
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    m5 = load_m5_csv(DATA)
    m5 = m5[m5.index >= pd.Timestamp("2025-10-01", tz="UTC")].copy()
    observed_end = min(END, m5.index.max() + pd.Timedelta(minutes=5))
    if observed_end <= START:
        raise RuntimeError("No 2026 Dukascopy data available")

    m15, f = prepare(m5)
    streams = _build_streams(m15, f)
    signals = _all_signals(streams, observed_end)

    ensembles = {
        "ANY-FIRST": route_any_first(signals),
        "PRIORITY-VETO": route_priority_veto(signals),
        "CONSENSUS-2": route_consensus2(signals),
        "CORE+BOOSTER": route_core_booster(signals),
        "REGIME-ROUTER": route_regime(signals, f),
    }

    rows = []
    monthly_parts = []
    trade_parts = []

    # Single-technique reference rows use the exact selected best versions.
    for name, t in streams.items():
        s = _compound_summary(t, observed_end)
        rows.append({"variant": name, "type": "single", **s})

    for name, t in ensembles.items():
        s = _compound_summary(t, observed_end)
        rows.append({"variant": name, "type": "ensemble", **s})
        z = _slice(t, START, observed_end)
        if not z.empty:
            z, _, _ = _compound(z)
            z.insert(0, "ensemble", name)
            trade_parts.append(z)
        mo = _monthly(t, observed_end)
        if not mo.empty:
            mo.insert(0, "ensemble", name)
            monthly_parts.append(mo)

    result = pd.DataFrame(rows).sort_values(
        ["requested_fit", "ending_balance_rm", "min_completed_month_trades"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    result.to_csv(OUT / "comparison.csv", index=False)
    signals.to_csv(OUT / "source_signals.csv", index=False)
    _overlap_matrix(signals).to_csv(OUT / "overlap.csv", index=False)
    if trade_parts:
        pd.concat(trade_parts, ignore_index=True).to_csv(OUT / "ensemble_trades.csv", index=False)
    if monthly_parts:
        pd.concat(monthly_parts, ignore_index=True).to_csv(OUT / "monthly.csv", index=False)

    contrib = []
    for name, t in ensembles.items():
        if t.empty:
            continue
        c = t.technique.value_counts()
        for technique, n in c.items():
            contrib.append({"ensemble": name, "technique": technique, "trades": int(n)})
    contrib_df = pd.DataFrame(contrib)
    if not contrib_df.empty:
        contrib_df.to_csv(OUT / "contributions.csv", index=False)

    e = result[result.type == "ensemble"].copy()
    top = e.iloc[0] if len(e) else None
    lines = [
        "# CASIO Multi-Technique Ensemble Test — 2026",
        "",
        "## Fixed test rule",
        "",
        "- Source: `data/xauusd_m5_dukascopy_research.csv`.",
        f"- Test window: **2026-01-01 through {observed_end.isoformat()}**.",
        "- One shared account per ensemble, starting **RM100**.",
        "- Risk **5% of current account balance** on each accepted trade.",
        "- Require **at least 8 filled trades in every completed month**.",
        "- 1 bp round-trip cost; source techniques keep their frozen 2R/3R/4R target logic.",
        "- Only one portfolio position may be open at a time. Overlapping source signals are skipped or routed by the ensemble rule.",
        "- No weight/threshold grid search was performed for the ensemble. These are five transparent combination rules.",
        "",
        "## Source techniques",
        "",
        "1. M15-0591 MTF",
        "2. Outcome First M15",
        "3. V1 Legacy M15",
        "4. Structural Portfolio MTF",
        "5. Structural Frequency M15",
        "",
        "## Combination methods",
        "",
        "- **ANY-FIRST**: first available signal wins; fixed priority breaks same-bar collisions.",
        "- **PRIORITY-VETO**: same as a stack, but a recent opposite signal from an equal/higher-priority technique vetoes the candidate.",
        "- **CONSENSUS-2**: requires at least two distinct techniques agreeing in the prior 30 minutes and more agreement than opposition.",
        "- **CORE+BOOSTER**: M15-0591 MTF + Structural Portfolio MTF are the core. Booster techniques need core support or agreement from another booster; opposite core signals veto.",
        "- **REGIME-ROUTER**: strong aligned H1/H4 trend favors momentum/breakout techniques; mixed regimes favor structural techniques. No future HTF data is used.",
        "",
        "## Results",
        "",
        result.to_markdown(index=False),
        "",
    ]
    if top is not None:
        lines += [
            "## Best ensemble under the requested test",
            "",
            f"**{top['variant']}**: RM100 -> **RM{top['ending_balance_rm']:.2f}**, "
            f"{int(top['trades'])} trades, minimum **{int(top['min_completed_month_trades'])}** trades in a completed month. "
            f"Requested fit: **{'PASS' if bool(top['requested_fit']) else 'FAIL'}**.",
            "",
        ]
    if not contrib_df.empty:
        lines += ["## Technique contribution to each ensemble", "", contrib_df.to_markdown(index=False), ""]
    lines += [
        "## Dashboard implication",
        "",
        "The five techniques should remain visible as separate dashboard modules. The ensemble layer should sit above them and show: each technique's direction, its target R, H1/H4 context, recent agreement/opposition, which router rule is active, and the final portfolio action. This preserves transparency instead of hiding the techniques inside one opaque score.",
        "",
        "## Research status",
        "",
        "This is an exploratory 2026 combination test built after seeing the individual 2026 results. It is useful for selecting dashboard architecture, but any chosen ensemble must be frozen and validated on earlier unseen years / the independent feed before being treated as robust.",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
