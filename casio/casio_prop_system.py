from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import argparse
import json
import math
from typing import Iterable

import numpy as np
import pandas as pd


START_BALANCE = 2500.0


@dataclass(frozen=True)
class SystemConfig:
    monthly_target_pct: float = 5.0
    mpd_target: int = 5
    mpd_day_pct_initial: float = 0.5

    # Finotive Lite hard limits are 3% daily / 6% static max drawdown.
    # The system deliberately uses earlier internal brakes.
    daily_soft_stop_pct: float = 1.75
    static_soft_stop_pct: float = 4.50

    base_risk_pct: float = 0.50
    reduced_risk_pct: float = 0.35
    survival_risk_pct: float = 0.25
    month_reduce_at_pct: float = -2.0
    month_survival_at_pct: float = -3.5

    max_losses_per_trading_day: int = 2
    max_active_positions: int = 1
    max_planned_symbol_risk_pct: float = 0.75

    health_lookback_days: int = 120
    health_min_trades: int = 5
    health_min_expectancy_r: float = 0.05
    health_min_pf: float = 1.05

    cost_r_fallback: float = 0.0


@dataclass
class DayState:
    start_equity: float
    pnl: float = 0.0
    losses: int = 0


@dataclass
class MonthState:
    start_equity: float
    profitable_days: int = 0
    daily: dict[str, DayState] = field(default_factory=dict)


def _ts(v) -> pd.Timestamp:
    x = pd.Timestamp(v)
    return x.tz_localize("UTC") if x.tzinfo is None else x.tz_convert("UTC")


def _trading_day(ts: pd.Timestamp) -> str:
    # Finotive daily drawdown resets at 17:00 New York.
    ny = _ts(ts).tz_convert("America/New_York")
    return (ny - pd.Timedelta(hours=17)).strftime("%Y-%m-%d")


def _month_key(ts: pd.Timestamp) -> str:
    return _ts(ts).strftime("%Y-%m")


def _profit_factor(r: pd.Series) -> float:
    w = r[r > 0].sum()
    l = -r[r < 0].sum()
    if l <= 0:
        return 999.0 if w > 0 else 0.0
    return float(w / l)


def _health(history: pd.DataFrame, engine: str, now: pd.Timestamp, cfg: SystemConfig) -> dict:
    if history.empty:
        return {"n": 0, "expectancy_r": None, "pf": None, "score": -999.0, "eligible": False}
    start = now - pd.Timedelta(days=cfg.health_lookback_days)
    x = history[
        (history.engine == engine)
        & (history.exit_time <= now)
        & (history.exit_time >= start)
    ].copy()
    r = pd.to_numeric(x.net_r, errors="coerce").dropna()
    if r.empty:
        return {"n": 0, "expectancy_r": None, "pf": None, "score": -999.0, "eligible": False}
    exp = float(r.mean())
    pf = _profit_factor(r)
    n = int(len(r))
    # Frequency confidence stops a 1-2 trade hot streak from dominating routing.
    confidence = min(1.0, math.sqrt(n / max(cfg.health_min_trades * 3, 1)))
    score = confidence * (exp + 0.12 * math.log(max(pf, 1e-6)))
    eligible = (
        n >= cfg.health_min_trades
        and exp >= cfg.health_min_expectancy_r
        and pf >= cfg.health_min_pf
    )
    return {"n": n, "expectancy_r": exp, "pf": pf, "score": score, "eligible": eligible}


def _load_trade_file(path: str | Path) -> pd.DataFrame:
    x = pd.read_csv(path)
    req = {"engine", "symbol", "entry_time", "exit_time", "net_r"}
    missing = req - set(x.columns)
    if missing:
        raise ValueError(f"{path}: missing {sorted(missing)}")
    x["entry_time"] = pd.to_datetime(x.entry_time, utc=True)
    x["exit_time"] = pd.to_datetime(x.exit_time, utc=True)
    x["net_r"] = pd.to_numeric(x.net_r, errors="coerce")
    x = x.dropna(subset=["entry_time", "exit_time", "net_r", "engine", "symbol"])
    return x.sort_values(["entry_time", "engine", "symbol"]).reset_index(drop=True)


def _risk_pct(month_return_pct: float, cfg: SystemConfig) -> float:
    if month_return_pct <= cfg.month_survival_at_pct:
        return cfg.survival_risk_pct
    if month_return_pct <= cfg.month_reduce_at_pct:
        return cfg.reduced_risk_pct
    return cfg.base_risk_pct


