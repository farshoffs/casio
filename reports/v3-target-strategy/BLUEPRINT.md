# CASIO A+ Portfolio — Target Strategy Blueprint

Status: **research only**. Do not deploy from this document.

## Portfolio objective

The target is a portfolio-level objective, not a promise for every playbook:

- ~8 completed trades / 30 days
- 42–50% profitable trades
- ~3.5R average winner
- >= +0.70R expectancy / trade
- PF >= 2.0
- structural loss kept near -1R

If average loss stays close to 1R, 45% wins with 3.5R average winners mathematically implies about +1.025R expectancy and PF about 2.86. Therefore the research should focus primarily on frequency, hit quality and winner size rather than separately optimizing PF.

## Core decision chain

1. Determine D1/H4/H1 market state from confirmed structure, not ADX.
2. Map major liquidity: previous day H/L, Asia H/L, confirmed H1/H4 external swings, equal highs/lows, and prior-week H/L when available.
3. Select the appropriate playbook for the regime.
4. Require an actual liquidity event or pullback into value.
5. Require M5 displacement plus local market-structure shift/BOS.
6. Do not chase the displacement close. Wait for a 38.2–61.8% retracement of the displacement leg; 50% is the baseline entry.
7. Place the stop beyond the swept liquidity / structural invalidation with a volatility buffer.
8. Classify liquidity ahead as internal or external. Internal liquidity is an obstacle/confirmation level; it is not automatically the final TP.
9. Require realistic external runway for at least 3R; preferred trade objective is 3.5R–4R.
10. WAIT when the market state does not map cleanly to a playbook.

## Playbook router

### A — Trend pullback continuation

Target contribution: roughly 3–4 trades/month.

- H4/H1 structure directional or one directional while the other is neutral; no direct HTF structural conflict.
- M15 continuation structure agrees.
- M5 pulls back into value / prior impulse origin.
- M5 produces displacement and BOS in the HTF direction.
- Enter on displacement retracement, not breakout close.
- Structural stop behind the pullback swing.
- External-liquidity target, preferred >=3.5R.

### B — External liquidity sweep

Target contribution: roughly 2–3 trades/month.

- Sweep of PDH/PDL, Asia H/L, or confirmed external H1 liquidity.
- Close/reclaim after the sweep.
- M5 displacement plus MSS/BOS away from the swept level.
- No strong H4+H1 conflict against the trade.
- Retracement entry into the displacement leg.
- Stop behind the sweep extreme.
- Opposing external liquidity must offer >=3R, preferred 3.5R+.

### C — Session expansion retest

Target contribution: roughly 1–2 trades/month.

- London/NY expansion through meaningful session liquidity in the higher-timeframe direction.
- No chase entry.
- Wait for retest of the broken external/session level.
- Require renewed M5 displacement/BOS from the retest.
- Stop behind retest invalidation.
- Preferred target 3.5R–5R where external liquidity supports it.

## Execution and management

Baseline research management:

- no scale-out initially, because the portfolio objective explicitly requires ~3.5R average winners;
- preferred full target = 3.5R, optionally extended to the external-liquidity objective when structure supports >3.5R;
- one active position at a time;
- conservative stop-first assumption when stop and target are both touched in the same M5 candle;
- transaction-cost assumption included;
- setup expires if the retracement entry is not filled within its defined window;
- no automatic re-entry immediately after a stopped trade unless a new liquidity event and a new M5 structure shift occur.

## Research discipline

Do not select settings merely because they hit the requested headline numbers on one sample. A candidate can be promoted only after the same frozen rules survive:

1. development data,
2. later chronological validation,
3. a different broker/feed,
4. additional untouched Dukascopy years as the canonical backfill arrives.

The live v3 model remains frozen until a challenger survives these stages. The target metrics are the acceptance criteria, not values the optimizer is allowed to manufacture by curve fitting.
