from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from numba import njit


OUT = Path("reports/bbma-cleaner-robustness")
OUT.mkdir(parents=True, exist_ok=True)

FEEDS = {
    "DUKASCOPY": Path("data/xauusd_m5_dukascopy_research.csv"),
    "OCTAFX": Path("data/xauusd_m5_secondary_octafx_mt4.csv"),
}

NS_DAY = 86_400_000_000_000


def _rma(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def _atr(x: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = x["close"].shift(1)
    tr = pd.concat(
        [
            x["high"] - x["low"],
            (x["high"] - pc).abs(),
            (x["low"] - pc).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return _rma(tr, n)


def _wma(s: pd.Series, n: int) -> pd.Series:
    # Newest observation gets the largest weight.
    den = n * (n + 1) / 2.0
    out = pd.Series(0.0, index=s.index)
    for j in range(n):
        out = out + (j + 1) * s.shift(n - 1 - j)
    return out / den


def _bars_since(event: pd.Series) -> pd.Series:
    ev = event.fillna(False).to_numpy(dtype=bool)
    idx = np.arange(len(ev))
    last = np.where(ev, idx, -1)
    last = np.maximum.accumulate(last)
    age = idx - last
    age[last < 0] = 100_000
    return pd.Series(age, index=event.index, dtype="int32")


def _ohlc(frame: pd.DataFrame, rule: str) -> pd.DataFrame:
    return (
        frame[["open", "high", "low", "close"]]
        .resample(rule, label="left", closed="left")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        .dropna()
    )


def _features(frame: pd.DataFrame) -> pd.DataFrame:
    x = frame.copy()
    x["mid"] = x["close"].rolling(20).mean()
    sd = x["close"].rolling(20).std(ddof=0)
    x["bb_u"] = x["mid"] + 2.0 * sd
    x["bb_l"] = x["mid"] - 2.0 * sd
    x["ema50"] = x["close"].ewm(span=50, adjust=False, min_periods=50).mean()
    x["ma5h"] = _wma(x["high"], 5)
    x["ma5l"] = _wma(x["low"], 5)
    x["ma10h"] = _wma(x["high"], 10)
    x["ma10l"] = _wma(x["low"], 10)
    x["atr"] = _atr(x)

    x["csm_b"] = x["close"] > x["bb_u"]
    x["csm_s"] = x["close"] < x["bb_l"]

    cross_b = (
        (x["close"] > x["ma5h"])
        & (x["close"] > x["ma10h"])
        & (x["close"] > x["mid"])
        & (x["close"] > x["open"])
    )
    cross_s = (
        (x["close"] < x["ma5l"])
        & (x["close"] < x["ma10l"])
        & (x["close"] < x["mid"])
        & (x["close"] < x["open"])
    )
    x["csak_b"] = cross_b & ~cross_b.shift(1).fillna(False)
    x["csak_s"] = cross_s & ~cross_s.shift(1).fillna(False)

    sig_b = x["csm_b"] | x["csak_b"]
    sig_s = x["csm_s"] | x["csak_s"]
    x["sig_b_age"] = _bars_since(sig_b)
    x["sig_s_age"] = _bars_since(sig_s)
    x["csm_b_age"] = _bars_since(x["csm_b"])
    x["csm_s_age"] = _bars_since(x["csm_s"])

    zone_b = pd.concat([x["ma5l"], x["ma10l"], x["mid"]], axis=1).max(axis=1)
    zone_s = pd.concat([x["ma5h"], x["ma10h"], x["mid"]], axis=1).min(axis=1)

    re_b = (
        x["sig_b_age"].between(1, 12)
        & (x["low"] <= zone_b)
        & (x["close"] > x["ma5l"])
        & (x["close"] > x["ma10l"])
        & (x["close"] > x["open"])
    )
    re_s = (
        x["sig_s_age"].between(1, 12)
        & (x["high"] >= zone_s)
        & (x["close"] < x["ma5h"])
        & (x["close"] < x["ma10h"])
        & (x["close"] < x["open"])
    )
    x["re_b"] = re_b & ~re_b.shift(1).fillna(False)
    x["re_s"] = re_s & ~re_s.shift(1).fillna(False)
    x["re_b_age"] = _bars_since(x["re_b"])
    x["re_s_age"] = _bars_since(x["re_s"])

    x["zzl_b"] = (
        (x["ma5l"] > x["mid"])
        & (x["ma10l"] > x["mid"])
        & (x["mid"] > x["ema50"])
        & (x["close"] > x["ema50"])
    )
    x["zzl_s"] = (
        (x["ma5h"] < x["mid"])
        & (x["ma10h"] < x["mid"])
        & (x["mid"] < x["ema50"])
        & (x["close"] < x["ema50"])
    )
    x["trend_b"] = (x["mid"] > x["ema50"]) & (x["close"] > x["ema50"])
    x["trend_s"] = (x["mid"] < x["ema50"]) & (x["close"] < x["ema50"])
    return x


def _align(htf: pd.DataFrame, cols: list[str], idx: pd.DatetimeIndex, prefix: str) -> pd.DataFrame:
    # Previous closed HTF candle only.
    z = htf[cols].shift(1).reindex(idx, method="ffill")
    return z.rename(columns={c: f"{prefix}_{c}" for c in cols})


def load_feed(path: Path) -> pd.DataFrame:
    x = pd.read_csv(path)
    if "timestamp" not in x.columns:
        if "time_utc" in x.columns:
            x = x.rename(columns={"time_utc": "timestamp"})
        else:
            raise ValueError(f"{path}: no timestamp column")
    req = ["timestamp", "open", "high", "low", "close"]
    x = x[req].copy()
    x["timestamp"] = pd.to_datetime(x["timestamp"], utc=True, errors="raise")
    for c in ["open", "high", "low", "close"]:
        x[c] = pd.to_numeric(x[c], errors="raise")
    return x.drop_duplicates("timestamp").sort_values("timestamp").set_index("timestamp")


def prepare(frame: pd.DataFrame) -> pd.DataFrame:
    m5 = _features(frame)
    m15 = _features(_ohlc(frame, "15min"))
    h1 = _features(_ohlc(frame, "1h"))
    h4 = _features(_ohlc(frame, "4h"))

    cols = [
        "re_b", "re_s", "re_b_age", "re_s_age",
        "csm_b_age", "csm_s_age", "zzl_b", "zzl_s",
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

    # Frozen robustness entry rules:
    # A) fresh H1 CSM + fresh M15 CSM + M5 Re-entry
    # B) H1 Re-entry state + exact previous-closed M15 CSM + M5 Re-entry
    # C) exact previous-closed H1 Re-entry + exact previous-closed M15 Re-entry + M5 Re-entry
    a_b = (f["h1_csm_b_age"] <= 2) & (f["m15_csm_b_age"] <= 1) & f["re_b"]
    a_s = (f["h1_csm_s_age"] <= 2) & (f["m15_csm_s_age"] <= 1) & f["re_s"]
    b_b = (f["h1_re_b_age"] <= 4) & (f["m15_csm_b_age"] == 0) & f["re_b"]
    b_s = (f["h1_re_s_age"] <= 4) & (f["m15_csm_s_age"] == 0) & f["re_s"]
    c_b = (f["h1_re_b_age"] == 0) & (f["m15_re_b_age"] == 0) & f["re_b"]
    c_s = (f["h1_re_s_age"] == 0) & (f["m15_re_s_age"] == 0) & f["re_s"]

    f["long_signal"] = (a_b | b_b | c_b) & f["h4_trend_b"]
    # Short side keeps the stricter H1 Zero-Loss gate from the cleaner-core research.
    f["short_signal"] = (a_s | b_s | c_s) & f["h4_trend_s"] & f["h1_zzl_s"]

    f["long_stop"] = f["low"].rolling(6).min() - 0.15 * f["atr"]
    f["short_stop"] = f["high"].rolling(6).max() + 0.15 * f["atr"]
    return f


@njit
def replay_np(
    o, h, l, c, atr, long_signal, short_signal, long_stop, short_stop, daycodes,
    target1, target2, first_weight, be_trigger, be_lock,
    min_risk_atr, max_risk_atr, cooldown, max_per_day,
):
    n = len(o)
    cap = n // 8 + 1000
    rs = np.empty(cap, np.float64)
    entries = np.empty(cap, np.int64)
    exits = np.empty(cap, np.int64)
    sides = np.empty(cap, np.int8)
    count = 0

    pos = 0
    entry = stop = risk = t1 = t2 = 0.0
    rem = realized = 0.0
    entry_i = -1
    last_entry_i = -10**9
    current_day = -10**9
    day_count = 0
    pending_i = -1
    pending_side = 0
    pending_stop = 0.0

    for i in range(1, n):
        d = daycodes[i]
        if d != current_day:
            current_day = d
            day_count = 0

        if pos == 0 and pending_i == i:
            side = pending_side
            e = o[i]
            st = pending_stop
            a = atr[i - 1]
            rrisk = (e - st) if side == 1 else (st - e)
            risk_atr = rrisk / a if a > 0 else 1e9
            if (
                rrisk > 0
                and min_risk_atr <= risk_atr <= max_risk_atr
                and day_count < max_per_day
                and i - last_entry_i >= cooldown
            ):
                pos = side
                entry = e
                stop = st
                risk = rrisk
                t1 = entry + side * target1 * risk
                t2 = entry + side * target2 * risk
                rem = 1.0
                realized = 0.0
                entry_i = i
                last_entry_i = i
                day_count += 1
            pending_i = -1

        if pos != 0:
            hit_stop = l[i] <= stop if pos == 1 else h[i] >= stop
            hit_t1 = h[i] >= t1 if pos == 1 else l[i] <= t1
            hit_t2 = h[i] >= t2 if pos == 1 else l[i] <= t2

            # Conservative stop-first collision rule.
            if hit_stop:
                sr = (stop - entry) / risk if pos == 1 else (entry - stop) / risk
                realized += rem * sr
                rs[count] = realized
                entries[count] = entry_i
                exits[count] = i
                sides[count] = pos
                count += 1
                pos = 0
                rem = 0.0
                continue

            if rem == 1.0 and hit_t1:
                realized += first_weight * target1
                rem = 1.0 - first_weight
                if hit_t2:
                    realized += rem * target2
                    rs[count] = realized
                    entries[count] = entry_i
                    exits[count] = i
                    sides[count] = pos
                    count += 1
                    pos = 0
                    rem = 0.0
                    continue
            elif 0.0 < rem < 1.0 and hit_t2:
                realized += rem * target2
                rs[count] = realized
                entries[count] = entry_i
                exits[count] = i
                sides[count] = pos
                count += 1
                pos = 0
                rem = 0.0
                continue

            # Protection becomes active on the next M5 bar.
            excursion = (h[i] - entry) / risk if pos == 1 else (entry - l[i]) / risk
            if excursion >= be_trigger:
                new_stop = entry + pos * be_lock * risk
                if pos == 1:
                    if new_stop > stop:
                        stop = new_stop
                else:
                    if new_stop < stop:
                        stop = new_stop

        if pos == 0 and pending_i == -1 and i + 1 < n:
            if day_count < max_per_day and i + 1 - last_entry_i >= cooldown:
                lb = long_signal[i]
                sb = short_signal[i]
                if lb or sb:
                    side = 1 if (lb and not sb) else -1 if (sb and not lb) else (1 if c[i] >= o[i] else -1)
                    pending_i = i + 1
                    pending_side = side
                    pending_stop = long_stop[i] if side == 1 else short_stop[i]

    return rs[:count], entries[:count], exits[:count], sides[:count]


def replay(f: pd.DataFrame, target1=4.0, target2=5.0, first_weight=0.25, min_atr=1.0, max_atr=1.8) -> pd.DataFrame:
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
        f["long_signal"].to_numpy(bool), f["short_signal"].to_numpy(bool),
        ls, ss, daycodes,
        target1, target2, first_weight, 1.0, 0.25,
        min_atr, max_atr, 36, 3,
    )
    sig = ei - 1
    entry = o[ei]
    risk = np.where(side == 1, entry - ls[sig], ss[sig] - entry)
    t = pd.DataFrame(
        {
            "entry_time": f.index[ei],
            "exit_time": f.index[xi],
            "side": side,
            "entry": entry,
            "risk": risk,
            "gross_r": r,
        }
    )
    # Current FxPro indicative cost stress models, applied consistently to all feeds.
    t["standard_r"] = t["gross_r"] - 0.25 / t["risk"]
    t["ctrader_r"] = t["gross_r"] - (0.1714 + 0.00007 * t["entry"]) / t["risk"]
    t["ctrader_slip10_r"] = t["gross_r"] - (0.2714 + 0.00007 * t["entry"]) / t["risk"]
    return t


def metric(r: pd.Series) -> dict:
    x = r.astype(float).to_numpy()
    if len(x) == 0:
        return {"trades": 0, "positive_rate": 0.0, "avg_r": 0.0, "pf": 0.0, "net_r": 0.0}
    p = x[x > 0].sum()
    n = -x[x < 0].sum()
    return {
        "trades": int(len(x)),
        "positive_rate": float((x > 0).mean() * 100.0),
        "avg_r": float(x.mean()),
        "pf": float(p / n) if n > 0 else float("inf"),
        "net_r": float(x.sum()),
    }


def money_path(r: pd.Series, risk_pct: float = 0.05) -> tuple[float, float]:
    eq = 100.0
    peak = eq
    max_dd = 0.0
    for rr in r.astype(float):
        eq *= 1.0 + risk_pct * rr
        peak = max(peak, eq)
        if peak > 0:
            max_dd = max(max_dd, (peak - eq) / peak)
    return float(eq), float(max_dd * 100.0)


def summarize(feed: str, t: pd.DataFrame) -> tuple[list[dict], dict]:
    t = t.copy()
    t["year"] = t["entry_time"].dt.year
    rows = []
    for y, g in t[t["year"] >= 2017].groupby("year"):
        for model in ["gross_r", "standard_r", "ctrader_r", "ctrader_slip10_r"]:
            m = metric(g[model])
            end_rm, dd = money_path(g[model])
            rows.append(
                {
                    "feed": feed,
                    "year": int(y),
                    "model": model,
                    **m,
                    "end_rm_5pct": end_rm,
                    "max_dd_pct_5pct": dd,
                }
            )

    x = t[t["entry_time"] >= pd.Timestamp("2017-01-01", tz="UTC")].copy()
    months = max(
        1.0,
        (x["entry_time"].max() - x["entry_time"].min()).total_seconds() / (365.25 / 12.0 * 86400.0)
        if not x.empty else 1.0,
    )
    overall = {
        "feed": feed,
        "start": x["entry_time"].min().isoformat() if not x.empty else None,
        "end": x["entry_time"].max().isoformat() if not x.empty else None,
        "trades": int(len(x)),
        "trades_per_month": float(len(x) / months),
        "gross": metric(x["gross_r"]),
        "standard": metric(x["standard_r"]),
        "ctrader": metric(x["ctrader_r"]),
        "ctrader_slip10": metric(x["ctrader_slip10_r"]),
    }
    return rows, overall


def exact_overlap(a: pd.DataFrame, b: pd.DataFrame, start: str, end: str) -> dict:
    aa = a[(a["entry_time"] >= start) & (a["entry_time"] < end)]
    bb = b[(b["entry_time"] >= start) & (b["entry_time"] < end)]
    aset = {(int(ts.value), int(side)) for ts, side in zip(aa["entry_time"], aa["side"])}
    bset = {(int(ts.value), int(side)) for ts, side in zip(bb["entry_time"], bb["side"])}
    same = len(aset & bset)
    union = len(aset | bset)
    return {
        "period": f"{start} to {end}",
        "a_trades": len(aset),
        "b_trades": len(bset),
        "same_timestamp_side": same,
        "jaccard": float(same / union) if union else 0.0,
        "a_match_rate": float(same / len(aset)) if aset else 0.0,
        "b_match_rate": float(same / len(bset)) if bset else 0.0,
    }


def run() -> None:
    yearly = []
    overall = []
    trades: dict[str, pd.DataFrame] = {}
    sensitivity = []

    for feed, path in FEEDS.items():
        print(f"Loading {feed}: {path}")
        raw = load_feed(path)
        f = prepare(raw)

        base = replay(f, 4.0, 5.0, 0.25, 1.0, 1.8)
        trades[feed] = base
        yr, ov = summarize(feed, base)
        yearly.extend(yr)
        overall.append(ov)

        for name, t1, t2, w1, min_atr, max_atr in [
            ("T3_T5_W25", 3.0, 5.0, 0.25, 1.0, 1.8),
            ("BASE_T4_T5_W25", 4.0, 5.0, 0.25, 1.0, 1.8),
            ("T4_T5_W50", 4.0, 5.0, 0.50, 1.0, 1.8),
            ("STOP_0.8_1.8", 4.0, 5.0, 0.25, 0.8, 1.8),
            ("STOP_1.0_2.0", 4.0, 5.0, 0.25, 1.0, 2.0),
            ("STOP_1.2_2.0", 4.0, 5.0, 0.25, 1.2, 2.0),
        ]:
            tt = replay(f, t1, t2, w1, min_atr, max_atr)
            cut = tt[tt["entry_time"] >= pd.Timestamp("2017-01-01", tz="UTC")]
            months = max(
                1.0,
                (cut["entry_time"].max() - cut["entry_time"].min()).total_seconds() / (365.25 / 12.0 * 86400.0)
                if not cut.empty else 1.0,
            )
            sensitivity.append(
                {
                    "feed": feed,
                    "variant": name,
                    "trades": len(cut),
                    "trades_per_month": len(cut) / months,
                    "gross_avg_r": metric(cut["gross_r"])["avg_r"],
                    "gross_pf": metric(cut["gross_r"])["pf"],
                    "ctrader_avg_r": metric(cut["ctrader_r"])["avg_r"],
                    "ctrader_pf": metric(cut["ctrader_r"])["pf"],
                }
            )

    pd.DataFrame(yearly).to_csv(OUT / "yearly.csv", index=False)
    pd.DataFrame(sensitivity).to_csv(OUT / "sensitivity.csv", index=False)

    overlaps = []
    if "DUKASCOPY" in trades and "OCTAFX" in trades:
        overlaps.append(exact_overlap(trades["DUKASCOPY"], trades["OCTAFX"], "2024-01-01", "2025-01-01"))
        overlaps.append(exact_overlap(trades["DUKASCOPY"], trades["OCTAFX"], "2025-01-01", "2026-01-01"))

    payload = {"overall": overall, "overlap": overlaps}
    (OUT / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# BBMA Cleaner Core — Robustness Stage",
        "",
        "Frozen rules: causal H4/H1/M15/M5 BBMA; fresh CSM/RE combinations; short H1 ZZL; next-M5-open execution; structural stop 1.0–1.8 M5 ATR; 36-bar cooldown; max 3/day; +1R -> +0.25R protection; 25% at 4R + 75% at 5R.",
        "",
        "## Feed summary",
        "",
        "| Feed | Period | Trades | Trades/mo | Gross avg R | Gross PF | FxPro cTrader avg R | FxPro cTrader PF |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for o in overall:
        lines.append(
            f"| {o['feed']} | {o['start']} → {o['end']} | {o['trades']} | {o['trades_per_month']:.2f} | "
            f"{o['gross']['avg_r']:.3f} | {o['gross']['pf']:.2f} | {o['ctrader']['avg_r']:.3f} | {o['ctrader']['pf']:.2f} |"
        )
    lines.extend(["", "## Exact entry overlap", ""])
    for o in overlaps:
        lines.append(
            f"- {o['period']}: exact same timestamp+side {o['same_timestamp_side']} trades; "
            f"Jaccard {o['jaccard']:.3f}; Dukascopy match {o['a_match_rate']:.1%}; OctaFX match {o['b_match_rate']:.1%}."
        )
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print((OUT / "REPORT.md").read_text(encoding="utf-8"))
    print((OUT / "summary.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    run()