def simulate(trades: pd.DataFrame, cfg: SystemConfig | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = cfg or SystemConfig()
    if trades.empty:
        return pd.DataFrame(), pd.DataFrame()

    x = trades.sort_values(["entry_time", "engine", "symbol"]).copy()
    equity = START_BALANCE
    initial = START_BALANCE
    peak = equity
    active_until = pd.Timestamp("1900-01-01", tz="UTC")
    history = pd.DataFrame(columns=x.columns)

    months: dict[str, MonthState] = {}
    routed = []

    for ts, group in x.groupby("entry_time", sort=True):
        now = _ts(ts)
        mk = _month_key(now)
        if mk not in months:
            months[mk] = MonthState(start_equity=equity)
        m = months[mk]

        month_ret = (equity / m.start_equity - 1.0) * 100.0
        if month_ret >= cfg.monthly_target_pct and m.profitable_days >= cfg.mpd_target:
            continue

        td = _trading_day(now)
        if td not in m.daily:
            m.daily[td] = DayState(start_equity=equity)
        dstate = m.daily[td]

        day_ret = (equity / dstate.start_equity - 1.0) * 100.0
        static_dd = (initial - equity) / initial * 100.0
        if day_ret <= -cfg.daily_soft_stop_pct or static_dd >= cfg.static_soft_stop_pct:
            continue
        if dstate.losses >= cfg.max_losses_per_trading_day:
            continue
        if now < active_until:
            continue

        ranked = []
        for row in group.itertuples(index=False):
            h = _health(history, str(row.engine), now, cfg)
            # Allow the first trade history to bootstrap only when the input row
            # is explicitly marked validated_pre2026=1.
            bootstrap = bool(getattr(row, "validated_pre2026", False))
            eligible = h["eligible"] or bootstrap
            if not eligible:
                continue
            bootstrap_score = float(getattr(row, "prior_expectancy_r", 0.0) or 0.0)
            score = h["score"] if h["n"] else bootstrap_score
            ranked.append((score, row, h))

        if not ranked:
            # All candidates are appended to history only after their hypothetical
            # exit, via the chronological flush below. No look-ahead selection.
            pass
        else:
            ranked.sort(key=lambda z: z[0], reverse=True)
            score, row, h = ranked[0]

            risk_pct = _risk_pct(month_ret, cfg)
            planned_symbol_risk = risk_pct
            if planned_symbol_risk > cfg.max_planned_symbol_risk_pct:
                continue

            r = float(row.net_r)
            pnl = equity * (risk_pct / 100.0) * r
            before = equity
            equity += pnl
            peak = max(peak, equity)
            dstate.pnl += pnl
            if r < 0:
                dstate.losses += 1

            active_until = _ts(row.exit_time)
            routed.append({
                "engine": str(row.engine),
                "symbol": str(row.symbol),
                "entry_time": now,
                "exit_time": active_until,
                "health_score": score,
                "health_n": h["n"],
                "health_expectancy_r": h["expectancy_r"],
                "health_pf": h["pf"],
                "risk_pct": risk_pct,
                "net_r": r,
                "equity_before": before,
                "pnl": pnl,
                "equity_after": equity,
                "month": mk,
                "trading_day": td,
            })

        # Flush all candidates whose outcomes were known by now into causal history.
        known = x[x.exit_time <= now]
        if not known.empty:
            history = known.copy()

        # Recompute completed profitable days at every new entry point.
        m.profitable_days = sum(
            1 for ds in m.daily.values()
            if ds.pnl / initial * 100.0 >= cfg.mpd_day_pct_initial
        )

    routed_df = pd.DataFrame(routed)
    monthly_rows = []
    for mk, m in sorted(months.items()):
        if routed_df.empty:
            xm = routed_df
        else:
            xm = routed_df[routed_df.month == mk]
        if xm.empty:
            ret = 0.0
            maxdd = 0.0
            worstday = 0.0
            trades_n = 0
        else:
            end_equity = float(xm.equity_after.iloc[-1])
            ret = (end_equity / m.start_equity - 1.0) * 100.0
            ec = xm.equity_after.astype(float)
            dd = (ec.cummax() - ec) / ec.cummax() * 100.0
            maxdd = float(dd.max()) if len(dd) else 0.0
            daily = xm.groupby("trading_day").pnl.sum()
            day_starts = xm.groupby("trading_day").equity_before.first()
            worstday = float((daily / day_starts * 100.0).min()) if len(daily) else 0.0
            trades_n = len(xm)

        mpd = sum(
            1 for ds in m.daily.values()
            if ds.pnl / initial * 100.0 >= cfg.mpd_day_pct_initial
        )
        monthly_rows.append({
            "month": mk,
            "return_pct": ret,
            "trades": trades_n,
            "mpd": mpd,
            "max_dd_pct": maxdd,
            "worst_day_pct": worstday,
            "target5_and_5mpd": bool(ret >= cfg.monthly_target_pct and mpd >= cfg.mpd_target),
        })

    return routed_df, pd.DataFrame(monthly_rows)


def main() -> None:
    p = argparse.ArgumentParser(description="CASIO Prop System causal portfolio router")
    p.add_argument("--trades", nargs="+", required=True, help="Candidate trade-event CSV files")
    p.add_argument("--output", default="reports/casio-prop-system")
    a = p.parse_args()

    parts = [_load_trade_file(pth) for pth in a.trades]
    all_trades = pd.concat(parts, ignore_index=True).sort_values(["entry_time","engine","symbol"])
    routed, monthly = simulate(all_trades)

    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    routed.to_csv(out / "routed_trades.csv", index=False)
    monthly.to_csv(out / "monthly.csv", index=False)

    summary = {
        "months": int(len(monthly)),
        "months_ge_5_and_5mpd": int(monthly.target5_and_5mpd.sum()) if len(monthly) else 0,
        "worst_month_pct": float(monthly.return_pct.min()) if len(monthly) else None,
        "avg_month_pct": float(monthly.return_pct.mean()) if len(monthly) else None,
        "max_month_dd_pct": float(monthly.max_dd_pct.max()) if len(monthly) else None,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(monthly.to_string(index=False))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
