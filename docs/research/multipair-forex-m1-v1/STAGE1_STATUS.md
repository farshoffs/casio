# Multi-Pair Forex M1 Research — Stage 1 Status

Date: 2026-09-24

Pairs:
- EURUSD
- GBPUSD
- GBPJPY

Common rules:
- FxPro M1 2017-2026 YTD
- RM100 start
- 5% current-equity risk
- fixed 3R first-pass target
- causal MTF where applicable
- real SL only
- no BE/protected SL
- one position at a time
- M1 chronological execution
- target WR 70%

Completed transferred / reconstructed engines:
- EMA Ribbon Break
- Donchian-10
- Tick-Volume Momentum
- ADX/DI Rotation
- CASIO NY Precision v1
- NY Open60 Precision
- BBMA Reentry
- ICT pre-NY sweep/MSS
- Silver Bullet 10-11
- London/Asia sweep/MSS
- PDH/PDL sweep/MSS
- Bermula Accurate-Fast
- Pure S&D First Retest
- Naked S/R Reversal
- FiboRSI8 20/80
- FiboRSI8 23/77 + HTF32.5/67.5

Current headline:
- No strategy/pair is near 70% WR.
- Highest WR overall: GBPJPY NY_OPEN60_PRECISION, 36 trades, 33.33% WR (too sparse).
- Highest WR with >=50 trades: GBPJPY ICT_PRENY_SWEEP_MSS, 59 trades, 30.51% WR (too sparse and negative after cost).
- Highest WR with >=500 trades: EURUSD FIBORSI8_23_77_HTF32.5, 2,947 trades, 30.74% WR.
- Best broad engines mostly cluster around 24-31% WR at 3R.

Examples:
- EURUSD FIBORSI8_23_77_HTF32.5: 2,947 trades, 30.74% WR, 25.2 trades/month, min month 14.
- GBPJPY FIBORSI8_23_77_HTF32.5: 2,753 trades, 28.77% WR.
- GBPUSD FIBORSI8_20_80: 1,784 trades, 28.08% WR.
- GBPUSD BBMA_REENTRY: 1,534 trades, 26.60% WR.
- GBPUSD BERMULA_ACCURATE_FAST translation: 1,522 trades, 25.95% WR.
- GBPJPY Tick-Volume Momentum: 2,930 trades, 26.25% WR.
- S&D / Naked S/R broad structural sleeves are ~25% WR.

Interpretation:
Simple transfer from XAUUSD to these FX pairs does not produce the requested 70% WR at 3R. The next valid research stage is a bounded high-precision deep-retracement / MTF confirmation search designed specifically for FX; tiny-sample >70% variants will not be accepted.
