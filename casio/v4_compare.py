from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .v3_backtest import backtest_signals, metrics
from .v3_core import V3Config, load_m5_csv, prepare_features
from .v3_strategy import signals_for_config as v3_signals
from .v4_core import V4Config
from .v4_strategy import signals_for_config as v4_signals


def _iso(value: str | None) -> pd.Timestamp | None:
    if not value:
        return None
    x = pd.Timestamp(value)
    return x.tz_localize("UTC") if x.tzinfo is None else x.tz_convert("UTC")


def _playbooks(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {}
    return {str(name): metrics(group) for name, group in trades.groupby("playbook")}


def compare(data_path: str | Path, start: pd.Timestamp | None = None, end: pd.Timestamp | None = None) -> dict:
    m5 = load_m5_csv(data_path)
    features = prepare_features(m5)

    v3_cfg = V3Config()
    v4_cfg = V4Config()
    sig3 = v3_signals(features, v3_cfg)
    sig4 = v4_signals(features, v4_cfg)
    tr3 = backtest_signals(m5, sig3, v3_cfg, start=start, end=end)
    tr4 = backtest_signals(m5, sig4, v4_cfg, start=start, end=end)

    return {
        "warning": "Diagnostic only. Do not treat a partial historical backfill as robust evidence.",
        "coverage": {
            "first_m5": m5.index.min().isoformat(),
            "last_m5": m5.index.max().isoformat(),
            "bars": int(len(m5)),
            "start_filter": start.isoformat() if start is not None else None,
            "end_filter": end.isoformat() if end is not None else None,
        },
        "v3": {"metrics": metrics(tr3), "playbooks": _playbooks(tr3)},
        "v4": {"metrics": metrics(tr4), "playbooks": _playbooks(tr4)},
    }


def _markdown(result: dict) -> str:
    def row(name: str, m: dict) -> str:
        return "| {name} | {trades} | {wr} | {exp} | {pf} | {dd} |".format(
            name=name,
            trades=m.get("trades", 0),
            wr="—" if m.get("win_rate") is None else f"{m['win_rate']:.1f}%",
            exp="—" if m.get("expectancy_r") is None else f"{m['expectancy_r']:.3f}R",
            pf="—" if m.get("profit_factor") is None else f"{m['profit_factor']:.2f}",
            dd="—" if m.get("max_drawdown_r") is None else f"{m['max_drawdown_r']:.2f}R",
        )

    lines = [
        "# CASIO v3 vs v4 diagnostic",
        "",
        "> Diagnostic only: the historical CSV may still be an incomplete backfill.",
        "",
        f"Coverage: `{result['coverage']['first_m5']}` → `{result['coverage']['last_m5']}` ({result['coverage']['bars']:,} M5 bars)",
        "",
        "| Strategy | Trades | Win rate | Expectancy | Profit factor | Max DD |",
        "|---|---:|---:|---:|---:|---:|",
        row("v3 baseline", result["v3"]["metrics"]),
        row("v4 setup-first", result["v4"]["metrics"]),
        "",
        "## v4 playbooks",
        "",
        "| Playbook | Trades | Win rate | Expectancy | Profit factor | Max DD |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, m in sorted(result["v4"]["playbooks"].items()):
        lines.append(row(name, m))
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare frozen CASIO v3 with experimental setup-first v4")
    parser.add_argument("--data", default="data/xauusd_m5.csv")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--output", default="reports/v4-diagnostic")
    args = parser.parse_args()

    result = compare(args.data, _iso(args.start), _iso(args.end))
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "comparison.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    report = _markdown(result)
    (output / "REPORT.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
