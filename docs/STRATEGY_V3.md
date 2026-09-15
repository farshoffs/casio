# CASIO v3 Strategy — Regime-First + Adaptive 24H Sessions

CASIO is currently **version 3**.

The current strategy keeps the **v2 regime-first multi-timeframe core** and adds a **v3 adaptive 24h session overlay**. That distinction matters: the H4/H1/M15/M5 logic is still the baseline, but v3 no longer treats London/New York as the only possible Intraday hours.

Primary TradingView implementation:

```text
pine/CASIO_XAUUSD_v3_FAST.pine
```

Primary automated implementation:

```text
casio/v3_core.py
casio/v3_strategy.py
casio/live_signal.py
```

Recommended visual setup:

```text
XAUUSD
M15
AUTO
Session policy: ADAPTIVE_24H
```

> CASIO is research software. A backtest, score or research ranking is not a guarantee of future profitability.

## 1. Decision order

CASIO follows this hierarchy:

```text
1. Determine market regime
2. Select SCALPING or INTRADAY
3. Classify current session
4. Apply mandatory vetoes
5. Apply the session-specific threshold
6. Check usable R:R
7. LONG / SHORT / WAIT
```

It is not an equal-vote MTF model. A mandatory veto cannot be overcome by a high score.

## 2. Timeframe roles

```text
H4  -> macro directional context
H1  -> bias, value proxy, opposing liquidity, range state
M15 -> main trigger, sweep, BOS, session, SL/TP
M5  -> confirmation for Scalping and finer Python execution replay
```

M15 remains the normal chart timeframe. CASIO reads the other timeframes internally.

## 3. Regime routing

AUTO mode first decides whether the market is a range.

H1 range checks:

```text
abs(EMA20 - EMA50) / ATR <= 0.40
20-bar H1 range / ATR <= 8.0
```

M15 range checks:

```text
ADX <= 22
30-bar M15 range / ATR <= 5.5
```

Routing:

```text
H1 range AND M15 range
    -> SCALPING
otherwise
    -> INTRADAY
```

This happens before the session overlay. A quiet Asian range therefore naturally routes toward the Scalping engine rather than forcing a trend trade.

## 4. H4 directional context

H4 bias is deterministic:

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

Baseline Intraday requires H4 bullish for longs and H4 bearish for shorts. The research engine can test the H4 veto ON vs OFF.

## 5. H1 directional context and value

H1 bias uses the same broad EMA relationship:

```text
Bullish: EMA20 > EMA50 and close > EMA20
Bearish: EMA20 < EMA50 and close < EMA20
Neutral: otherwise
```

Primary-session Intraday rules allow H1 to be aligned or neutral but veto the strongly opposite direction.

Outside the primary sessions, v3 is stricter:

```text
Asia long exception       -> H1 must be bullish
Asia short exception      -> H1 must be bearish
Transition long exception -> H1 must be bullish
Transition short exception-> H1 must be bearish
```

The current H1 value model is still an EMA/ATR proxy, not a discretionary institutional supply/demand detector.

Default value distance:

```text
0.65 H1 ATR
```

Python research also supports a causal pivot-zone proxy for comparison.

## 6. H1 opposing liquidity

Prior H1 20-bar high/low levels are used as simple opposing-liquidity references:

```text
LONG  -> prior H1 high
SHORT -> prior H1 low
```

These levels cap the preferred target and determine whether there is enough room to justify the trade.

## 7. M15 liquidity sweep

Potential long sweep:

```text
current low < previous 20-bar low
AND
current close > previous 20-bar low
```

Potential short sweep is the inverse.

The sweep remains valid for a configurable number of M15 bars.

Baseline:

```text
sweepFreshBars = 3
```

Research tests 1, 2, 3, 4 and 5.

## 8. M15 BOS proxy

Bullish:

```text
close > previous 5-bar high
AND close > open
```

Bearish:

```text
close < previous 5-bar low
AND close < open
```

This is a deterministic proxy, not a discretionary market-structure parser.

## 9. Session classification

Every M15 bar belongs to one of four UTC buckets:

```text
ASIA        00:00-06:00
LONDON      07:00-11:00
NEW YORK    12:30-16:30
TRANSITION  all remaining times
```

The default policy is:

```text
ADAPTIVE_24H
```

A research-only compatibility comparison also exists:

```text
PRIMARY_ONLY
```

`PRIMARY_ONLY` reproduces the earlier Intraday restriction to London/New York. Scalping remains range-regime driven across sessions in both policies.

## 10. Primary Intraday playbook — London / New York

A long requires:

```text
H4 bullish
H1 not bearish
H1 value condition
recent M15 sell-side sweep
bullish M15 BOS proxy
inside London or New York primary window
usable R:R >= 2.5
score >= 80
```

