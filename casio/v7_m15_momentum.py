from __future__ import annotations

from dataclasses import dataclass, asdict
from itertools import product
from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

from .v3_core import load_m5_csv, _atr


DISCOVERY_DATA = Path("data/xauusd_m5_secondary_octafx_mt4.csv")
TEST_DATA = Path("data/xauusd_m5_dukascopy_research.csv")
OUT = Path("reports/v7-m15-momentum-2026")

DISCOVERY_WARMUP = pd.Timestamp("2023-10-01", tz="UTC")
DISCOVERY_START = pd.Timestamp("2024-01-01", tz="UTC")
DISCOVERY_END = pd.Timestamp("2026-01-01", tz="UTC")
TEST_WARMUP = pd.Timestamp("2025-10-01", tz="UTC")
TEST_START = pd.Timestamp("2026-01-01", tz="UTC")
TEST_END = pd.Timestamp("2027-01-01", tz="UTC")

START_RM = 100.0
RISK_FRACTION = 0.05
ROUND_TRIP_BPS = 1.0
MIN_MONTH_TRADES = 8
FINALISTS = 24


@dataclass(frozen=True)
class Candidate:
    lookback: int
    impulse_atr: float
    body_min: float
    breakout_buffer_atr: float
    pullback_bars: int
    retrace_max: float
    target_r: float
    session: str
    stop_buffer_atr: float = 0.12
    min_risk_atr: float = 0.35
    max_risk_atr: float = 2.8
    max_hold_bars: int = 40


def _safe(x):
    if isinstance(x, dict): return {str(k): _safe(v) for k, v in x.items()}
    if isinstance(x, list): return [_safe(v) for v in x]
    if isinstance(x, (np.bool_, bool)): return bool(x)
    if isinstance(x, np.integer): return int(x)
    if isinstance(x, (np.floating, float)):
        y = float(x)
        return y if math.isfinite(y) else None
    if isinstance(x, pd.Timestamp): return x.isoformat()
    return x


def _resample_m15(m5: pd.DataFrame) -> pd.DataFrame:
    x = m5.resample("15min", label="left", closed="left", origin="epoch").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    )
    return x.dropna(subset=["open", "high", "low", "close"])


def _prepare(m15: pd.DataFrame, max_lookback: int = 20) -> pd.DataFrame:
    f = m15.copy()
    f["atr"] = _atr(m15, 14)
    rng = (f.high - f.low).replace(0, np.nan)
    body = (f.close - f.open).abs()
    f["body_frac"] = body / rng
    f["range_atr"] = rng / f.atr.replace(0, np.nan)
    f["close_loc"] = (f.close - f.low) / rng
    for n in sorted({8, 12, 20}):
        f[f"prior_high_{n}"] = f.high.shift(1).rolling(n, min_periods=n).max()
        f[f"prior_low_{n}"] = f.low.shift(1).rolling(n, min_periods=n).min()
    return f


def _session_ok(index: pd.DatetimeIndex, mode: str) -> np.ndarray:
    mins = index.hour * 60 + index.minute
    if mode == "ALL":
        return np.ones(len(index), dtype=bool)
    # London + New York active window, UTC.
    return (mins >= 390) & (mins < 1020)  # 06:30-17:00 UTC


