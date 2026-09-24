# RR2 Positive-Month Benchmark v1

Data: FxPro EURUSD / GBPUSD / GBPJPY M1, 2017-2026 YTD.

New gate:
- RR 1:2
- 5% current-equity risk per entry
- >=8 trades/month
- every completed month >0R
- no BE/protected stop

## Best causal benchmark found

Architecture:
- Fibo primary UTC hours 19,21,22,23
- NY MTF precision always eligible
- from day 10 onward, rescue trades are allowed only from pair/hour groups that qualified on 2017-2022 development:
  - Fibo pair/hour PF >=1.40 with >=10 development trades
  - other CASIO technique pair/hour PF >=1.25 with >=10 development trades
- one open position per pair
- stop all new entries for the month once >=8 trades AND cumulative month R >0

Result through completed Aug-2026:
- 1,322 trades
- 43.27% WR
- PF 1.525 at fixed 2R
- +394R
- minimum completed-month trades = 8
- positive completed months = 115/116
- only historical miss: May 2024, 57 trades, 14W/43L, -15R
- 2026 Jan-Aug: every completed month positive
- Sep-2026 partial: +1R

This is **not a final pass** because May 2024 remains negative.

5% continuous compounding is extremely aggressive:
- historical max DD ~76.0%

Research decision:
- this replaces the previous 3R target as the active benchmark;
- do not use BE/protected SL;
- next work should specifically solve the single remaining negative-month regime without tuning against May 2024 alone.
