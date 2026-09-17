from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

from .v3_core import _bars_since, load_m5_csv
from .structural_portfolio_latest import StructuralPortfolioConfig, _session, prepare_features
from .structural_frequency_research import _recent_level_retest
from .route_ab_2026_backtest import _replay_variable_targets


DATA = Path("data/xauusd_m5_dukascopy_research.csv")
OUT = Path("reports/equity-first-search-2026")
DISCOVERY_START = pd.Timestamp("2025-01-01", tz="UTC")
DISCOVERY_END = pd.Timestamp("2026-01-01", tz="UTC")
TEST_START = pd.Timestamp("2026-01-01", tz="UTC")
START_BALANCE_RM = 100.0
RISK_FRACTION = 0.05
MIN_TRADES_PER_30D = 8.0
RANDOM_CANDIDATES = 650
FINALISTS = 30
SEED = 260917


@dataclass(frozen=True)
class Candidate:
    playbooks: str
    session: str
    body_min: float
    range_atr_min: float
    trend_min: int
    require_m15: bool
    entry_model: str
    internal_fresh: int
    external_fresh: int
    fill_bars: int
    cooldown_bars: int
    stop_lookback: int
    stop_buffer_atr: float
    target_policy: str
    max_hold_bars: int
    require_day_alignment: bool
    require_runway: bool


