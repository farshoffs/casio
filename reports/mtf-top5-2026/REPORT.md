# CASIO Top Five M15 -> H1 -> H4 MTF Test — 2026

## Test rule

- Dukascopy 2026 only, through the latest available bar.
- Start **RM100** independently for each strategy/variant.
- Risk **5% of current balance** per filled trade.
- Require **at least 8 filled trades in every completed month**.
- Same **1 bp round-trip cost** and stop-first same-bar handling.
- M15 still creates the setup. Only completed H1/H4 candles may influence the decision.
- A trade is blocked only when **both H1 and H4 oppose** its direction.
- Target is graded **2R / 3R / 4R** from original M15 setup quality plus H1/H4 alignment.

## Side-by-side result

| strategy                 |   m15_end_rm |   mtf_end_rm |   delta_rm |   m15_trades |   mtf_trades |   m15_min_month |   mtf_min_month |   mtf_lowest_rm | mtf_frequency_pass   | mtf_growth_pass   | mtf_requested_fit   |
|:-------------------------|-------------:|-------------:|-----------:|-------------:|-------------:|----------------:|----------------:|----------------:|:---------------------|:------------------|:--------------------|
| M15-0591                 |      190.166 |      419.753 |   229.587  |          263 |          238 |              21 |              21 |         42.175  | True                 | True              | True                |
| V1 Legacy M15            |      345.8   |      304.202 |   -41.5979 |          321 |          301 |              31 |              31 |         63.0696 | True                 | True              | True                |
| Structural Portfolio M15 |      199.602 |      258.153 |    58.5503 |          125 |          124 |              11 |              10 |         92.6531 | True                 | True              | True                |
| Structural Frequency M15 |      237.784 |      192.892 |   -44.8914 |          113 |          113 |               8 |               8 |         93.3058 | True                 | True              | True                |
| Outcome First M15        |      419.596 |      152.652 |  -266.944  |          121 |          107 |              10 |              10 |         66.8097 | True                 | True              | True                |

## Interpretation rule

MTF is useful only if it improves the RM100 path without breaking the >=8-trades-per-completed-month requirement. This test does not retune the original M15 entry rules.