Short is the inverse.

This remains the normal directional playbook.

## 11. Asia directional exception

Asia is not simply treated like London.

In AUTO mode, if H1+M15 qualify as a range, CASIO uses Scalping. If the market is directional, an Intraday trade can still qualify, but the default Asia exception requires:

```text
normal H4 directional gate
H1 aligned in the trade direction
H1 value condition
recent M15 sweep
M15 BOS
usable R:R >= 3.0
score >= 90
```

Asia gets only a 5-point session contribution versus 10 points in London/New York. The stricter threshold prevents the system from manufacturing low-quality overnight trend trades simply because 24h trading is technically possible.

## 12. Transition directional exception

Hours outside Asia, London and New York are classified as `TRANSITION`.

A Transition Intraday setup must pass everything in the directional core plus:

```text
H1 aligned in the trade direction
M15 ADX >= 25
usable R:R >= 3.0
score >= 90
```

Transition receives no session bonus. In practice this means only unusually clean directional setups can pass.

## 13. Intraday score

The directional score is still a checklist, not a probability.

```text
H4 directional alignment       20
H1 alignment / neutrality      15 or 8
H1 value condition             15
recent M15 liquidity sweep     20
M15 BOS                        15
session contribution           10 London/NY, 5 Asia, 0 Transition
usable R:R                      5
```

Maximum scores therefore differ by session unless all directional conditions align.

A score of 90 does **not** mean a 90% probability of winning.

## 14. Intraday stop and target

Long stop distance is the larger of:

```text
distance below M15 liquidity low with a 0.20 ATR buffer
or
1.00 M15 ATR
```

Short is mirrored above liquidity.

Preferred target:

```text
entry +/- stop distance * 3.0R
```

Liquidity target:

```text
opposing H1 20-bar liquidity
```

CASIO chooses the nearer target in the trade direction. If the available room is below the current session's required R:R, the setup is rejected.

## 15. Scalping engine

Scalping is a separate mean-reversion playbook.

Long trigger:

```text
H1 range regime
M15 range regime
M15 trades below prior 30-bar range low
M15 closes back above range low
M5 bullish confirmation
>= 1:1.3 to range mean
score >= 85
```

Short is the inverse at the upper edge.

M5 bullish confirmation:

```text
M5 close > M5 open
AND
M5 close > M5 EMA20
```

Target is the M15 30-bar range mean.

Scalping is intentionally not blocked by the Intraday session gate. That is how CASIO can participate in quieter sessions without forcing directional logic.

## 16. What AUTO now means

```text
Range regime?
    YES -> SCALPING, regardless of session
    NO  -> INTRADAY
             |
             +-- London/NY -> normal threshold
             +-- Asia      -> stricter aligned exception
             +-- Transition-> stricter aligned + ADX exception
```

`WAIT` remains a normal and desirable output.

## 17. TradingView vs automated Python

### v3 FAST Pine

```text
visual chart/dashboard
bundled H4/H1/M5 requests
session-aware rules
optional Pine alerts for accounts that support them
```

### Python live engine

```text
Dukascopy M5
causal H1/H4 reconstruction
session-aware v3 rules
runs every M15 close via GitHub Actions
sends valid fresh signals through Apps Script
```

TradingView Free is not required to generate the automated email signal.

## 18. v2 reference limitation

`pine/CASIO_XAUUSD_v2_MTF.pine` remains useful as a reference for the original v2 MTF core, but it does **not** contain the new v3 adaptive 24h session overlay. It is therefore no longer a complete 1:1 historical reference for current v3 entry gating.

## 19. Current limitations

CASIO v3 does not claim to have:

- a true discretionary supply/demand-zone detector,
- institutional order-flow data,
- DOM/order-book analysis,
- news sentiment inside the signal,
- broker-identical spread/slippage modelling,
- a statistically calibrated probability score,
- automatic profitable self-optimization,
- proven tick-for-tick parity between TradingView and Python.

The session rules are hypotheses to validate, not assumptions that Asia/Transition must be profitable.

## 20. Research questions

The research engine now asks:

1. Does the H4 veto improve expectancy enough to justify fewer trades?
2. Does EMA/ATR H1 value outperform the causal pivot proxy?
3. Does `ADAPTIVE_24H` outperform the older `PRIMARY_ONLY` policy after costs and drawdown, and which sessions actually contribute positive expectancy?
4. Which sweep freshness remains stable out-of-sample?
5. Does M5 Scalping confirmation improve net expectancy?
6. What primary-session minimum usable R:R is robust?
7. Does Scalping remain positive after friction?
8. Which choices remain stable across years, modes, sessions and walk-forward segments?

See `docs/RESEARCH_V3.md` for the validation process.