def _build_setups(f: pd.DataFrame, c: Candidate) -> pd.DataFrame:
    ph = f[f"prior_high_{c.lookback}"]
    pl = f[f"prior_low_{c.lookback}"]
    sess = _session_ok(f.index, c.session)
    atr = f.atr

    long_imp = (
        sess
        & atr.notna().to_numpy()
        & (f.range_atr >= c.impulse_atr).to_numpy()
        & (f.body_frac >= c.body_min).to_numpy()
        & (f.close_loc >= 0.72).to_numpy()
        & (f.close > ph + c.breakout_buffer_atr * atr).to_numpy()
    )
    short_imp = (
        sess
        & atr.notna().to_numpy()
        & (f.range_atr >= c.impulse_atr).to_numpy()
        & (f.body_frac >= c.body_min).to_numpy()
        & (f.close_loc <= 0.28).to_numpy()
        & (f.close < pl - c.breakout_buffer_atr * atr).to_numpy()
    )

    events = np.flatnonzero(long_imp | short_imp)
    rows: list[dict] = []
    last_signal = -999

    for i in events:
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
        broken_level = float(ph.iat[i] if d == 1 else pl.iat[i])
        if not np.isfinite(broken_level):
            continue

        # Pullback zone is measured from the impulse close back into its body.
        if d == 1:
            zone_near = imp_close - 0.18 * imp_body
            zone_far = imp_close - c.retrace_max * imp_body
        else:
            zone_near = imp_close + 0.18 * imp_body
            zone_far = imp_close + c.retrace_max * imp_body

        confirm_j = None
        pull_extreme = imp_low if d == 1 else imp_high
        for j in range(i + 1, min(len(f) - 1, i + 1 + c.pullback_bars)):
            r = f.iloc[j]
            if d == 1:
                pull_extreme = min(pull_extreme, float(r.low))
                invalid = float(r.low) < imp_low - 0.30 * a
                touched = float(r.low) <= zone_near and float(r.high) >= zone_far
                confirm = float(r.close) > float(r.open) and float(r.close) > broken_level
            else:
                pull_extreme = max(pull_extreme, float(r.high))
                invalid = float(r.high) > imp_high + 0.30 * a
                touched = float(r.high) >= zone_near and float(r.low) <= zone_far
                confirm = float(r.close) < float(r.open) and float(r.close) < broken_level
            if invalid:
                break
            if touched and confirm:
                confirm_j = j
                break
        if confirm_j is None or confirm_j + 1 >= len(f):
            continue

        entry_i = confirm_j + 1
        entry = float(f.open.iat[entry_i])
        if d == 1:
            stop = pull_extreme - c.stop_buffer_atr * a
            risk = entry - stop
        else:
            stop = pull_extreme + c.stop_buffer_atr * a
            risk = stop - entry
        if not np.isfinite(risk) or risk <= 0:
            continue
        risk_atr = risk / a
        if risk_atr < c.min_risk_atr or risk_atr > c.max_risk_atr:
            continue

        rows.append({
            "signal_i": int(confirm_j),
            "signal_time": f.index[confirm_j] + pd.Timedelta(minutes=15),
            "entry_i": int(entry_i),
            "entry_time": f.index[entry_i],
            "direction": d,
            "entry": entry,
            "stop": stop,
            "risk": risk,
            "target": entry + d * c.target_r * risk,
            "target_r": c.target_r,
            "impulse_i": int(i),
            "impulse_time": f.index[i],
            "broken_level": broken_level,
            "risk_atr": risk_atr,
        })
        last_signal = confirm_j
    return pd.DataFrame(rows)


def _replay(m15: pd.DataFrame, setups: pd.DataFrame, c: Candidate) -> pd.DataFrame:
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
        target = float(s.target)
        risk = float(s.risk)
        end = min(len(m15), ei + 1 + c.max_hold_bars)
        gross = None
        reason = None
        exit_i = None
        for j in range(ei, end):
            lo = float(m15.low.iat[j]); hi = float(m15.high.iat[j]); close = float(m15.close.iat[j])
            hs = lo <= stop if d == 1 else hi >= stop
            ht = hi >= target if d == 1 else lo <= target
            if hs and ht:
                gross, reason = -1.0, "stop_same_bar"
            elif hs:
                gross, reason = -1.0, "stop"
            elif ht:
                gross, reason = c.target_r, "target"
            elif j == end - 1:
                gross = (close - entry) / risk * d
                reason = "time_exit"
            else:
                continue
            exit_i = j
            break
        if gross is None or exit_i is None:
            continue
        cost_r = (entry * ROUND_TRIP_BPS / 10000.0) / risk
        row = s._asdict()
        row.update({
            "exit_time": m15.index[exit_i] + pd.Timedelta(minutes=15),
            "gross_r": float(gross),
            "net_r": float(gross - cost_r),
            "reason": reason,
        })
        out.append(row)
        next_free = exit_i + 1
    return pd.DataFrame(out)


