from __future__ import annotations

from pathlib import Path
import argparse
import json
import math

import numpy as np
import pandas as pd


START_CAPITAL = 100.0
RISK_FRACTION = 0.05
YEAR_START = pd.Timestamp("2026-01-01", tz="UTC")
YEAR_END = pd.Timestamp("2027-01-01", tz="UTC")


def load_m5(path: str | Path) -> pd.DataFrame:
    x = pd.read_csv(path)
    x["timestamp"] = pd.to_datetime(x["timestamp"], utc=True, errors="raise")
    x = x.sort_values("timestamp").drop_duplicates("timestamp").set_index("timestamp")
    cols = ["open", "high", "low", "close"]
    for c in cols:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna(subset=cols)
    return x


def resample_ohlc(x: pd.DataFrame, rule: str) -> pd.DataFrame:
    out = x.resample(rule, label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
    )
    return out.dropna()


def rsi_wilder(close: pd.Series, period: int = 8) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(avg_loss > 0, 100.0)
    rsi = rsi.where(avg_gain > 0, 0.0)
    return rsi


def max_streak(values: list[bool], wanted: bool) -> int:
    best = cur = 0
    for v in values:
        if v is wanted:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def prepare_signals(m5: pd.DataFrame, buy_level: float, sell_level: float) -> pd.DataFrame:
    m15 = resample_ohlc(m5, "15min")
    m30 = resample_ohlc(m5, "30min")
    m15["rsi8"] = rsi_wilder(m15["close"], 8)
    m30["rsi8"] = rsi_wilder(m30["close"], 8)

    # Only use a completed M30 bar. Its RSI becomes available 30 minutes after bar open.
    m30_available = m30["rsi8"].copy()
    m30_available.index = m30_available.index + pd.Timedelta(minutes=30)
    close_times = m15.index + pd.Timedelta(minutes=15)
    htf = m30_available.reindex(close_times, method="ffill")
    htf.index = m15.index
    m15["m30_rsi8_completed"] = htf

    prev = m15["rsi8"].shift(1)
    buy_cross = (prev > buy_level) & (m15["rsi8"] <= buy_level)
    sell_cross = (prev < sell_level) & (m15["rsi8"] >= sell_level)

    # Public FiboRSI8 SOP: RSI extreme + trigger candle direction + one-TF-higher filter.
    buy = (
        buy_cross
        & (m15["close"] < m15["open"])
        & (m15["m30_rsi8_completed"] >= 30.0)
    )
    sell = (
        sell_cross
        & (m15["close"] > m15["open"])
        & (m15["m30_rsi8_completed"] <= 70.0)
    )

    rows = []
    for t in m15.index[buy | sell]:
        direction = 1 if bool(buy.loc[t]) else -1
        rows.append(
            {
                "signal_time": t,
                "signal_close_time": t + pd.Timedelta(minutes=15),
                "direction": direction,
                "signal_open": float(m15.loc[t, "open"]),
                "signal_high": float(m15.loc[t, "high"]),
                "signal_low": float(m15.loc[t, "low"]),
                "signal_close": float(m15.loc[t, "close"]),
                "rsi8": float(m15.loc[t, "rsi8"]),
                "m30_rsi8": float(m15.loc[t, "m30_rsi8_completed"]),
            }
        )
    return pd.DataFrame(rows)


