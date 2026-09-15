# CASIO v3 Strategy — v2 Rule Baseline

CASIO is currently **version 3**.

The current live v3 engine deliberately keeps the **v2 regime-first multi-timeframe rule set** as its trading baseline. Version 3 changes the product architecture, live Pine performance and research tooling; it does not pretend that every strategy rule was reinvented.

Primary live implementation:

```text
pine/CASIO_XAUUSD_v3_FAST.pine
```

TradingView historical reference for the same baseline rules:

```text
pine/CASIO_XAUUSD_v2_MTF.pine
```

Recommended live chart:

```text
XAUUSD
M15
AUTO
```

> CASIO is research software. A backtest, score or research ranking is not a guarantee of future profitability.

## 1. Strategy philosophy

CASIO is built around this order of decisions:

```text
1. Determine market regime
2. Select the allowed playbook
3. Apply mandatory vetoes
4. Evaluate setup quality
5. Check usable R:R
6. LONG / SHORT / WAIT
```

It is **not** an equal-vote system where H4, H1, M15 and M5 each add a few points until a trade appears.

A mandatory veto cannot be overridden by a high score.

## 2. Why M15 is the operating chart

M15 is the main execution timeframe because it offers a practical compromise between structure, noise and trade frequency for XAUUSD.

CASIO reads the other timeframes internally:

```text
H4  -> macro directional context
H1  -> structure, value proxy, opposing liquidity, range state
M15 -> main trigger, sweep, BOS, session, SL/TP
M5  -> confirmation for Scalping only
```

For normal live use, stay on M15. Manually changing TradingView timeframe is not necessary for the MTF analysis.

## 3. H4 directional context

The baseline H4 bias is deterministic:

```text
Bullish:
EMA20 > EMA50
AND close > EMA20

Bearish:
EMA20 < EMA50
AND close < EMA20

Otherwise:
Neutral
```

H4 does not directly create an entry. In the baseline Intraday engine it acts as a directional gate.

For a long, baseline v2 rules require H4 bullish. For a short, H4 bearish.

The v3 Python research engine can explicitly test `h4_veto = ON` versus `OFF` to answer whether this reduction in trade count materially improves expectancy and drawdown.

## 4. H1 structure and value

### Directional veto

H1 uses the same broad EMA logic:

```text
Bullish: EMA20 > EMA50 and close > EMA20
Bearish: EMA20 < EMA50 and close < EMA20
Neutral: otherwise
```

For an Intraday long:

```text
H1 bearish -> veto
H1 bullish or neutral -> may continue
```

For a short, the inverse applies.

### H1 value proxy

The current live rule set does **not** claim to detect discretionary institutional supply/demand zones.

Its baseline value model is a practical EMA/ATR proxy. A long wants price close enough to H1 EMA20 relative to H1 ATR rather than buying after price has already extended too far.

Default distance:

```text
0.65 H1 ATR
```

The v3 Python research engine also implements a **causal pivot-zone proxy** so the baseline EMA/ATR model can be compared against an alternative without future-data leakage.

That pivot experiment is still a rule-based proxy; it is not DOM/order-flow or institutional positioning data.

### H1 opposing liquidity

Prior H1 20-bar high/low levels are used as simple opposing-liquidity references:

```text
LONG  -> prior H1 high
SHORT -> prior H1 low
```

This matters because CASIO does not blindly demand a fixed 3R target through a nearer obstacle.

## 5. M15 liquidity sweep

M15 tracks the previous 20-bar high and low.

A sell-side sweep for a potential long means:

```text
current low < previous 20-bar low
AND
current close > previous 20-bar low
```

A buy-side sweep for a short is the inverse.

The sweep does not need to occur on the exact BOS candle. `sweepFreshBars` controls how long the event remains usable.

Baseline:

```text
sweepFreshBars = 3
```

The v3 research engine tests 1, 2, 3, 4 and 5 bars.

## 6. M15 structure confirmation

The current BOS proxy compares the current M15 close with the previous five-bar structure:

```text
Bullish BOS proxy:
close > previous 5-bar high
AND close > open

Bearish BOS proxy:
close < previous 5-bar low
AND close < open
```

This is intentionally deterministic. It is not a fully discretionary market-structure parser.

## 7. Session filter

Baseline Intraday trading windows are fixed in UTC so chart timezone changes do not alter the rules:

```text
London:   07:00-11:00 UTC
New York: 12:30-16:30 UTC
```

The v3 research engine tests several bounded session profiles rather than assuming these windows are optimal forever.

