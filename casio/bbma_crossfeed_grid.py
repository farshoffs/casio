from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from casio.bbma_cleaner_robustness import (
    FEEDS, NS_DAY, _align, _features, _ohlc, load_feed, metric, replay_np,
)

OUT = Path("reports/bbma-crossfeed-grid")
OUT.mkdir(parents=True, exist_ok=True)

VARIANTS = [
    ("CSM_STRICT", 2, 1, -1, -1, -1, -1, "csm"),
    ("CSM_MED", 4, 2, -1, -1, -1, -1, "csm"),
    ("CSM_WIDE", 8, 4, -1, -1, -1, -1, "csm"),
    ("CSM_XWIDE", 12, 8, -1, -1, -1, -1, "csm"),
    ("RE_CSM_MED", -1, -1, 8, 1, -1, -1, "recsm"),
    ("RE_CSM_WIDE", -1, -1, 12, 2, -1, -1, "recsm"),
    ("RRR_MED", -1, -1, -1, -1, 4, 2, "rrr"),
    ("RRR_WIDE", -1, -1, -1, -1, 8, 4, "rrr"),
    ("UNION_MED", 4, 2, 8, 1, 4, 2, "union"),
    ("UNION_WIDE", 8, 4, 12, 2, 8, 4, "union"),
    ("STATE_TREND", -1, -1, -1, -1, -1, -1, "state"),
    ("STATE_TREND_ZZL", -1, -1, -1, -1, -1, -1, "state_zzl"),
]


def prepare_base(frame: pd.DataFrame) -> pd.DataFrame:
    m5 = _features(frame)
    m15 = _features(_ohlc(frame, "15min"))
    h1 = _features(_ohlc(frame, "1h"))
    h4 = _features(_ohlc(frame, "4h"))
    cols = [
        "re_b", "re_s", "re_b_age", "re_s_age",
        "csm_b_age", "csm_s_age", "zzl_b", "zzl_s",
        "trend_b", "trend_s",
    ]
    ctx = pd.concat(
        [
            _align(m15, cols, m5.index, "m15"),
            _align(h1, cols, m5.index, "h1"),
            _align(h4, ["trend_b", "trend_s"], m5.index, "h4"),
        ],
        axis=1,
    )
    f = pd.concat(
        [
            m5[["open", "high", "low", "close", "atr", "re_b", "re_s"]],
            ctx,
        ],
        axis=1,
    ).dropna(subset=["atr", "h4_trend_b", "h4_trend_s"])
    f["long_stop"] = f["low"].rolling(6).min() - 0.15 * f["atr"]
    f["short_stop"] = f["high"].rolling(6).max() + 0.15 * f["atr"]
    return f


def signals(f: pd.DataFrame, spec) -> tuple[pd.Series, pd.Series]:
    name, hc, mc, hr, mcr, hrr, mrr, mode = spec
    false = pd.Series(False, index=f.index)

    csm_b = ((f["h1_csm_b_age"] <= hc) & (f["m15_csm_b_age"] <= mc) & f["re_b"]) if hc >= 0 else false
    csm_s = ((f["h1_csm_s_age"] <= hc) & (f["m15_csm_s_age"] <= mc) & f["re_s"]) if hc >= 0 else false
    recsm_b = ((f["h1_re_b_age"] <= hr) & (f["m15_csm_b_age"] <= mcr) & f["re_b"]) if hr >= 0 else false
    recsm_s = ((f["h1_re_s_age"] <= hr) & (f["m15_csm_s_age"] <= mcr) & f["re_s"]) if hr >= 0 else false
    rrr_b = ((f["h1_re_b_age"] <= hrr) & (f["m15_re_b_age"] <= mrr) & f["re_b"]) if hrr >= 0 else false
    rrr_s = ((f["h1_re_s_age"] <= hrr) & (f["m15_re_s_age"] <= mrr) & f["re_s"]) if hrr >= 0 else false

    if mode == "csm":
        lb, sb = csm_b, csm_s
    elif mode == "recsm":
        lb, sb = recsm_b, recsm_s
    elif mode == "rrr":
        lb, sb = rrr_b, rrr_s
    elif mode == "union":
        lb, sb = csm_b | recsm_b | rrr_b, csm_s | recsm_s | rrr_s
    elif mode in ("state", "state_zzl"):
        lb = f["re_b"] & f["h1_trend_b"] & f["m15_trend_b"]
        sb = f["re_s"] & f["h1_trend_s"] & f["m15_trend_s"]
        if mode == "state_zzl":
            lb = lb & f["h1_zzl_b"]
            sb = sb & f["h1_zzl_s"]
    else:
        raise ValueError(mode)

    lb = lb & f["h4_trend_b"]
    sb = sb & f["h4_trend_s"]
    return lb, sb