def replay_variant(
    m5: pd.DataFrame,
    signals: pd.DataFrame,
    rr: float,
    variant: str,
    buy_level: float,
    sell_level: float,
) -> pd.DataFrame:
    rows = []
    if signals.empty:
        return pd.DataFrame()

    idx = m5.index
    busy_until: pd.Timestamp | None = None

    for s in signals.itertuples(index=False):
        signal_time = pd.Timestamp(s.signal_time)
        if signal_time < YEAR_START or signal_time >= YEAR_END:
            continue

        # Entry only after the signal M15 candle has fully closed.
        entry_pos = idx.searchsorted(pd.Timestamp(s.signal_close_time), side="left")
        if entry_pos >= len(idx):
            continue
        entry_time = idx[entry_pos]
        if entry_time >= YEAR_END:
            continue
        if busy_until is not None and entry_time <= busy_until:
            continue

        entry = float(m5.iloc[entry_pos]["open"])
        direction = int(s.direction)
        stop = float(s.signal_low if direction == 1 else s.signal_high)
        if direction == 1 and entry <= stop:
            continue
        if direction == -1 and entry >= stop:
            continue

        risk = abs(entry - stop)
        if not np.isfinite(risk) or risk <= 0:
            continue
        target = entry + direction * rr * risk

        exit_price = None
        exit_time = None
        reason = None

        # M5 execution; conservative same-bar convention: stop before target.
        for j in range(entry_pos, len(idx)):
            t = idx[j]
            if t >= YEAR_END:
                break
            lo = float(m5.iloc[j]["low"])
            hi = float(m5.iloc[j]["high"])
            if direction == 1:
                hit_stop = lo <= stop
                hit_target = hi >= target
            else:
                hit_stop = hi >= stop
                hit_target = lo <= target

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
            rows.append(
                {
                    "variant": variant,
                    "buy_level": buy_level,
                    "sell_level": sell_level,
                    "rr": rr,
                    "signal_time": signal_time,
                    "entry_time": entry_time,
                    "exit_time": pd.NaT,
                    "direction": "BUY" if direction == 1 else "SELL",
                    "rsi8": float(s.rsi8),
                    "m30_rsi8": float(s.m30_rsi8),
                    "entry": entry,
                    "stop": stop,
                    "target": target,
                    "risk_distance": risk,
                    "exit_price": np.nan,
                    "r_multiple": np.nan,
                    "result": "OPEN",
                    "exit_reason": "unresolved",
                }
            )
            busy_until = idx[-1]
            break

        r_mult = (exit_price - entry) / risk if direction == 1 else (entry - exit_price) / risk
        rows.append(
            {
                "variant": variant,
                "buy_level": buy_level,
                "sell_level": sell_level,
                "rr": rr,
                "signal_time": signal_time,
                "entry_time": entry_time,
                "exit_time": exit_time,
                "direction": "BUY" if direction == 1 else "SELL",
                "rsi8": float(s.rsi8),
                "m30_rsi8": float(s.m30_rsi8),
                "entry": entry,
                "stop": stop,
                "target": target,
                "risk_distance": risk,
                "exit_price": exit_price,
                "r_multiple": float(r_mult),
                "result": "WIN" if r_mult > 0 else "LOSS",
                "exit_reason": reason,
            }
        )
        busy_until = exit_time

    return pd.DataFrame(rows)


def add_equity(trades: pd.DataFrame) -> pd.DataFrame:
    x = trades.copy()
    x["balance_before"] = np.nan
    x["balance_after"] = np.nan
    bal = START_CAPITAL
    for i in x.index:
        r = x.at[i, "r_multiple"]
        if not np.isfinite(r):
            continue
        x.at[i, "balance_before"] = bal
        bal = bal * (1.0 + RISK_FRACTION * float(r))
        x.at[i, "balance_after"] = bal
    return x


