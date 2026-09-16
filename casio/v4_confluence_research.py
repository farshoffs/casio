from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Candidate:
    min_score: int
    target_r: float
    be_trigger_r: float
    cooldown_bars: int
    stop_buffer_atr: float = 0.15
    min_risk_atr: float = 0.35
    max_risk_atr: float = 1.80
    be_lock_r: float = 0.05
    max_trades_per_day: int = 3


@dataclass
class Metrics:
    trades: int
    trades_per_week: float
    win_rate: float
    expectancy_r: float
    profit_factor: float
    max_drawdown_r: float
    net_r: float


def _rma(s: pd.Series, length: int) -> pd.Series:
    return s.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()


def _atr(frame: pd.DataFrame, length: int = 14) -> pd.Series:
    prev_close = frame["close"].shift(1)
    tr = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - prev_close).abs(),
            (frame["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return _rma(tr, length)


def _adx(frame: pd.DataFrame, length: int = 14) -> pd.Series:
    up = frame["high"].diff()
    down = -frame["low"].diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=frame.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=frame.index)
    atr = _atr(frame, length)
    plus_di = 100.0 * _rma(plus_dm, length) / atr.replace(0, np.nan)
    minus_di = 100.0 * _rma(minus_dm, length) / atr.replace(0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return _rma(dx, length)


def _wma(s: pd.Series, length: int) -> pd.Series:
    weights = np.arange(1, length + 1, dtype=float)
    denom = weights.sum()
    return s.rolling(length).apply(lambda x: float(np.dot(x, weights) / denom), raw=True)


def _bars_since(event: pd.Series) -> pd.Series:
    ev = event.fillna(False).to_numpy(dtype=bool)
    idx = np.arange(len(ev))
    last = np.where(ev, idx, -1)
    last = np.maximum.accumulate(last)
    age = idx - last
    age[last < 0] = 10000
    return pd.Series(age, index=event.index, dtype=int)


def _ohlc(frame: pd.DataFrame, rule: str) -> pd.DataFrame:
    return (
        frame[["open", "high", "low", "close"]]
        .resample(rule, label="left", closed="left")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        .dropna()
    )


def _confirmed_context(frame: pd.DataFrame, rule: str, include_adx: bool = False) -> pd.DataFrame:
    htf = _ohlc(frame, rule)
    htf["ema20"] = htf["close"].ewm(span=20, adjust=False, min_periods=20).mean()
    htf["ema50"] = htf["close"].ewm(span=50, adjust=False, min_periods=50).mean()
    htf["atr"] = _atr(htf)
    if include_adx:
        htf["adx"] = _adx(htf)
    # Pine uses previous CLOSED HTF bar with lookahead_on. Shift before forward fill.
    return htf.shift(1).reindex(frame.index, method="ffill")


def load_features(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"timestamp", "open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.drop_duplicates("timestamp").sort_values("timestamp").set_index("timestamp")
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"]).copy()

    df["atr"] = _atr(df)
    df["ema20"] = df["close"].ewm(span=20, adjust=False, min_periods=20).mean()
    df["ema50"] = df["close"].ewm(span=50, adjust=False, min_periods=50).mean()
    basis = df["close"].rolling(20).mean()
    dev = df["close"].rolling(20).std(ddof=0) * 2.0
    df["bb_upper"] = basis + dev
    df["bb_lower"] = basis - dev
    df["ma5_high"] = _wma(df["high"], 5)
    df["ma5_low"] = _wma(df["low"], 5)

    h4 = _confirmed_context(df, "4h")
    h1 = _confirmed_context(df, "1h")
    m15 = _confirmed_context(df, "15min", include_adx=True)
    for prefix, ctx in [("h4", h4), ("h1", h1), ("m15", m15)]:
        for col in ctx.columns:
            df[f"{prefix}_{col}"] = ctx[col]

    def bias(prefix: str) -> pd.Series:
        bull = (df[f"{prefix}_ema20"] > df[f"{prefix}_ema50"]) & (
            df[f"{prefix}_close"] > df[f"{prefix}_ema20"]
        )
        bear = (df[f"{prefix}_ema20"] < df[f"{prefix}_ema50"]) & (
            df[f"{prefix}_close"] < df[f"{prefix}_ema20"]
        )
        return pd.Series(np.select([bull, bear], [1, -1], default=0), index=df.index)

    df["h4_bias"] = bias("h4")
    df["h1_bias"] = bias("h1")
    df["m15_bias"] = bias("m15")
    df["trend_vote"] = df["h4_bias"] + df["h1_bias"] + df["m15_bias"]

    hour = df.index.hour
    minute = df.index.minute
    df["in_asia"] = (hour >= 0) & (hour < 6)
    df["in_london"] = ((hour == 7) | (hour == 8) | (hour == 9) | (hour == 10)) | (
        (hour == 11) & (minute < 30)
    )
    df["in_newyork"] = ((hour == 12) & (minute >= 30)) | (hour.isin([13, 14, 15, 16]))
    df["in_primary"] = df["in_london"] | df["in_newyork"]

    day = df.index.floor("D")
    daily = df.groupby(day).agg(day_high=("high", "max"), day_low=("low", "min"))
    prev_daily = daily.shift(1)
    df["prev_day_high"] = day.map(prev_daily["day_high"])
    df["prev_day_low"] = day.map(prev_daily["day_low"])
    asia = df[df["in_asia"]].groupby(df[df["in_asia"]].index.floor("D")).agg(
        asia_high=("high", "max"), asia_low=("low", "min")
    )
    df["asia_high"] = day.map(asia["asia_high"])
    df["asia_low"] = day.map(asia["asia_low"])

    candle_range = df["high"] - df["low"]
    df["body_fraction"] = (df["close"] - df["open"]).abs() / candle_range.replace(0, np.nan)
    df["close_location"] = (df["close"] - df["low"]) / candle_range.replace(0, np.nan)
    df["range_atr"] = candle_range / df["atr"].replace(0, np.nan)
    prior_high5 = df["high"].shift(1).rolling(5).max()
    prior_low5 = df["low"].shift(1).rolling(5).min()
    df["disp_long"] = (
        (df["close"] > df["open"])
        & (df["body_fraction"] >= 0.52)
        & (df["close_location"] >= 0.65)
        & (df["range_atr"] >= 0.70)
        & (df["close"] > prior_high5)
    )
    df["disp_short"] = (
        (df["close"] < df["open"])
        & (df["body_fraction"] >= 0.52)
        & (df["close_location"] <= 0.35)
        & (df["range_atr"] >= 0.70)
        & (df["close"] < prior_low5)
    )
    df["bull_fvg"] = df["low"] > df["high"].shift(2)
    df["bear_fvg"] = df["high"] < df["low"].shift(2)

    internal_low = df["low"].shift(1).rolling(10).min()
    internal_high = df["high"].shift(1).rolling(10).max()
    internal_sell = (df["low"] < internal_low) & (df["close"] > internal_low)
    internal_buy = (df["high"] > internal_high) & (df["close"] < internal_high)
    external_sell = ((df["low"] < df["prev_day_low"]) & (df["close"] > df["prev_day_low"])) | (
        (~df["in_asia"]) & (df["low"] < df["asia_low"]) & (df["close"] > df["asia_low"])
    )
    external_buy = ((df["high"] > df["prev_day_high"]) & (df["close"] < df["prev_day_high"])) | (
        (~df["in_asia"]) & (df["high"] > df["asia_high"]) & (df["close"] < df["asia_high"])
    )
    df["sell_sweep_age"] = _bars_since(internal_sell | external_sell)
    df["buy_sweep_age"] = _bars_since(internal_buy | external_buy)

    # Confirmed 2-left/2-right pivots: candidate at t-2 becomes available only at t.
    low2 = df["low"].shift(2)
    pivot_low_confirmed = low2.where(
        (low2 < df["low"].shift(4))
        & (low2 <= df["low"].shift(3))
        & (low2 < df["low"].shift(1))
        & (low2 <= df["low"])
    )
    high2 = df["high"].shift(2)
    pivot_high_confirmed = high2.where(
        (high2 > df["high"].shift(4))
        & (high2 >= df["high"].shift(3))
        & (high2 > df["high"].shift(1))
        & (high2 >= df["high"])
    )
    df["demand"] = pivot_low_confirmed.ffill()
    df["supply"] = pivot_high_confirmed.ffill()
    near_demand = (df["low"] <= df["demand"] + df["atr"] * 0.35) & (df["close"] > df["demand"])
    near_supply = (df["high"] >= df["supply"] - df["atr"] * 0.35) & (df["close"] < df["supply"])
    df["demand_reject"] = near_demand & (df["close"] > df["open"]) & (df["close_location"] >= 0.58)
    df["supply_reject"] = near_supply & (df["close"] < df["open"]) & (df["close_location"] <= 0.42)

    break_high_level = df["high"].shift(1).rolling(20).max()
    break_low_level = df["low"].shift(1).rolling(20).min()
    break_long = (df["close"] > break_high_level) & (df["close"].shift(1) <= break_high_level)
    break_short = (df["close"] < break_low_level) & (df["close"].shift(1) >= break_low_level)
    last_break_long = break_high_level.where(break_long).ffill()
    last_break_short = break_low_level.where(break_short).ffill()
    break_long_age = _bars_since(break_long)
    break_short_age = _bars_since(break_short)
    df["retest_long"] = (
        break_long_age.between(1, 8)
        & (df["low"] <= last_break_long + df["atr"] * 0.20)
        & (df["close"] > last_break_long)
        & (df["close"] > df["open"])
    )
    df["retest_short"] = (
        break_short_age.between(1, 8)
        & (df["high"] >= last_break_short - df["atr"] * 0.20)
        & (df["close"] < last_break_short)
        & (df["close"] < df["open"])
    )

    bb_extreme_long = df["low"] < df["bb_lower"]
    bb_extreme_short = df["high"] > df["bb_upper"]
    df["bb_long_age"] = _bars_since(bb_extreme_long)
    df["bb_short_age"] = _bars_since(bb_extreme_short)
    df["bbma_long"] = (
        (df["bb_long_age"] <= 4)
        & (df["close"] > df["ma5_high"])
        & (df["close"] > df["bb_lower"])
        & (df["close"] > df["open"])
        & (df["ema20"] >= df["ema50"])
    )
    df["bbma_short"] = (
        (df["bb_short_age"] <= 4)
        & (df["close"] < df["ma5_low"])
        & (df["close"] < df["bb_upper"])
        & (df["close"] < df["open"])
        & (df["ema20"] <= df["ema50"])
    )

    df["liq_fvg_long"] = (df["sell_sweep_age"] <= 3) & df["disp_long"] & (
        df["bull_fvg"] | (df["close"] > df["ema20"])
    )
    df["liq_fvg_short"] = (df["buy_sweep_age"] <= 3) & df["disp_short"] & (
        df["bear_fvg"] | (df["close"] < df["ema20"])
    )
    df["break_retest_long"] = df["retest_long"] & ((df["m15_bias"] >= 0) | (df["h1_bias"] == 1))
    df["break_retest_short"] = df["retest_short"] & ((df["m15_bias"] <= 0) | (df["h1_bias"] == -1))
    df["bbma_reentry_long"] = df["bbma_long"] & (df["h1_bias"] >= 0) & (df["m15_bias"] >= 0)
    df["bbma_reentry_short"] = df["bbma_short"] & (df["h1_bias"] <= 0) & (df["m15_bias"] <= 0)
    df["sd_long"] = df["demand_reject"] & ((df["sell_sweep_age"] <= 5) | (df["bb_long_age"] <= 4)) & (df["h1_bias"] >= 0)
    df["sd_short"] = df["supply_reject"] & ((df["buy_sweep_age"] <= 5) | (df["bb_short_age"] <= 4)) & (df["h1_bias"] <= 0)
    df["long_setup"] = df[["liq_fvg_long", "break_retest_long", "bbma_reentry_long", "sd_long"]].any(axis=1)
    df["short_setup"] = df[["liq_fvg_short", "break_retest_short", "bbma_reentry_short", "sd_short"]].any(axis=1)

    primary_score = np.where(df["in_primary"], 10, np.where(df["in_asia"], 5, 0))
    df["long_score"] = (
        np.where(df["h4_bias"] == 1, 15, np.where(df["h4_bias"] == 0, 5, 0))
        + np.where(df["h1_bias"] == 1, 15, np.where(df["h1_bias"] == 0, 5, 0))
        + np.where(df["m15_bias"] == 1, 10, np.where(df["m15_bias"] == 0, 3, 0))
        + primary_score
        + np.where(df["sell_sweep_age"] <= 3, 10, 0)
        + np.where(df["disp_long"], 10, 0)
        + np.where(df["bull_fvg"], 10, 0)
        + np.where(df["bbma_long"], 10, 0)
        + np.where(df["retest_long"], 5, 0)
        + np.where(df["demand_reject"], 5, 0)
    ).clip(upper=100)
    df["short_score"] = (
        np.where(df["h4_bias"] == -1, 15, np.where(df["h4_bias"] == 0, 5, 0))
        + np.where(df["h1_bias"] == -1, 15, np.where(df["h1_bias"] == 0, 5, 0))
        + np.where(df["m15_bias"] == -1, 10, np.where(df["m15_bias"] == 0, 3, 0))
        + primary_score
        + np.where(df["buy_sweep_age"] <= 3, 10, 0)
        + np.where(df["disp_short"], 10, 0)
        + np.where(df["bear_fvg"], 10, 0)
        + np.where(df["bbma_short"], 10, 0)
        + np.where(df["retest_short"], 5, 0)
        + np.where(df["supply_reject"], 5, 0)
    ).clip(upper=100)
    df["recent_low"] = df["low"].rolling(7).min()
    df["recent_high"] = df["high"].rolling(7).max()
    return df.dropna(subset=["atr", "h4_ema50", "h1_ema50", "m15_ema50"])


def _playbook(row: pd.Series, side: int) -> str:
    if side == 1:
        if row.liq_fvg_long:
            return "LIQ_FVG"
        if row.break_retest_long:
            return "BREAK_RETEST"
        if row.bbma_reentry_long:
            return "BBMA_REENTRY"
        return "DEMAND_REJECT"
    if row.liq_fvg_short:
        return "LIQ_FVG"
    if row.break_retest_short:
        return "BREAK_RETEST"
    if row.bbma_reentry_short:
        return "BBMA_REENTRY"
    return "SUPPLY_REJECT"


def replay(df: pd.DataFrame, candidate: Candidate) -> pd.DataFrame:
    records: list[dict] = []
    position = 0
    entry = stop = target = risk = np.nan
    playbook = ""
    entry_time = None
    last_entry_i = -100000
    day_count = 0
    current_day = None

    for i, (ts, row) in enumerate(df.iterrows()):
        day = ts.date()
        if day != current_day:
            current_day = day
            day_count = 0

        if position != 0:
            if position == 1:
                hit_stop = row.low <= stop
                hit_target = row.high >= target
            else:
                hit_stop = row.high >= stop
                hit_target = row.low <= target

            if hit_stop or hit_target:
                # Conservative stop-first assumption if both are touched in one M5 candle.
                if hit_stop:
                    r = (stop - entry) / risk if position == 1 else (entry - stop) / risk
                    exit_price = stop
                    reason = "STOP"
                else:
                    r = candidate.target_r
                    exit_price = target
                    reason = "TARGET"
                records.append(
                    {
                        "entry_time": entry_time,
                        "exit_time": ts,
                        "direction": "long" if position == 1 else "short",
                        "playbook": playbook,
                        "entry": entry,
                        "exit": exit_price,
                        "r": float(r),
                        "reason": reason,
                    }
                )
                position = 0
                continue

            # Pine recalculates the protective stop after the bar closes, so the new BE applies next bar.
            if candidate.be_trigger_r > 0:
                if position == 1 and row.high >= entry + candidate.be_trigger_r * risk:
                    stop = max(stop, entry + candidate.be_lock_r * risk)
                elif position == -1 and row.low <= entry - candidate.be_trigger_r * risk:
                    stop = min(stop, entry - candidate.be_lock_r * risk)
            continue

        if day_count >= candidate.max_trades_per_day or i - last_entry_i < candidate.cooldown_bars:
            continue
        session_allowed = bool(row.in_primary or row.in_asia)
        if not session_allowed:
            continue
        required = candidate.min_score + (0 if row.in_primary else 5)
        long_stop = row.recent_low - row.atr * candidate.stop_buffer_atr
        short_stop = row.recent_high + row.atr * candidate.stop_buffer_atr
        long_risk = row.close - long_stop
        short_risk = short_stop - row.close
        long_risk_atr = long_risk / row.atr if row.atr > 0 else np.nan
        short_risk_atr = short_risk / row.atr if row.atr > 0 else np.nan
        long_ok = bool(
            row.long_setup
            and row.long_score >= required
            and candidate.min_risk_atr <= long_risk_atr <= candidate.max_risk_atr
            and long_stop < row.close
        )
        short_ok = bool(
            row.short_setup
            and row.short_score >= required
            and candidate.min_risk_atr <= short_risk_atr <= candidate.max_risk_atr
            and short_stop > row.close
        )
        if not long_ok and not short_ok:
            continue
        side = 1 if long_ok and (not short_ok or row.long_score >= row.short_score) else -1
        position = side
        entry = float(row.close)
        if side == 1:
            stop = float(long_stop)
            risk = float(long_risk)
            target = entry + candidate.target_r * risk
        else:
            stop = float(short_stop)
            risk = float(short_risk)
            target = entry - candidate.target_r * risk
        playbook = _playbook(row, side)
        entry_time = ts
        last_entry_i = i
        day_count += 1

    return pd.DataFrame.from_records(records)


def metrics(trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> Metrics:
    if trades.empty:
        return Metrics(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    r = trades["r"].astype(float)
    weeks = max((end - start).total_seconds() / 604800.0, 1.0)
    wins = r[r > 0]
    losses = r[r < 0]
    pf = float(wins.sum() / abs(losses.sum())) if len(losses) and losses.sum() != 0 else float("inf")
    equity = r.cumsum()
    dd = equity.cummax() - equity
    return Metrics(
        trades=len(r),
        trades_per_week=float(len(r) / weeks),
        win_rate=float((r > 0).mean() * 100.0),
        expectancy_r=float(r.mean()),
        profit_factor=pf,
        max_drawdown_r=float(dd.max() if len(dd) else 0.0),
        net_r=float(r.sum()),
    )


def _safe(v: float) -> float | None:
    return None if not np.isfinite(v) else float(v)


def rank_candidate(full: Metrics, validation: Metrics) -> float:
    # Targets are acceptance criteria, not hard-coded outputs. Reward robust proximity/clearance.
    if full.trades < 20 or validation.trades < 8:
        return -999.0
    if full.expectancy_r <= 0 or validation.expectancy_r <= 0:
        return -500.0
    wr = min(validation.win_rate / 70.0, 1.15)
    freq = min(validation.trades_per_week / 8.0, 1.15)
    exp = min(max(validation.expectancy_r, 0.0) / 0.35, 1.2)
    pf = min(max(validation.profit_factor, 0.0) / 1.5, 1.2)
    stability = min(full.win_rate, validation.win_rate) / max(full.win_rate, validation.win_rate, 1.0)
    dd_penalty = max(validation.max_drawdown_r - 8.0, 0.0) * 0.03
    return 2.2 * wr + 2.2 * freq + 1.2 * exp + 0.8 * pf + 0.6 * stability - dd_penalty


def research(data: Path, output: Path) -> dict:
    df = load_features(data)
    if len(df) < 5000:
        raise ValueError("not enough initialized M5 rows for v4 research")
    split_i = int(len(df) * 0.70)
    split_time = df.index[split_i]
    validation_df = df.iloc[split_i:]

    candidates = [
        Candidate(score, target, be, cooldown)
        for score in [55, 60, 65, 70]
        for target in [0.90, 1.00, 1.10, 1.20, 1.30]
        for be in [0.60, 0.80, 1.00]
        for cooldown in [6, 9, 12]
    ]

    rows: list[dict] = []
    for candidate in candidates:
        trades = replay(df, candidate)
        full = metrics(trades, df.index[0], df.index[-1])
        val_trades = trades[trades["entry_time"] >= split_time] if not trades.empty else trades
        val = metrics(val_trades, validation_df.index[0], validation_df.index[-1])
        rows.append(
            {
                **asdict(candidate),
                "rank": rank_candidate(full, val),
                **{f"full_{k}": _safe(v) if isinstance(v, float) else v for k, v in asdict(full).items()},
                **{f"val_{k}": _safe(v) if isinstance(v, float) else v for k, v in asdict(val).items()},
            }
        )

    ranked = pd.DataFrame(rows).sort_values(["rank", "val_expectancy_r", "val_win_rate"], ascending=False)
    output.mkdir(parents=True, exist_ok=True)
    ranked.to_csv(output / "candidate_grid.csv", index=False)
    top = ranked.head(15).copy()
    best = top.iloc[0].to_dict()

    result = {
        "status": "research_only",
        "data_start": df.index[0].isoformat(),
        "data_end": df.index[-1].isoformat(),
        "rows": int(len(df)),
        "validation_start": split_time.isoformat(),
        "target": {"trades_per_week": 8.0, "win_rate": 70.0},
        "best": best,
        "target_cleared_validation": bool(
            best.get("val_trades_per_week", 0) >= 8.0
            and best.get("val_win_rate", 0) >= 70.0
            and best.get("val_expectancy_r", 0) > 0
        ),
        "top15": top.to_dict(orient="records"),
    }
    (output / "latest.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    lines = [
        "# CASIO v4 Confluence Research",
        "",
        "Research only. The 8 trades/week and 70% win-rate numbers are acceptance targets, not forced outputs.",
        "",
        f"Data: {result['data_start']} → {result['data_end']} ({result['rows']:,} initialized M5 rows)",
        f"Validation starts: {result['validation_start']}",
        "",
        "## Best robust candidate",
        "",
        f"- primary minimum score: {int(best['min_score'])}",
        f"- target: {best['target_r']:.2f}R",
        f"- breakeven trigger: {best['be_trigger_r']:.2f}R",
        f"- cooldown: {int(best['cooldown_bars'])} M5 bars",
        f"- full: {best['full_trades_per_week']:.2f} trades/week, {best['full_win_rate']:.2f}% WR, {best['full_expectancy_r']:.3f}R expectancy, PF {best['full_profit_factor']:.2f}",
        f"- validation: {best['val_trades_per_week']:.2f} trades/week, {best['val_win_rate']:.2f}% WR, {best['val_expectancy_r']:.3f}R expectancy, PF {best['val_profit_factor']:.2f}",
        f"- validation target cleared: {'YES' if result['target_cleared_validation'] else 'NO'}",
        "",
        "See `candidate_grid.csv` for the complete bounded grid. Do not promote a candidate solely because it tops this sample; confirm in TradingView and on another feed/window.",
    ]
    (output / "LATEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="CASIO v4 confluence bounded research")
    parser.add_argument("--data", type=Path, default=Path("data/xauusd_m5_dukascopy_research.csv"))
    parser.add_argument("--output", type=Path, default=Path("reports/v4-confluence"))
    args = parser.parse_args()
    result = research(args.data, args.output)
    best = result["best"]
    print((args.output / "LATEST.md").read_text(encoding="utf-8"))
    print("BEST_JSON=" + json.dumps(best, separators=(",", ":"), default=str))


if __name__ == "__main__":
    main()
