from __future__ import annotations

import hashlib
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

SIGNAL_SCHEMAS = {"casio.tv.v1", "casio.tv.v2", "casio.tv.v3"}
MARKET_SCHEMAS = {"casio.market.v1"}
SUPPORTED_SCHEMAS = SIGNAL_SCHEMAS | MARKET_SCHEMAS

# Safe to keep in source: this is only a one-way hash of the TradingView -> Vercel token.
DEFAULT_TOKEN_SHA256 = "59de3b12b3bf168eba0a5a4b10f84b9fc79165bcf218949fc134aaa458f563f9"

SIGNAL_REQUIRED_FIELDS = {
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

BAR_REQUIRED_FIELDS = {
    "schema",
    "event",
    "symbol",
    "ticker",
    "timeframe",
    "bar_time",
    "open",
    "high",
    "low",
    "close",
}


def _optional_float(payload: dict, key: str):
    value = payload.get(key)
    return float(value) if value is not None else None


def _validate_xauusd(payload: dict) -> str:
    ticker = str(payload.get("ticker", "")).upper()
    symbol = str(payload.get("symbol", "")).upper()
    if ticker != "XAUUSD" and "XAUUSD" not in symbol:
        raise ValueError("CASIO webhook currently accepts XAUUSD only")
    return ticker or "XAUUSD"


def _normalize_signal(payload: dict) -> dict:
    missing = sorted(SIGNAL_REQUIRED_FIELDS - payload.keys())
    if missing:
        raise ValueError(f"missing fields: {', '.join(missing)}")

    schema = str(payload.get("schema", ""))
    if schema not in SIGNAL_SCHEMAS:
        raise ValueError("unsupported signal schema")
    if payload.get("event") != "signal":
        raise ValueError("unsupported signal event")
    if payload.get("mode") not in {"intraday", "scalping"}:
        raise ValueError("invalid mode")
    if payload.get("direction") not in {"long", "short"}:
        raise ValueError("invalid direction")

    ticker = _validate_xauusd(payload)
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

    if schema in {"casio.tv.v2", "casio.tv.v3"}:
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


def _normalize_bar(payload: dict) -> dict:
    missing = sorted(BAR_REQUIRED_FIELDS - payload.keys())
    if missing:
        raise ValueError(f"missing fields: {', '.join(missing)}")

    schema = str(payload.get("schema", ""))
    if schema not in MARKET_SCHEMAS:
        raise ValueError("unsupported market-data schema")
    if payload.get("event") != "bar":
        raise ValueError("unsupported market-data event")

    timeframe = str(payload.get("timeframe", ""))
    if timeframe not in {"5", "5m", "5M"}:
        raise ValueError("CASIO market collector currently accepts M5 bars only")

    ticker = _validate_xauusd(payload)
    bar = {
        "schema": schema,
        "event": "bar",
        "symbol": str(payload["symbol"]),
        "ticker": ticker,
        "timeframe": "5",
        "bar_time": int(payload["bar_time"]),
        "open": float(payload["open"]),
        "high": float(payload["high"]),
        "low": float(payload["low"]),
        "close": float(payload["close"]),
        "volume": float(payload.get("volume") or 0.0),
    }
    if bar["high"] < max(bar["open"], bar["close"], bar["low"]):
        raise ValueError("invalid OHLC bar: high is inconsistent")
    if bar["low"] > min(bar["open"], bar["close"], bar["high"]):
        raise ValueError("invalid OHLC bar: low is inconsistent")
    return bar


def _normalize(payload: dict) -> dict:
    event = payload.get("event")
    if event == "signal":
        return _normalize_signal(payload)
    if event == "bar":
        return _normalize_bar(payload)
    raise ValueError("unsupported event")


def _authorized(supplied_token: str) -> bool:
    expected_token = os.environ.get("CASIO_WEBHOOK_TOKEN", "")
    if expected_token:
        return bool(supplied_token) and hmac.compare_digest(supplied_token, expected_token)

    expected_hash = os.environ.get("CASIO_WEBHOOK_TOKEN_SHA256", DEFAULT_TOKEN_SHA256)
    if not expected_hash or not supplied_token:
        return False
    supplied_hash = hashlib.sha256(supplied_token.encode("utf-8")).hexdigest()
    return hmac.compare_digest(supplied_hash, expected_hash)


def _gas_url(extra_query: dict[str, str] | None = None) -> str:
    base = os.environ.get("CASIO_GAS_WEBAPP_URL", "").strip()
    token = os.environ.get("CASIO_GAS_TOKEN", "").strip()
    if not base or not token:
        return ""

    parsed = urlparse(base)
    query = parse_qs(parsed.query)
    query["token"] = [token]
    for key, value in (extra_query or {}).items():
        query[key] = [str(value)]

    flat = []
    for key, values in query.items():
        for value in values:
            flat.append((key, value))
    return urlunparse(parsed._replace(query=urlencode(flat)))


def _relay_to_apps_script(message: dict) -> tuple[bool, str]:
    url = _gas_url()
    if not url:
        return True, "not_configured"

    # v1 is retained for webhook compatibility but the current Apps Script handles v2/v3 signals and market bars.
    if message.get("event") == "signal" and message.get("schema") == "casio.tv.v1":
        return True, "legacy_not_relayed"

    raw = json.dumps(message, separators=(",", ":")).encode("utf-8")
    request = Request(
        url,
        data=raw,
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "CASIO-Vercel/3"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=1.8) as response:
            return 200 <= response.status < 400, f"http_{response.status}"
    except HTTPError as exc:
        if 300 <= exc.code < 400:
            return True, f"http_{exc.code}"
        return False, f"http_{exc.code}"
    except (URLError, TimeoutError) as exc:
        return False, f"relay_error:{type(exc).__name__}"


def _fetch_market_csv() -> tuple[bool, bytes, str]:
    url = _gas_url({"action": "csv"})
    if not url:
        return False, b"", "email_relay_not_configured"
    request = Request(url, headers={"User-Agent": "CASIO-Vercel/3"}, method="GET")
    try:
        with urlopen(request, timeout=12) as response:
            data = response.read(25_000_000)
            if response.status < 200 or response.status >= 400:
                return False, b"", f"http_{response.status}"
            return True, data, f"http_{response.status}"
    except HTTPError as exc:
        return False, b"", f"http_{exc.code}"
    except (URLError, TimeoutError) as exc:
        return False, b"", f"export_error:{type(exc).__name__}"


class handler(BaseHTTPRequestHandler):
    def _json(self, status: int, body: dict) -> None:
        raw = json.dumps(body, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _raw(self, status: int, body: bytes, content_type: str, filename: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        if filename:
            self.send_header("Content-Disposition", f'inline; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if query.get("export", [""])[0].lower() == "m5":
            ok, raw, status = _fetch_market_csv()
            if not ok:
                self._json(503, {"ok": False, "error": status})
                return
            self._raw(200, raw, "text/csv; charset=utf-8", "xauusd_m5.csv")
            return

        self._json(
            200,
            {
                "ok": True,
                "service": "casio-tradingview",
                "schemas": sorted(SUPPORTED_SCHEMAS),
                "email_relay_configured": bool(_gas_url()),
                "market_csv_export": bool(_gas_url()),
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
            message = _normalize(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
            self._json(400, {"ok": False, "error": str(exc)})
            return

        log_prefix = "CASIO_SIGNAL" if message["event"] == "signal" else "CASIO_M5_BAR"
        print(log_prefix + " " + json.dumps(message, separators=(",", ":"), sort_keys=True))

        relay_ok, relay_status = _relay_to_apps_script(message)
        if not relay_ok:
            print("CASIO_APPS_SCRIPT_RELAY_FAILED " + relay_status)
            self._json(503, {"ok": False, "accepted": True, "event": message["event"], "relay": relay_status})
            return

        body = {
            "ok": True,
            "accepted": True,
            "event": message["event"],
            "schema": message["schema"],
            "bar_time": message["bar_time"],
            "relay": relay_status,
        }
        if message["event"] == "signal":
            body.update({"mode": message["mode"], "direction": message["direction"]})
        else:
            body.update({"timeframe": message["timeframe"]})
        self._json(202, body)
