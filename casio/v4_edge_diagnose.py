from __future__ import annotations

import argparse
from pathlib import Path

from casio.v4_confluence_research import Candidate, load_features, metrics, replay


def gated(df, *, liq=True, breakout=True, bbma=True, sd=True, strict_sd_h4=False):
    x = df.copy()
    if not liq:
        x["liq_fvg_long"] = False
        x["liq_fvg_short"] = False
    if not breakout:
        x["break_retest_long"] = False
        x["break_retest_short"] = False
    if not bbma:
        x["bbma_reentry_long"] = False
        x["bbma_reentry_short"] = False
    if not sd:
        x["sd_long"] = False
        x["sd_short"] = False
    if strict_sd_h4:
        x["sd_long"] = x["sd_long"] & (x["h4_bias"] >= 0)
        x["sd_short"] = x["sd_short"] & (x["h4_bias"] <= 0)
    x["long_setup"] = x[["liq_fvg_long", "break_retest_long", "bbma_reentry_long", "sd_long"]].any(axis=1)
    x["short_setup"] = x[["liq_fvg_short", "break_retest_short", "bbma_reentry_short", "sd_short"]].any(axis=1)
    return x


def report(name, data, candidate, split_time, val_start, val_end):
    trades = replay(data, candidate)
    val = trades[trades["entry_time"] >= split_time].copy()
    m = metrics(val, val_start, val_end)
    print(
        f"{name}: {m.trades_per_week:.2f}/wk WR={m.win_rate:.2f}% "
        f"E={m.expectancy_r:.3f}R PF={m.profit_factor:.2f} DD={m.max_drawdown_r:.2f}R n={m.trades}"
    )
    for playbook, group in val.groupby("playbook"):
        pm = metrics(group, val_start, val_end)
        print(
            f"  {playbook}: n={pm.trades} {pm.trades_per_week:.2f}/wk "
            f"WR={pm.win_rate:.2f}% E={pm.expectancy_r:.3f}R PF={pm.profit_factor:.2f}"
        )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, default=Path("data/xauusd_m5_dukascopy_research.csv"))
    args = p.parse_args()
    df = load_features(args.data)
    split_i = int(len(df) * 0.70)
    split_time = df.index[split_i]
    val_start = df.index[split_i]
    val_end = df.index[-1]
    c = Candidate(55, 0.60, 0.35, 6)

    variants = {
        "ALL_R060": df,
        "NO_BREAKOUT": gated(df, breakout=False),
        "NO_LIQ_FVG": gated(df, liq=False),
        "BBMA_SD_ONLY": gated(df, liq=False, breakout=False),
        "BBMA_SD_H4": gated(df, liq=False, breakout=False, strict_sd_h4=True),
        "BREAK_BBMA_SD_H4": gated(df, liq=False, breakout=True, strict_sd_h4=True),
    }
    for name, data in variants.items():
        report(name, data, c, split_time, val_start, val_end)


if __name__ == "__main__":
    main()
