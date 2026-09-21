from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json
import numpy as np
import pandas as pd

from .structural_frequency_research import setup_frame_mode
from .structural_portfolio_latest import StructuralPortfolioConfig, prepare_features, replay


def load_flexible_m5(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    ts = "timestamp" if "timestamp" in df.columns else "time_utc" if "time_utc" in df.columns else None
    if ts is None:
        raise ValueError("CSV requires timestamp or time_utc")
    df[ts] = pd.to_datetime(df[ts], utc=True, errors="raise")
    df = df.sort_values(ts).drop_duplicates(ts, keep="last")
    for c in ("open", "high", "low", "close"):
        df[c] = pd.to_numeric(df[c], errors="raise")
    if "volume" not in df.columns:
        df["volume"] = pd.to_numeric(df.get("tick_volume", 0.0), errors="coerce").fillna(0.0)
    return df.set_index(ts)[["open", "high", "low", "close", "volume"]]


def _streaks(r: pd.Series) -> tuple[int, int]:
    max_w = max_l = cur_w = cur_l = 0
    for x in r.astype(float):
        if x > 0:
            cur_w += 1
            cur_l = 0
            max_w = max(max_w, cur_w)
        elif x < 0:
            cur_l += 1
            cur_w = 0
            max_l = max(max_l, cur_l)
        else:
            cur_w = cur_l = 0
    return max_w, max_l


def _equity(t: pd.DataFrame, start: float = 100.0, risk: float = 0.05) -> tuple[float, float]:
    eq = peak = start
    max_dd = 0.0
    for r in t.net_r.astype(float):
        eq *= max(0.0, 1.0 + risk * r)
        peak = max(peak, eq)
        max_dd = max(max_dd, (peak - eq) / peak if peak else 0.0)
    return eq, 100.0 * max_dd


def _slice(t: pd.DataFrame, start_rm: float = 100.0) -> dict:
    if t.empty:
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, target_hits=0, sl=0,
                    time_exit=0, net_r=0.0, expectancy_r=0.0, pf=None,
                    max_win_streak=0, max_loss_streak=0, start_rm=start_rm,
                    end_rm=start_rm, return_pct=0.0, max_dd_pct=0.0)
    r = t.net_r.astype(float)
    wins, losses = r[r > 0], r[r < 0]
    max_w, max_l = _streaks(r)
    end_rm, max_dd = _equity(t, start_rm)
    return dict(
        trades=int(len(t)),
        wins=int((r > 0).sum()),
        losses=int((r < 0).sum()),
        win_rate=float((r > 0).mean() * 100.0),
        target_hits=int(t.reason.eq("target").sum()),
        sl=int(t.reason.isin(["stop", "stop_same_bar"]).sum()),
        time_exit=int(t.reason.eq("time_exit").sum()),
        net_r=float(r.sum()),
        expectancy_r=float(r.mean()),
        pf=float(wins.sum() / -losses.sum()) if len(losses) else None,
        max_win_streak=max_w,
        max_loss_streak=max_l,
        start_rm=float(start_rm),
        end_rm=float(end_rm),
        return_pct=float((end_rm / start_rm - 1.0) * 100.0),
        max_dd_pct=float(max_dd),
    )


def run(data_path: str | Path, output_dir: str | Path) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    m5 = load_flexible_m5(data_path)
    features = prepare_features(m5, StructuralPortfolioConfig())
    result = {}

    for target_r in (3.0, 3.5):
        cfg = replace(
            StructuralPortfolioConfig(),
            target_r=target_r,
            min_external_runway_r=target_r,
        )
        setups = setup_frame_mode(features, cfg, "DISPLACEMENT_RETRACE")
        trades = replay(m5, setups, cfg)
        trades.to_csv(out / f"trades_{target_r:.1f}R.csv", index=False)

        tt = pd.to_datetime(trades.entry_time, utc=True)
        annual = []
        for year in range(2017, 2027):
            a = pd.Timestamp(f"{year}-01-01", tz="UTC")
            b = pd.Timestamp(f"{year + 1}-01-01", tz="UTC")
            row = _slice(trades[(tt >= a) & (tt < b)], 100.0)
            annual.append({"year": year, **row})
        annual_df = pd.DataFrame(annual)
        annual_df.to_csv(out / f"annual_{target_r:.1f}R.csv", index=False)

        monthly = []
        equity = 100.0
        for month in range(1, 10):
            a = pd.Timestamp(2026, month, 1, tz="UTC")
            b = pd.Timestamp(2026, month + 1, 1, tz="UTC")
            row = _slice(trades[(tt >= a) & (tt < b)], equity)
            monthly.append({"month": a.strftime("%b"), **row})
            equity = row["end_rm"]
        monthly_df = pd.DataFrame(monthly)
        monthly_df.to_csv(out / f"monthly_2026_{target_r:.1f}R.csv", index=False)

        result[f"{target_r:.1f}R"] = {
            "annual": annual,
            "monthly_2026": monthly,
            "positive_years": int((annual_df.net_r > 0).sum()),
            "worst_year_dd_pct": float(annual_df.max_dd_pct.max()),
        }

    (out / "summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--output", default="reports/next-system-search-v1/displacement-retrace-full")
    args = p.parse_args()
    print(json.dumps(run(args.data, args.output), indent=2))


if __name__ == "__main__":
    main()
