from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .m15_all_families_2026 import prepare
from .multi_technique_2026 import _build_streams, PRIORITY, _ctx, _recent, _finalize
from .regime_router_validation import summarize, monthly
from .regime_router_diagnostics import SECONDARY, DUKASCOPY, _signals, _session_label

OUT = Path("reports/regime-router-repair-research")

TREND_ORDER = [
    "M15-0591 MTF", "V1 Legacy M15", "Outcome First M15",
    "Structural Portfolio MTF", "Structural Frequency M15",
]
MIXED_ORDER = [
    "Structural Portfolio MTF", "Outcome First M15", "Structural Frequency M15",
    "M15-0591 MTF", "V1 Legacy M15",
]
RANK_TREND = {n: i for i, n in enumerate(TREND_ORDER)}
RANK_MIXED = {n: i for i, n in enumerate(MIXED_ORDER)}
MOMENTUM = {"M15-0591 MTF", "V1 Legacy M15"}


def _support(recent: pd.DataFrame, direction: int) -> int:
    return int(recent[recent.direction == direction].technique.nunique())


def _route(signals: pd.DataFrame, f: pd.DataFrame, variant: str) -> pd.DataFrame:
    rows: list[pd.Series] = []
    next_free = None

    for t, group in signals.groupby("entry_time", sort=True):
        if next_free is not None and t < next_free:
            continue

        c = _ctx(f, t)
        h1 = int(c.h1_bias) if pd.notna(c.h1_bias) else 0
        h4 = int(c.h4_bias) if pd.notna(c.h4_bias) else 0
        h4_adx = float(c.h4_adx) if pd.notna(c.h4_adx) else 0.0
        strong_trend = h1 != 0 and h1 == h4 and h4_adx >= 18.0
        recent = _recent(signals, t)
        session = _session_label(pd.Timestamp(t))

        z = group.copy()
        if strong_trend:
            z = z[z.direction == h1].copy()
            z["route_rank"] = z.technique.map(RANK_TREND)
        else:
            keep = []
            for idx, cand in z.iterrows():
                d = int(cand.direction)
                # Frozen baseline: momentum needs a second agreeing technique in mixed regime.
                if cand.technique in MOMENTUM and _support(recent, d) < 2:
                    continue
                keep.append(idx)
            z = z.loc[keep].copy()
            z["route_rank"] = z.technique.map(RANK_MIXED)

        if z.empty:
            continue

        keep = []
        for idx, cand in z.sort_values(["route_rank", "priority", "technique"]).iterrows():
            d = int(cand.direction)
            same_support = _support(recent, d)
            both_oppose = h1 == -d and h4 == -d

            if variant in {"NO_DOUBLE_OPPOSE", "LONDON_CONSENSUS", "NARROW_CONFIRM", "COMBINED_GUARD"} and both_oppose:
                continue

            if variant == "LONDON_CONSENSUS" and session == "LONDON" and same_support < 2:
                continue

            if variant in {"NARROW_CONFIRM", "COMBINED_GUARD"}:
                if session == "LONDON" and cand.technique == "Structural Portfolio MTF" and same_support < 2:
                    continue
                if cand.technique == "V1 Legacy M15" and d == -1 and same_support < 2:
                    continue

            if variant == "COMBINED_GUARD":
                # 2024 was especially hostile to large London impulses. Do not ban them;
                # require cross-technique confirmation when the current M15 bar is >= 1 ATR.
                range_atr = float(c.range_atr) if pd.notna(c.range_atr) else np.nan
                if session == "LONDON" and np.isfinite(range_atr) and range_atr >= 1.0 and same_support < 2:
                    continue

            keep.append(idx)

        z = z.loc[keep].copy()
        if z.empty:
            continue
        pick = z.sort_values(["route_rank", "priority", "technique"]).iloc[0]
        rows.append(pick)
        next_free = pick.exit_time

    return _finalize(rows, f"Regime Router {variant}")


