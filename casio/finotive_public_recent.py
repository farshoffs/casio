from __future__ import annotations

from pathlib import Path
import json
import math
import re

import numpy as np
import pandas as pd

START_BALANCE = 2500.0
RISK = 0.005
COST_R = 0.05


def _safe(x):
    if x is pd.NaT or (not isinstance(x, (dict, list, str, bytes)) and pd.isna(x)):
        return None
    if isinstance(x, dict):
        return {str(k): _safe(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_safe(v) for v in x]
    if isinstance(x, pd.Timestamp):
        return x.isoformat()
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, (np.floating, float)):
        y = float(x)
        return y if math.isfinite(y) else None
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    return x


def load_mt5(path: str | Path, server_tz: str = "Europe/Helsinki") -> pd.DataFrame:
    raw = pd.read_csv(path)
    raw.columns = [str(c).strip().lower().replace("<", "").replace(">", "") for c in raw.columns]

    # Common MT5 / generic layouts.
    if "time" in raw.columns:
        ts = pd.to_datetime(raw["time"], errors="coerce")
    elif "date" in raw.columns and "time" in raw.columns:
        ts = pd.to_datetime(raw["date"].astype(str) + " " + raw["time"].astype(str), errors="coerce")
    elif "date" in raw.columns:
        ts = pd.to_datetime(raw["date"], errors="coerce")
    elif len(raw.columns) >= 2 and ("date" in raw.columns[0] or "time" in raw.columns[0]):
        ts = pd.to_datetime(raw.iloc[:, 0].astype(str) + " " + raw.iloc[:, 1].astype(str), errors="coerce")
    else:
        # Inspect first one/two fields heuristically.
        a = raw.iloc[:, 0].astype(str)
        b = raw.iloc[:, 1].astype(str) if raw.shape[1] > 1 else pd.Series("", index=raw.index)
        combo = pd.to_datetime(a + " " + b, errors="coerce")
        ts = combo if combo.notna().mean() > 0.8 else pd.to_datetime(a, errors="coerce")

    # If source is tz-naive, MT5 export is treated as EET/EEST broker server time.
    if getattr(ts.dt, "tz", None) is None:
        ts = ts.dt.tz_localize(server_tz, ambiguous="infer", nonexistent="shift_forward").dt.tz_convert("UTC")
    else:
        ts = ts.dt.tz_convert("UTC")

    aliases = {
        "open": ["open"],
        "high": ["high"],
        "low": ["low"],
        "close": ["close"],
        "volume": ["tick_volume", "tickvol", "volume", "vol"],
    }
    cols = {}
    for target, choices in aliases.items():
        for c in choices:
            if c in raw.columns:
                cols[target] = c
                break
    if not all(k in cols for k in ("open", "high", "low", "close")):
        # MT5 angle-bracket headers become lower-case names above.
        raise ValueError(f"Cannot identify OHLC columns in {path}: {list(raw.columns)}")

    out = pd.DataFrame(index=pd.DatetimeIndex(ts))
    for c in ("open", "high", "low", "close"):
        out[c] = pd.to_numeric(raw[cols[c]], errors="coerce").to_numpy()
    out["volume"] = pd.to_numeric(raw[cols.get("volume", cols["close"])], errors="coerce").fillna(0).to_numpy()
    out = out[~out.index.isna()].dropna(subset=["open", "high", "low", "close"])
    return out.sort_index().loc[lambda x: ~x.index.duplicated(keep="last")]


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df.close.shift(1)
    tr = pd.concat([(df.high - df.low), (df.high - pc).abs(), (df.low - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def _resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    return df.resample(rule, label="left", closed="left", origin="epoch").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), volume=("volume", "sum")
    ).dropna(subset=["open", "high", "low", "close"])


def _scan(m5: pd.DataFrame, fill_i: int, d: int, entry: float, stop: float, target: float, max_bars: int) -> tuple[int, float, str]:
    risk = abs(entry - stop)
    end = min(len(m5), fill_i + max_bars)
    for j in range(fill_i, end):
        lo = float(m5.low.iat[j]); hi = float(m5.high.iat[j]); cl = float(m5.close.iat[j])
        hs = lo <= stop if d == 1 else hi >= stop
        ht = hi >= target if d == 1 else lo <= target
        if hs and ht:
            return j, -1.0, "stop_same_bar"
        if hs:
            return j, -1.0, "stop"
        if ht:
            return j, abs(target - entry) / risk, "target"
        if j == end - 1:
            return j, (cl - entry) / risk * d, "time"
    return end - 1, 0.0, "time"


def london_open(m5: pd.DataFrame, target_r: float, reverse: bool = False) -> pd.DataFrame:
    h1 = _resample(m5, "1h")
    h1atr = _atr(h1).reindex(m5.index, method="ffill")

    lon = m5.index.tz_convert("Europe/London")
    mins = lon.hour * 60 + lon.minute
    ldate = pd.Series(lon.date, index=m5.index)
    first = (mins >= 8 * 60) & (mins < 8 * 60 + 30)
    pos = pd.Series(np.arange(len(m5)), index=m5.index)

    rows = []
    for _, g in m5[first].groupby(ldate[first]):
        if len(g) < 5:
            continue
        last = g.index[-1]
        i = int(pos.loc[last]) + 1
        if i >= len(m5):
            continue
        move = float(g.close.iloc[-1] - g.open.iloc[0])
        if move == 0:
            continue
        d = 1 if move > 0 else -1
        if reverse:
            d *= -1
        entry = float(m5.open.iat[i])
        orng = float(g.high.max() - g.low.min())
        a = float(h1atr.iat[i]) if np.isfinite(h1atr.iat[i]) else np.nan
        dist = max(orng, 0.30 * a if np.isfinite(a) else 0.0)
        if not np.isfinite(dist) or dist <= 0:
            continue
        stop = entry - d * dist
        target = entry + d * target_r * dist
        j, r, reason = _scan(m5, i, d, entry, stop, target, 42)
        rows.append({
            "entry_time": m5.index[i], "exit_time": m5.index[j] + pd.Timedelta(minutes=5),
            "direction": d, "net_r": r - COST_R, "reason": reason,
        })
    return pd.DataFrame(rows)


def choch_fvg_fade(m5: pd.DataFrame, target_r: float, entry_model: str) -> pd.DataFrame:
    h = _resample(m5, "1h")
    h["atr"] = _atr(h)
    h["hi10"] = h.high.shift(1).rolling(10, min_periods=10).max()
    h["lo10"] = h.low.shift(1).rolling(10, min_periods=10).min()
    bull = (h.close > h.hi10) & (h.close > h.open) & (h.low > h.high.shift(2))
    bear = (h.close < h.lo10) & (h.close < h.open) & (h.high < h.low.shift(2))
    pos = pd.Series(np.arange(len(m5)), index=m5.index)
    rows = []

    for k in np.flatnonzero((bull | bear).fillna(False).to_numpy()):
        textbook = 1 if bool(bull.iat[k]) else -1
        d = -textbook
        signal_close = h.index[k] + pd.Timedelta(hours=1)
        after = m5.index[(m5.index >= signal_close) & (m5.index < signal_close + pd.Timedelta(hours=12))]
        if not len(after):
            continue

        if entry_model == "CLOSE":
            i = int(pos.loc[after[0]])
            entry = float(m5.open.iat[i])
        else:
            if textbook == 1:
                zone_a, zone_b = float(h.high.iat[k - 2]), float(h.low.iat[k])
            else:
                zone_a, zone_b = float(h.high.iat[k]), float(h.low.iat[k - 2])
            entry = (zone_a + zone_b) / 2.0
            i = None
            for ts in after:
                j = int(pos.loc[ts])
                if float(m5.low.iat[j]) <= entry <= float(m5.high.iat[j]):
                    i = j
                    break
            if i is None:
                continue

        a = float(h.atr.iat[k])
        if not np.isfinite(a) or a <= 0:
            continue
        # Minimum stop-distance floor as suggested by empirical replication.
        if d == 1:
            structural = float(h.low.iloc[max(0, k - 2):k + 1].min())
            stop = min(structural - 0.05 * a, entry - 0.35 * a)
        else:
            structural = float(h.high.iloc[max(0, k - 2):k + 1].max())
            stop = max(structural + 0.05 * a, entry + 0.35 * a)
        risk = abs(entry - stop)
        if risk <= 0:
            continue
        target = entry + d * target_r * risk
        j, r, reason = _scan(m5, i, d, entry, stop, target, 144)
        rows.append({
            "entry_time": m5.index[i], "exit_time": m5.index[j] + pd.Timedelta(minutes=5),
            "direction": d, "net_r": r - COST_R, "reason": reason,
        })
    return pd.DataFrame(rows)


def asia_sweep_cont(m5: pd.DataFrame, target_r: float) -> pd.DataFrame:
    lon = m5.index.tz_convert("Europe/London")
    mins = lon.hour * 60 + lon.minute
    ldate = pd.Series(lon.date, index=m5.index)
    asia = (mins >= 2 * 60) & (mins < 7 * 60)  # avoids Finotive 22:00-01:59 UTC focus
    ar = m5[asia].groupby(ldate[asia]).agg(ah=("high", "max"), al=("low", "min"))
    ah = ldate.map(ar.ah); al = ldate.map(ar.al)

    h1 = _resample(m5, "1h")
    h1atr = _atr(h1).reindex(m5.index, method="ffill")
    london = (mins >= 7 * 60) & (mins < 12 * 60)
    up = london & ah.notna() & (m5.high > ah) & (m5.close > ah)
    dn = london & al.notna() & (m5.low < al) & (m5.close < al)

    rows = []
    used = set()
    for i in np.flatnonzero((up | dn).fillna(False).to_numpy()):
        if i + 1 >= len(m5):
            continue
        d = 1 if bool(up.iat[i]) else -1
        key = (ldate.iat[i], d)
        if key in used:
            continue
        used.add(key)
        entry = float(m5.open.iat[i + 1])
        a = float(h1atr.iat[i]) if np.isfinite(h1atr.iat[i]) else np.nan
        if not np.isfinite(a) or a <= 0:
            continue
        level = float(ah.iat[i] if d == 1 else al.iat[i])
        dist = max(0.35 * a, abs(entry - level) + 0.05 * a)
        stop = entry - d * dist
        target = entry + d * target_r * dist
        j, r, reason = _scan(m5, i + 1, d, entry, stop, target, 96)
        rows.append({
            "entry_time": m5.index[i + 1], "exit_time": m5.index[j] + pd.Timedelta(minutes=5),
            "direction": d, "net_r": r - COST_R, "reason": reason,
        })
    return pd.DataFrame(rows)


def metrics(tr: pd.DataFrame, a: str, b: str) -> dict:
    if tr is None or tr.empty:
        return {"trades": 0, "exp_r": None, "pf": None, "wr": None}
    a = pd.Timestamp(a, tz="UTC"); b = pd.Timestamp(b, tz="UTC")
    t = pd.to_datetime(tr.entry_time, utc=True)
    r = pd.to_numeric(tr.loc[(t >= a) & (t < b), "net_r"], errors="coerce").dropna()
    if r.empty:
        return {"trades": 0, "exp_r": None, "pf": None, "wr": None}
    w = r[r > 0]; l = r[r < 0]
    return {
        "trades": int(len(r)),
        "exp_r": float(r.mean()),
        "pf": float(w.sum() / (-l.sum())) if len(l) else 999.0,
        "wr": float((r > 0).mean() * 100.0),
    }


def month_return(tr: pd.DataFrame, month: str) -> dict:
    a = pd.Timestamp(month + "-01", tz="UTC")
    b = a + pd.offsets.MonthBegin(1)
    if tr.empty:
        x = tr
    else:
        t = pd.to_datetime(tr.entry_time, utc=True)
        x = tr[(t >= a) & (t < b)].sort_values("entry_time")
    eq = START_BALANCE
    peak = eq
    maxdd = 0.0
    daily = {}
    free = pd.Timestamp("1900-01-01", tz="UTC")
    used = 0
    for z in x.itertuples(index=False):
        et = pd.Timestamp(z.entry_time); xt = pd.Timestamp(z.exit_time)
        if et < free:
            continue
        ny = et.tz_convert("America/New_York")
        td = (ny - pd.Timedelta(hours=17)).strftime("%Y-%m-%d")
        daily.setdefault(td, {"start": eq, "pnl": 0.0, "losses": 0})
        if daily[td]["losses"] >= 2:
            continue
        pnl = eq * RISK * float(z.net_r)
        eq += pnl
        daily[td]["pnl"] += pnl
        if float(z.net_r) < 0:
            daily[td]["losses"] += 1
        free = xt
        used += 1
        peak = max(peak, eq)
        maxdd = max(maxdd, (peak - eq) / peak * 100.0)
    mpd = sum(v["pnl"] / START_BALANCE * 100.0 >= 0.5 for v in daily.values())
    return {
        "return_pct": (eq / START_BALANCE - 1.0) * 100.0,
        "trades": used,
        "mpd": int(mpd),
        "maxdd_pct": maxdd,
    }


def evaluate(name: str, tr: pd.DataFrame) -> dict:
    dev = metrics(tr, "2024-07-01", "2025-07-01")
    val = metrics(tr, "2025-07-01", "2026-01-01")
    row = {"candidate": name, **{f"dev_{k}": v for k, v in dev.items()}, **{f"val_{k}": v for k, v in val.items()}}
    for m in ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]:
        z = month_return(tr, m)
        for k, v in z.items():
            row[f"{m}_{k}"] = v
    return row


