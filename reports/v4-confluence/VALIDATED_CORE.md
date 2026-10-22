# CASIO v4 Validated Core — 2026-09-17

## Status

Research challenger only. The configuration below clears the requested historical frequency and win-rate gates on the chronological validation slice, but its measured expectancy is modest and the Python replay does not yet debit live execution costs explicitly.

## Promoted challenger configuration

- Native timeframe: XAUUSD M5
- Standalone entries: BBMA re-entry + confirmed supply/demand rejection
- Liquidity/FVG: confluence only by default
- Breakout/retest: confluence only by default
- Primary-session minimum score: 55
- TP: 0.60R
- Breakeven trigger: 0.35R
- Breakeven lock: +0.05R
- Cooldown: 6 M5 bars
- Maximum accepted trades/day: 3
- Structural SL: recent M5 swing extreme + 0.15 ATR buffer
- Accepted SL range: 0.35–1.80 ATR

## Chronological validation result

The latest 30% of initialized Dukascopy research rows was held as the chronological validation slice.

| Metric | Result | Acceptance target |
| --- | ---: | ---: |
| Completed trades | 178 | — |
| Trades/week | 9.48 | >= 8 |
| Win rate | 74.16% | >= 70% |
| Mean expectancy | +0.032R/trade | > 0 |
| Profit factor | 1.12 | > 1 |
| Max closed-trade drawdown | 9.95R | monitor |

The headline 8 trades/week and 70% win-rate requirements are therefore cleared **on this historical validation sample**.

## Playbook contribution on validation

| Playbook | Trades | Trades/week | Win rate | Expectancy | PF |
| --- | ---: | ---: | ---: | ---: | ---: |
| BBMA re-entry | 20 | 1.07 | 80.00% | +0.033R | 1.16 |
| Demand rejection | 57 | 3.04 | 70.18% | -0.032R | 0.89 |
| Supply rejection | 101 | 5.38 | 75.25% | +0.068R | 1.27 |

The asymmetric historical contribution is recorded rather than used to introduce a discretionary long/short rule. Further research should determine whether the weaker demand-rejection result is regime/sample-specific before changing the production logic.

## Why breakout/FVG are not standalone defaults

With all four entry families enabled at 0.60R / 0.35R breakeven, validation measured approximately 10.07 trades/week, 73.54% win rate, +0.017R expectancy and PF 1.06. Disabling breakout/retest and liquidity/FVG as standalone triggers while retaining them as confluence produced the stronger combined result above: 9.48 trades/week, 74.16% win rate, +0.032R expectancy and PF 1.12.

## Promotion gates still outstanding

1. Compile and run `pine/CASIO_XAUUSD_v4_CONFLUENCE.pine` directly in TradingView on the intended XAUUSD symbol/feed.
2. Configure realistic TradingView commission and, where possible, spread/slippage assumptions. The current Python replay does not explicitly debit these costs.
3. Compare TradingView fills to the Python causal replay over an overlapping period.
4. Validate on an additional feed or genuinely unseen later window.
5. Keep CASIO v3 production automation unchanged until these gates are satisfied.

The modest +0.032R historical expectancy means execution costs matter materially. The 74.16% historical win rate should not be interpreted as a guaranteed live win rate.
