from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from casio.v4_confluence_research import Candidate, load_features, metrics, replay


def main() -> None:
    parser = argparse.ArgumentParser(description="Fast CASIO v4 profile validation")
    parser.add_argument("--data", type=Path, default=Path("data/xauusd_m5_dukascopy_research.csv"))
    args = parser.parse_args()

    df = load_features(args.data)
    split_i = int(len(df) * 0.70)
    split_time = df.index[split_i]
    validation = df.iloc[split_i:]

    profiles = {
        "QUALITY_70": Candidate(min_score=65, target_r=1.20, be_trigger_r=0.80, cooldown_bars=9),
        "BALANCED": Candidate(min_score=60, target_r=1.10, be_trigger_r=0.80, cooldown_bars=9),
        "FREQUENCY": Candidate(min_score=55, target_r=1.00, be_trigger_r=0.60, cooldown_bars=6),
    }

    output = {}
    for name, candidate in profiles.items():
        trades = replay(df, candidate)
        val_trades = trades[trades["entry_time"] >= split_time] if not trades.empty else trades
        full = metrics(trades, df.index[0], df.index[-1])
        val = metrics(val_trades, validation.index[0], validation.index[-1])
        output[name] = {
            "candidate": asdict(candidate),
            "full": asdict(full),
            "validation": asdict(val),
            "clears_8pw_70wr": bool(
                val.trades_per_week >= 8.0 and val.win_rate >= 70.0 and val.expectancy_r > 0
            ),
        }
        print(
            f"{name}: full={full.trades_per_week:.2f}/wk {full.win_rate:.2f}% WR "
            f"E={full.expectancy_r:.3f}R PF={full.profit_factor:.2f}; "
            f"validation={val.trades_per_week:.2f}/wk {val.win_rate:.2f}% WR "
            f"E={val.expectancy_r:.3f}R PF={val.profit_factor:.2f}; "
            f"target={'YES' if output[name]['clears_8pw_70wr'] else 'NO'}"
        )

    print("RESULT_JSON=" + json.dumps(output, separators=(",", ":"), default=str))


if __name__ == "__main__":
    main()