def run(eur_path: str, jpy_path: str, output: str) -> dict:
    out = Path(output); out.mkdir(parents=True, exist_ok=True)
    eur = load_mt5(eur_path)
    jpy = load_mt5(jpy_path)

    candidates = {}
    for rr in (1.5, 2.0, 2.5, 3.0):
        candidates[f"USDJPY_LO30_MOM_{rr:g}R"] = london_open(jpy, rr, False)
        candidates[f"USDJPY_LO30_REV_{rr:g}R"] = london_open(jpy, rr, True)
        candidates[f"EURUSD_ASIA_SWEEP_CONT_{rr:g}R"] = asia_sweep_cont(eur, rr)
        candidates[f"USDJPY_ASIA_SWEEP_CONT_{rr:g}R"] = asia_sweep_cont(jpy, rr)
        for model in ("CLOSE", "FVG50"):
            candidates[f"EURUSD_CHOCH_FVG_FADE_{model}_{rr:g}R"] = choch_fvg_fade(eur, rr, model)

    rows = [evaluate(n, tr) for n, tr in candidates.items()]
    table = pd.DataFrame(rows)
    # Rank only on pre-2026 windows; 2026 is strictly display/holdout.
    table["pre2026_ok"] = (
        table.dev_trades.ge(20) & table.val_trades.ge(10)
        & table.dev_exp_r.gt(0) & table.val_exp_r.gt(0)
        & table.dev_pf.gt(1) & table.val_pf.gt(1)
    )
    table["robust_exp"] = table[["dev_exp_r", "val_exp_r"]].min(axis=1)
    table = table.sort_values(["pre2026_ok", "robust_exp", "val_pf"], ascending=[False, False, False], na_position="last")
    table.to_csv(out / "ranking.csv", index=False)

    selected = table[table.pre2026_ok].head(8).candidate.tolist()
    for n in selected:
        candidates[n].to_csv(out / f"trades_{re.sub(r'[^A-Za-z0-9_-]+','_',n)}.csv", index=False)

    summary = {
        "eur_coverage": {"start": eur.index.min(), "end": eur.index.max(), "rows": len(eur)},
        "jpy_coverage": {"start": jpy.index.min(), "end": jpy.index.max(), "rows": len(jpy)},
        "selected_pre2026": selected,
        "top": table.head(12).to_dict(orient="records"),
    }
    (out / "summary.json").write_text(json.dumps(_safe(summary), indent=2), encoding="utf-8")

    cols = [
        "candidate", "pre2026_ok", "dev_trades", "dev_exp_r", "dev_pf", "val_trades", "val_exp_r", "val_pf",
        "2026-01_return_pct", "2026-02_return_pct", "2026-03_return_pct",
        "2026-04_return_pct", "2026-05_return_pct", "2026-06_return_pct",
        "2026-02_mpd", "2026-02_maxdd_pct",
    ]
    report = "\n".join([
        "# CASIO Recent Public-Feed Edge Check",
        "",
        "Source: public MT5 M5 exports, July 2024 through June 2026. Server timestamps interpreted as EET/EEST and converted to UTC.",
        "Selection windows: Jul 2024-Jun 2025 development, Jul-Dec 2025 validation. Jan-Jun 2026 is untouched holdout.",
        "",
        "## Ranking",
        "~~~text",
        table[cols].head(20).to_string(index=False),
        "~~~",
        "",
        "This is an external-feed robustness check, not final FxPro acceptance.",
    ])
    (out / "REPORT.md").write_text(report, encoding="utf-8")
    print(report)
    return summary


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--eur", required=True)
    p.add_argument("--jpy", required=True)
    p.add_argument("--output", default="reports/finotive-public-recent")
    a = p.parse_args()
    run(a.eur, a.jpy, a.output)


if __name__ == "__main__":
    main()
