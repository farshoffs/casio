from __future__ import annotations

from dataclasses import asdict
from typing import Literal

import numpy as np
import pandas as pd

from .config import IntradayConfig, ScalpingConfig

Mode = Literal["intraday", "scalping", "none"]
Direction = Literal["long", "short", "flat"]


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    up = df["high"].diff()
    down = -df["low"].diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    atr = _atr(df, period).replace(0, np.nan)
    plus_di = 100 * pd.Series(plus_dm, index=df.index).rolling(period).mean() / atr
    minus_di = 100 * pd.Series(minus_dm, index=df.index).rolling(period).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.rolling(period).mean()


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ema20"] = out["close"].ewm(span=20, adjust=False).mean()
    out["ema50"] = out["close"].ewm(span=50, adjust=False).mean()
    out["atr14"] = _atr(out, 14)
    out["adx14"] = _adx(out, 14)
    out["hh20"] = out["high"].rolling(20).max().shift(1)
    out["ll20"] = out["low"].rolling(20).min().shift(1)
    out["range_high30"] = out["high"].rolling(30).max().shift(1)
    out["range_low30"] = out["low"].rolling(30).min().shift(1)
    out["range_size30"] = out["range_high30"] - out["range_low30"]
    return out


def classify_regime(row: pd.Series, scalp: ScalpingConfig = ScalpingConfig()) -> Mode:
    if pd.isna(row.get("atr14")) or pd.isna(row.get("adx14")):
        return "none"
    range_atr = row["range_size30"] / row["atr14"] if row["atr14"] else np.inf
    if row["adx14"] <= scalp.max_adx and range_atr <= scalp.max_range_atr:
        return "scalping"
    return "intraday"


def intraday_signal(row: pd.Series, cfg: IntradayConfig = IntradayConfig()) -> dict:
    score = 0
    reasons: list[str] = []
    direction: Direction = "flat"

    bullish = row["ema20"] > row["ema50"] and row["close"] > row["ema20"]
    bearish = row["ema20"] < row["ema50"] and row["close"] < row["ema20"]
    if bullish:
        direction = "long"
        score += 25
        reasons.append("EMA20 above EMA50 with price above EMA20")
    elif bearish:
        direction = "short"
        score += 25
        reasons.append("EMA20 below EMA50 with price below EMA20")

    if direction == "long" and row["low"] < row["ll20"] and row["close"] > row["ll20"]:
        score += 25
        reasons.append("sell-side liquidity sweep and reclaim")
    if direction == "short" and row["high"] > row["hh20"] and row["close"] < row["hh20"]:
        score += 25
        reasons.append("buy-side liquidity sweep and rejection")

    if direction == "long" and row["close"] > row["open"]:
        score += 15
        reasons.append("bullish confirmation candle")
    if direction == "short" and row["close"] < row["open"]:
        score += 15
        reasons.append("bearish confirmation candle")

    atr_pct = row["atr14"] / row["close"] if row["close"] else np.inf
    if atr_pct <= cfg.max_atr_pct:
        score += 10
        reasons.append("volatility within configured limit")

    if direction != "flat":
        score += 10
        reasons.append("trend alignment")

    valid = direction != "flat" and score >= cfg.min_score
    stop_distance = max(float(row["atr14"]) * 1.1, 0.01) if valid else None
    entry = float(row["close"]) if valid else None
    if valid and direction == "long":
        stop = entry - stop_distance
        target = entry + stop_distance * cfg.target_rr
    elif valid and direction == "short":
        stop = entry + stop_distance
        target = entry - stop_distance * cfg.target_rr
    else:
        stop = target = None

    return {
        "mode": "intraday",
        "valid": valid,
        "direction": direction,
        "score": score,
        "entry": entry,
        "stop": stop,
        "target": target,
        "rr": cfg.target_rr if valid else None,
        "reasons": reasons,
        "config": asdict(cfg),
    }


def scalping_signal(row: pd.Series, cfg: ScalpingConfig = ScalpingConfig()) -> dict:
    score = 0
    reasons: list[str] = []
    direction: Direction = "flat"

    if pd.isna(row["range_high30"]) or pd.isna(row["range_low30"]) or row["range_size30"] <= 0:
        return {"mode": "scalping", "valid": False, "direction": "flat", "score": 0, "reasons": ["insufficient range data"]}

    pos = (row["close"] - row["range_low30"]) / row["range_size30"]
    if pos <= cfg.edge_fraction:
        direction = "long"
        score += 30
        reasons.append("price at lower range edge")
        if row["low"] < row["range_low30"] and row["close"] > row["range_low30"]:
            score += 25
            reasons.append("lower-edge liquidity sweep and reclaim")
    elif pos >= 1 - cfg.edge_fraction:
        direction = "short"
        score += 30
        reasons.append("price at upper range edge")
        if row["high"] > row["range_high30"] and row["close"] < row["range_high30"]:
            score += 25
            reasons.append("upper-edge liquidity sweep and rejection")

    range_atr = row["range_size30"] / row["atr14"] if row["atr14"] else np.inf
    if row["adx14"] <= cfg.max_adx:
        score += 20
        reasons.append("low ADX confirms sideways regime")
    if range_atr <= cfg.max_range_atr:
        score += 10
        reasons.append("range compression confirmed")
    if (direction == "long" and row["close"] > row["open"]) or (direction == "short" and row["close"] < row["open"]):
        score += 10
        reasons.append("reversal candle confirmation")

    valid = direction != "flat" and score >= cfg.min_score
    entry = float(row["close"]) if valid else None
    stop_distance = max(float(row["atr14"]) * 0.8, 0.01) if valid else None
    if valid and direction == "long":
        stop = entry - stop_distance
        target = entry + stop_distance * cfg.target_rr
    elif valid and direction == "short":
        stop = entry + stop_distance
        target = entry - stop_distance * cfg.target_rr
    else:
        stop = target = None

    return {
        "mode": "scalping",
        "valid": valid,
        "direction": direction,
        "score": score,
        "entry": entry,
        "stop": stop,
        "target": target,
        "rr": cfg.target_rr if valid else None,
        "reasons": reasons,
        "config": asdict(cfg),
    }


def signal_for_row(row: pd.Series) -> dict:
    mode = classify_regime(row)
    if mode == "scalping":
        return scalping_signal(row)
    if mode == "intraday":
        return intraday_signal(row)
    return {"mode": "none", "valid": False, "direction": "flat", "score": 0, "reasons": ["insufficient feature history"]}