def summarize_variant(trades: pd.DataFrame, data_end: pd.Timestamp) -> tuple[dict, pd.DataFrame]:
    realized = trades[np.isfinite(pd.to_numeric(trades.get("r_multiple"), errors="coerce"))].copy()
    realized = add_equity(realized)
    if realized.empty:
        overall = {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate_pct": 0.0,
            "expectancy_r": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_pct": 0.0,
            "max_win_streak": 0,
            "max_loss_streak": 0,
            "start_balance_rm": START_CAPITAL,
            "end_balance_rm": START_CAPITAL,
            "return_pct": 0.0,
            "avg_trades_per_month": 0.0,
            "min_trades_month": 0,
            "positive_months": 0,
            "negative_months": 0,
            "open_trades": int((trades.get("result") == "OPEN").sum()) if not trades.empty else 0,
        }
        return overall, pd.DataFrame()

    r = realized["r_multiple"].astype(float)
    wins = int((r > 0).sum())
    losses = int((r < 0).sum())
    gross_win = float(r[r > 0].sum())
    gross_loss = float(-r[r < 0].sum())
    pf = gross_win / gross_loss if gross_loss > 0 else math.inf

    eq = [START_CAPITAL] + realized["balance_after"].astype(float).tolist()
    peak = eq[0]
    max_dd = 0.0
    for v in eq:
        peak = max(peak, v)
        max_dd = max(max_dd, (peak - v) / peak if peak > 0 else 0.0)

    outcomes = [v > 0 for v in r.tolist()]
    end_balance = float(realized.iloc[-1]["balance_after"])

    last_month = min(pd.Timestamp(data_end).tz_convert("UTC").to_period("M"), pd.Period("2026-12", freq="M"))
    months = pd.period_range("2026-01", last_month, freq="M")
    monthly_rows = []
    rolling_balance = START_CAPITAL
    for p in months:
        g = realized[pd.to_datetime(realized["entry_time"], utc=True).dt.to_period("M") == p].copy()
        start_bal = rolling_balance
        vals = g["r_multiple"].astype(float).tolist() if not g.empty else []
        for rv in vals:
            rolling_balance *= 1.0 + RISK_FRACTION * rv
        mw = sum(v > 0 for v in vals)
        ml = sum(v < 0 for v in vals)
        monthly_rows.append(
            {
                "month": str(p),
                "trades": len(vals),
                "wins": mw,
                "sl": ml,
                "win_rate_pct": (mw * 100.0 / len(vals)) if vals else 0.0,
                "net_r": float(sum(vals)),
                "max_win_streak": max_streak([v > 0 for v in vals], True),
                "max_loss_streak": max_streak([v > 0 for v in vals], False),
                "start_balance_rm": start_bal,
                "end_balance_rm": rolling_balance,
                "pnl_rm": rolling_balance - start_bal,
                "return_pct": ((rolling_balance / start_bal) - 1.0) * 100.0 if start_bal else 0.0,
            }
        )

    monthly = pd.DataFrame(monthly_rows)
    active_months = len(monthly)
    overall = {
        "trades": int(len(realized)),
        "wins": wins,
        "losses": losses,
        "win_rate_pct": wins * 100.0 / len(realized),
        "expectancy_r": float(r.mean()),
        "profit_factor": float(pf),
        "max_drawdown_pct": max_dd * 100.0,
        "max_win_streak": max_streak(outcomes, True),
        "max_loss_streak": max_streak(outcomes, False),
        "start_balance_rm": START_CAPITAL,
        "end_balance_rm": end_balance,
        "return_pct": (end_balance / START_CAPITAL - 1.0) * 100.0,
        "avg_trades_per_month": len(realized) / active_months if active_months else 0.0,
        "min_trades_month": int(monthly["trades"].min()) if not monthly.empty else 0,
        "positive_months": int((monthly["pnl_rm"] > 0).sum()) if not monthly.empty else 0,
        "negative_months": int((monthly["pnl_rm"] < 0).sum()) if not monthly.empty else 0,
        "flat_months": int((monthly["pnl_rm"] == 0).sum()) if not monthly.empty else 0,
        "open_trades": int((trades.get("result") == "OPEN").sum()) if not trades.empty else 0,
    }
    return overall, monthly


def f2(x: float) -> str:
    if x is None or not np.isfinite(x):
        return "∞" if x is not None and math.isinf(x) else "—"
    return f"{x:.2f}"


