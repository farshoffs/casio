# CASIO Structural Frequency — Current-Market Result

Research only. Production v3 was not changed.

Objective:

- ~8 trades / 30 days
- 42–50% win rate
- ~3.5R average winner
- average loss ~1R or better
- expectancy >= +0.70R / trade
- PF >= 2.0

## Current 60-day discovery

The curated `DISPLACEMENT_RETRACE` technique replaces the requirement for a literal 3-candle FVG with:

1. same structural/liquidity playbook router,
2. same M5 displacement + local BOS requirement,
3. FVG midpoint retracement when an FVG exists,
4. otherwise 50% displacement-body retracement,
5. same structural stop,
6. same >=3.5R external-liquidity runway,
7. same 3.5R target.

Observed on the latest 60-day Dukascopy M5 BID research window ending 2026-09-16:

- Trades: 19
- Trades / 30 days: **9.5**
- Win rate: **42.105%**
- Average winner: **+3.432R**
- Average loser: **-1.041R**
- Expectancy: **+0.843R / trade**
- Profit factor: **2.398**
- Max drawdown: **3.120R**

This satisfies the research target band on the current 60-day development window.

## Important limitation

The first frequency workflow completed the calculation but failed while serializing the selected mode after the latest-window table had already been produced. That software bug was fixed. The immediate rerun then hit Dukascopy HTTP 429 on the final download chunk after repeated full-window downloads, so the frozen backward 60-day checks have not yet been regenerated for this exact candidate.

Therefore these figures are a current-market discovery result, not established long-run performance. The TradingView research assistant has been updated to use `DISPLACEMENT_RETRACE` as its default entry model, while retaining `FVG_STRICT` as an option. Production v3 remains unchanged.
