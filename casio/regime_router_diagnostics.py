from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .m15_all_families_2026 import prepare
from .multi_technique_2026 import _build_streams, route_regime, PRIORITY, _ctx
from .regime_router_validation import compound, monthly, summarize

SECONDARY = Path("data/xauusd_m5_secondary_octafx_mt4.csv")
DUKASCOPY = Path("data/xauusd_m5_dukascopy_research.csv")
OUT = Path("reports/regime-router-2024-diagnostics")


def _signals(streams: dict[str, pd.DataFrame], start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    parts = []
    for name, t in streams.items():
        if t.empty:
            continue
        x = t.copy()
        x["entry_time"] = pd.to_datetime(x.entry_time, utc=True)
        x["exit_time"] = pd.to_datetime(x.exit_time, utc=True)
        x = x[(x.entry_time >= start) & (x.entry_time < end)].copy()
        if x.empty:
            continue
        x["priority"] = PRIORITY[name]
        parts.append(x)
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True).sort_values(
        ["entry_time", "priority", "technique"]
    ).reset_index(drop=True)


def _session_label(ts: pd.Timestamp) -> str:
    m = ts.hour * 60 + ts.minute
    if m < 360:
        return "ASIA"
    if 420 <= m < 720:
        return "LONDON"
    if 750 <= m < 1020:
        return "NEW_YORK"
    return "OTHER"


def _adx_band(x: float) -> str:
    if not np.isfinite(x):
        return "NA"
    if x < 18:
        return "<18"
    if x < 22:
        return "18-22"
    if x < 30:
        return "22-30"
    return "30+"


def _m15_adx_band(x: float) -> str:
    if not np.isfinite(x):
        return "NA"
    if x < 15:
        return "<15"
    if x < 20:
        return "15-20"
    if x < 25:
        return "20-25"
    return "25+"


def _range_band(x: float) -> str:
    if not np.isfinite(x):
        return "NA"
    if x < 0.60:
        return "<0.6 ATR"
    if x < 1.00:
        return "0.6-1.0 ATR"
    if x < 1.50:
        return "1.0-1.5 ATR"
    return "1.5+ ATR"


def _annotate(trades: pd.DataFrame, f: pd.DataFrame, year: int, feed: str) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    x = trades.copy().sort_values("entry_time").reset_index(drop=True)
    rows = []
    for r in x.itertuples(index=False):
        t = pd.Timestamp(r.entry_time)
        c = _ctx(f, t)
        h1 = int(c.h1_bias) if pd.notna(c.h1_bias) else 0
        h4 = int(c.h4_bias) if pd.notna(c.h4_bias) else 0
        h4_adx = float(c.h4_adx) if pd.notna(c.h4_adx) else np.nan
        m15_adx = float(c.adx) if pd.notna(c.adx) else np.nan
        range_atr = float(c.range_atr) if pd.notna(c.range_atr) else np.nan
        atr = float(c.atr) if pd.notna(c.atr) else np.nan
        strong = h1 != 0 and h1 == h4 and np.isfinite(h4_adx) and h4_adx >= 18.0
        if strong:
            state = "STRONG_ALIGNED"
        elif h1 != 0 and h1 == h4:
            state = "ALIGNED_WEAK"
        elif h1 == 0 or h4 == 0:
            state = "NEUTRAL_MIX"
        else:
            state = "OPPOSED_HTF"
        d = int(r.direction)
        rows.append({
            "year": year,
            "feed": feed,
            "entry_time": t,
            "month": t.strftime("%Y-%m"),
            "hour_utc": int(t.hour),
            "session": _session_label(t),
            "technique": r.technique,
            "direction": d,
            "direction_text": "LONG" if d == 1 else "SHORT",
            "net_r": float(r.net_r),
            "gross_r": float(r.gross_r),
            "target_r": float(r.target_r),
            "reason": str(r.reason),
            "h1_bias": h1,
            "h4_bias": h4,
            "h1_align_trade": h1 == d,
            "h4_align_trade": h4 == d,
            "both_align_trade": h1 == d and h4 == d,
            "both_oppose_trade": h1 == -d and h4 == -d,
            "htf_state": state,
            "router_mode": "TREND" if strong else "MIXED",
            "h4_adx": h4_adx,
            "h4_adx_band": _adx_band(h4_adx),
            "m15_adx": m15_adx,
            "m15_adx_band": _m15_adx_band(m15_adx),
            "range_atr": range_atr,
            "range_atr_band": _range_band(range_atr),
            "atr": atr,
        })
    return pd.DataFrame(rows)


