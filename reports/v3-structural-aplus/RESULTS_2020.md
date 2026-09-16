# CASIO Structural A+ — 2020 first pass

Research only. Live CASIO was not modified.

Target objective:

- ~8 trades / 30 days
- 42–50% win rate
- ~3.5R average winner
- >= +0.70R expectancy / trade
- profit factor >= 2.0

Implemented research sequence:

1. H4/H1 confirmed swing structure.
2. Major liquidity: previous-day H/L, current Asia H/L, confirmed H1 swing liquidity, H1 equal highs/lows.
3. Pullback or major-liquidity sweep.
4. M5 displacement plus micro structure break.
5. Wait for retracement after displacement instead of entering the displacement close.
6. Structural stop behind the sweep / recent structure.
7. Measure R room to the next identified major liquidity.
8. Only admit setups that pass the configured exceptional-reward runway.

The research grid tested 3.0R / 3.5R / 4.0R minimum liquidity runway, 4 / 6 / 8 M5 bars to obtain the retracement fill, and two management styles: full 3.5R exit and 25% at +2R with 75% runner to +4R.

## Best development-selected variant

`R3_5_RB8_FULL_3_5R`

Configuration: minimum liquidity runway 3.5R; 50% displacement retracement entry; up to 8 M5 bars to fill; full target at 3.5R.

### Development

- Trades: 16
- Trades / 30 days: 1.95
- Win rate: 37.50%
- Average winner: +3.43R
- Average loser: -1.14R
- Expectancy: +0.574R / trade
- Profit factor: 1.806
- Max drawdown: 8.04R

### Later validation slice

- Trades: 5
- Trades / 30 days: 1.83
- Win rate: 40.00%
- Average winner: +1.96R
- Average loser: -1.13R
- Expectancy: +0.102R / trade
- Profit factor: 1.150
- Max drawdown: 2.31R

## Interpretation

The exact eight-step structural implementation does **not** meet the target yet. It gets close to the desired payoff size in development, but becomes too selective and loses too much edge in the later slice. The result argues against replacing the existing A+ model with this strict version.

Next research should keep these market-structure concepts but avoid treating every identified liquidity level as a hard final barrier. In particular, distinguish internal liquidity / partial objectives from external liquidity / runner objectives, and measure pullback-continuation and liquidity-sweep playbooks separately before attempting any live promotion.
