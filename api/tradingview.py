from __future__ import annotations

import hashlib
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

SUPPORTED_SCHEMAS = {"casio.tv.v1", "casio.tv.v2"}
# Safe to keep in source: this is only a one-way hash of the TradingView -> Vercel token.
DEFAULT_TOKEN_SHA256 = "59de3b12b3bf168eba0a5a4b10f84b9fc79165bcf218949fc134aaa458f563f9"

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


def _optional_float(payload: dict, key: str):
    value = payload.get(key)
    return float(value) if value is not None else None


def _normalize(payload: dict) -> dict:
    missing = sorted(REQUIRED_FIELDS - payload.keys())
    if missing:
        raise ValueError(f"missing fields: {', '.join(missing)}")

    schema = str(payload.get("schema", ""))
    if schema not in SUPPORTED_SCHEMAS:
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

    signal = {
        "schema": schema,
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
    }

    if schema == "casio.tv.v2":
        signal.update(
            {
                "regime": str(payload.get("regime", "")),
                "session": str(payload.get("session", "")),
                "h4_bias": str(payload.get("h4_bias", "")),
                "h1_bias": str(payload.get("h1_bias", "")),
                "m15_adx": _optional_float(payload, "m15_adx"),
                "win_rate": _optional_float(payload, "win_rate"),
                "expectancy_r": _optional_float(payload, "expectancy_r"),
                "profit_factor": _optional_float(payload, "profit_factor"),
                "audit_status": str(payload.get("audit_status", "")),
            }
        )
    else:
        signal.update(
            {
                "adx": _optional_float(payload, "adx"),
                "atr": _optional_float(payload, "atr"),
            }
        )
    return signal


def _authorized(supplied_token: str) -> bool:
    expected_token = os.environ.get("CASIO_WEBHOOK_TOKEN", "")
    if expected_token:
        return bool(supplied_token) and hmac.compare_digest(supplied_token, expected_token)

    expected_hash = os.environ.get("CASIO_WEBHOOK_TOKEN_SHA256", DEFAULT_TOKEN_SHA256)
    if not expected_hash or not supplied_token:
        return False
    supplied_hash = hashlib.sha256(supplied_token.encode("utf-8")).hexdigest()
    return hmac.compare_digest(supplied_hash, expected_hash)


def _gas_url() -> str:
    base = os.environ.get("CASIO_GAS_WEBAPP_URL", "").strip()
    token = os.environ.get("CASIO_GAS_TOKEN", "").strip()
    if not base or not token:
        return ""

    parsed = urlparse(base)
    query = parse_qs(parsed.query)
    query["token"] = [token]
    flat = []
    for key, values in query.items():
        for value in values:
            flat.append((key, value))
    return urlunparse(parsed._replace(query=urlencode(flat)))


def _relay_to_apps_script(signal: dict) -> tuple[bool, str]:
    url = _gas_url()
    if not url:
        return True, "not_configured"
    if signal.get("schema") != "casio.tv.v2":
        return True, "v1_not_relayed"

    raw = json.dumps(signal, separators=(",", ":")).encode("utf-8")
    request = Request(
        url,
        data=raw,
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "CASIO-Vercel/2"},
        method="POST",
    )
    try:
        # Apps Script queues email before returning. Keep this under TradingView's 3s ceiling.
        with urlopen(request, timeout=1.8) as response:
            return 200 <= response.status < 400, f"http_{response.status}"
    except HTTPError as exc:
        # Apps Script ContentService can respond with redirects; doPost has already executed.
        if 300 <= exc.code < 400:
            return True, f"http_{exc.code}"
        return False, f"http_{exc.code}"
    except (URLError, TimeoutError) as exc:
        return False, f"relay_error:{type(exc).__name__}"


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
        self._json(
            200,
            {
                "ok": True,
                "service": "casio-tradingview",
                "schemas": sorted(SUPPORTED_SCHEMAS),
                "email_relay_configured": bool(_gas_url()),
            },
        )

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        supplied_token = parse_qs(parsed.query).get("token", [""])[0]
        supplied_token = supplied_token or self.headers.get("x-casio-token", "")
        if not _authorized(supplied_token):
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

        print("CASIO_SIGNAL " + json.dumps(signal, separators=(",", ":"), sort_keys=True))

        relay_ok, relay_status = _relay_to_apps_script(signal)
        if not relay_ok:
            # TradingView can retry a 5xx webhook; this keeps email delivery recoverable.
            print("CASIO_EMAIL_RELAY_FAILED " + relay_status)
            self._json(503, {"ok": False, "accepted": True, "email_relay": relay_status})
            return

        self._json(
            202,
            {
                "ok": True,
                "accepted": True,
                "schema": signal["schema"],
                "mode": signal["mode"],
                "direction": signal["direction"],
                "bar_time": signal["bar_time"],
                "email_relay": relay_status,
            },
        )
