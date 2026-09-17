from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .regime_router_diagnostics import SECONDARY, DUKASCOPY, _run_window, _group

OUT = Path("reports/regime-router-volatility-diagnostics")


def _daily_context(data: pd.DataFrame) -> pd.DataFrame:
    d = data.resample("1D").agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last")).dropna()
    ret = d.close.pct_change()
    tr = pd.concat([
        d.high - d.low,
        (d.high - d.close.shift(1)).abs(),
        (d.low - d.close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    ctx = pd.DataFrame(index=d.index)
    ctx["rv20"] = ret.rolling(20, min_periods=15).std()
    ctx["rv60"] = ret.rolling(60, min_periods=40).std()
    ctx["rv_ratio"] = ctx.rv20 / ctx.rv60.replace(0, np.nan)
    ctx["atr14_pct"] = tr.rolling(14, min_periods=10).mean() / d.close.replace(0, np.nan)
    absret = ret.abs().rolling(20, min_periods=15).sum()
    ctx["trend_eff20"] = ret.rolling(20, min_periods=15).sum().abs() / absret.replace(0, np.nan)
    # Shift so a trade on day D sees only completed data through D-1.
    return ctx.shift(1)


def _band_ratio(x: float) -> str:
    if not np.isfinite(x): return "NA"
    if x < .75: return "<0.75"
    if x < 1.0: return "0.75-1.0"
    if x < 1.25: return "1.0-1.25"
    return "1.25+"


def _band_atr(x: float) -> str:
    if not np.isfinite(x): return "NA"
    if x < .008: return "<0.8%"
    if x < .012: return "0.8-1.2%"
    if x < .018: return "1.2-1.8%"
    return "1.8%+"


def _band_eff(x: float) -> str:
    if not np.isfinite(x): return "NA"
    if x < .20: return "<0.20"
    if x < .40: return "0.20-0.40"
    if x < .60: return "0.40-0.60"
    return "0.60+"


def _annotate_with_daily(trades: pd.DataFrame, data: pd.DataFrame) -> pd.DataFrame:
    if trades.empty: return trades.copy()
    ctx = _daily_context(data)
    x = trades.copy()
    x["day"] = pd.to_datetime(x.entry_time, utc=True).dt.floor("D").dt.tz_localize(None)
    ctx2 = ctx.copy()
    ctx2.index = ctx2.index.tz_localize(None) if ctx2.index.tz is not None else ctx2.index
    x = x.join(ctx2, on="day")
    x["rv_ratio_band"] = x.rv_ratio.map(_band_ratio)
    x["daily_atr_pct_band"] = x.atr14_pct.map(_band_atr)
    x["trend_eff20_band"] = x.trend_eff20.map(_band_eff)
    return x


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sec = load_m5_csv(SECONDARY)
    duk = load_m5_csv(DUKASCOPY)
    windows = [
        (sec, pd.Timestamp("2024-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC"), 2024, "secondary"),
        (sec, pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-01-01", tz="UTC"), 2025, "secondary"),
        (duk, pd.Timestamp("2026-01-01", tz="UTC"), min(pd.Timestamp("2027-01-01", tz="UTC"), duk.index.max() + pd.Timedelta(minutes=5)), 2026, "dukascopy"),
    ]
    parts = []
    for data, start, end, year, feed in windows:
        routed, ann, _ = _run_window(data, start, end, year, feed)
        if routed.empty: continue
        z = _annotate_with_daily(ann, data[(data.index >= start - pd.Timedelta(days=100)) & (data.index < end)])
        parts.append(z)
    a = pd.concat(parts, ignore_index=True)
    a.to_csv(OUT / "annotated_trades.csv", index=False)

    by_ratio = _group(a, ["year", "rv_ratio_band"])
    by_atr = _group(a, ["year", "daily_atr_pct_band"])
    by_eff = _group(a, ["year", "trend_eff20_band"])
    by_combo = _group(a, ["year", "rv_ratio_band", "trend_eff20_band"])
    by_tech_ratio = _group(a, ["year", "technique", "rv_ratio_band"])
    for name, df in {
        "by_rv_ratio": by_ratio,
        "by_daily_atr_pct": by_atr,
        "by_trend_eff20": by_eff,
        "by_vol_trend_combo": by_combo,
        "by_technique_rv_ratio": by_tech_ratio,
    }.items():
        df.to_csv(OUT / f"{name}.csv", index=False)

    lines = [
        "# CASIO Regime Router — Rolling Volatility Diagnostics",
        "",
        "All daily state variables are shifted one day, so each trade uses only information available before that trading day.",
        "",
        "## 20d / 60d realized-volatility ratio",
        "",
        by_ratio.to_markdown(index=False),
        "",
        "## Daily ATR(14) as percent of price",
        "",
        by_atr.to_markdown(index=False),
        "",
        "## 20-day directional efficiency",
        "",
        by_eff.to_markdown(index=False),
        "",
        "## Volatility ratio × directional efficiency",
        "",
        by_combo.to_markdown(index=False),
        "",
        "## Technique × volatility ratio",
        "",
        by_tech_ratio.to_markdown(index=False),
        "",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
