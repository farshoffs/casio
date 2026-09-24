# CASIO FX Scalping Rule Set v1

Updated: 2026-09-25

## Hard rules

- Starting equity: RM100
- Risk: 5% of current equity per accepted entry
- Fixed RR: 1:2
- Minimum 8 accepted trades per calendar month
- Every completed calendar month must finish with actual compounded equity above its RM100 monthly reset baseline
- Real SL only
- No breakeven stop
- No protected stop
- Scalping focus: small pip movement, M1/M5 execution, tight structural stops
- Current research universe: EURUSD, GBPUSD, GBPJPY on user-supplied FxPro M1

## Important accounting clarification

A nominal +1R month is not sufficient.

At RM100 and 5% risk, 1R initially equals RM5. More importantly, when many trades are compounded sequentially, an additive +1R month can still finish below RM100 because losses and wins act multiplicatively on changing equity.

Therefore the acceptance rule is based on actual monthly compounded RM balance, not additive R alone.

## First scalp screen findings

A naked-chart micro-sweep/reclaim family was tested using:
- M1 sweep/reclaim of recent 10/20-bar highs/lows and previous completed M15 levels
- London/New York windows
- structural wick stop
- fixed 2R target
- stop-first same-M1 collision handling
- one open position per pair
- development-selected pair/setup/hour groups
- causal month lock after >=8 trades and a profitable month

Tight-stop research bands included approximately:
- EURUSD: small structural stops up to ~4 pips
- GBPUSD: up to ~5 pips
- GBPJPY: up to ~8 pips

A gross additive-R router could make all 116 completed months positive, but that was rejected as the final interpretation because some +1R months still finished below RM100 after 5% compounding.

Example from the wider scalp candidate:
- January 2026: +1R additive, but RM100 -> about RM85.24 after 86 trades
- June 2026: +1R additive, but RM100 -> about RM94.38 after 44 trades

This confirms that monthly RM equity, not additive R, is the correct gate.

## Current verdict

The new scalping rule is active, but no production candidate is accepted yet.

The next scalp candidate must satisfy simultaneously:
1. fixed 2R;
2. real SL / no BE / no protected SL;
3. at least 8 trades in every completed month;
4. each monthly RM100 reset finishes above RM100;
5. small-pip execution geometry;
6. realistic spread/commission sensitivity suitable for scalping.
