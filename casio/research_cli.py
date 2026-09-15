from __future__ import annotations

import argparse
import json
from pathlib import Path

from .v3_core import load_m5_csv
from .v3_research import run_research


def main() -> None:
    parser = argparse.ArgumentParser(description="CASIO v3 robustness research engine (v2 rules baseline)")
    parser.add_argument("--data", default="data/xauusd_m5.csv", help="UTC M5 OHLC CSV")
    parser.add_argument("--output", default="reports/v3-research", help="Output directory")
    parser.add_argument("--max-candidates", type=int, default=64, help="Bounded candidate search size")
    parser.add_argument("--cost-bps", type=float, default=1.0, help="Round-trip friction assumption in basis points")
    args = parser.parse_args()
    if args.max_candidates < 1 or args.cost_bps < 0:
        raise SystemExit("max-candidates must be >= 1 and cost-bps must be >= 0")
    data = load_m5_csv(args.data)
    Path(args.output).mkdir(parents=True, exist_ok=True)
    print(json.dumps(run_research(data, args.output, args.max_candidates, args.cost_bps), indent=2))


if __name__ == "__main__":
    main()
