from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import json
import math

import numpy as np
import pandas as pd

from .fiborsi8_backtest import (
    START_CAPITAL,
    RISK_FRACTION,
    YEAR_START,
    YEAR_END,
    load_m5,
    resample_ohlc,
    rsi_wilder,
    summarize_variant,
)


@dataclass(frozen=True)
class Variant:
    name: str
    signal_mode: str = "cross"       # cross | repeat
    delay_bars: int = 0              # only for repeat
    htf_buy_min: float = 30.0
    htf_sell_max: float = 70.0
    entry_mode: str = "immediate"    # immediate | rsi_recovery | mid_reclaim | mid_retest | extreme_break_retest
    confirm_bars: int = 4


VARIANTS = (
    Variant("CONTROL_CROSS_IMMEDIATE"),
    Variant("DELAY3_IMMEDIATE", signal_mode="repeat", delay_bars=3),
    Variant("DELAY5_IMMEDIATE", signal_mode="repeat", delay_bars=5),
    Variant("DELAY3_HTF35_65", signal_mode="repeat", delay_bars=3, htf_buy_min=35.0, htf_sell_max=65.0),
    Variant("DELAY3_HTF40_60", signal_mode="repeat", delay_bars=3, htf_buy_min=40.0, htf_sell_max=60.0),
    Variant("DELAY3_RSI_RECOVERY", signal_mode="repeat", delay_bars=3, entry_mode="rsi_recovery"),
    Variant("DELAY3_MID_RECLAIM", signal_mode="repeat", delay_bars=3, entry_mode="mid_reclaim"),
    Variant("DELAY3_MID_RECLAIM_HTF35", signal_mode="repeat", delay_bars=3, htf_buy_min=35.0, htf_sell_max=65.0, entry_mode="mid_reclaim"),
    Variant("DELAY3_MID_RETEST", signal_mode="repeat", delay_bars=3, entry_mode="mid_retest"),
    Variant("DELAY3_EXTREME_BREAK_RETEST", signal_mode="repeat", delay_bars=3, entry_mode="extreme_break_retest"),
)


