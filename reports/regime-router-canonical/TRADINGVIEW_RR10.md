# RR10 TradingView adapter

Use `pine/CASIO_REGIME_ROUTER_RR10.pine` as the TradingView representation of the canonical RR10 ruleset.

Important: the canonical live decision is RR10 only. The older TradingView Regime Router script should not remain active in parallel because it can produce a different signal stream.

The Pine adapter uses completed H1/H4 bars, a fixed 3R target, and a strict one-active-trade lifecycle. TradingView and FxPro can still differ slightly at marginal conditions because their OHLC feeds are not identical. Exact channel consistency requires all consumers to use the same market-data event source.
