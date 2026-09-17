export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');

  if (req.method === 'OPTIONS') return res.status(204).end();

  if (req.method === 'GET') {
    return res.status(200).json({
      ok: true,
      service: 'casio-regime-router-signal',
      now: new Date().toISOString(),
    });
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ ok: false, error: 'method_not_allowed' });
  }

  const body = typeof req.body === 'string' ? safeJson(req.body) : (req.body || {});
  if (!body || typeof body !== 'object') {
    return res.status(400).json({ ok: false, error: 'invalid_json' });
  }

  const expectedSecret = process.env.SIGNAL_SECRET || '';
  if (expectedSecret && String(body.secret || '') !== expectedSecret) {
    return res.status(401).json({ ok: false, error: 'invalid_secret' });
  }

  const required = ['source', 'symbol', 'action', 'technique', 'bar_time'];
  const missing = required.filter((key) => body[key] === undefined || body[key] === null || body[key] === '');
  if (missing.length) {
    return res.status(400).json({ ok: false, error: 'missing_fields', missing });
  }

  const normalized = {
    received_at: new Date().toISOString(),
    source: String(body.source),
    symbol: String(body.symbol),
    timeframe: String(body.timeframe || ''),
    action: String(body.action).toUpperCase(),
    technique: String(body.technique),
    router_mode: String(body.router_mode || ''),
    entry_estimate: toNumber(body.entry_estimate),
    stop: toNumber(body.stop),
    target_estimate: toNumber(body.target_estimate),
    target_r: toNumber(body.target_r),
    risk_pct: toNumber(body.risk_pct),
    h1_bias: toNumber(body.h1_bias),
    h4_bias: toNumber(body.h4_bias),
    h4_adx: toNumber(body.h4_adx),
    bar_time: toNumber(body.bar_time),
  };

  if (!['LONG', 'SHORT'].includes(normalized.action)) {
    return res.status(400).json({ ok: false, error: 'invalid_action' });
  }

  // Keep the secret out of downstream logs/payloads.
  const appsScriptUrl = process.env.APPS_SCRIPT_WEBHOOK_URL || '';
  let downstream = { configured: Boolean(appsScriptUrl), delivered: false };

  if (appsScriptUrl) {
    try {
      const response = await fetch(appsScriptUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...normalized,
          relay_secret: process.env.APPS_SCRIPT_RELAY_SECRET || '',
        }),
      });
      const text = await response.text();
      downstream = {
        configured: true,
        delivered: response.ok,
        status: response.status,
        response: text.slice(0, 500),
      };
    } catch (error) {
      downstream = {
        configured: true,
        delivered: false,
        error: String(error && error.message ? error.message : error),
      };
    }
  }

  console.log(JSON.stringify({ event: 'casio_signal', signal: normalized, downstream }));

  // Return 200 after validation even when Apps Script is temporarily unavailable.
  // TradingView does not provide a durable webhook retry queue; the Vercel logs preserve the event.
  return res.status(200).json({
    ok: true,
    accepted: true,
    signal: normalized,
    downstream,
  });
}

function safeJson(value) {
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function toNumber(value) {
  if (value === undefined || value === null || value === '') return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}
