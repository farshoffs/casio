# CASIO Strategy Documentation

The current product is **CASIO v3**.

Its current trading logic is:

```text
v2 regime-first MTF core
+
v3 adaptive 24h session overlay
```

The up-to-date strategy explanation is:

```text
docs/STRATEGY_V3.md
```

Read [`STRATEGY_V3.md`](STRATEGY_V3.md) for:

- H4/H1/M15/M5 responsibilities,
- AUTO regime selection,
- Asia/London/New York/Transition playbooks,
- Intraday and Scalping rules,
- vetoes versus scoring,
- session-specific score/R:R requirements,
- stop/target construction,
- current proxies and limitations,
- the research questions tested by the v3 Python engine.

For automated research methodology and per-session outputs, see [`RESEARCH_V3.md`](RESEARCH_V3.md).

This file is retained as a compatibility pointer so old links do not break.
