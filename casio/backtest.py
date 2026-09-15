from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable

import numpy as np
import pandas as pd

from .strategy import add_features, signal_for_row


@dataclass
class Trade:
    mode: str
    direction: str
    entry_time: str
    exit_time: str
    entry: float
    stop: float
    target: float
    exit_price: float
    r_multiple: float
    result: str
    score: float


def _resolve_trade(df: pd.DataFrame, i: int, signal: dict, max_bars: int = 48) -> Trade | None:
    direction = signal["direction"]
    entry = float(signal["entry"])
    stop = float(signal["stop"])
    target = float(signal["target"])
    risk = abs(entry - stop)
    if risk <= 0:
        return None

    end = min(len(df), i + 1 + max_bars)
    exit_price = float(df.iloc[end - 1]["close"])
    exit_time = str(df.index[end - 1])
    result = "timeout"

    for j in range(i + 1, end):
        bar = df.iloc[j]
        # Conservative same-bar assumption: stop is evaluated before target.
        if direction == "long":
            if bar["low"] <= stop:
                exit_price, exit_time, result = stop, str(df.index[j]), "loss"
                break
            if bar["high"] >= target:
                exit_price, exit_time, result = target, str(df.index[j]), "win"
                break
        else:
            if bar["high"] >= stop:
                exit_price, exit_time, result = stop, str(df.index[j]), "loss"
                break
            if bar["low"] <= target:
                exit_price, exit_time, result = target, str(df.index[j]), "win"
                break

    pnl = (exit_price - entry) if direction == "long" else (entry - exit_price)
    r_multiple = pnl / risk
    if result == "timeout":
        result = "win" if r_multiple > 0 else "loss" if r_multiple < 0 else "flat"

    return Trade(
        mode=signal["mode"],
        direction=direction,
        entry_time=str(df.index[i]),
        exit_time=exit_time,
        entry=entry,
        stop=stop,
        target=target,
        exit_price=float(exit_price),
        r_multiple=float(r_multiple),
        result=result,
        score=float(signal["score"]),
    )


def run_backtest(df: pd.DataFrame, max_trades: int | None = None, max_bars_per_trade: int = 48) -> pd.DataFrame:
    data = add_features(df)
    trades: list[Trade] = []
    next_free_bar = 0

    for i in range(50, len(data) - 1):
        if i < next_free_bar:
            continue
        signal = signal_for_row(data.iloc[i])
        if not signal.get("valid"):
            continue
        trade = _resolve_trade(data, i, signal, max_bars=max_bars_per_trade)
        if trade is None:
            continue
        trades.append(trade)
        # Avoid overlapping trades by advancing to the resolved exit bar.
        try:
            next_free_bar = data.index.get_loc(pd.Timestamp(trade.exit_time)) + 1
        except Exception:
            next_free_bar = i + 1
        if max_trades and len(trades) >= max_trades:
            break

    return pd.DataFrame([asdict(t) for t in trades])


def metrics(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate_pct": 0.0,
            "avg_r": 0.0,
            "expectancy_r": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_r": 0.0,
        }

    r = trades["r_multiple"].astype(float)
    wins = int((r > 0).sum())
    losses = int((r < 0).sum())
    gross_win = float(r[r > 0].sum())
    gross_loss = float(-r[r < 0].sum())
    equity = r.cumsum()
    drawdown = equity.cummax() - equity

    return {
        "trades": int(len(trades)),
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round((wins / len(trades)) * 100, 2),
        "avg_r": round(float(r.mean()), 4),
        "expectancy_r": round(float(r.mean()), 4),
        "profit_factor": round(gross_win / gross_loss, 3) if gross_loss > 0 else float("inf"),
        "max_drawdown_r": round(float(drawdown.max()) if len(drawdown) else 0.0, 4),
    }


def rolling_report(trades: pd.DataFrame, n: int = 100) -> dict:
    current = trades.tail(n).copy()
    report = {"overall": metrics(current), "modes": {}}
    for mode in ["intraday", "scalping"]:
        report["modes"][mode] = metrics(current[current["mode"] == mode]) if not current.empty else metrics(pd.DataFrame())
    return report
