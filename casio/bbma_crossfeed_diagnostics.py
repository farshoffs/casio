from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np

from casio.bbma_cleaner_robustness import FEEDS, load_feed, _features, _ohlc, _align
from casio.bbma_crossfeed_grid import prepare_base, signals, VARIANTS

OUT = Path("reports/bbma-crossfeed-diagnostics")
OUT.mkdir(parents=True, exist_ok=True)


def event_counts(feed: str, raw: pd.DataFrame) -> list[dict]:
    rows = []
    for tf, frame in [
        ("M5", _features(raw)),
        ("M15", _features(_ohlc(raw, "15min"))),
        ("H1", _features(_ohlc(raw, "1h"))),
        ("H4", _features(_ohlc(raw, "4h"))),
    ]:
        start = max(pd.Timestamp("2017-01-01", tz="UTC"), frame.index.min())
        z = frame[frame.index >= start]
        span_months = max(1.0, (z.index.max() - z.index.min()).total_seconds() / (365.25/12*86400)) if len(z) else 1.0
        rows.append({
            "feed": feed, "tf": tf,
            "start": z.index.min().isoformat() if len(z) else None,
            "end": z.index.max().isoformat() if len(z) else None,
            "bars": len(z),
            "csm_buy": int(z["csm_b"].sum()),
            "csm_sell": int(z["csm_s"].sum()),
            "re_buy": int(z["re_b"].sum()),
            "re_sell": int(z["re_s"].sum()),
            "m5_re_per_month": float((z["re_b"].sum()+z["re_s"].sum())/span_months) if tf=="M5" else np.nan,
        })
    return rows


def signal_diagnostics(feed: str, f: pd.DataFrame) -> list[dict]:
    rows = []
    for spec in VARIANTS:
        lb, sb = signals(f, spec)
        sig = lb | sb
        idx = np.flatnonzero(sig.to_numpy())
        if len(idx) == 0:
            rows.append({"feed":feed,"variant":spec[0],"raw_signals":0,"raw_per_month":0.0})
            continue
        rr = []
        for i in idx:
            if lb.iloc[i]:
                risk = f["close"].iloc[i] - f["long_stop"].iloc[i]
            else:
                risk = f["short_stop"].iloc[i] - f["close"].iloc[i]
            a = f["atr"].iloc[i]
            if a > 0 and risk > 0:
                rr.append(risk/a)
        s = pd.Series(rr, dtype=float)
        start, end = f.index[idx[0]], f.index[idx[-1]]
        span_months = max(1.0,(end-start).total_seconds()/(365.25/12*86400))
        rows.append({
            "feed":feed,"variant":spec[0],"raw_signals":len(idx),"raw_per_month":len(idx)/span_months,
            "riskatr_median":float(s.median()) if len(s) else np.nan,
            "riskatr_p10":float(s.quantile(.10)) if len(s) else np.nan,
            "riskatr_p90":float(s.quantile(.90)) if len(s) else np.nan,
            "pct_riskatr_0_5_4":float(s.between(.5,4).mean()*100) if len(s) else 0.0,
            "pct_riskatr_1_2":float(s.between(1,2).mean()*100) if len(s) else 0.0,
        })
    return rows


def main():
    erows, srows = [], []
    for feed,path in FEEDS.items():
        raw=load_feed(path)
        erows.extend(event_counts(feed,raw))
        f=prepare_base(raw)
        srows.extend(signal_diagnostics(feed,f))
    ev=pd.DataFrame(erows); sg=pd.DataFrame(srows)
    ev.to_csv(OUT/"event_counts.csv",index=False)
    sg.to_csv(OUT/"signal_diagnostics.csv",index=False)
    print("# EVENT COUNTS")
    print(ev.to_string(index=False))
    print("\n# SIGNAL DIAGNOSTICS")
    print(sg.to_string(index=False))


if __name__=="__main__":
    main()