def _slice(trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    t = pd.to_datetime(trades.entry_time, utc=True)
    return trades.loc[(t >= start) & (t < end)].copy()


def _compound(trades: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    x = trades.sort_values("entry_time").copy()
    bal = START_RM
    peak = START_RM
    low = START_RM
    max_dd = 0.0
    pnls, bals = [], []
    for r in pd.to_numeric(x.get("net_r", pd.Series(dtype=float)), errors="coerce").fillna(0.0):
        pnl = bal * RISK_FRACTION * float(r)
        bal += pnl
        pnls.append(pnl); bals.append(bal)
        peak = max(peak, bal); low = min(low, bal)
        if peak > 0:
            max_dd = max(max_dd, (peak - bal) / peak * 100.0)
    if len(x):
        x["pnl_rm"] = pnls
        x["balance_rm"] = bals
    return x, {"end_rm": bal, "lowest_rm": low, "max_drawdown_pct": max_dd}


def _monthly(trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    x = _slice(trades, start, end)
    x, _ = _compound(x)
    periods = pd.period_range(start=start.tz_localize(None).to_period("M"), end=(end - pd.Timedelta(seconds=1)).tz_localize(None).to_period("M"), freq="M")
    rows = []
    prev = START_RM
    for p in periods:
        a = pd.Timestamp(p.start_time, tz="UTC")
        b = pd.Timestamp((p + 1).start_time, tz="UTC")
        z = x[(pd.to_datetime(x.entry_time, utc=True) >= a) & (pd.to_datetime(x.entry_time, utc=True) < b)] if not x.empty else x
        ending = float(z.balance_rm.iloc[-1]) if len(z) else prev
        pnl = ending - prev
        rows.append({"month": str(p), "trades": int(len(z)), "pnl_rm": pnl, "ending_balance_rm": ending})
        prev = ending
    return pd.DataFrame(rows)


def _summary(trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, require_complete_months: bool) -> dict:
    x = _slice(trades, start, end)
    x, eq = _compound(x)
    mon = _monthly(trades, start, end)
    if require_complete_months:
        complete = mon.copy()
    else:
        # Exclude a partial final month from the minimum-month frequency test.
        complete = mon.iloc[:-1].copy() if end.day < 28 and len(mon) > 1 else mon.copy()
    min_month = int(complete.trades.min()) if len(complete) else 0
    days = max((end - start).total_seconds() / 86400.0, 1e-9)
    return {
        "trades": int(len(x)),
        "trades_per_30d": float(len(x) * 30.0 / days),
        "min_month_trades": min_month,
        **eq,
    }


def _candidates() -> list[Candidate]:
    out = []
    for vals in product(
        [8, 12, 20],          # recent M15 range
        [1.20, 1.50, 1.80],  # expansion candle vs ATR
        [0.55, 0.65],        # body quality
        [0.00, 0.10],        # breakout penetration
        [2, 4],              # allowed pullback bars
        [0.50, 0.67],        # maximum body retrace
        [2.0, 3.0, 4.0],     # target R
        ["ALL", "PRIMARY"],
    ):
        out.append(Candidate(*vals))
    return out


def _md(df: pd.DataFrame, cols: list[str], n: int | None = None) -> str:
    if df.empty: return "No rows."
    z = df[cols].head(n) if n else df[cols]
    return z.to_markdown(index=False)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    sec5 = load_m5_csv(DISCOVERY_DATA)
    sec5 = sec5[(sec5.index >= DISCOVERY_WARMUP) & (sec5.index < DISCOVERY_END)].copy()
    if sec5.index.min() > DISCOVERY_START - pd.Timedelta(days=60) or sec5.index.max() < DISCOVERY_END - pd.Timedelta(days=3):
        raise RuntimeError("Secondary feed lacks enough 2024-2025 discovery coverage")

    duk5 = load_m5_csv(TEST_DATA)
    duk5 = duk5[duk5.index >= TEST_WARMUP].copy()
    observed_end = min(TEST_END, duk5.index.max() + pd.Timedelta(minutes=5))
    if observed_end <= TEST_START:
        raise RuntimeError("Dukascopy feed has no 2026 test data")

    sec = _resample_m15(sec5)
    duk = _resample_m15(duk5)
    f_sec = _prepare(sec)
    f_duk = _prepare(duk)

    candidates = _candidates()
    rows = []
    cmap: dict[str, Candidate] = {}
    print(f"Searching {len(candidates)} native-M15 candidates on 2024-2025 secondary feed")
    for k, c in enumerate(candidates, start=1):
        cid = f"M15-{k:04d}"
        cmap[cid] = c
        setups = _build_setups(f_sec, c)
        if setups.empty:
            continue
        st = pd.to_datetime(setups.entry_time, utc=True)
        raw = setups[(st >= DISCOVERY_START) & (st < DISCOVERY_END)]
        # Cheap rejection before replay: must have enough raw setups to possibly make 8/month.
        if len(raw) < 192:
            continue
        trades = _replay(sec, setups, c)
        s = _summary(trades, DISCOVERY_START, DISCOVERY_END, True)
        if s["min_month_trades"] < MIN_MONTH_TRADES:
            continue
        rows.append({"candidate": cid, **s, "params": json.dumps(asdict(c), sort_keys=True)})
        if k % 100 == 0:
            print(f"processed {k}/{len(candidates)}; frequency-qualified={len(rows)}")

    discovery = pd.DataFrame(rows)
    if discovery.empty:
        # Still produce a useful failure report rather than exit 1.
        report = [
            "# CASIO v7 — Native M15 Volatility Momentum",
            "",
            "Start RM100, risk 5% of current balance, and require at least 8 filled trades in every completed month.",
            "",
            f"Candidates searched: **{len(candidates)}**.",
            "",
            "**Result: no candidate met the 8-trades-per-month discovery requirement on 2024-2025 secondary data.**",
        ]
        (OUT / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
        print("No candidate met the discovery frequency floor; report written.")
        return

    discovery = discovery.sort_values(["end_rm", "lowest_rm"], ascending=[False, False]).reset_index(drop=True)
    discovery.to_csv(OUT / "discovery_2024_2025.csv", index=False)
    finalists = discovery.head(FINALISTS).copy()

    test_rows = []
    cache: dict[str, pd.DataFrame] = {}
    for _, row in finalists.iterrows():
        cid = str(row.candidate)
        c = cmap[cid]
        setups = _build_setups(f_duk, c)
        trades = _replay(duk, setups, c)
        s = _summary(trades, TEST_START, observed_end, False)
        cache[cid] = trades
        test_rows.append({
            "candidate": cid,
            **s,
            "passes_monthly_frequency": bool(s["min_month_trades"] >= MIN_MONTH_TRADES),
            "discovery_end_rm": float(row.end_rm),
            "params": json.dumps(asdict(c), sort_keys=True),
        })
    test = pd.DataFrame(test_rows).sort_values(["passes_monthly_frequency", "end_rm"], ascending=[False, False]).reset_index(drop=True)
    test.to_csv(OUT / "dukascopy_2026_finalists.csv", index=False)

    primary_id = str(discovery.iloc[0].candidate)
    primary = test[test.candidate.eq(primary_id)].iloc[0]
    p_trades = _slice(cache[primary_id], TEST_START, observed_end)
    p_trades, _ = _compound(p_trades)
    p_trades.to_csv(OUT / "primary_2026_trades.csv", index=False)
    p_month = _monthly(cache[primary_id], TEST_START, observed_end)
    p_month.to_csv(OUT / "primary_2026_monthly.csv", index=False)

    eligible = test[test.passes_monthly_frequency].copy()
    exploratory_id = str(eligible.iloc[0].candidate) if len(eligible) else "NONE"

    report = [
        "# CASIO v7 — Native M15 Volatility Expansion Momentum",
        "",
        "This is a new native-M15 strategy family. M5 is used only as the source file and is resampled before any signal logic; all signals, entries, stops, targets and exits are evaluated on M15 bars.",
        "",
        "## User test",
        "",
        "- Start **RM100**.",
        "- Risk **5% of current balance** per filled trade.",
        "- Require **at least 8 trades in every completed month**.",
        "- Judge primarily by where RM100 ends up.",
        "- 1 bp round-trip cost assumption.",
        "",
        "## New strategy logic",
        "",
        "A large M15 expansion candle must break the high/low of a recent M15 range. Price then gets only a few M15 bars to make a controlled retracement into the impulse body and close back in the breakout direction. Entry is the next M15 open. Stop is beyond the impulse/pullback extreme; targets are fixed 2R, 3R or 4R. Same-bar stop/target collisions are stop-first.",
        "",
        "## Find/test separation",
        "",
        "- Discovery: secondary Octa/MT4 feed, 2024-01-01 through 2025-12-31.",
        f"- Untouched test: Dukascopy 2026-01-01 through {observed_end.isoformat()}.",
        f"- Candidate rules searched: **{len(candidates)}**.",
        f"- Discovery candidates meeting the monthly frequency floor: **{len(discovery)}**.",
        "",
        "## Best discovery candidates",
        "",
        _md(discovery, ["candidate", "trades", "trades_per_30d", "min_month_trades", "end_rm", "lowest_rm"], 20),
        "",
        "## Frozen finalists on Dukascopy 2026",
        "",
        _md(test, ["candidate", "trades", "trades_per_30d", "min_month_trades", "end_rm", "lowest_rm", "passes_monthly_frequency", "discovery_end_rm"], 24),
        "",
        "## Primary candidate — selected before 2026",
        "",
        f"Candidate **{primary_id}**",
        f"- 2024-2025 discovery: RM100 -> **RM{float(discovery.iloc[0].end_rm):.2f}**.",
        f"- Dukascopy 2026: RM100 -> **RM{float(primary.end_rm):.2f}**.",
        f"- 2026 trades: **{int(primary.trades)}**, equivalent to **{float(primary.trades_per_30d):.2f}/30d**.",
        f"- Minimum trades among completed 2026 months: **{int(primary.min_month_trades)}**.",
        f"- Lowest 2026 balance: **RM{float(primary.lowest_rm):.2f}**.",
        f"- Frequency requirement: **{'PASS' if bool(primary.passes_monthly_frequency) else 'FAIL'}**.",
        f"- RM100 growth requirement: **{'PASS' if float(primary.end_rm) > START_RM else 'FAIL'}**.",
        f"- Overall requested fit: **{'PASS' if bool(primary.passes_monthly_frequency) and float(primary.end_rm) > START_RM else 'FAIL'}**.",
        "",
        "### Frozen rules",
        "",
        "```json",
        json.dumps(asdict(cmap[primary_id]), indent=2, sort_keys=True),
        "```",
        "",
        "### 2026 month-by-month balance",
        "",
        _md(p_month, ["month", "trades", "pnl_rm", "ending_balance_rm"]),
        "",
        "## Exploratory best 2026 finalist",
        "",
    ]

    if exploratory_id == "NONE":
        report.append("No frozen finalist maintained at least 8 trades in every completed Dukascopy 2026 month.")
    else:
        e = test[test.candidate.eq(exploratory_id)].iloc[0]
        report += [
            "This is exploratory because it is chosen after comparing 2026 finalists; it is not an untouched selection.",
            "",
            f"Candidate **{exploratory_id}**: RM100 -> **RM{float(e.end_rm):.2f}**, with minimum completed-month frequency **{int(e.min_month_trades)}**.",
        ]

    (OUT / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    (OUT / "summary.json").write_text(json.dumps(_safe({
        "primary_candidate": primary_id,
        "primary_2026": primary.to_dict(),
        "exploratory_candidate": exploratory_id,
        "candidates": len(candidates),
        "discovery_qualified": len(discovery),
        "test_end": observed_end,
    }), indent=2), encoding="utf-8")
    print(f"Report: {OUT / 'REPORT.md'}")


if __name__ == "__main__":
    main()