def run(data_path: str | Path, output_dir: str | Path) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    m5 = load_m5(data_path)
    data_end = m5.index.max()
    if data_end < YEAR_START:
        raise ValueError("Dataset has no 2026 data")

    configs = [
        ("STRICT_20_80", 20.0, 80.0),
        ("CLASSIC_2026_27_73", 27.0, 73.0),
    ]

    all_trades = []
    overall_rows = []
    monthly_rows = []

    for name, buy_level, sell_level in configs:
        signals = prepare_signals(m5, buy_level, sell_level)
        for rr in (2.0, 3.0):
            variant = f"{name}_RR{int(rr)}"
            trades = replay_variant(m5, signals, rr, variant, buy_level, sell_level)
            if trades.empty:
                trades = pd.DataFrame(columns=[
                    "variant","buy_level","sell_level","rr","signal_time","entry_time","exit_time",
                    "direction","rsi8","m30_rsi8","entry","stop","target","risk_distance","exit_price",
                    "r_multiple","result","exit_reason"
                ])
            all_trades.append(trades)
            overall, monthly = summarize_variant(trades, data_end)
            overall_rows.append({"variant": variant, "buy_level": buy_level, "sell_level": sell_level, "rr": rr, **overall})
            if not monthly.empty:
                monthly.insert(0, "variant", variant)
                monthly_rows.append(monthly)

    overall_df = pd.DataFrame(overall_rows)
    trades_df = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    monthly_df = pd.concat(monthly_rows, ignore_index=True) if monthly_rows else pd.DataFrame()

    overall_df.to_csv(out / "overall.csv", index=False)
    trades_df.to_csv(out / "trades.csv", index=False)
    monthly_df.to_csv(out / "monthly.csv", index=False)

    lines = [
        "# FiboRSI8 — CASIO-style 2026 backtest",
        "",
        f"Data: Dukascopy XAUUSD BID M5, coverage used through {data_end.isoformat()}",
        "Execution: M15 signal, completed M30 RSI8 filter, next available M5/M15-open entry, M5 path simulation.",
        "Risk: RM100 start, 5% current-equity risk per trade, compounding.",
        "Exit: real fixed SL at trigger-candle wick, fixed 2R/3R TP; no BE/protected-SL trick.",
        "Same M5 bar touches SL+TP: SL first (conservative). One position at a time.",
        "Broker spread/commission/slippage are not added.",
        "",
        "Public-SOP limitation: proprietary FiboBucci numeric PR/R1/R2/TP2 ratios are not public enough to reproduce exactly.",
        "This test therefore freezes the public RSI8+candle+HTF-filter entry logic and evaluates the user's preferred fixed-RR exits.",
        "",
        "## Overall",
        "",
        "| Variant | Trades | Avg/mo | Min/mo | Win | SL | WR | Exp R | PF | Max DD | W streak | L streak | End RM | Return |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in overall_df.itertuples(index=False):
        lines.append(
            f"| {r.variant} | {r.trades} | {r.avg_trades_per_month:.2f} | {r.min_trades_month} | "
            f"{r.wins} | {r.losses} | {r.win_rate_pct:.2f}% | {r.expectancy_r:+.3f} | "
            f"{f2(r.profit_factor)} | {r.max_drawdown_pct:.2f}% | {r.max_win_streak} | "
            f"{r.max_loss_streak} | RM{r.end_balance_rm:.2f} | {r.return_pct:+.2f}% |"
        )

    for variant in overall_df["variant"].tolist():
        lines += ["", f"## {variant}", ""]
        g = monthly_df[monthly_df["variant"] == variant] if not monthly_df.empty else pd.DataFrame()
        if g.empty:
            lines.append("No realized trades.")
            continue
        lines += [
            "| Month | Trades | Win | SL | WR | Net R | W streak | L streak | Start RM | End RM | P/L RM |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for m in g.itertuples(index=False):
            lines.append(
                f"| {m.month} | {m.trades} | {m.wins} | {m.sl} | {m.win_rate_pct:.2f}% | "
                f"{m.net_r:+.1f}R | {m.max_win_streak} | {m.max_loss_streak} | "
                f"RM{m.start_balance_rm:.2f} | RM{m.end_balance_rm:.2f} | RM{m.pnl_rm:+.2f} |"
            )

    report = "\n".join(lines) + "\n"
    (out / "REPORT.md").write_text(report, encoding="utf-8")

    summary = {
        "coverage": {"start": m5.index.min().isoformat(), "end": data_end.isoformat(), "bars": int(len(m5))},
        "assumptions": {
            "instrument": "XAUUSD",
            "source": "Dukascopy BID M5 canonical CASIO dataset",
            "signal_tf": "M15",
            "htf_filter": "completed M30 RSI8",
            "rsi_period": 8,
            "threshold_sets": ["20/80", "27/73"],
            "entry": "first available bar open after M15 signal candle closes",
            "stop": "signal candle opposite wick",
            "targets": ["2R", "3R"],
            "risk_per_trade": 0.05,
            "start_capital_rm": 100.0,
            "same_bar_policy": "stop first",
            "overlap": "one position at a time",
            "costs": "not modeled",
        },
        "overall": overall_df.replace({np.nan: None, np.inf: None, -np.inf: None}).to_dict(orient="records"),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(report)
    return summary


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data/xauusd_m5.csv")
    p.add_argument("--output", default="reports/fiborsi8-2026")
    a = p.parse_args()
    run(a.data, a.output)


if __name__ == "__main__":
    main()
