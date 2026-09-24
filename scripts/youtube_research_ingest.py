#!/usr/bin/env python3
"""Fetch public YouTube captions for research and emit bounded rule-relevant excerpts.

Raw transcripts are NOT committed. Output is intentionally limited to context windows
around trading vocabulary so the research branch stores evidence snippets rather than
wholesale copyrighted transcripts.
"""
from __future__ import annotations
import json, pathlib, re, sys, time, urllib.parse, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/research/youtube-playlist-technique/source_manifest.json"
OUT = ROOT / ".research_artifacts/youtube_rule_excerpts"
OUT.mkdir(parents=True, exist_ok=True)

KEYWORDS = [
    "entry","enter","buy","sell","long","short","stop loss","stoploss","sl","take profit","target","tp",
    "risk","reward","rr","r:r","timeframe","time frame","multi timeframe","mtf","trend","bias","structure",
    "break of structure","bos","choch","support","resistance","zone","supply","demand","liquidity","sweep",
    "breakout","retest","pullback","retracement","fibonacci","fib","rsi","moving average","ema","sma",
    "candle","candlestick","wick","engulf","momentum","session","london","new york","asia","news",
    "confirmation","confluence","invalid","setup","signal","level","high","low"
]
RX = re.compile("|".join(re.escape(x) for x in sorted(KEYWORDS,key=len,reverse=True)), re.I)

def get(url: str, timeout=35):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 CASIOResearch/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.headers.get("content-type",""), r.read().decode("utf-8","replace")

def fetch(video_id: str):
    # First choice: structured anonymous JSON.
    url = "https://api.freetranscriptapi.com/v1/transcript?" + urllib.parse.urlencode({"video_url":video_id})
    try:
        status, ctype, body = get(url)
        data = json.loads(body)
        if isinstance(data, dict):
            transcript = data.get("transcript")
            if transcript:
                segs=[]
                if isinstance(transcript,list):
                    for s in transcript:
                        if isinstance(s,dict):
                            segs.append({
                                "start": s.get("start") or s.get("offset") or 0,
                                "text": str(s.get("text",""))
                            })
                elif isinstance(transcript,str):
                    segs=[{"start":0,"text":transcript}]
                if segs:
                    return {"provider":"freetranscriptapi","metadata":{k:data.get(k) for k in ("title","language","video_id") if k in data},"segments":segs}
    except Exception as e:
        first_error = repr(e)
    else:
        first_error = "no transcript field"

    # Fallback: timestamped text endpoint.
    url2 = f"https://youtube-transcript.ai/transcript/{video_id}.txt"
    try:
        status, ctype, body = get(url2)
        if body.strip():
            segs=[]
            for line in body.splitlines():
                line=line.strip()
                if not line: continue
                m=re.match(r"^\[?(\d{1,2}):(\d{2})(?::(\d{2}))?\]?\s*(.*)$", line)
                if m:
                    if m.group(3):
                        sec=int(m.group(1))*3600+int(m.group(2))*60+int(m.group(3))
                    else:
                        sec=int(m.group(1))*60+int(m.group(2))
                    text=m.group(4)
                else:
                    sec=0; text=line
                segs.append({"start":sec,"text":text})
            return {"provider":"youtube-transcript.ai","metadata":{},"segments":segs}
    except Exception as e:
        return {"error": f"primary={first_error}; fallback={repr(e)}"}
    return {"error": f"primary={first_error}; fallback empty"}

def fmt_time(v):
    try: s=float(v)
    except: s=0
    h=int(s//3600); m=int((s%3600)//60); sec=int(s%60)
    return f"{h:02d}:{m:02d}:{sec:02d}"

def excerpts(result):
    segs=result.get("segments",[])
    hits=[]
    seen=set()
    for i,s in enumerate(segs):
        txt=s.get("text","")
        if not RX.search(txt):
            continue
        lo=max(0,i-1); hi=min(len(segs),i+2)
        chunk=" ".join(str(segs[j].get("text","")).strip() for j in range(lo,hi)).strip()
        key=re.sub(r"\s+"," ",chunk.lower())[:180]
        if not chunk or key in seen: continue
        seen.add(key)
        hits.append((s.get("start",0),chunk))
        if len(hits)>=120: break
    return hits

def main():
    manifest=json.loads(MANIFEST.read_text())
    summary=[]
    for v in manifest["videos"]:
        vid=v["video_id"]; idx=v["index"]
        print(f"Fetching {idx:02d} {vid}", flush=True)
        result=fetch(vid)
        row={"index":idx,"video_id":vid,"provider":result.get("provider"),"error":result.get("error")}
        if "error" not in result:
            hits=excerpts(result)
            row["segment_count"]=len(result.get("segments",[])); row["excerpt_count"]=len(hits); row["metadata"]=result.get("metadata",{})
            lines=[f"# Video {idx:02d} — {vid}","",f"Provider: {result.get('provider')}",""]
            if result.get("metadata"): lines += ["Metadata: `"+json.dumps(result["metadata"],ensure_ascii=False)+"`",""]
            lines += ["## Rule-relevant evidence excerpts",""]
            for n,(start,text) in enumerate(hits,1):
                # cap each excerpt to avoid wholesale reproduction
                text=re.sub(r"\s+"," ",text).strip()[:600]
                lines.append(f"{n}. [{fmt_time(start)}] {text}")
            (OUT/f"{idx:02d}_{vid}.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
        summary.append(row)
        time.sleep(0.7)
    (OUT/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2,ensure_ascii=False))

if __name__=="__main__":
    sys.exit(main())
