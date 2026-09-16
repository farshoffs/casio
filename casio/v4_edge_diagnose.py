from __future__ import annotations

import argparse
from pathlib import Path

from casio.v4_confluence_research import Candidate, load_features, metrics, replay


def core(df, *, sd_score=0, sd_m15=False):
    x = df.copy()
    x["liq_fvg_long"] = False
    x["liq_fvg_short"] = False
    x["break_retest_long"] = False
    x["break_retest_short"] = False
    if sd_score:
        x["sd_long"] = x["sd_long"] & (x["long_score"] >= sd_score)
        x["sd_short"] = x["sd_short"] & (x["short_score"] >= sd_score)
    if sd_m15:
        x["sd_long"] = x["sd_long"] & (x["m15_bias"] == 1)
        x["sd_short"] = x["sd_short"] & (x["m15_bias"] == -1)
    x["long_setup"] = x[["bbma_reentry_long", "sd_long"]].any(axis=1)
    x["short_setup"] = x[["bbma_reentry_short", "sd_short"]].any(axis=1)
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
        "CORE": core(df),
        "CORE_SD_SCORE60": core(df, sd_score=60),
        "CORE_SD_SCORE65": core(df, sd_score=65),
        "CORE_SD_M15": core(df, sd_m15=True),
        "CORE_SD_M15_SCORE60": core(df, sd_score=60, sd_m15=True),
        "CORE_SD_M15_SCORE65": core(df, sd_score=65, sd_m15=True),
    }
    for name, data in variants.items():
        report(name, data, c, split_time, val_start, val_end)


if __name__ == "__main__":
    main()