def _window(data: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, year: int, feed: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    warm = start - pd.Timedelta(days=120)
    z = data[(data.index >= warm) & (data.index < end)].copy()
    m15, f = prepare(z)
    streams = _build_streams(m15, f)
    signals = _signals(streams, start, end)
    return signals, f


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sec = load_m5_csv(SECONDARY)
    duk = load_m5_csv(DUKASCOPY)
    windows = [
        (sec, pd.Timestamp("2024-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC"), 2024, "secondary"),
        (sec, pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-01-01", tz="UTC"), 2025, "secondary"),
        (duk, pd.Timestamp("2026-01-01", tz="UTC"), min(pd.Timestamp("2027-01-01", tz="UTC"), duk.index.max() + pd.Timedelta(minutes=5)), 2026, "dukascopy"),
    ]
    variants = ["BASELINE", "NO_DOUBLE_OPPOSE", "LONDON_CONSENSUS", "NARROW_CONFIRM", "COMBINED_GUARD"]

    rows = []
    months = []
    contributions = []
    for data, start, end, year, feed in windows:
        signals, f = _window(data, start, end, year, feed)
        for variant in variants:
            routed = _route(signals, f, variant)
            if not routed.empty:
                routed["entry_time"] = pd.to_datetime(routed.entry_time, utc=True)
                routed["exit_time"] = pd.to_datetime(routed.exit_time, utc=True)
                routed = routed[(routed.entry_time >= start) & (routed.entry_time < end)].copy()
            s = summarize(routed, start, end)
            rows.append({"year": year, "feed": feed, "variant": variant, **s})

            mo = monthly(routed, start, end)
            if not mo.empty:
                mo.insert(0, "variant", variant)
                mo.insert(0, "year", year)
                months.append(mo)
            if not routed.empty:
                vc = routed.technique.value_counts()
                for tech, n in vc.items():
                    contributions.append({"year": year, "variant": variant, "technique": tech, "trades": int(n)})

    result = pd.DataFrame(rows)
    result.to_csv(OUT / "comparison.csv", index=False)
    if months:
        pd.concat(months, ignore_index=True).to_csv(OUT / "monthly.csv", index=False)
    pd.DataFrame(contributions).to_csv(OUT / "contributions.csv", index=False)

    pivot = result.pivot(index="variant", columns="year", values="ending_balance_rm").reset_index()
    freq = result.pivot(index="variant", columns="year", values="min_completed_month_trades").reset_index()
    fits = result.pivot(index="variant", columns="year", values="requested_fit").reset_index()

    lines = [
        "# CASIO Regime Router — Interpretable Repair Research",
        "",
        "## Rules",
        "",
        "- BASELINE: frozen 2026 Regime Router logic.",
        "- NO_DOUBLE_OPPOSE: never accept a trade when completed H1 and H4 both point against its direction.",
        "- LONDON_CONSENSUS: NO_DOUBLE_OPPOSE plus every London trade needs agreement from >=2 techniques in the prior 30 minutes.",
        "- NARROW_CONFIRM: NO_DOUBLE_OPPOSE plus Structural Portfolio needs confirmation in London and V1 shorts need confirmation everywhere.",
        "- COMBINED_GUARD: NARROW_CONFIRM plus >=1 ATR London bars need >=2-technique agreement.",
        "- No numerical threshold grid search was performed; these are hypotheses derived from the 2024 diagnostic concentration.",
        "",
        "## Full comparison",
        "",
        result.to_markdown(index=False),
        "",
        "## RM100 ending balance by year",
        "",
        pivot.to_markdown(index=False),
        "",
        "## Minimum trades in any completed month",
        "",
        freq.to_markdown(index=False),
        "",
        "## Requested-fit PASS by year",
        "",
        fits.to_markdown(index=False),
        "",
        "A repair is only interesting if it improves the 2024 failure without collapsing 2025/2026 or the >=8-trades-per-month rule. 2023 Dukascopy remains the next genuinely older validation window.",
        "",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