def prepare_context(m5: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    m15 = resample_ohlc(m5, "15min")
    m30 = resample_ohlc(m5, "30min")
    m15["rsi8"] = rsi_wilder(m15["close"], 8)
    m30["rsi8"] = rsi_wilder(m30["close"], 8)

    # Only completed M30 values can be used by an M15 signal.
    m30_available = m30["rsi8"].copy()
    m30_available.index = m30_available.index + pd.Timedelta(minutes=30)
    m15_close_times = m15.index + pd.Timedelta(minutes=15)
    htf = m30_available.reindex(m15_close_times, method="ffill")
    htf.index = m15.index
    m15["m30_rsi8_completed"] = htf
    return m15, m30


def make_signals(m15: pd.DataFrame, v: Variant) -> pd.DataFrame:
    prev = m15["rsi8"].shift(1)
    buy_raw = (
        (m15["rsi8"] <= 20.0)
        & (m15["close"] < m15["open"])
        & (m15["m30_rsi8_completed"] >= v.htf_buy_min)
    )
    sell_raw = (
        (m15["rsi8"] >= 80.0)
        & (m15["close"] > m15["open"])
        & (m15["m30_rsi8_completed"] <= v.htf_sell_max)
    )

    if v.signal_mode == "cross":
        buy_raw &= prev > 20.0
        sell_raw &= prev < 80.0

    rows: list[dict] = []
    last_dir_bar = {1: -10**9, -1: -10**9}

    for i, t in enumerate(m15.index):
        direction = 1 if bool(buy_raw.iloc[i]) else -1 if bool(sell_raw.iloc[i]) else 0
        if direction == 0:
            continue
        if v.signal_mode == "repeat" and i - last_dir_bar[direction] < v.delay_bars:
            continue
        last_dir_bar[direction] = i
        row = m15.iloc[i]
        rows.append(
            {
                "signal_i": i,
                "signal_time": t,
                "signal_close_time": t + pd.Timedelta(minutes=15),
                "direction": direction,
                "signal_open": float(row.open),
                "signal_high": float(row.high),
                "signal_low": float(row.low),
                "signal_close": float(row.close),
                "signal_mid": float((row.high + row.low) / 2.0),
                "rsi8": float(row.rsi8),
                "m30_rsi8": float(row.m30_rsi8_completed),
            }
        )
    return pd.DataFrame(rows)


def _market_entry_after(idx: pd.DatetimeIndex, when: pd.Timestamp) -> tuple[int, pd.Timestamp] | None:
    pos = idx.searchsorted(when, side="left")
    if pos >= len(idx):
        return None
    return int(pos), idx[pos]


def _find_m15_confirm(m15: pd.DataFrame, s, mode: str, max_bars: int) -> pd.Timestamp | None:
    i0 = int(s.signal_i)
    end = min(len(m15), i0 + 1 + max_bars)
    for j in range(i0 + 1, end):
        row = m15.iloc[j]
        if mode == "rsi_recovery":
            ok = (
                (int(s.direction) == 1 and row.rsi8 >= 30.0 and row.close > row.open)
                or (int(s.direction) == -1 and row.rsi8 <= 70.0 and row.close < row.open)
            )
        elif mode in ("mid_reclaim", "mid_retest"):
            ok = (
                (int(s.direction) == 1 and row.close > float(s.signal_mid))
                or (int(s.direction) == -1 and row.close < float(s.signal_mid))
            )
        elif mode == "extreme_break_retest":
            ok = (
                (int(s.direction) == 1 and row.close > float(s.signal_high))
                or (int(s.direction) == -1 and row.close < float(s.signal_low))
            )
        else:
            raise ValueError(mode)
        if ok:
            return m15.index[j] + pd.Timedelta(minutes=15)
    return None


def _find_retest_fill(
    m5: pd.DataFrame,
    after: pd.Timestamp,
    price: float,
    horizon_minutes: int,
) -> tuple[int, pd.Timestamp] | None:
    idx = m5.index
    start = idx.searchsorted(after, side="left")
    end_time = after + pd.Timedelta(minutes=horizon_minutes)
    for j in range(start, len(idx)):
        t = idx[j]
        if t >= end_time:
            break
        bar = m5.iloc[j]
        if float(bar.low) <= price <= float(bar.high):
            return int(j), t
    return None


def _resolve(
    m5: pd.DataFrame,
    entry_pos: int,
    entry_time: pd.Timestamp,
    entry: float,
    direction: int,
    stop: float,
    rr: float = 3.0,
) -> dict | None:
    risk = abs(entry - stop)
    if not np.isfinite(risk) or risk <= 0:
        return None
    if direction == 1 and entry <= stop:
        return None
    if direction == -1 and entry >= stop:
        return None

    target = entry + direction * rr * risk
    idx = m5.index
    exit_price = exit_time = reason = None

    for j in range(entry_pos, len(idx)):
        t = idx[j]
        if t >= YEAR_END:
            break
        lo, hi = float(m5.iloc[j].low), float(m5.iloc[j].high)
        if direction == 1:
            hit_stop, hit_target = lo <= stop, hi >= target
        else:
            hit_stop, hit_target = hi >= stop, lo <= target

        # Conservative intrabar ordering.
        if hit_stop:
            exit_price = stop
            exit_time = t + pd.Timedelta(minutes=5)
            reason = "SL_same_bar" if hit_target else "SL"
            break
        if hit_target:
            exit_price = target
            exit_time = t + pd.Timedelta(minutes=5)
            reason = "TP"
            break

    if exit_price is None:
        return {
            "exit_time": pd.NaT,
            "target": target,
            "risk_distance": risk,
            "exit_price": np.nan,
            "r_multiple": np.nan,
            "result": "OPEN",
            "exit_reason": "unresolved",
        }

    r = (exit_price - entry) / risk if direction == 1 else (entry - exit_price) / risk
    return {
        "exit_time": exit_time,
        "target": target,
        "risk_distance": risk,
        "exit_price": exit_price,
        "r_multiple": float(r),
        "result": "WIN" if r > 0 else "LOSS",
        "exit_reason": reason,
    }


def replay(m5: pd.DataFrame, m15: pd.DataFrame, signals: pd.DataFrame, v: Variant) -> pd.DataFrame:
    if signals.empty:
        return pd.DataFrame()

    rows: list[dict] = []
    idx = m5.index
    busy_until: pd.Timestamp | None = None

    for s in signals.itertuples(index=False):
        signal_time = pd.Timestamp(s.signal_time)
        if signal_time < YEAR_START or signal_time >= YEAR_END:
            continue

        direction = int(s.direction)
        entry_pos = None
        entry_time = None
        entry = None

        if v.entry_mode == "immediate":
            found = _market_entry_after(idx, pd.Timestamp(s.signal_close_time))
            if found is None:
                continue
            entry_pos, entry_time = found
            entry = float(m5.iloc[entry_pos].open)

        elif v.entry_mode in ("rsi_recovery", "mid_reclaim"):
            confirm = _find_m15_confirm(m15, s, v.entry_mode, v.confirm_bars)
            if confirm is None:
                continue
            found = _market_entry_after(idx, confirm)
            if found is None:
                continue
            entry_pos, entry_time = found
            entry = float(m5.iloc[entry_pos].open)

        elif v.entry_mode == "mid_retest":
            confirm = _find_m15_confirm(m15, s, "mid_retest", v.confirm_bars)
            if confirm is None:
                continue
            found = _find_retest_fill(m5, confirm, float(s.signal_mid), v.confirm_bars * 15)
            if found is None:
                continue
            entry_pos, entry_time = found
            entry = float(s.signal_mid)

        elif v.entry_mode == "extreme_break_retest":
            confirm = _find_m15_confirm(m15, s, "extreme_break_retest", v.confirm_bars)
            if confirm is None:
                continue
            level = float(s.signal_high if direction == 1 else s.signal_low)
            found = _find_retest_fill(m5, confirm, level, v.confirm_bars * 15)
            if found is None:
                continue
            entry_pos, entry_time = found
            entry = level

        else:
            raise ValueError(v.entry_mode)

        if entry_time >= YEAR_END:
            continue
        if busy_until is not None and entry_time <= busy_until:
            continue

        stop = float(s.signal_low if direction == 1 else s.signal_high)
        outcome = _resolve(m5, entry_pos, entry_time, entry, direction, stop, 3.0)
        if outcome is None:
            continue

        rows.append(
            {
                "variant": v.name,
                "signal_time": signal_time,
                "entry_time": entry_time,
                "exit_time": outcome["exit_time"],
                "direction": "BUY" if direction == 1 else "SELL",
                "signal_mode": v.signal_mode,
                "delay_bars": v.delay_bars,
                "htf_buy_min": v.htf_buy_min,
                "htf_sell_max": v.htf_sell_max,
                "entry_mode": v.entry_mode,
                "rsi8": float(s.rsi8),
                "m30_rsi8": float(s.m30_rsi8),
                "entry": entry,
                "stop": stop,
                "target": outcome["target"],
                "risk_distance": outcome["risk_distance"],
                "exit_price": outcome["exit_price"],
                "r_multiple": outcome["r_multiple"],
                "result": outcome["result"],
                "exit_reason": outcome["exit_reason"],
            }
        )

        if pd.isna(outcome["exit_time"]):
            busy_until = idx[-1]
            break
        busy_until = pd.Timestamp(outcome["exit_time"])

    return pd.DataFrame(rows)


def run(data_path: str | Path, output_dir: str | Path) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    m5 = load_m5(data_path)
    m15, _ = prepare_context(m5)
    data_end = m5.index.max()

    overall_rows = []
    monthly_rows = []
    all_trades = []

    for v in VARIANTS:
        signals = make_signals(m15, v)
        trades = replay(m5, m15, signals, v)
        if trades.empty:
            trades = pd.DataFrame(columns=[
                "variant","signal_time","entry_time","exit_time","direction","signal_mode","delay_bars",
                "htf_buy_min","htf_sell_max","entry_mode","rsi8","m30_rsi8","entry","stop","target",
                "risk_distance","exit_price","r_multiple","result","exit_reason"
            ])
        overall, monthly = summarize_variant(trades, data_end)
        overall_rows.append({
            "variant": v.name,
            "signal_mode": v.signal_mode,
            "delay_bars": v.delay_bars,
            "entry_mode": v.entry_mode,
            "htf_buy_min": v.htf_buy_min,
            "htf_sell_max": v.htf_sell_max,
            **overall,
        })
        if not monthly.empty:
            monthly.insert(0, "variant", v.name)
            monthly_rows.append(monthly)
        all_trades.append(trades)

    overall_df = pd.DataFrame(overall_rows)
    monthly_df = pd.concat(monthly_rows, ignore_index=True) if monthly_rows else pd.DataFrame()
    trades_df = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()

    # Decision view: frequency first, then expectancy/PF. No automatic promotion.
    overall_df["freq_gap_to_8"] = (overall_df["avg_trades_per_month"] - 8.0).abs()
    overall_df["meets_avg8"] = overall_df["avg_trades_per_month"] >= 8.0
    overall_df["positive_edge"] = (overall_df["expectancy_r"] > 0) & (overall_df["profit_factor"] > 1.0)
    ranked = overall_df.sort_values(
        ["positive_edge", "meets_avg8", "expectancy_r", "profit_factor", "max_drawdown_pct"],
        ascending=[False, False, False, False, True],
    )

    overall_df.to_csv(out / "overall.csv", index=False)
    monthly_df.to_csv(out / "monthly.csv", index=False)
    trades_df.to_csv(out / "trades.csv", index=False)
    ranked.to_csv(out / "ranked.csv", index=False)

    lines = [
        "# FiboRSI8 Phase 2 — frequency + structural confirmation research",
        "",
        f"Coverage: {m5.index.min().isoformat()} -> {data_end.isoformat()}",
        "Instrument/data: XAUUSD Dukascopy BID M5; 2026 trades only.",
        "Capital: RM100; 5% current-equity risk; fixed 3R TP; real signal-wick SL; compounding.",
        "Execution: one position at a time; M5 path simulation; if SL and TP occur in same M5 bar, SL wins.",
        "Costs: spread/commission/slippage not modeled, matching the Phase-1 control.",
        "",
        "Control = first cross into RSI8 20/80 with trigger-candle color + completed M30 30/70 filter.",
        "DELAY3/5 = while RSI remains extreme, a new same-direction setup may be emitted after 3/5 completed M15 bars.",
        "MID_RECLAIM/RETEST and EXTREME_BREAK_RETEST are research proxies for body-break/pullback structure; they are NOT claimed to be proprietary PR/R1/R2 numeric levels.",
        "",
        "## Overall",
        "",
        "| Variant | Trades | Avg/mo | Min/mo | Win | SL | WR | Exp R | PF | Max DD | W/L streak | RM100 → | Return |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in ranked.itertuples(index=False):
        pf = "∞" if math.isinf(float(r.profit_factor)) else f"{r.profit_factor:.2f}"
        lines.append(
            f"| {r.variant} | {r.trades} | {r.avg_trades_per_month:.2f} | {r.min_trades_month} | "
            f"{r.wins} | {r.losses} | {r.win_rate_pct:.2f}% | {r.expectancy_r:+.3f} | {pf} | "
            f"{r.max_drawdown_pct:.2f}% | {r.max_win_streak}/{r.max_loss_streak} | "
            f"RM{r.end_balance_rm:.2f} | {r.return_pct:+.2f}% |"
        )

    for variant in ranked["variant"].tolist():
        lines += ["", f"## {variant}", ""]
        g = monthly_df[monthly_df["variant"] == variant] if not monthly_df.empty else pd.DataFrame()
        if g.empty:
            lines.append("No realized trades.")
            continue
        lines += [
            "| Month | Trades | Win | SL | WR | Net R | W/L streak | Start RM | End RM | P/L RM |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for m in g.itertuples(index=False):
            lines.append(
                f"| {m.month} | {m.trades} | {m.wins} | {m.sl} | {m.win_rate_pct:.2f}% | "
                f"{m.net_r:+.1f}R | {m.max_win_streak}/{m.max_loss_streak} | "
                f"RM{m.start_balance_rm:.2f} | RM{m.end_balance_rm:.2f} | RM{m.pnl_rm:+.2f} |"
            )

    report = "\n".join(lines) + "\n"
    (out / "REPORT.md").write_text(report, encoding="utf-8")

    summary = {
        "coverage": {"start": m5.index.min().isoformat(), "end": data_end.isoformat(), "bars": int(len(m5))},
        "phase": "FiboRSI8 Phase 2",
        "risk": {"start_rm": START_CAPITAL, "risk_fraction": RISK_FRACTION, "rr": 3.0},
        "variants": ranked.replace({np.nan: None, np.inf: None, -np.inf: None}).to_dict(orient="records"),
        "note": "Structural proxies are hypothesis tests, not a claim to reproduce proprietary FiboBucci numeric levels.",
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(report)
    return summary


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data/xauusd_m5_dukascopy_research.csv")
    p.add_argument("--output", default="reports/fiborsi8-phase2-2026")
    a = p.parse_args()
    run(a.data, a.output)


if __name__ == "__main__":
    main()
