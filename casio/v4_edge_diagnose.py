from __future__ import annotations

import argparse
from pathlib import Path

from casio.v4_confluence_research import Candidate, load_features, metrics, replay


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, default=Path("data/xauusd_m5_dukascopy_research.csv"))
    args = p.parse_args()
    df = load_features(args.data)
    split_i = int(len(df) * 0.70)
    split_time = df.index[split_i]
    val_start = df.index[split_i]
    val_end = df.index[-1]

    candidates = {
        "R075_BE045": Candidate(55, 0.75, 0.45, 6),
        "R070_BE045": Candidate(55, 0.70, 0.45, 6),
        "R065_BE040": Candidate(55, 0.65, 0.40, 6),
        "R060_BE035": Candidate(55, 0.60, 0.35, 6),
        "R070_NOBE": Candidate(55, 0.70, 10.0, 6),
    }

    for name, candidate in candidates.items():
        trades = replay(df, candidate)
        val = trades[trades["entry_time"] >= split_time].copy()
        m = metrics(val, val_start, val_end)
        print(
            f"{name}: {m.trades_per_week:.2f}/wk WR={m.win_rate:.2f}% "
            f"E={m.expectancy_r:.3f}R PF={m.profit_factor:.2f} DD={m.max_drawdown_r:.2f}R"
        )
        for playbook, group in val.groupby("playbook"):
            pm = metrics(group, val_start, val_end)
            print(
                f"  {playbook}: n={pm.trades} {pm.trades_per_week:.2f}/wk "
                f"WR={pm.win_rate:.2f}% E={pm.expectancy_r:.3f}R PF={pm.profit_factor:.2f}"
            )


if __name__ == "__main__":
    main()
