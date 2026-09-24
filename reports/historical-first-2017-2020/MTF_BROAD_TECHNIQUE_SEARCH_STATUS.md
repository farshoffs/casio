# CASIO MTF Broad Technique Search — Status

## Hard rules

Every tested technique must be multi-timeframe:
- completed H1/H4 context,
- M5 setup,
- M1 execution/fill/SL-TP ordering.

Other fixed rules:
- XAUUSD FxPro M1 source supplied by user.
- Development slice: 2017-01-01 through 2020-12-31 only.
- 2021+ sealed.
- New York session only, DST-aware America/New_York.
- Start RM100.
- Risk 5% current equity per entry.
- Fixed TP 3R.
- Real structural stop only; no BE/protected stop.
- One position at a time.
- 1 bp round-trip cost.
- M1 same-bar SL/TP ambiguity = SL first.
- Target WR floor 50%.
- Max DD <25%.
- Minimum 8 completed trades in every calendar month.

## Search coverage

Current broad catalog tested 4,616 strategy configurations across 26 MTF families:
ADX/DI rotation, tick-volume breakout, Donchian breakout, EMA20 pullback, EMA50 pullback, RSI8 reclaim, RSI2 snapback, MACD rotation, Bollinger squeeze, displacement, FVG trend, inside-bar breakout, NR4/NR7 breakout, NY VWAP reclaim, ORB breakout, ORB retest, overnight breakout, overnight retest, previous-NY sweep, overnight sweep, premarket sweep, rolling liquidity sweep, failed breakout, VWAP fade, Bollinger fade, and volatility-shock reversal.

MTF contexts:
- ALIGN = H1 and H4 EMA20/EMA50 direction plus completed HTF slope alignment.
- H4_H1ADX = H4 directional trend plus H1 DI/ADX confirmation.
- H4_RANGE = H4 low/moderate-ADX reversal context for reversal families.

Execution variants included market, 50% retrace, 70.5% retrace, 88.6% retrace, and M1 micro-MSS where applicable.

## Result

Strict passes: **0**.

### Quality frontier

30 configurations achieved WR >=50% and DD <25%, but every one failed the minimum-8-trades-every-month rule.

Best quality candidate:

`DISPLACEMENT__H4_H1ADX__NY_CASH_AM__r705__adx30__bf0.75__body0.5__cd2__lb16__vol1.15`

- 24 trades total.
- WR 58.33%.
- Expectancy +1.131R/trade.
- PF 3.22.
- Max DD 22.52%.
- Profitable years 4/4.
- RM100 -> RM335.70 continuous.
- Average 0.50 trades/month.
- Minimum month 0.
- Months >=8 trades: 0/48.

A looser aligned displacement variant:

`DISPLACEMENT__ALIGN__NY_CASH_AM__r705__adx30__bf0.75__body0.5__cd2__lb16__vol1.15`

- 32 trades.
- WR 53.13%.
- +0.923R/trade.
- PF 2.62.
- DD 17.40%.
- 4/4 profitable years.
- RM100 -> RM364.61.
- Average 0.67 trades/month.
- Minimum month 0.

### Frequency frontier

35 configurations achieved minimum >=8 trades in every month.

None achieved the quality requirements.

Best WR among the full-frequency group was approximately 28.64%:
- Donchian H4/H1-ADX NY Cash, 70.5% retrace.
- 887 trades.
- Minimum 10 trades/month.
- WR 28.64%.
- Expectancy -0.301R.
- PF 0.71.
- DD ~100%.
- 0/4 profitable years.

Other full-frequency families such as EMA20 pullback, FVG trend and Donchian variants clustered around roughly 26–28% WR and catastrophic DD.

## NY sub-session search

An additional 960 displacement configurations were tested across NY sub-session variants.

Strict passes: 0.

Quality remained strong in some opening-hour variants:
- WR 50–58.82%.
- PF ~2.1–3.05.
- DD 7–23%.
- several were profitable 4/4 years.

But minimum monthly trades remained 0 for every sub-session candidate.

## Current conclusion

The current MTF search shows a sharp frontier:

1. High-precision MTF displacement can satisfy WR 50–60%, DD <25%, fixed 3R and 4/4 profitable years, but produces far fewer than 8 trades every month.
2. Techniques dense enough to guarantee >=8 trades every month collapse toward ~26–29% WR and unacceptable DD.
3. No current single MTF technique satisfies all hard rules simultaneously.

The next useful research direction is not simply loosening a high-quality displacement filter. It is to combine independent MTF high-precision setups into a single one-position-at-a-time portfolio/router and test the portfolio itself against the exact same hard rules.

No criteria have been relaxed and 2021+ remains sealed.
