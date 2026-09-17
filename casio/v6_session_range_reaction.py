from __future__ import annotations

from dataclasses import dataclass, asdict
from itertools import product
from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

from .v3_core import load_m5_csv


DISCOVERY_DATA = Path("data/xauusd_m5_secondary_octafx_mt4.csv")
TEST_DATA = Path("data/xauusd_m5_dukascopy_research.csv")
OUT = Path("reports/v6-session-range-2026")
START_RM = 100.0
RISK_FRACTION = 0.05
MIN_TRADES_PER_MONTH = 8
ROUND_TRIP_BPS = 1.0
DISCOVERY_START = pd.Timestamp("2024-01-01", tz="UTC")
DISCOVERY_END = pd.Timestamp("2026-01-01", tz="UTC")
TEST_START = pd.Timestamp("2026-01-01", tz="UTC")
TEST_END = pd.Timestamp("2027-01-01", tz="UTC")
FINALISTS = 20


@dataclass(frozen=True)
class Candidate:
    mode: str                    # REVERSAL, BREAKOUT, ADAPTIVE
    sessions: str                # LONDON, NEW_YORK, BOTH
    range_ratio_cut: float       # adaptive threshold vs trailing 20-session median
    excursion_atr: float         # minimum sweep/break distance
    body_min: float              # signal body / candle range
    retest_bars: int             # breakout retest allowance
    stop_buffer_atr: float
    target_scheme: str           # FIXED2, FIXED3, FIXED4, DYNAMIC


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df.close.shift(1)
    tr = pd.concat([(df.high - df.low).abs(), (df.high - pc).abs(), (df.low - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def _prepare(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[pd.Timestamp, dict[str, float]]]:
    x = df.copy()
    x["atr"] = _atr(x, 14)
    rng = (x.high - x.low).replace(0, np.nan)
    x["body_frac"] = (x.close - x.open).abs() / rng
    x["close_loc"] = (x.close - x.low) / rng
    day = x.index.floor("D")

    contexts: dict[pd.Timestamp, dict[str, float]] = {}
    days = pd.DatetimeIndex(sorted(pd.unique(day)))
    asia_widths: list[float] = []
    london_widths: list[float] = []

    for d in days:
        bars = x[day == d]
        if bars.empty:
            continue
        mins = bars.index.hour * 60 + bars.index.minute
        asia = bars[(mins >= 0) & (mins < 360)]
        london_ref = bars[(mins >= 420) & (mins < 720)]

        def info(ref: pd.DataFrame, hist: list[float]) -> tuple[float, float, float, float]:
            if ref.empty:
                return np.nan, np.nan, np.nan, np.nan
            hi, lo = float(ref.high.max()), float(ref.low.min())
            width = hi - lo
            med = float(np.median(hist[-20:])) if len(hist) >= 10 else np.nan
            ratio = width / med if np.isfinite(med) and med > 0 else np.nan
            return hi, lo, width, ratio

        ah, al, aw, ar = info(asia, asia_widths)
        lh, ll, lw, lr = info(london_ref, london_widths)
        contexts[d] = {
            "asia_high": ah, "asia_low": al, "asia_width": aw, "asia_ratio": ar,
            "london_high": lh, "london_low": ll, "london_width": lw, "london_ratio": lr,
        }
        if np.isfinite(aw) and aw > 0:
            asia_widths.append(aw)
        if np.isfinite(lw) and lw > 0:
            london_widths.append(lw)
    return x, contexts


def _rr(c: Candidate, style: str, ratio: float, excursion: float, body_frac: float) -> float:
    if c.target_scheme == "FIXED2":
        return 2.0
    if c.target_scheme == "FIXED3":
        return 3.0
    if c.target_scheme == "FIXED4":
        return 4.0
    # Dynamic 2R-4R: stronger compression breakouts and deeper/cleaner traps get more runway.
    if style == "BREAKOUT":
        if np.isfinite(ratio) and ratio <= 0.70 and body_frac >= 0.60:
            return 4.0
        if np.isfinite(ratio) and ratio <= 0.90 and body_frac >= 0.50:
            return 3.0
        return 2.0
    if excursion >= 0.20 and body_frac >= 0.60:
        return 4.0
    if excursion >= 0.10 and body_frac >= 0.50:
        return 3.0
    return 2.0


def _session_specs(c: Candidate):
    specs = []
    if c.sessions in ("LONDON", "BOTH"):
        specs.append(("LONDON", 420, 690, "asia_high", "asia_low", "asia_ratio"))
    if c.sessions in ("NEW_YORK", "BOTH"):
        specs.append(("NEW_YORK", 750, 1020, "london_high", "london_low", "london_ratio"))
    return specs


def _style(c: Candidate, ratio: float) -> str | None:
    if c.mode == "REVERSAL":
        return "REVERSAL"
    if c.mode == "BREAKOUT":
        return "BREAKOUT"
    if not np.isfinite(ratio):
        return None
    return "BREAKOUT" if ratio <= c.range_ratio_cut else "REVERSAL"


def _candidate_setups(x: pd.DataFrame, ctx: dict[pd.Timestamp, dict[str, float]], c: Candidate) -> pd.DataFrame:
    rows: list[dict] = []
    days = sorted(ctx)
    for d in days:
        context = ctx[d]
        day_bars = x[x.index.floor("D") == d]
        if day_bars.empty:
            continue
        mins_all = day_bars.index.hour * 60 + day_bars.index.minute
        for session, start_min, end_min, hi_key, lo_key, ratio_key in _session_specs(c):
            hi = context[hi_key]; lo = context[lo_key]; ratio = context[ratio_key]
            if not (np.isfinite(hi) and np.isfinite(lo) and hi > lo):
                continue
            style = _style(c, ratio)
            if style is None:
                continue
            bars = day_bars[(mins_all >= start_min) & (mins_all < end_min)]
            if len(bars) < 3:
                continue

            idxs = x.index.get_indexer(bars.index)
            taken = False
            if style == "REVERSAL":
                for pos, gi in enumerate(idxs[:-1]):
                    r = x.iloc[gi]
                    if not np.isfinite(r.atr) or r.atr <= 0 or not np.isfinite(r.body_frac):
                        continue
                    # Long: false break below completed range, close back inside.
                    long_exc = (lo - float(r.low)) / float(r.atr)
                    short_exc = (float(r.high) - hi) / float(r.atr)
                    long_sig = long_exc >= c.excursion_atr and float(r.close) > lo and float(r.close) < hi and r.body_frac >= c.body_min and r.close_loc >= 0.55
                    short_sig = short_exc >= c.excursion_atr and float(r.close) < hi and float(r.close) > lo and r.body_frac >= c.body_min and r.close_loc <= 0.45
                    if not (long_sig or short_sig):
                        continue
                    direction = 1 if long_sig else -1
                    entry_i = gi + 1
                    if entry_i >= len(x):
                        continue
                    entry = float(x.open.iat[entry_i])
                    stop = float(r.low) - c.stop_buffer_atr * float(r.atr) if direction == 1 else float(r.high) + c.stop_buffer_atr * float(r.atr)
                    risk = (entry - stop) if direction == 1 else (stop - entry)
                    if not np.isfinite(risk) or risk <= 0 or risk / float(r.atr) < 0.20 or risk / float(r.atr) > 3.0:
                        continue
                    exc = long_exc if direction == 1 else short_exc
                    target_r = _rr(c, "REVERSAL", ratio, exc, float(r.body_frac))
                    rows.append({"signal_i": gi, "entry_i": entry_i, "signal_time": x.index[gi], "session": session, "style": style, "direction": direction, "entry": entry, "stop": stop, "risk": risk, "target_r": target_r, "range_ratio": ratio, "excursion_atr": exc, "body_frac": float(r.body_frac)})
                    taken = True
                    break
            else:
                breakout = None
                for pos, gi in enumerate(idxs[:-2]):
                    r = x.iloc[gi]
                    if not np.isfinite(r.atr) or r.atr <= 0 or not np.isfinite(r.body_frac):
                        continue
                    up_exc = (float(r.close) - hi) / float(r.atr)
                    dn_exc = (lo - float(r.close)) / float(r.atr)
                    up = up_exc >= c.excursion_atr and r.body_frac >= c.body_min and r.close_loc >= 0.65
                    dn = dn_exc >= c.excursion_atr and r.body_frac >= c.body_min and r.close_loc <= 0.35
                    if up or dn:
                        breakout = (gi, 1 if up else -1, up_exc if up else dn_exc, float(r.low), float(r.high))
                        break
                if breakout is None:
                    continue
                bi, direction, exc, b_low, b_high = breakout
                local_end = min(idxs[-1], bi + c.retest_bars)
                for gi in range(bi + 1, local_end + 1):
                    r = x.iloc[gi]
                    if not np.isfinite(r.atr) or r.atr <= 0 or not np.isfinite(r.body_frac):
                        continue
                    tol = 0.12 * float(r.atr)
                    if direction == 1:
                        retest = float(r.low) <= hi + tol and float(r.close) > hi and r.body_frac >= max(0.30, c.body_min - 0.10) and r.close_loc >= 0.55
                    else:
                        retest = float(r.high) >= lo - tol and float(r.close) < lo and r.body_frac >= max(0.30, c.body_min - 0.10) and r.close_loc <= 0.45
                    if not retest:
                        continue
                    entry_i = gi + 1
                    if entry_i >= len(x):
                        break
                    entry = float(x.open.iat[entry_i])
                    if direction == 1:
                        stop = min(b_low, float(r.low)) - c.stop_buffer_atr * float(r.atr)
                        risk = entry - stop
                    else:
                        stop = max(b_high, float(r.high)) + c.stop_buffer_atr * float(r.atr)
                        risk = stop - entry
                    if not np.isfinite(risk) or risk <= 0 or risk / float(r.atr) < 0.20 or risk / float(r.atr) > 3.0:
                        break
                    target_r = _rr(c, "BREAKOUT", ratio, exc, float(r.body_frac))
                    rows.append({"signal_i": gi, "entry_i": entry_i, "signal_time": x.index[gi], "session": session, "style": style, "direction": direction, "entry": entry, "stop": stop, "risk": risk, "target_r": target_r, "range_ratio": ratio, "excursion_atr": exc, "body_frac": float(r.body_frac)})
                    taken = True
                    break
            if taken:
                continue
    return pd.DataFrame(rows)


def _replay(x: pd.DataFrame, setups: pd.DataFrame, max_hold_bars: int = 96) -> pd.DataFrame:
    if setups.empty:
        return pd.DataFrame()
    out: list[dict] = []
    next_free = -1
    for s in setups.sort_values("entry_i").itertuples(index=False):
        ei = int(s.entry_i)
        if ei < next_free or ei >= len(x):
            continue
        d = int(s.direction); entry = float(s.entry); stop = float(s.stop); risk = float(s.risk); tr = float(s.target_r)
        target = entry + d * tr * risk
        last = min(len(x) - 1, ei + max_hold_bars)
        gross = None; exit_i = None; reason = None
        for j in range(ei, last + 1):
            lo, hi = float(x.low.iat[j]), float(x.high.iat[j])
            hs = lo <= stop if d == 1 else hi >= stop
            ht = hi >= target if d == 1 else lo <= target
            if hs and ht:
                gross, reason, exit_i = -1.0, "stop_same_bar", j; break
            if hs:
                gross, reason, exit_i = -1.0, "stop", j; break
            if ht:
                gross, reason, exit_i = tr, "target", j; break
        if gross is None:
            exit_i = last
            close = float(x.close.iat[last])
            gross = (close - entry) / risk * d
            gross = float(np.clip(gross, -1.0, tr))
            reason = "time_exit"
        cost_r = (entry * ROUND_TRIP_BPS / 10000.0) / risk
        e = s._asdict(); e.update({"entry_time": x.index[ei], "exit_time": x.index[exit_i], "gross_r": gross, "net_r": gross - cost_r, "reason": reason})
        out.append(e)
        next_free = exit_i + 1
    return pd.DataFrame(out)


def _slice(trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    t = pd.to_datetime(trades.entry_time, utc=True)
    return trades[(t >= start) & (t < end)].copy().sort_values("entry_time")


def _compound(trades: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    t = trades.copy().sort_values("entry_time")
    bal = START_RM; peak = bal; low = bal; maxdd = 0.0
    before=[]; risk_rm=[]; pnl=[]; after=[]
    for r in pd.to_numeric(t.get("net_r", pd.Series(dtype=float)), errors="coerce").fillna(0.0):
        before.append(bal)
        rrisk = bal * RISK_FRACTION
        p = rrisk * float(r)
        risk_rm.append(rrisk); pnl.append(p)
        bal += p
        after.append(bal)
        low = min(low, bal); peak = max(peak, bal)
        if peak > 0:
            maxdd = max(maxdd, (peak - bal) / peak * 100.0)
    t["balance_before_rm"] = before
    t["risk_rm"] = risk_rm
    t["pnl_rm"] = pnl
    t["balance_after_rm"] = after
    return t, {"end_rm": bal, "lowest_rm": low, "max_drawdown_pct": maxdd}


def _month_counts(trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    t = _slice(trades, start, end)
    if t.empty:
        return pd.DataFrame(columns=["month", "trades", "pnl_rm", "ending_balance_rm"])
    tc, _ = _compound(t)
    tc["month"] = pd.to_datetime(tc.entry_time, utc=True).dt.strftime("%Y-%m")
    rows=[]
    for m, g in tc.groupby("month"):
        rows.append({"month":m, "trades":len(g), "pnl_rm":float(g.pnl_rm.sum()), "ending_balance_rm":float(g.balance_after_rm.iloc[-1])})
    return pd.DataFrame(rows)


def _period_summary(trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    t = _slice(trades, start, end)
    tc, money = _compound(t)
    days = max((end - start).total_seconds()/86400.0, 1e-9)
    monthly = _month_counts(t, start, end)
    full_month_counts = monthly.trades.to_list() if not monthly.empty else []
    return {
        "trades": int(len(t)),
        "trades_per_30d": float(len(t) * 30.0 / days),
        "end_rm": float(money["end_rm"]),
        "lowest_rm": float(money["lowest_rm"]),
        "max_drawdown_pct": float(money["max_drawdown_pct"]),
        "min_month_trades": int(min(full_month_counts)) if full_month_counts else 0,
    }


def _candidates() -> list[Candidate]:
    rows=[]
    # Fresh strategy search. 3 modes x 3 session choices x 3 cuts x 3 excursions x 2 bodies x 2 retests x 2 stops x 4 targets.
    for vals in product(
        ("REVERSAL", "BREAKOUT", "ADAPTIVE"),
        ("LONDON", "NEW_YORK", "BOTH"),
        (0.80, 1.00, 1.20),
        (0.00, 0.10, 0.20),
        (0.40, 0.55),
        (4, 8),
        (0.08, 0.16),
        ("FIXED2", "FIXED3", "FIXED4", "DYNAMIC"),
    ):
        c = Candidate(*vals)
        # range_ratio_cut does not matter for fixed mode; keep only neutral 1.0 there to avoid duplicate candidates.
        if c.mode != "ADAPTIVE" and c.range_ratio_cut != 1.00:
            continue
        rows.append(c)
    return rows


def _fmt_table(df: pd.DataFrame, cols: list[str], n: int | None=None) -> str:
    if n is not None:
        df = df.head(n)
    if df.empty:
        return "(none)"
    y = df[cols].copy()
    return y.to_markdown(index=False)


def _safe(v):
    if isinstance(v, dict): return {k:_safe(x) for k,x in v.items()}
    if isinstance(v, list): return [_safe(x) for x in v]
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (np.floating,float)):
        z=float(v); return z if math.isfinite(z) else None
    if isinstance(v, pd.Timestamp): return v.isoformat()
    if isinstance(v, (np.bool_,bool)): return bool(v)
    return v


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    secondary = load_m5_csv(DISCOVERY_DATA)
    # Need causal warm-up, but weekend gaps are valid.
    secondary = secondary[(secondary.index >= pd.Timestamp("2023-10-01", tz="UTC")) & (secondary.index < DISCOVERY_END)].copy()
    if secondary.empty or secondary.index.min() > pd.Timestamp("2023-11-01", tz="UTC") or secondary.index.max() < pd.Timestamp("2025-12-30", tz="UTC"):
        raise RuntimeError(f"Secondary feed coverage insufficient: {secondary.index.min() if len(secondary) else 'EMPTY'} -> {secondary.index.max() if len(secondary) else 'EMPTY'}")

    duk = load_m5_csv(TEST_DATA)
    duk = duk[duk.index >= pd.Timestamp("2025-10-01", tz="UTC")].copy()
    if duk.empty:
        raise RuntimeError("Dukascopy test feed is empty")
    observed_end = min(TEST_END, duk.index.max() + pd.Timedelta(minutes=5))
    if observed_end <= TEST_START:
        raise RuntimeError(f"No 2026 Dukascopy test data: end={observed_end}")

    print("Preparing brand-new session-range features...")
    disc_x, disc_ctx = _prepare(secondary)
    test_x, test_ctx = _prepare(duk)
    cs = _candidates()
    print(f"Searching {len(cs)} new-strategy candidates on 2024-2025 secondary feed")

    discovery_rows=[]; cmap={}
    for i,c in enumerate(cs,1):
        cid=f"V6-{i:04d}"; cmap[cid]=c
        setups=_candidate_setups(disc_x,disc_ctx,c)
        trades=_replay(disc_x,setups)
        s=_period_summary(trades,DISCOVERY_START,DISCOVERY_END)
        # User's rule: minimum 8 trades/month. Discovery requires average >=8 and every represented full month >=8.
        if s["trades_per_30d"] < MIN_TRADES_PER_MONTH or s["min_month_trades"] < MIN_TRADES_PER_MONTH:
            continue
        discovery_rows.append({"candidate":cid,**s,"params":json.dumps(asdict(c),sort_keys=True)})
        if i % 100 == 0:
            print(f"processed {i}/{len(cs)}; qualified={len(discovery_rows)}")

    discovery=pd.DataFrame(discovery_rows)
    if discovery.empty:
        # Still produce a report instead of crashing: honest negative result.
        report=["# CASIO v6 — New Strategy Search", "", "No fresh Adaptive Session Range Reaction candidate met the discovery requirement of at least 8 trades in every month of 2024-2025.", "", f"Candidates searched: **{len(cs)}**.", "", "No 2026 parameter selection was performed."]
        (OUT/"REPORT.md").write_text("\n".join(report),encoding="utf-8")
        pd.DataFrame(columns=["candidate"]).to_csv(OUT/"discovery.csv",index=False)
        print("No discovery candidate met frequency floor; report written")
        return

    discovery=discovery.sort_values("end_rm",ascending=False).reset_index(drop=True)
    discovery.to_csv(OUT/"discovery.csv",index=False)
    finalists=discovery.head(FINALISTS).copy()

    print(f"Testing {len(finalists)} frozen finalists on untouched Dukascopy 2026")
    test_rows=[]; cache={}
    for _,row in finalists.iterrows():
        cid=str(row.candidate); c=cmap[cid]
        setups=_candidate_setups(test_x,test_ctx,c)
        trades=_replay(test_x,setups)
        s=_period_summary(trades,TEST_START,observed_end)
        test_rows.append({"candidate":cid,**s,"discovery_end_rm":float(row.end_rm),"params":json.dumps(asdict(c),sort_keys=True)})
        cache[cid]=trades
    test=pd.DataFrame(test_rows).sort_values("end_rm",ascending=False).reset_index(drop=True)
    test.to_csv(OUT/"test_2026_finalists.csv",index=False)

    primary_id=str(discovery.iloc[0].candidate)
    primary=test[test.candidate.eq(primary_id)].iloc[0]
    primary_trades=_slice(cache[primary_id],TEST_START,observed_end)
    primary_comp,_=_compound(primary_trades)
    primary_comp.to_csv(OUT/"primary_2026_trades.csv",index=False)
    primary_month=_month_counts(cache[primary_id],TEST_START,observed_end)
    primary_month.to_csv(OUT/"primary_2026_monthly.csv",index=False)

    # For the partial final month, frequency pass is based on average plus all completed months visible in 2026.
    complete_months=primary_month.copy()
    if observed_end.day < 25 and not complete_months.empty:
        complete_months=complete_months.iloc[:-1]
    completed_month_floor=int(complete_months.trades.min()) if not complete_months.empty else 0
    pass_freq=bool(float(primary.trades_per_30d)>=MIN_TRADES_PER_MONTH and completed_month_floor>=MIN_TRADES_PER_MONTH)
    pass_growth=bool(float(primary.end_rm)>START_RM)

    report=[
        "# CASIO v6 — Adaptive Session Range Reaction",
        "",
        "This is a **new strategy family**, not a retune of Structural Portfolio, Route A/B, v3, v4 or v5.",
        "",
        "## Test rule",
        "",
        f"Start **RM{START_RM:.0f}**, risk **5% of current balance per trade**, require **>= {MIN_TRADES_PER_MONTH} trades/month**, and judge the result by ending balance.",
        "",
        "## Strategy idea",
        "",
        "- London trades reactions to the completed Asia 00:00-06:00 UTC range.",
        "- New York trades reactions to the completed London-morning 07:00-12:00 UTC range.",
        "- REVERSAL mode fades false breaks that return inside the completed range.",
        "- BREAKOUT mode waits for a break and retest from outside the completed range.",
        "- ADAPTIVE mode uses the current session-range size versus its trailing 20-session median: compressed ranges use breakout/retest; expanded ranges use false-break reversal.",
        "- Entries occur on the **next bar** after confirmation. Same-bar stop/target collisions are stop-first.",
        "- Targets are fixed or dynamic **2R-4R**. Round-trip cost assumption: **1 bp**.",
        "",
        "## Find vs test separation",
        "",
        "- Rule search: Octa/MT4 secondary feed, 2024-01-01 through 2025-12-31.",
        f"- Untouched test: Dukascopy, 2026-01-01 through {observed_end.isoformat()}.",
        f"- Candidates searched: **{len(cs)}**. Frequency-qualified discovery candidates: **{len(discovery)}**.",
        "",
        "## Best discovery candidates",
        "",
        _fmt_table(discovery,["candidate","trades","trades_per_30d","min_month_trades","end_rm","lowest_rm"],20),
        "",
        "## Frozen finalists on Dukascopy 2026",
        "",
        _fmt_table(test,["candidate","trades","trades_per_30d","min_month_trades","end_rm","lowest_rm","discovery_end_rm"],20),
        "",
        "## Primary candidate — selected before 2026 was inspected",
        "",
        f"Candidate **{primary_id}**",
        f"- 2024-2025 discovery: RM100 -> **RM{float(discovery.iloc[0].end_rm):.2f}**.",
        f"- Dukascopy 2026: RM100 -> **RM{float(primary.end_rm):.2f}**.",
        f"- Trades: **{int(primary.trades)}**, equivalent to **{float(primary.trades_per_30d):.2f}/30d**.",
        f"- Minimum trades among completed 2026 months: **{completed_month_floor}**.",
        f"- Lowest balance reached: **RM{float(primary.lowest_rm):.2f}**.",
        f"- Frequency requirement: **{'PASS' if pass_freq else 'FAIL'}**.",
        f"- RM100 growth requirement: **{'PASS' if pass_growth else 'FAIL'}**.",
        f"- Overall requested fit: **{'PASS' if pass_freq and pass_growth else 'FAIL'}**.",
        "",
        "### Frozen rules",
        "",
        "```json",
        json.dumps(asdict(cmap[primary_id]),indent=2,sort_keys=True),
        "```",
        "",
        "### 2026 month-by-month balance",
        "",
        _fmt_table(primary_month,["month","trades","pnl_rm","ending_balance_rm"]),
        "",
        "The selection criterion is not PF or win rate. It is the user's requested equity-first test: frequency plus RM100 ending balance.",
    ]
    (OUT/"REPORT.md").write_text("\n".join(report),encoding="utf-8")
    (OUT/"summary.json").write_text(json.dumps(_safe({"primary":primary_id,"primary_2026":primary.to_dict(),"frequency_pass":pass_freq,"growth_pass":pass_growth,"overall_pass":pass_freq and pass_growth,"test_end":observed_end}),indent=2),encoding="utf-8")
    print(json.dumps(_safe({"primary":primary_id,"end_rm":float(primary.end_rm),"trades_per_30d":float(primary.trades_per_30d),"completed_month_floor":completed_month_floor,"pass":pass_freq and pass_growth}),indent=2))
    print(f"Report: {OUT/'REPORT.md'}")


if __name__ == "__main__":
    main()
