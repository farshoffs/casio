from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json

import pandas as pd

from .v3_core import load_m5_csv
from .route_ab_2026_backtest import _replay_variable_targets
from .equity_first_search import (
    START_BALANCE_RM,
    MIN_TRADES_PER_30D,
    FINALISTS,
    _build_setups,
    _candidate_cfg,
    _compound,
    _days,
    _generate_candidates,
    _md_table,
    _monthly,
    _period_summary,
    _prepare_base,
    _safe,
    _slice,
)


DISCOVERY_DATA = Path("data/xauusd_m5_secondary_octafx_mt4.csv")
TEST_DATA = Path("data/xauusd_m5_dukascopy_research.csv")
OUT = Path("reports/equity-first-search-2026")
DISCOVERY_WARMUP = pd.Timestamp("2023-10-01", tz="UTC")
DISCOVERY_START = pd.Timestamp("2024-01-01", tz="UTC")
DISCOVERY_END = pd.Timestamp("2026-01-01", tz="UTC")
TEST_WARMUP = pd.Timestamp("2025-10-01", tz="UTC")
TEST_START = pd.Timestamp("2026-01-01", tz="UTC")
TEST_END = pd.Timestamp("2027-01-01", tz="UTC")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    secondary = load_m5_csv(DISCOVERY_DATA)
    secondary = secondary[(secondary.index >= DISCOVERY_WARMUP) & (secondary.index < DISCOVERY_END)].copy()
    if secondary.index.min() > DISCOVERY_WARMUP or secondary.index.max() < DISCOVERY_END - pd.Timedelta(days=2):
        raise RuntimeError("Secondary discovery feed does not cover the required 2024-2025 window")

    duk = load_m5_csv(TEST_DATA)
    duk = duk[duk.index >= TEST_WARMUP].copy()
    observed_end = min(TEST_END, duk.index.max() + pd.Timedelta(minutes=5))
    if observed_end <= TEST_START:
        raise RuntimeError("Dukascopy feed has no 2026 test data")

    print("Preparing secondary 2024-2025 discovery features...")
    f_disc = _prepare_base(secondary)
    print("Preparing Dukascopy 2026 test features...")
    f_test = _prepare_base(duk)

    candidates = _generate_candidates()
    candidate_map = {}
    discovery_rows = []

    print(f"Searching {len(candidates)} candidates on independent 2024-2025 secondary feed...")
    for k, c in enumerate(candidates, start=1):
        cid = f"C{k:04d}"
        candidate_map[cid] = c
        setups = _build_setups(f_disc, c)
        if setups.empty:
            continue
        st = pd.to_datetime(setups.signal_time, utc=True)
        raw_n = int(((st >= DISCOVERY_START) & (st < DISCOVERY_END)).sum())
        raw_tpm = raw_n * 30.0 / _days(DISCOVERY_START, DISCOVERY_END)
        if raw_tpm < MIN_TRADES_PER_30D:
            continue
        trades = _replay_variable_targets(secondary, setups, _candidate_cfg(c))
        s = _period_summary(trades, DISCOVERY_START, DISCOVERY_END)
        if s["trades_per_30d"] < MIN_TRADES_PER_30D:
            continue
        discovery_rows.append({
            "candidate": cid,
            **s,
            "params": json.dumps(asdict(c), sort_keys=True),
        })
        if k % 50 == 0:
            print(f"processed {k}/{len(candidates)}; qualified={len(discovery_rows)}")

    discovery = pd.DataFrame(discovery_rows)
    if discovery.empty:
        raise RuntimeError("No candidate met 8 trades/30d on 2024-2025 discovery")
    discovery = discovery.sort_values(["end_rm", "lowest_rm"], ascending=[False, False]).reset_index(drop=True)
    discovery.to_csv(OUT / "discovery_secondary_2024_2025.csv", index=False)

    finalists = discovery.head(FINALISTS).copy()
    test_rows = []
    trade_cache = {}
    print(f"Testing {len(finalists)} frozen finalists on Dukascopy 2026...")
    for _, drow in finalists.iterrows():
        cid = str(drow.candidate)
        c = candidate_map[cid]
        setups = _build_setups(f_test, c)
        trades = _replay_variable_targets(duk, setups, _candidate_cfg(c))
        s = _period_summary(trades, TEST_START, observed_end)
        test_rows.append({
            "candidate": cid,
            **s,
            "meets_8_per_30d": bool(s["trades_per_30d"] >= MIN_TRADES_PER_30D),
            "discovery_end_rm": float(drow.end_rm),
            "params": json.dumps(asdict(c), sort_keys=True),
        })
        trade_cache[cid] = trades

    test = pd.DataFrame(test_rows).sort_values(["meets_8_per_30d", "end_rm"], ascending=[False, False]).reset_index(drop=True)
    test.to_csv(OUT / "dukascopy_2026_finalists.csv", index=False)

    discovery_winner = str(discovery.iloc[0].candidate)
    primary = test[test.candidate.eq(discovery_winner)].iloc[0]
    eligible = test[test.meets_8_per_30d].copy()
    exploratory = str(eligible.iloc[0].candidate) if not eligible.empty else "NONE"

    p_trades = _slice(trade_cache[discovery_winner], TEST_START, observed_end)
    p_trades, _ = _compound(p_trades)
    p_trades.to_csv(OUT / "primary_2026_trades.csv", index=False)
    p_month = _monthly(trade_cache[discovery_winner], TEST_START, observed_end)
    p_month.to_csv(OUT / "primary_2026_monthly.csv", index=False)

    if exploratory != "NONE":
        e_trades = _slice(trade_cache[exploratory], TEST_START, observed_end)
        e_trades, _ = _compound(e_trades)
        e_trades.to_csv(OUT / "exploratory_2026_trades.csv", index=False)
        e_month = _monthly(trade_cache[exploratory], TEST_START, observed_end)
        e_month.to_csv(OUT / "exploratory_2026_monthly.csv", index=False)
    else:
        e_month = pd.DataFrame()

    def rules(cid: str) -> str:
        return "```json\n" + json.dumps(asdict(candidate_map[cid]), indent=2, sort_keys=True) + "\n```"

    report = [
        "# CASIO Equity-First Search — Independent Find, Dukascopy 2026 Test",
        "",
        "## The only ranking objective",
        "",
        f"Start **RM{START_BALANCE_RM:.0f}**, risk **5% of current balance per filled trade**, require **>= {MIN_TRADES_PER_30D:.0f} trades/30d**, and see where the balance goes.",
        "",
        "PF and win rate are not used to select candidates in this experiment.",
        "",
        "## Separation between find and test",
        "",
        "- **Find/search:** independent Octa/MT4 secondary feed, entries from **2024-01-01 through 2025-12-31**.",
        f"- **Test:** Dukascopy research feed, entries from **2026-01-01 through {observed_end.isoformat()}**.",
        "- 2026 parameters are frozen before the Dukascopy replay.",
        "- Candidate techniques include structural pullbacks, external liquidity sweeps, breakout/retests, M15 sweeps, session retests, BODY50/BODY66/FVG50 retracement entries, structural stops, and 2R-4R fixed/dynamic targets.",
        "- Replay uses the repository's **1.0 bps round-trip cost assumption** and conservative stop-first same-bar handling.",
        "",
        f"Candidates searched: **{len(candidates)}**. Discovery candidates satisfying the frequency floor: **{len(discovery)}**. Frozen finalists: **{len(finalists)}**.",
        "",
        "## Best balances on 2024-2025 discovery",
        "",
        _md_table(discovery, ["candidate", "trades", "trades_per_30d", "end_rm", "lowest_rm", "max_drawdown_pct"], 20),
        "",
        "## Frozen finalists on Dukascopy 2026",
        "",
        _md_table(test, ["candidate", "trades", "trades_per_30d", "end_rm", "lowest_rm", "max_drawdown_pct", "meets_8_per_30d", "discovery_end_rm"], 30),
        "",
        "## Primary result — chosen before looking at Dukascopy 2026",
        "",
        f"Candidate **{discovery_winner}**",
        f"- Discovery: RM100 -> **RM{float(discovery.iloc[0].end_rm):.2f}** with **{float(discovery.iloc[0].trades_per_30d):.2f} trades/30d**.",
        f"- Dukascopy 2026: RM100 -> **RM{float(primary.end_rm):.2f}** from **{int(primary.trades)} trades**, or **{float(primary.trades_per_30d):.2f} trades/30d**.",
        f"- Lowest 2026 balance: **RM{float(primary.lowest_rm):.2f}**. Maximum drawdown: **{float(primary.max_drawdown_pct):.2f}%**.",
        f"- 8 trades/30d floor: **{'PASS' if bool(primary.meets_8_per_30d) else 'FAIL'}**.",
        "",
        "### Primary rules",
        "",
        rules(discovery_winner),
        "",
        "### Primary 2026 balance path",
        "",
        _md_table(p_month, ["month", "trades", "pnl_rm", "ending_balance_rm"]),
        "",
        "## Exploratory best 2026 finalist",
        "",
    ]

    if exploratory == "NONE":
        report.append("No frozen finalist maintained >=8 trades/30d on Dukascopy 2026.")
    else:
        erow = test[test.candidate.eq(exploratory)].iloc[0]
        report += [
            "This is exploratory because it is identified after comparing 2026 finalists; it is not an untouched winner.",
            "",
            f"Candidate **{exploratory}**",
            f"- RM100 -> **RM{float(erow.end_rm):.2f}**.",
            f"- **{int(erow.trades)} trades**, **{float(erow.trades_per_30d):.2f} trades/30d**.",
            f"- Lowest balance **RM{float(erow.lowest_rm):.2f}**; max drawdown **{float(erow.max_drawdown_pct):.2f}%**.",
            "",
            "### Exploratory rules",
            "",
            rules(exploratory),
            "",
            "### Exploratory 2026 balance path",
            "",
            _md_table(e_month, ["month", "trades", "pnl_rm", "ending_balance_rm"]),
        ]

    report += [
        "",
        "## Pass/fail interpretation",
        "",
        "For this research, a strategy suits the requested method only if the **pre-2026-selected primary candidate** both maintains >=8 trades/30d and grows RM100 on Dukascopy 2026. If it does not, the honest answer is that the search has not found the requested strategy yet.",
        "",
    ]
    (OUT / "REPORT.md").write_text("\n".join(report), encoding="utf-8")

    summary = {
        "primary_candidate": discovery_winner,
        "primary_2026": _safe(primary.to_dict()),
        "exploratory_candidate": exploratory,
        "candidate_count": len(candidates),
        "discovery_qualified": len(discovery),
        "finalists": len(finalists),
        "test_end": observed_end,
    }
    (OUT / "summary.json").write_text(json.dumps(_safe(summary), indent=2), encoding="utf-8")
    print(json.dumps(_safe(summary), indent=2))
    print(f"Report: {OUT / 'REPORT.md'}")


if __name__ == "__main__":
    main()