def replay_variant(f: pd.DataFrame, spec) -> pd.DataFrame:
    lb, sb = signals(f, spec)
    idx_ns = f.index.view("int64")
    daycodes = (idx_ns // NS_DAY).astype(np.int64)
    o = f["open"].to_numpy(float)
    h = f["high"].to_numpy(float)
    l = f["low"].to_numpy(float)
    c = f["close"].to_numpy(float)
    a = f["atr"].to_numpy(float)
    ls = f["long_stop"].to_numpy(float)
    ss = f["short_stop"].to_numpy(float)

    r, ei, xi, side = replay_np(
        o, h, l, c, a,
        lb.to_numpy(bool), sb.to_numpy(bool), ls, ss, daycodes,
        4.0, 8.0, 0.20, 1.25, 0.25,
        1.0, 2.0, 36, 3,
    )
    sig = ei - 1
    entry = o[ei]
    risk = np.where(side == 1, entry - ls[sig], ss[sig] - entry)
    t = pd.DataFrame({
        "entry_time": f.index[ei],
        "side": side,
        "entry": entry,
        "risk": risk,
        "gross_r": r,
    })
    t["cost_r"] = (0.1714 + 0.00007 * t["entry"]) / t["risk"]
    t["net_r"] = t["gross_r"] - t["cost_r"]
    return t


def summarize(feed: str, variant: str, t: pd.DataFrame) -> dict:
    x = t[t["entry_time"] >= pd.Timestamp("2017-01-01", tz="UTC")].copy()
    if x.empty:
        return {
            "feed": feed, "variant": variant, "start": None, "end": None,
            "trades": 0, "trades_per_month": 0.0,
            "gross_avg_r": 0.0, "gross_pf": 0.0, "net_avg_r": 0.0, "net_pf": 0.0,
        }
    span_months = max(
        1.0,
        (x["entry_time"].max() - x["entry_time"].min()).total_seconds()
        / (365.25 / 12.0 * 86400.0),
    )
    gm, nm = metric(x["gross_r"]), metric(x["net_r"])
    return {
        "feed": feed, "variant": variant,
        "start": x["entry_time"].min().isoformat(),
        "end": x["entry_time"].max().isoformat(),
        "trades": int(len(x)), "trades_per_month": float(len(x) / span_months),
        "gross_avg_r": gm["avg_r"], "gross_pf": gm["pf"],
        "net_avg_r": nm["avg_r"], "net_pf": nm["pf"],
    }


def run() -> None:
    rows = []
    for feed, path in FEEDS.items():
        print(f"Loading {feed}")
        f = prepare_base(load_feed(path))
        for spec in VARIANTS:
            t = replay_variant(f, spec)
            rows.append(summarize(feed, spec[0], t))

    out = pd.DataFrame(rows)
    out.to_csv(OUT / "grid.csv", index=False)

    pivot = []
    for name in [v[0] for v in VARIANTS]:
        rec = {"variant": name}
        for feed in FEEDS:
            row = out[(out.feed == feed) & (out.variant == name)].iloc[0]
            rec[f"{feed}_trades_mo"] = float(row.trades_per_month)
            rec[f"{feed}_net_avg_r"] = float(row.net_avg_r)
            rec[f"{feed}_net_pf"] = float(row.net_pf)
        rec["min_net_avg_r"] = min(rec[f"{feed}_net_avg_r"] for feed in FEEDS)
        rec["min_trades_mo"] = min(rec[f"{feed}_trades_mo"] for feed in FEEDS)
        pivot.append(rec)
    p = pd.DataFrame(pivot).sort_values(["min_net_avg_r", "min_trades_mo"], ascending=False)
    p.to_csv(OUT / "crossfeed_rank.csv", index=False)

    lines = [
        "# BBMA Cross-Feed State-Freshness Grid",
        "",
        "All variants keep M5 Re-entry as the entry trigger, previous-closed HTF context, H4 trend direction, next-M5-open execution, 1.0-2.0 ATR structural stop, 36-bar cooldown, max 3/day, +1.25R -> +0.25R protection, 20% at 4R and 80% at 8R.",
        "",
        "| Variant | Duk trades/mo | Duk net R/trade | Duk PF | Octa trades/mo | Octa net R/trade | Octa PF | Min feed R |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in p.iterrows():
        lines.append(
            f"| {r['variant']} | {r['DUKASCOPY_trades_mo']:.2f} | {r['DUKASCOPY_net_avg_r']:.3f} | {r['DUKASCOPY_net_pf']:.2f} | "
            f"{r['OCTAFX_trades_mo']:.2f} | {r['OCTAFX_net_avg_r']:.3f} | {r['OCTAFX_net_pf']:.2f} | {r['min_net_avg_r']:.3f} |"
        )

    best = p.iloc[0].to_dict()
    lines.extend([
        "",
        "## Highest minimum-feed expectancy",
        "",
        f"{best['variant']} with minimum feed net expectancy {best['min_net_avg_r']:.3f}R/trade and minimum feed frequency {best['min_trades_mo']:.2f}/month.",
    ])
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "summary.json").write_text(json.dumps({"rank": pivot}, indent=2), encoding="utf-8")
    print((OUT / "REPORT.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    run()