## 8. Intraday engine

A baseline long requires all of the following:

```text
H4 bullish
H1 is not bearish
H1 value condition passes
recent M15 sell-side sweep
M15 bullish BOS proxy
inside London or New York primary window
>= minimum usable R:R to H1 opposing liquidity
score >= minimum score
```

Short is the inverse.

Defaults:

```text
minimum score = 80
preferred target R:R = 3.0
minimum usable R:R = 2.5
```

### Intraday stop

For a long, the stop distance is the larger of:

```text
distance below recent M15 liquidity low with a 0.20 ATR buffer
or
1.00 M15 ATR
```

Short is mirrored above recent liquidity.

### Intraday target

CASIO calculates two targets:

```text
preferred target = entry +/- stop distance * preferred R:R
liquidity target = opposing H1 20-bar liquidity
```

It chooses the nearer target in the trade direction.

Therefore a setup can be rejected even if direction looks attractive when the available room before H1 opposing liquidity is too small.

## 9. Scalping engine

Scalping is a separate mean-reversion strategy.

### Range regime

H1 baseline range checks:

```text
abs(EMA20 - EMA50) / ATR <= 0.40
20-bar H1 range / ATR <= 8.0
```

M15 baseline range checks:

```text
ADX <= 22
30-bar M15 range / ATR <= 5.5
```

Both must pass for AUTO mode to select `SCALPING`.

Otherwise AUTO selects `INTRADAY`.

### Range-edge trigger

Long scalp:

```text
M15 trades below the prior 30-bar range low
AND closes back above that range low
```

Short is the inverse at the upper edge.

### M5 confirmation

Baseline bullish confirmation:

```text
M5 close > M5 open
AND
M5 close > M5 EMA20
```

Bearish is the inverse.

M5 is not required for baseline Intraday trades.

The v3 Python engine tests Scalping with this confirmation ON and OFF so its higher win rate, if any, is evaluated against the worse/later entry opportunity and actual expectancy.

### Scalping target

Target is the M15 30-bar range mean.

Default minimum usable R:R:

```text
1.3
```

## 10. Scoring vs mandatory conditions

The score is a **setup-quality checklist**, not a calibrated probability.

An Intraday long can receive points for:

```text
H4 directional alignment       20
H1 alignment / neutrality      15 or 8
H1 value condition             15
recent M15 liquidity sweep     20
M15 BOS                        15
primary session                10
usable R:R                      5
```

A score of `90` does **not** mean a 90% win probability.

More importantly, a setup cannot use score to bypass a mandatory veto.

## 11. AUTO mode

The current routing logic is:

```text
H1 range regime AND M15 range regime
    -> SCALPING
otherwise
    -> INTRADAY
```

This is why CASIO can legitimately show `WAIT` even when one timeframe looks bullish or bearish. The whole active playbook still has to qualify.

## 12. v3 FAST vs v2 Pine

### v3 FAST

```text
indicator()
fast live dashboard
bundled H4/H1/M5 requests
limited requested MTF history
live signal alerts
no heavy historical rolling audit
```

### v2 MTF reference

```text
strategy()
TradingView Strategy Tester
historical trade replay
rolling closed-trade audit
heavier chart recalculation
```

They use the same intended baseline strategy logic, but exact signal parity should still be checked whenever Pine implementation details change.

## 13. Current limitations

CASIO v3 currently does not claim to have:

- a true discretionary supply/demand-zone detector,
- institutional order-flow data,
- DOM/order-book analysis,
- news sentiment built into the Pine signal,
- spread/slippage modelling identical to a live broker,
- a statistically calibrated probability score,
- automatic profitable self-optimization,
- proven tick-for-tick parity between Pine and the Python research engine.

The Python v3 engine now reproduces the rule family independently, but parity remains something to **verify**, not assume.

## 14. What the research engine is trying to learn

The current priority questions are:

1. Does the H4 veto improve expectancy enough to justify fewer trades?
2. Does the EMA/ATR H1 value proxy outperform a causal pivot-zone proxy?
3. Which tested London/New York window is most robust?
4. Which sweep freshness remains stable out-of-sample?
5. Does M5 Scalping confirmation improve net expectancy?
6. What minimum Intraday usable R:R is robust?
7. Does Scalping remain positive after friction?
8. Which choices remain stable across years and walk-forward segments?

See `docs/RESEARCH_V3.md` for how CASIO tests those questions without automatically promoting the prettiest backtest.
