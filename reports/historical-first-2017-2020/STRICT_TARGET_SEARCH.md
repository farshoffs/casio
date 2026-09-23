# CASIO Strict Target Search — 2017–2020

Branch: `research/historical-2017-2020`

## Hard requirements

The research target is treated as pass/fail:

- Fixed TP = 3R.
- Real structural stop only; no breakeven/protected-SL manipulation.
- Win rate >= 60%.
- Maximum equity drawdown <= 25%.
- Minimum 8 realized trades in every calendar month.
- Profitable in each of 2017, 2018, 2019 and 2020.
- RM100 start.
- 5% current-equity risk per trade.
- 1 bp round-trip cost.
- Same-M5 SL + TP => SL first.
- 2021+ remains sealed during development.

## Strict M15 / price-action search

Workflow run: 35855152851

Tested 126 coarse, interpretable setup cards plus portfolio combinations.

Families included:
- EMA20 rejection / pin rejection.
- EMA50 rejection.
- Engulfing pullback.
- Liquidity sweep continuation.
- Breakout + retest.
- Inside-bar break.
- Bollinger/Keltner squeeze expansion.
- FVG/imbalance continuation proxy.
- Two-bar momentum.
- NY opening-range retest.
- Previous-day high/low retest.

Biases included strict D1/H4 alignment and H4 bias.

Result: **0 strict passes**.

Best robust precision examples:

### EMA20 rejection, D1+H4 aligned, ADX26, wick/body >=2.5
- 116 trades.
- 37.07% WR.
- +0.333R/trade.
- PF 1.46.
- 34.56% overall max DD.
- 2.42 trades/month average.
- Minimum month = 0.
- 4/4 positive years.

### EMA20 rejection, D1+H4 aligned, ADX22, wick/body >=2.5
- 171 trades.
- 39.18% WR.
- +0.404R/trade.
- PF 1.57.
- 50.29% max DD.
- 3.56 trades/month.
- Minimum month = 0.
- 4/4 positive years.

This family improved precision and expectancy versus prior trend systems, but remained far below the 60% WR and frequency requirements.

## Strict M5 precision search

Workflow run: 35855698945

Tested 360 additional M5 setup cards.

Families included:
- M5 EMA20 pin rejection.
- M5 EMA20 engulfing.
- M5 VWAP rejection.
- Micro liquidity sweeps.
- Micro breakout/retest.
- RSI8 trend reclaim.
- Stochastic reclaim.
- MACD turn.
- Asia breakout retest.
- NY opening-range retest.

Bias combinations:
- H4 + D1.
- H1 + H4.
- H1 + H4 + D1.

Session combinations:
- All day.
- London.
- New York.
- London + New York.

Result: **0 strict passes**.

The only cards reaching >=60% observed WR were extremely sparse:

### RSI8 triple-timeframe all-session
- 5 trades total across 2017–2020.
- 60.00% WR.
- +1.182R/trade.
- PF 3.25.
- 7.36% DD.
- Average 0.10 trades/month.
- Minimum month 0.
- Only 3/4 years had trades/profit.

Other 66.67–100% WR variants had only 1–3 total trades.

Once frequency became meaningful, observed WR fell back into roughly the 30–40% range. Example:

### M5 EMA20 pin, H4+D1, London
- 104 trades.
- 38.46% WR.
- +0.227R/trade.
- PF 1.28.
- 40.49% DD.
- 2.17 trades/month.
- 3/4 positive years.

## Comparison with earlier development candidates

The earlier systems that satisfy the monthly frequency requirement remain around 29–30% WR:

- EMA Ribbon + Session: 20.25 trades/month, minimum 8, 48/48 months >=8, 4/4 positive years, 29.73% WR, +0.131R, but 79.47% worst yearly DD.
- Trend Alternative + Session: 23.81 trades/month, minimum 10, 48/48 months >=8, 4/4 positive years, 29.13% WR, +0.104R, but 78.45% worst yearly DD.
- Donchian-8 + Session: 23.04 trades/month, minimum 10, 4/4 positive years, 29.20% WR, +0.109R, but 79.58% worst yearly DD.

## Constraint interaction

At 5% equity risk, six consecutive -1R losses produce an equity drawdown of:

`1 - 0.95^6 = 26.49%`

Therefore the DD <=25% constraint effectively requires avoiding six-loss sequences (and can be breached even without six consecutive losses if recovery is incomplete).

At 60% WR the loss probability is 40%. With hundreds of trades required by the >=8/month condition over four years, six-loss clusters are not unusual enough to ignore. A strategy meeting all hard requirements therefore needs materially better sequence quality than a generic 60% Bernoulli process, not merely a 60% average win rate.

## Current decision

No tested system meets all hard requirements yet.

Total newly tested in the strict phase:
- 126 M15/price-action cards.
- 360 M5 precision cards.
- 486 strict-search configurations, plus the earlier trend/session/Donchian/FiboRSI8 research.

The empirical frontier currently observed is:
- high frequency + 4/4 positive years => around 29–31% WR at 3R, with excessive 5%-risk drawdown;
- higher precision => around 37–40% WR, but frequency falls well below 8/month;
- >=60% WR => only tiny samples of 1–7 trades over four years.

The target remains open; no criterion has been relaxed and 2021–2026 remains sealed.
