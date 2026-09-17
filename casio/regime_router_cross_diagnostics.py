from __future__ import annotations

from pathlib import Path
import pandas as pd

from .v3_core import load_m5_csv
from .regime_router_diagnostics import SECONDARY, DUKASCOPY, _run_window, _group

OUT = Path("reports/regime-router-2024-cross-diagnostics")


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
        _, ann, _ = _run_window(data, start, end, year, feed)
        parts.append(ann)
    a = pd.concat(parts, ignore_index=True)

    tables = {
        "technique_session": _group(a, ["year", "technique", "session"]),
        "technique_direction": _group(a, ["year", "technique", "direction_text"]),
        "technique_mode": _group(a, ["year", "technique", "router_mode"]),
        "technique_htf_state": _group(a, ["year", "technique", "htf_state"]),
        "technique_h4_adx": _group(a, ["year", "technique", "h4_adx_band"]),
        "technique_range": _group(a, ["year", "technique", "range_atr_band"]),
        "session_direction": _group(a, ["year", "session", "direction_text"]),
        "session_mode": _group(a, ["year", "session", "router_mode"]),
        "session_h4_adx": _group(a, ["year", "session", "h4_adx_band"]),
        "session_range": _group(a, ["year", "session", "range_atr_band"]),
    }
    for name, df in tables.items():
        df.to_csv(OUT / f"{name}.csv", index=False)

    # Concentrated 2024 damage combinations with enough observations to matter.
    combo = _group(a, ["year", "technique", "session", "direction_text", "router_mode", "h4_adx_band"])
    combo.to_csv(OUT / "full_combo.csv", index=False)
    damage = combo[(combo.year == 2024) & (combo.trades >= 5)].sort_values("net_r_sum").head(25)

    # Compare the exact same technique/session combinations across years.
    ts = tables["technique_session"].pivot_table(
        index=["technique", "session"], columns="year", values=["trades", "net_r_sum", "avg_net_r"], aggfunc="first"
    ).reset_index()
    ts.columns = ["_".join(str(x) for x in c if str(x) != "") if isinstance(c, tuple) else str(c) for c in ts.columns]
    ts.to_csv(OUT / "technique_session_year_compare.csv", index=False)

    lines = [
        "# CASIO Regime Router — 2024 Cross-State Diagnostics",
        "",
        "The objective is to locate concentrated failure combinations rather than apply a broad 2024-only filter.",
        "",
        "## Largest 2024 damage combinations (minimum 5 trades)",
        "",
        damage.to_markdown(index=False),
        "",
        "## Technique × session",
        "",
        tables["technique_session"].to_markdown(index=False),
        "",
        "## Technique × direction",
        "",
        tables["technique_direction"].to_markdown(index=False),
        "",
        "## Session × direction",
        "",
        tables["session_direction"].to_markdown(index=False),
        "",
        "## Technique × router mode",
        "",
        tables["technique_mode"].to_markdown(index=False),
        "",
        "## Technique × H4 ADX band",
        "",
        tables["technique_h4_adx"].to_markdown(index=False),
        "",
        "## Session × H4 ADX band",
        "",
        tables["session_h4_adx"].to_markdown(index=False),
        "",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