def _run_window(m5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, year: int, feed: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    warm = start - pd.Timedelta(days=120)
    z = m5[(m5.index >= warm) & (m5.index < end)].copy()
    m15, f = prepare(z)
    streams = _build_streams(m15, f)
    sig = _signals(streams, start, end)
    routed = route_regime(sig, f)
    if not routed.empty:
        routed["entry_time"] = pd.to_datetime(routed.entry_time, utc=True)
        routed["exit_time"] = pd.to_datetime(routed.exit_time, utc=True)
        routed = routed[(routed.entry_time >= start) & (routed.entry_time < end)].copy()
    ann = _annotate(routed, f, year, feed)
    return routed, ann, summarize(routed, start, end)


def _group(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=cols + ["trades", "net_r_sum", "avg_net_r", "positive_trade_pct"])
    g = df.groupby(cols, dropna=False).agg(
        trades=("net_r", "size"),
        net_r_sum=("net_r", "sum"),
        avg_net_r=("net_r", "mean"),
        positive_trade_pct=("net_r", lambda x: float((x > 0).mean() * 100.0)),
    ).reset_index()
    return g.sort_values(["net_r_sum", "trades"], ascending=[True, False])


def _month_table(df: pd.DataFrame) -> pd.DataFrame:
    return _group(df, ["year", "month"])


def _loss_streaks(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, g in df.sort_values("entry_time").groupby("year"):
        max_count = 0
        max_r = 0.0
        cur_count = 0
        cur_r = 0.0
        worst_window_start = None
        streak_start = None
        for r in g.itertuples(index=False):
            if r.net_r <= 0:
                if cur_count == 0:
                    streak_start = r.entry_time
                cur_count += 1
                cur_r += float(r.net_r)
                if cur_count > max_count or (cur_count == max_count and cur_r < max_r):
                    max_count = cur_count
                    max_r = cur_r
                    worst_window_start = streak_start
            else:
                cur_count = 0
                cur_r = 0.0
                streak_start = None
        rows.append({
            "year": int(year),
            "max_consecutive_nonpositive_trades": int(max_count),
            "streak_net_r": float(max_r),
            "streak_start": worst_window_start,
        })
    return pd.DataFrame(rows)


def _comparison_pivot(grouped: pd.DataFrame, index: list[str], metric: str = "avg_net_r") -> pd.DataFrame:
    if grouped.empty:
        return pd.DataFrame()
    p = grouped.pivot_table(index=index, columns="year", values=metric, aggfunc="first")
    return p.reset_index()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sec = load_m5_csv(SECONDARY)
    duk = load_m5_csv(DUKASCOPY)

    windows = [
        (sec, pd.Timestamp("2024-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC"), 2024, "secondary"),
        (sec, pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-01-01", tz="UTC"), 2025, "secondary"),
        (duk, pd.Timestamp("2026-01-01", tz="UTC"), min(pd.Timestamp("2027-01-01", tz="UTC"), duk.index.max() + pd.Timedelta(minutes=5)), 2026, "dukascopy"),
    ]

    ann_parts = []
    summaries = []
    for data, start, end, year, feed in windows:
        _, ann, s = _run_window(data, start, end, year, feed)
        ann_parts.append(ann)
        summaries.append({"year": year, "feed": feed, **s})

    all_ann = pd.concat(ann_parts, ignore_index=True)
    summary_df = pd.DataFrame(summaries)

    by_tech = _group(all_ann, ["year", "technique"])
    by_mode = _group(all_ann, ["year", "router_mode"])
    by_state = _group(all_ann, ["year", "htf_state"])
    by_dir = _group(all_ann, ["year", "direction_text"])
    by_h4adx = _group(all_ann, ["year", "h4_adx_band"])
    by_m15adx = _group(all_ann, ["year", "m15_adx_band"])
    by_range = _group(all_ann, ["year", "range_atr_band"])
    by_session = _group(all_ann, ["year", "session"])
    by_align = _group(all_ann.assign(
        alignment=np.select(
            [all_ann.both_align_trade, all_ann.both_oppose_trade, all_ann.h1_align_trade | all_ann.h4_align_trade],
            ["BOTH_ALIGN", "BOTH_OPPOSE", "ONE_ALIGN"],
            default="NO_ALIGN",
        )
    ), ["year", "alignment"])
    by_month = _month_table(all_ann)
    streaks = _loss_streaks(all_ann)

    summary_df.to_csv(OUT / "annual_summary.csv", index=False)
    all_ann.to_csv(OUT / "annotated_trades.csv", index=False)
    by_tech.to_csv(OUT / "by_technique.csv", index=False)
    by_mode.to_csv(OUT / "by_router_mode.csv", index=False)
    by_state.to_csv(OUT / "by_htf_state.csv", index=False)
    by_dir.to_csv(OUT / "by_direction.csv", index=False)
    by_h4adx.to_csv(OUT / "by_h4_adx.csv", index=False)
    by_m15adx.to_csv(OUT / "by_m15_adx.csv", index=False)
    by_range.to_csv(OUT / "by_m15_range_atr.csv", index=False)
    by_session.to_csv(OUT / "by_session.csv", index=False)
    by_align.to_csv(OUT / "by_trade_alignment.csv", index=False)
    by_month.to_csv(OUT / "by_month.csv", index=False)
    streaks.to_csv(OUT / "loss_streaks.csv", index=False)

    # 2024-specific damage ranking: largest negative groups first.
    damage = by_tech[by_tech.year == 2024].sort_values("net_r_sum").copy()
    mode24 = by_mode[by_mode.year == 2024].sort_values("net_r_sum").copy()
    state24 = by_state[by_state.year == 2024].sort_values("net_r_sum").copy()
    adx24 = by_h4adx[by_h4adx.year == 2024].sort_values("net_r_sum").copy()
    align24 = by_align[by_align.year == 2024].sort_values("net_r_sum").copy()

    lines = [
        "# CASIO Regime Router — Why 2024 Failed",
        "",
        "## Annual context",
        "",
        summary_df.to_markdown(index=False),
        "",
        "## 2024 damage by selected technique",
        "",
        damage.to_markdown(index=False),
        "",
        "## Router mode",
        "",
        by_mode.to_markdown(index=False),
        "",
        "## HTF state",
        "",
        by_state.to_markdown(index=False),
        "",
        "## Trade-direction alignment with H1/H4",
        "",
        by_align.to_markdown(index=False),
        "",
        "## H4 ADX band",
        "",
        by_h4adx.to_markdown(index=False),
        "",
        "## M15 ADX band",
        "",
        by_m15adx.to_markdown(index=False),
        "",
        "## M15 range / ATR band",
        "",
        by_range.to_markdown(index=False),
        "",
        "## Direction",
        "",
        by_dir.to_markdown(index=False),
        "",
        "## Session",
        "",
        by_session.to_markdown(index=False),
        "",
        "## Monthly R contribution",
        "",
        by_month.to_markdown(index=False),
        "",
        "## Worst non-positive streaks",
        "",
        streaks.to_markdown(index=False),
        "",
        "## Diagnostic note",
        "",
        "This report decomposes the frozen router; it does not change thresholds or optimize 2024. The repair step should be designed only after identifying which state/technique combinations concentrate the 2024 losses, then validated separately rather than judged only on 2024.",
        "",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