def _safe(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        x = float(v)
        return x if math.isfinite(x) else None
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    if isinstance(v, dict):
        return {str(k): _safe(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_safe(x) for x in v]
    return v


def _days(a: pd.Timestamp, b: pd.Timestamp) -> float:
    return max((b - a).total_seconds() / 86400.0, 1e-9)


def _slice(trades: pd.DataFrame, a: pd.Timestamp, b: pd.Timestamp) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    t = pd.to_datetime(trades.entry_time, utc=True)
    return trades[(t >= a) & (t < b)].copy()


def _compound(trades: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    x = trades.sort_values("entry_time").copy()
    bal = START_BALANCE_RM
    peak = bal
    low = bal
    max_dd = 0.0
    max_dd_pct = 0.0
    before, risk_rm, pnl_rm, after = [], [], [], []
    for r in pd.to_numeric(x.get("net_r", pd.Series(dtype=float)), errors="coerce").fillna(0.0):
        b0 = bal
        risk = b0 * RISK_FRACTION
        pnl = risk * float(r)
        bal = max(0.0, b0 + pnl)
        peak = max(peak, bal)
        low = min(low, bal)
        dd = peak - bal
        dd_pct = dd / peak * 100.0 if peak > 0 else 100.0
        max_dd = max(max_dd, dd)
        max_dd_pct = max(max_dd_pct, dd_pct)
        before.append(b0); risk_rm.append(risk); pnl_rm.append(pnl); after.append(bal)
    if not x.empty:
        x["balance_before_rm"] = before
        x["risk_rm"] = risk_rm
        x["pnl_rm"] = pnl_rm
        x["balance_after_rm"] = after
    return x, {
        "start_rm": START_BALANCE_RM,
        "end_rm": bal,
        "return_pct": (bal / START_BALANCE_RM - 1.0) * 100.0,
        "lowest_rm": low,
        "max_drawdown_rm": max_dd,
        "max_drawdown_pct": max_dd_pct,
    }


def _period_summary(trades: pd.DataFrame, a: pd.Timestamp, b: pd.Timestamp) -> dict:
    x = _slice(trades, a, b)
    x, money = _compound(x)
    return {
        "trades": int(len(x)),
        "trades_per_30d": float(len(x) * 30.0 / _days(a, b)),
        **money,
    }


def _monthly(trades: pd.DataFrame, a: pd.Timestamp, b: pd.Timestamp) -> pd.DataFrame:
    x = _slice(trades, a, b)
    x, _ = _compound(x)
    periods = pd.period_range(a.tz_convert(None).to_period("M"), (b - pd.Timedelta(microseconds=1)).tz_convert(None).to_period("M"), freq="M")
    rows = []
    running = START_BALANCE_RM
    for p in periods:
        ma = pd.Timestamp(p.start_time, tz="UTC")
        mb = pd.Timestamp((p + 1).start_time, tz="UTC")
        mt = x[(pd.to_datetime(x.entry_time, utc=True) >= ma) & (pd.to_datetime(x.entry_time, utc=True) < mb)].copy() if not x.empty else x.copy()
        pnl = float(mt.pnl_rm.sum()) if not mt.empty and "pnl_rm" in mt else 0.0
        if not mt.empty and "balance_after_rm" in mt:
            running = float(mt.balance_after_rm.iloc[-1])
        rows.append({"month": str(p), "trades": int(len(mt)), "pnl_rm": pnl, "ending_balance_rm": running})
    return pd.DataFrame(rows)


def _nearest_runway(row: pd.Series, d: int, entry: float, risk: float) -> tuple[float, str, float]:
    if d == 1:
        levels = [
            ("ASIA_H", row.asia_high), ("PDH", row.prev_day_high),
            ("H1_H", row.h1_last_ph), ("H4_H", row.h4_last_ph), ("PWH", row.prev_week_high),
        ]
        vals = [(n, float(v), (float(v) - entry) / risk) for n, v in levels if np.isfinite(v) and float(v) > entry]
    else:
        levels = [
            ("ASIA_L", row.asia_low), ("PDL", row.prev_day_low),
            ("H1_L", row.h1_last_pl), ("H4_L", row.h4_last_pl), ("PWL", row.prev_week_low),
        ]
        vals = [(n, float(v), (entry - float(v)) / risk) for n, v in levels if np.isfinite(v) and float(v) < entry]
    if not vals:
        return np.nan, "NONE", np.nan
    name, level, runway = min(vals, key=lambda z: z[2])
    return level, name, runway


def _target_r(policy: str, runway: float, body_fraction: float, range_atr: float) -> float:
    if policy != "DYNAMIC":
        return float(policy)
    # The target is fixed before replay from information available on the signal bar.
    if np.isfinite(runway) and runway >= 4.0 and body_fraction >= 0.60 and range_atr >= 0.75:
        return 4.0
    if np.isfinite(runway) and runway >= 3.0:
        return 3.0
    return 2.0


def _entry(row: pd.Series, d: int, model: str, has_fvg: bool) -> tuple[float, str]:
    if model == "FVG50":
        if not has_fvg:
            return np.nan, "NONE"
        if d == 1:
            return (float(row.high.shift) if False else (float(row.bull_fvg_low) + float(row.bull_fvg_high)) / 2.0), "FVG50"
        return (float(row.bear_fvg_low) + float(row.bear_fvg_high)) / 2.0, "FVG50"
    body = abs(float(row.close) - float(row.open))
    frac = 0.50 if model == "BODY50" else 0.66
    if d == 1:
        return float(row.close) - frac * body, model
    return float(row.close) + frac * body, model


def _prepare_base(m5: pd.DataFrame) -> pd.DataFrame:
    cfg = replace(StructuralPortfolioConfig(), body_min=0.40, range_atr_min=0.45)
    f = prepare_features(m5, cfg).copy()
    for n in (4, 6, 8, 12):
        f[f"recent_low{n}"] = f.low.rolling(n, min_periods=n).min()
        f[f"recent_high{n}"] = f.high.rolling(n, min_periods=n).max()
    m15_sell = ((f.low < f.m15_last_pl) & (f.close > f.m15_last_pl) & f.m15_last_pl.notna()).fillna(False)
    m15_buy = ((f.high > f.m15_last_ph) & (f.close < f.m15_last_ph) & f.m15_last_ph.notna()).fillna(False)
    f["m15_sell_sweep_age_search"] = _bars_since(m15_sell)
    f["m15_buy_sweep_age_search"] = _bars_since(m15_buy)
    f["break_retest_long_search"] = _recent_level_retest(f, ["h1_last_ph", "h4_last_ph", "prev_day_high", "asia_high"], 1)
    f["break_retest_short_search"] = _recent_level_retest(f, ["h1_last_pl", "h4_last_pl", "prev_day_low", "asia_low"], -1)
    # Store permissive FVG geometry independent of stricter candidate displacement thresholds.
    f["search_bull_gap"] = f.low > f.high.shift(2)
    f["search_bear_gap"] = f.high < f.low.shift(2)
    f["bull_fvg_low"] = f.high.shift(2)
    f["bull_fvg_high"] = f.low
    f["bear_fvg_low"] = f.high
    f["bear_fvg_high"] = f.low.shift(2)
    return f


def _build_setups(f: pd.DataFrame, c: Candidate) -> pd.DataFrame:
    idx = f.index
    sess = pd.Series(_session(idx), index=idx)
    if c.session == "LONDON":
        allowed = sess.eq("LONDON")
    elif c.session == "NEW_YORK":
        allowed = sess.eq("NEW_YORK")
    else:
        allowed = ~sess.eq("OTHER")

    vote = f.trend_vote.fillna(0)
    tl = vote.ge(c.trend_min)
    ts = vote.le(-c.trend_min)
    if c.require_m15:
        tl &= f.m15_structure_bias.fillna(0).gt(0)
        ts &= f.m15_structure_bias.fillna(0).lt(0)

    disp_l = (
        (f.close > f.open)
        & f.body_fraction.ge(c.body_min)
        & f.close_location.ge(0.68)
        & f.range_atr.ge(c.range_atr_min)
        & (f.close > f.prior_high5)
    )
    disp_s = (
        (f.close < f.open)
        & f.body_fraction.ge(c.body_min)
        & f.close_location.le(0.32)
        & f.range_atr.ge(c.range_atr_min)
        & (f.close < f.prior_low5)
    )
    fvg_l = disp_l & f.search_bull_gap
    fvg_s = disp_s & f.search_bear_gap
    trigger_l = fvg_l if c.entry_model == "FVG50" else disp_l
    trigger_s = fvg_s if c.entry_model == "FVG50" else disp_s

    pb_l = allowed & tl & f.internal_sell_sweep_age.le(c.internal_fresh) & trigger_l
    pb_s = allowed & ts & f.internal_buy_sweep_age.le(c.internal_fresh) & trigger_s

    sw_l = allowed & vote.ge(0) & f.external_sell_sweep_age.le(c.external_fresh) & trigger_l
    sw_s = allowed & vote.le(0) & f.external_buy_sweep_age.le(c.external_fresh) & trigger_s
    if c.require_m15:
        sw_l &= f.m15_structure_bias.fillna(0).ge(0)
        sw_s &= f.m15_structure_bias.fillna(0).le(0)

    rt_l = allowed & tl & f.session_retest_long & trigger_l
    rt_s = allowed & ts & f.session_retest_short & trigger_s
    br_l = allowed & tl & f.break_retest_long_search & trigger_l
    br_s = allowed & ts & f.break_retest_short_search & trigger_s
    m15_l = allowed & tl & f.m15_sell_sweep_age_search.le(c.internal_fresh) & trigger_l
    m15_s = allowed & ts & f.m15_buy_sweep_age_search.le(c.internal_fresh) & trigger_s

    enabled = set(c.playbooks.split("+"))
    pairs = []
    if "SWEEP" in enabled: pairs.append(("EXTERNAL_SWEEP", sw_l, sw_s))
    if "BREAK" in enabled: pairs.append(("BREAK_RETEST", br_l, br_s))
    if "M15" in enabled: pairs.append(("M15_SWEEP", m15_l, m15_s))
    if "RETEST" in enabled: pairs.append(("SESSION_RETEST", rt_l, rt_s))
    if "PB" in enabled: pairs.append(("TREND_PULLBACK", pb_l, pb_s))
    if not pairs:
        return pd.DataFrame()

    any_l = pd.Series(False, index=idx); any_s = pd.Series(False, index=idx)
    for _, l, s in pairs:
        any_l |= l.fillna(False); any_s |= s.fillna(False)
    mask = any_l | any_s

    rows = []
    last = {1: -10**9, -1: -10**9}
    for i in np.flatnonzero(mask.to_numpy()):
        d = 1 if bool(any_l.iat[i]) else -1
        if i - last[d] < c.cooldown_bars:
            continue
        playbook = None
        for name, l, s in pairs:
            if bool(l.iat[i] if d == 1 else s.iat[i]):
                playbook = name
                break
        if playbook is None:
            continue
        row = f.iloc[i]
        has_fvg = bool(fvg_l.iat[i] if d == 1 else fvg_s.iat[i])
        entry, entry_model = _entry(row, d, c.entry_model, has_fvg)
        if not np.isfinite(entry):
            continue
        atr = float(row.m5_atr)
        if not np.isfinite(atr) or atr <= 0:
            continue
        if d == 1:
            base = float(row[f"recent_low{c.stop_lookback}"])
            stop = base - c.stop_buffer_atr * atr
            risk = entry - stop
            day_ok = entry > float(row.day_open)
        else:
            base = float(row[f"recent_high{c.stop_lookback}"])
            stop = base + c.stop_buffer_atr * atr
            risk = stop - entry
            day_ok = entry < float(row.day_open)
        if not np.isfinite(risk) or risk <= 0:
            continue
        risk_atr = risk / atr
        if not 0.25 <= risk_atr <= 3.5:
            continue
        if c.require_day_alignment and playbook in {"TREND_PULLBACK", "BREAK_RETEST", "M15_SWEEP"} and not day_ok:
            continue
        liq, liq_type, runway = _nearest_runway(row, d, entry, risk)
        target_r = _target_r(c.target_policy, runway, float(row.body_fraction), float(row.range_atr))
        if not 2.0 <= target_r <= 4.0:
            continue
        if c.require_runway and (not np.isfinite(runway) or runway < target_r):
            continue
        rows.append({
            "signal_i": i, "signal_time": idx[i], "direction": d,
            "playbook": playbook, "session": sess.iat[i], "entry_model": entry_model,
            "entry": entry, "stop": stop, "risk": risk, "risk_atr": risk_atr,
            "target_r": target_r, "target": entry + d * target_r * risk,
            "external_liquidity": liq, "external_liquidity_type": liq_type,
            "external_runway_r": runway, "trend_vote": int(vote.iat[i]),
            "body_fraction": float(row.body_fraction), "range_atr": float(row.range_atr),
            "day_open_aligned": bool(day_ok),
        })
        last[d] = i
    return pd.DataFrame(rows)


def _candidate_cfg(c: Candidate) -> StructuralPortfolioConfig:
    return replace(
        StructuralPortfolioConfig(),
        min_external_runway_r=2.0,
        target_r=2.0,
        retrace_fill_bars=c.fill_bars,
        cooldown_bars=c.cooldown_bars,
        max_hold_bars=c.max_hold_bars,
        stop_buffer_atr=c.stop_buffer_atr,
        min_risk_atr=0.25,
        max_risk_atr=3.5,
        round_trip_cost_bps=1.0,
    )


def _generate_candidates() -> list[Candidate]:
    rng = np.random.default_rng(SEED)
    playbooks = [
        "PB", "SWEEP", "BREAK", "M15", "PB+SWEEP", "PB+BREAK", "PB+M15",
        "SWEEP+BREAK", "SWEEP+M15", "PB+SWEEP+BREAK", "PB+SWEEP+M15",
        "PB+SWEEP+RETEST", "PB+SWEEP+BREAK+M15+RETEST",
    ]
    options = {
        "session": ["BOTH", "LONDON", "NEW_YORK"],
        "body_min": [0.45, 0.50, 0.55, 0.60, 0.65],
        "range_atr_min": [0.50, 0.60, 0.70, 0.85, 1.00],
        "trend_min": [1, 2, 3],
        "require_m15": [False, True],
        "entry_model": ["BODY50", "BODY66", "FVG50"],
        "internal_fresh": [3, 6, 9, 12],
        "external_fresh": [2, 4, 6, 9],
        "fill_bars": [4, 8, 12],
        "cooldown_bars": [3, 6, 9, 12],
        "stop_lookback": [4, 6, 8, 12],
        "stop_buffer_atr": [0.05, 0.10, 0.15],
        "target_policy": ["2.0", "2.5", "3.0", "3.5", "4.0", "DYNAMIC"],
        "max_hold_bars": [72, 144, 216],
        "require_day_alignment": [False, True],
        "require_runway": [False, True],
    }

    seeds = [
        Candidate("PB+SWEEP", "BOTH", .52, .65, 2, False, "BODY50", 6, 4, 8, 6, 8, .10, "3.5", 216, True, True),
        Candidate("PB+SWEEP", "BOTH", .52, .65, 2, False, "BODY50", 6, 4, 8, 6, 8, .10, "DYNAMIC", 216, True, False),
        Candidate("PB+SWEEP+BREAK", "BOTH", .50, .60, 1, False, "BODY50", 9, 6, 8, 6, 8, .10, "DYNAMIC", 144, False, False),
        Candidate("PB+SWEEP+M15", "BOTH", .50, .60, 1, False, "BODY66", 9, 6, 12, 6, 6, .10, "DYNAMIC", 144, False, False),
        Candidate("SWEEP+BREAK", "BOTH", .55, .70, 1, False, "FVG50", 6, 6, 8, 6, 8, .10, "3.0", 144, False, True),
    ]
    found = set(seeds)
    while len(found) < RANDOM_CANDIDATES + len(seeds):
        c = Candidate(
            playbooks=str(rng.choice(playbooks)),
            session=str(rng.choice(options["session"])),
            body_min=float(rng.choice(options["body_min"])),
            range_atr_min=float(rng.choice(options["range_atr_min"])),
            trend_min=int(rng.choice(options["trend_min"])),
            require_m15=bool(rng.choice(options["require_m15"])),
            entry_model=str(rng.choice(options["entry_model"])),
            internal_fresh=int(rng.choice(options["internal_fresh"])),
            external_fresh=int(rng.choice(options["external_fresh"])),
            fill_bars=int(rng.choice(options["fill_bars"])),
            cooldown_bars=int(rng.choice(options["cooldown_bars"])),
            stop_lookback=int(rng.choice(options["stop_lookback"])),
            stop_buffer_atr=float(rng.choice(options["stop_buffer_atr"])),
            target_policy=str(rng.choice(options["target_policy"])),
            max_hold_bars=int(rng.choice(options["max_hold_bars"])),
            require_day_alignment=bool(rng.choice(options["require_day_alignment"])),
            require_runway=bool(rng.choice(options["require_runway"])),
        )
        found.add(c)
    return list(found)


def _md_table(df: pd.DataFrame, cols: list[str], n: int | None = None) -> str:
    x = df.head(n).copy() if n else df.copy()
    if x.empty:
        return "_No rows._"
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in x.iterrows():
        vals = []
        for c in cols:
            v = r[c]
            if pd.isna(v): vals.append("—")
            elif isinstance(v, (float, np.floating)): vals.append(f"{float(v):.2f}")
            else: vals.append(str(v))
        out.append("| " + " | ".join(vals) + " |")
    return "\n".join(out)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    m5 = load_m5_csv(DATA)
    observed_end = min(pd.Timestamp("2027-01-01", tz="UTC"), m5.index.max() + pd.Timedelta(minutes=5))
    if observed_end <= TEST_START:
        raise RuntimeError("No 2026 Dukascopy data")
    if m5.index.min() > pd.Timestamp("2025-01-01", tz="UTC"):
        raise RuntimeError("Need 2025 data for discovery")

    print("Preparing causal structural feature frame...")
    f = _prepare_base(m5)
    candidates = _generate_candidates()
    discovery_rows = []
    candidate_map: dict[str, Candidate] = {}

    print(f"Searching {len(candidates)} frozen candidates on 2025 discovery...")
    for k, c in enumerate(candidates, start=1):
        cid = f"C{k:04d}"
        candidate_map[cid] = c
        setups = _build_setups(f, c)
        if setups.empty:
            continue
        st = pd.to_datetime(setups.signal_time, utc=True)
        raw_n = int(((st >= DISCOVERY_START) & (st < DISCOVERY_END)).sum())
        raw_tpm = raw_n * 30.0 / _days(DISCOVERY_START, DISCOVERY_END)
        if raw_tpm < MIN_TRADES_PER_30D:
            continue
        trades = _replay_variable_targets(m5, setups, _candidate_cfg(c))
        s = _period_summary(trades, DISCOVERY_START, DISCOVERY_END)
        if s["trades_per_30d"] < MIN_TRADES_PER_30D:
            continue
        discovery_rows.append({
            "candidate": cid,
            **s,
            "params": json.dumps(asdict(c), sort_keys=True),
        })
        if k % 50 == 0:
            print(f"  processed {k}/{len(candidates)}; qualifying={len(discovery_rows)}")

    discovery = pd.DataFrame(discovery_rows)
    if discovery.empty:
        raise RuntimeError("No candidate met the 8 trades/30d discovery floor")
    discovery = discovery.sort_values(["end_rm", "lowest_rm"], ascending=[False, False]).reset_index(drop=True)
    discovery.to_csv(OUT / "discovery_2025.csv", index=False)

    finalists = discovery.head(FINALISTS).copy()
    test_rows = []
    trade_cache: dict[str, pd.DataFrame] = {}
    print(f"Testing top {len(finalists)} frozen 2025 finalists on 2026...")
    for _, drow in finalists.iterrows():
        cid = str(drow.candidate)
        c = candidate_map[cid]
        setups = _build_setups(f, c)
        trades = _replay_variable_targets(m5, setups, _candidate_cfg(c))
        test = _period_summary(trades, TEST_START, observed_end)
        test_rows.append({
            "candidate": cid,
            **test,
            "meets_8_per_30d": bool(test["trades_per_30d"] >= MIN_TRADES_PER_30D),
            "discovery_end_rm": float(drow.end_rm),
            "params": json.dumps(asdict(c), sort_keys=True),
        })
        trade_cache[cid] = trades

    test = pd.DataFrame(test_rows).sort_values(["meets_8_per_30d", "end_rm"], ascending=[False, False]).reset_index(drop=True)
    test.to_csv(OUT / "test_2026_finalists.csv", index=False)

    discovery_winner = str(discovery.iloc[0].candidate)
    primary_row = test[test.candidate.eq(discovery_winner)].iloc[0]
    eligible_test = test[test.meets_8_per_30d].copy()
    exploratory_winner = str(eligible_test.iloc[0].candidate) if not eligible_test.empty else "NONE"

    primary_trades = _slice(trade_cache[discovery_winner], TEST_START, observed_end)
    primary_trades, _ = _compound(primary_trades)
    primary_trades.to_csv(OUT / "discovery_winner_2026_trades.csv", index=False)
    primary_monthly = _monthly(trade_cache[discovery_winner], TEST_START, observed_end)
    primary_monthly.to_csv(OUT / "discovery_winner_2026_monthly.csv", index=False)

    if exploratory_winner != "NONE":
        exp_trades = _slice(trade_cache[exploratory_winner], TEST_START, observed_end)
        exp_trades, _ = _compound(exp_trades)
        exp_trades.to_csv(OUT / "best_2026_exploratory_trades.csv", index=False)
        exp_monthly = _monthly(trade_cache[exploratory_winner], TEST_START, observed_end)
        exp_monthly.to_csv(OUT / "best_2026_exploratory_monthly.csv", index=False)
    else:
        exp_monthly = pd.DataFrame()

    def param_block(cid: str) -> str:
        return "```json\n" + json.dumps(asdict(candidate_map[cid]), indent=2, sort_keys=True) + "\n```"

    report = [
        "# CASIO Equity-First Search — 2025 Find / 2026 Test",
        "",
        "This research uses the user's simple money objective rather than PF/WR ranking.",
        "",
        "## Objective",
        "",
        "- Start each strategy at **RM100**.",
        "- Risk **5% of current balance per filled trade**.",
        "- Require at least **8 filled trades per 30 days on average** during discovery.",
        "- Rank discovery candidates by **ending RM balance only**.",
        "- Search on **2025**. Freeze the finalists. Then replay them on **2026** without changing parameters.",
        "- Targets are always between **2R and 4R**; some candidates use a causal dynamic 2R/3R/4R policy based on signal-bar runway/strength.",
        "- Existing CASIO structural data is causal; replay uses a retracement fill, structural stop, same-bar stop-first rule, and **1.0 bps round-trip cost**.",
        "",
        f"Candidates searched: **{len(candidates)}**. 2025 candidates meeting the 8/30d floor: **{len(discovery)}**. Frozen finalists tested in 2026: **{len(finalists)}**.",
        "",
        "## 2025 discovery leaders",
        "",
        _md_table(discovery, ["candidate", "trades", "trades_per_30d", "end_rm", "lowest_rm", "max_drawdown_pct"], 15),
        "",
        "## Frozen finalists — 2026 test",
        "",
        _md_table(test, ["candidate", "trades", "trades_per_30d", "end_rm", "lowest_rm", "max_drawdown_pct", "meets_8_per_30d", "discovery_end_rm"], 30),
        "",
        "## Honest primary result — winner selected on 2025 before seeing 2026",
        "",
        f"Candidate: **{discovery_winner}**",
        f"- 2025 discovery: RM100 → **RM{float(discovery.iloc[0].end_rm):.2f}**, {float(discovery.iloc[0].trades_per_30d):.2f} trades/30d.",
        f"- 2026 test: RM100 → **RM{float(primary_row.end_rm):.2f}**, {int(primary_row.trades)} trades, {float(primary_row.trades_per_30d):.2f} trades/30d.",
        f"- Lowest 2026 balance: **RM{float(primary_row.lowest_rm):.2f}**. Max drawdown: **{float(primary_row.max_drawdown_pct):.2f}%**.",
        f"- Frequency floor in 2026: **{'PASS' if bool(primary_row.meets_8_per_30d) else 'FAIL'}**.",
        "",
        "### Primary candidate rules",
        "",
        param_block(discovery_winner),
        "",
        "### Primary candidate — 2026 month by month",
        "",
        _md_table(primary_monthly, ["month", "trades", "pnl_rm", "ending_balance_rm"]),
        "",
        "## Exploratory best among frozen finalists on 2026",
        "",
    ]
    if exploratory_winner == "NONE":
        report += ["None of the frozen 2025 finalists maintained the 8 trades/30d floor in 2026."]
    else:
        erow = test[test.candidate.eq(exploratory_winner)].iloc[0]
        report += [
            "This is **exploratory**, because this candidate is identified after looking at 2026 and is therefore not an untouched result.",
            "",
            f"Candidate: **{exploratory_winner}**",
            f"- RM100 → **RM{float(erow.end_rm):.2f}** in 2026.",
            f"- {int(erow.trades)} trades; **{float(erow.trades_per_30d):.2f} trades/30d**.",
            f"- Lowest balance: **RM{float(erow.lowest_rm):.2f}**. Max drawdown: **{float(erow.max_drawdown_pct):.2f}%**.",
            "",
            "### Exploratory candidate rules",
            "",
            param_block(exploratory_winner),
            "",
            "### Exploratory candidate — 2026 month by month",
            "",
            _md_table(exp_monthly, ["month", "trades", "pnl_rm", "ending_balance_rm"]),
        ]

    report += [
        "",
        "## Decision rule",
        "",
        "The search does not care whether a candidate has a fashionable PF or win rate. For this experiment the practical question is: **did RM100 grow under 5% risk while maintaining at least 8 trades/30d on the untouched 2026 test?**",
        "",
        "If the primary 2025-selected winner fails that test, this search has **not** found a strategy that meets the user's needs, even if an exploratory 2026 finalist looks attractive.",
        "",
    ]
    (OUT / "REPORT.md").write_text("\n".join(report), encoding="utf-8")

    summary = {
        "discovery_winner": discovery_winner,
        "primary_2026": _safe(primary_row.to_dict()),
        "exploratory_2026_winner": exploratory_winner,
        "coverage": {"data_start": m5.index.min(), "data_end": m5.index.max(), "test_end": observed_end},
        "search": {"candidates": len(candidates), "discovery_qualified": len(discovery), "finalists": len(finalists)},
    }
    (OUT / "summary.json").write_text(json.dumps(_safe(summary), indent=2), encoding="utf-8")
    print(json.dumps(_safe(summary), indent=2))
    print(f"Report: {OUT / 'REPORT.md'}")


if __name__ == "__main__":
    main()
