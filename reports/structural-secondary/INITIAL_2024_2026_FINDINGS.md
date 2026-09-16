# CASIO secondary-feed research — 2026 to 2024

Research feed: separate OctaFX / Octa Markets MT4 XAUUSD M5 base, normalized from broker EET/EEST time to UTC. **Do not merge this feed into `data/xauusd_m5.csv`.**

The uploaded `XAU_5m_data.csv` contains 1,443,451 M5 bars. Raw broker-time coverage is 2004-06-11 07:15 through 2026-01-30 23:55; normalized UTC coverage is 2004-06-11 04:15 through 2026-01-30 21:55.

The archive ends on 2026-01-30, so its "latest" market is January 2026 — not the current September 2026 market. Current-market decisions must continue to use fresh Dukascopy data first.

## Exact current assistant reference

`DISPLACEMENT_RETRACE`, all three structural playbooks, target 3.5R, minimum external runway 3.5R.

| Period | Trades | Trades/30d | WR | Avg winner | Avg loser | Expectancy | PF | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Latest 60d ending 2026-01-30 | 15 | 7.50 | 6.67% | +3.392R | -1.052R | -0.756R | 0.230 | 10.29R |
| 2026 partial (Jan only) | 5 | 5.01 | 0.00% | — | -1.053R | -1.053R | 0.000 | 4.20R |
| 2025 | 107 | 8.79 | 21.50% | +3.153R | -1.072R | -0.164R | 0.805 | 29.69R |
| 2024 | 128 | 10.49 | 29.69% | +2.898R | -1.071R | +0.107R | 1.142 | 23.35R |

This is a useful robustness failure. The September-2026 current-market discovery result must **not** be assumed to work in every older regime.

## Technique-level findings

`STRICT_FVG` was materially stronger in 2025:

- 43 trades / 3.53 per 30d
- 44.19% WR
- +3.247R average winner
- -1.077R average loser
- +0.834R expectancy
- PF 2.386
- 5.26R max drawdown

Within that 2025 strict-FVG sample, `EXTERNAL_SWEEP` contributed 35 trades with 45.71% WR, +0.894R expectancy and PF 2.544. Frequency remained only ~2.88 trades/30d.

In 2024, the broad displacement model was weak, but its `TREND_PULLBACK` playbook was much better: 18 trades, 50.0% WR, +3.404R average winner, +1.160R expectancy and PF 3.138. Frequency was only ~1.48 trades/30d.

No tested portfolio combination met the full target on the archive's latest 60-day window. The closest latest-first combination was displacement-retrace trend-pullback only, but it was too sparse (3 trades / 60d) and therefore is not a production candidate.

## Research implication

Do **not** solve this by optimizing to calendar years. The result supports a causal regime router:

- trend-pullback continuation when trend structure and pullback quality support it,
- strict liquidity-sweep/FVG execution when the external-sweep regime supports it,
- session expansion only when it proves an independent edge,
- `WAIT` when none of the playbooks has a qualified market state.

The next research stage should identify price-action regime features that select those playbooks without knowing the year, and then freeze those rules before walking backward further.

No live strategy or TradingView production rule was promoted from this secondary-feed study.
