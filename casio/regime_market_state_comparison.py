from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .m15_all_families_2026 import prepare
from .regime_router_diagnostics import SECONDARY, DUKASCOPY

OUT = Path("reports/regime-router-market-state")


def _daily_eff(m5: pd.DataFrame) -> pd.DataFrame:
    d = m5.resample("1D").agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last")).dropna()
    rng = (d.high - d.low).replace(0, np.nan)
    d["body_range_eff"] = (d.close - d.open).abs() / rng
    d["signed_body_range"] = (d.close - d.open) / rng
    d["ret"] = d.close.pct_change()
    return d


def _state(data: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, year: int, feed: str) -> dict:
    z = data[(data.index >= start - pd.Timedelta(days=120)) & (data.index < end)].copy()
    test = data[(data.index >= start) & (data.index < end)].copy()
    m15, f = prepare(z)
    f = f[(f.index >= start) & (f.index < end)].copy()
    daily = _daily_eff(test)

    first_open = float(test.open.iloc[0])
    last_close = float(test.close.iloc[-1])
    price_return = (last_close / first_open - 1.0) * 100.0

    h4 = f[["h4_bias", "h4_adx"]].dropna().copy()
    aligned = (f.h1_bias != 0) & (f.h1_bias == f.h4_bias)
    strong = aligned & f.h4_adx.ge(18)
    weak = aligned & f.h4_adx.lt(18)
    neutral_mix = (f.h1_bias == 0) | (f.h4_bias == 0)
    opposed = (f.h1_bias != 0) & (f.h4_bias != 0) & (f.h1_bias != f.h4_bias)

    # Sample one row per H4 context update to avoid counting the 16 repeated M15 rows equally.
    h4_context = h4.loc[(h4.h4_bias.ne(h4.h4_bias.shift())) | (h4.h4_adx.ne(h4.h4_adx.shift()))].copy()
    bias_series = h4_context.h4_bias.astype(int)
    nonzero = bias_series[bias_series != 0]
    flips = int((nonzero.ne(nonzero.shift()) & nonzero.shift().notna()).sum()) if len(nonzero) else 0
    months = max((end - start).days / 30.0, 1.0)

    return {
        "year": year,
        "feed": feed,
        "start_price": first_open,
        "end_price": last_close,
        "price_return_pct": price_return,
        "median_daily_body_range_eff": float(daily.body_range_eff.median()),
        "p75_daily_body_range_eff": float(daily.body_range_eff.quantile(.75)),
        "positive_daily_pct": float((daily.close > daily.open).mean() * 100.0),
        "daily_return_vol_pct": float(daily.ret.std() * 100.0),
        "median_m15_range_atr": float(f.range_atr.median()),
        "p90_m15_range_atr": float(f.range_atr.quantile(.90)),
        "median_m15_adx": float(f.adx.median()),
        "median_h4_adx": float(f.h4_adx.median()),
        "h4_adx_lt18_pct": float((f.h4_adx < 18).mean() * 100.0),
        "h4_adx_18_22_pct": float(((f.h4_adx >= 18) & (f.h4_adx < 22)).mean() * 100.0),
        "h4_adx_22_30_pct": float(((f.h4_adx >= 22) & (f.h4_adx < 30)).mean() * 100.0),
        "h4_adx_30plus_pct": float((f.h4_adx >= 30).mean() * 100.0),
        "h1_h4_strong_aligned_pct": float(strong.mean() * 100.0),
        "h1_h4_aligned_weak_pct": float(weak.mean() * 100.0),
        "h1_h4_neutral_mix_pct": float(neutral_mix.mean() * 100.0),
        "h1_h4_opposed_pct": float(opposed.mean() * 100.0),
        "h4_bull_bias_pct": float((f.h4_bias == 1).mean() * 100.0),
        "h4_bear_bias_pct": float((f.h4_bias == -1).mean() * 100.0),
        "h4_neutral_bias_pct": float((f.h4_bias == 0).mean() * 100.0),
        "h4_bias_flips": flips,
        "h4_bias_flips_per_30d": float(flips / months),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sec = load_m5_csv(SECONDARY)
    duk = load_m5_csv(DUKASCOPY)
    rows = [
        _state(sec, pd.Timestamp("2024-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC"), 2024, "secondary"),
        _state(sec, pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-01-01", tz="UTC"), 2025, "secondary"),
        _state(duk, pd.Timestamp("2026-01-01", tz="UTC"), min(pd.Timestamp("2027-01-01", tz="UTC"), duk.index.max() + pd.Timedelta(minutes=5)), 2026, "dukascopy"),
    ]
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "market_state.csv", index=False)
    lines = [
        "# CASIO Regime Router — Market-State Comparison",
        "",
        "This describes the underlying price/context environment. It is separate from trade outcomes.",
        "",
        df.to_markdown(index=False),
        "",
        "Interpretation should focus on differences that could be detected causally from completed price bars, not on the calendar year label.",
        "",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
