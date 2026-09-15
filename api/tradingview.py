from __future__ import annotations

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

SCHEMA = "casio.tv.v1"
REQUIRED_FIELDS = {
    "schema",
    "event",
    "symbol",
    "ticker",
    "timeframe",
    "bar_time",
    "mode",
    "direction",
    "score",
    "entry",
    "stop",
    "target",
    "rr",
}


def _normalize(payload: dict) -> dict:
    missing = sorted(REQUIRED_FIELDS - payload.keys())
    if missing:
        raise ValueError(f"missing fields: {', '.join(missing)}")
    if payload.get("schema") != SCHEMA:
        raise ValueError("unsupported schema")
    if payload.get("event") != "signal":
        raise ValueError("unsupported event")
    if payload.get("mode") not in {"intraday", "scalping"}:
        raise ValueError("invalid mode")
    if payload.get("direction") not in {"long", "short"}:
        raise ValueError("invalid direction")

    ticker = str(payload.get("ticker", "")).upper()
    if ticker != "XAUUSD" and "XAUUSD" not in str(payload.get("symbol", "")).upper():
        raise ValueError("CASIO webhook currently accepts XAUUSD only")

    return {
        "schema": SCHEMA,
        "event": "signal",
        "symbol": str(payload["symbol"]),
        "ticker": ticker,
        "timeframe": str(payload["timeframe"]),
        "bar_time": int(payload["bar_time"]),
        "mode": payload["mode"],
        "direction": payload["direction"],
        "score": int(payload["score"]),
        "entry": float(payload["entry"]),
        "stop": float(payload["stop"]),
        "target": float(payload["target"]),
        "rr": float(payload["rr"]),
        "adx": float(payload["adx"]) if payload.get("adx") is not None else None,
        "atr": float(payload["atr"]) if payload.get("atr") is not None else None,
    }


class handler(BaseHTTPRequestHandler):
    def _json(self, status: int, body: dict) -> None:
        raw = json.dumps(body, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        self._json(200, {"ok": True, "service": "casio-tradingview", "schema": SCHEMA})

    def do_POST(self) -> None:
        expected_token = os.environ.get("CASIO_WEBHOOK_TOKEN", "")
        if not expected_token:
            self._json(503, {"ok": False, "error": "CASIO_WEBHOOK_TOKEN is not configured"})
            return

        parsed = urlparse(self.path)
        supplied_token = parse_qs(parsed.query).get("token", [""])[0]
        # x-casio-token is supported for manual tests; TradingView should use ?token= in the URL.
        supplied_token = supplied_token or self.headers.get("x-casio-token", "")
        if not supplied_token or not hmac.compare_digest(supplied_token, expected_token):
            self._json(401, {"ok": False, "error": "unauthorized"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(400, {"ok": False, "error": "invalid content length"})
            return

        if content_length <= 0 or content_length > 65536:
            self._json(413, {"ok": False, "error": "invalid payload size"})
            return

        try:
            raw = self.rfile.read(content_length)
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON body must be an object")
            signal = _normalize(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
            self._json(400, {"ok": False, "error": str(exc)})
            return

        # Fast acknowledgement is intentional: TradingView cancels slow webhook requests.
        # Vercel runtime logs provide the first live signal sink. Persistent storage/dashboard
        # can subscribe to this normalized event in the next CASIO layer.
        print("CASIO_SIGNAL " + json.dumps(signal, separators=(",", ":"), sort_keys=True))
        self._json(
            202,
            {
                "ok": True,
                "accepted": True,
                "schema": SCHEMA,
                "mode": signal["mode"],
                "direction": signal["direction"],
                "bar_time": signal["bar_time"],
            },
        )
