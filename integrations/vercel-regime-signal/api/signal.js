const ENGINE = 'RR10';
const SCHEMA = 'casio.regime-router.rr10';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');

  if (req.method === 'OPTIONS') return res.status(204).end();

  if (req.method === 'GET') {
    return res.status(200).json({
      ok: true,
      service: 'casio-regime-router-signal',
      engine: ENGINE,
      schema: SCHEMA,
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

  let normalized;
  try {
    normalized = normalizeCanonical(body);
  } catch (error) {
    return res.status(400).json({
      ok: false,
      engine: ENGINE,
      error: String(error && error.message ? error.message : error),
    });
  }

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

  console.log(JSON.stringify({ event: 'casio_rr10_signal', signal: normalized, downstream }));
  return res.status(200).json({
    ok: true,
    accepted: true,
    engine: ENGINE,
    signal: normalized,
    downstream,
  });
}

function normalizeCanonical(body) {
  const engine = String(body.engine || (body.schema === SCHEMA ? ENGINE : '')).toUpperCase();
  const schema = String(body.schema || '');
  if (engine !== ENGINE || (schema && schema !== SCHEMA)) {
    throw new Error('non_canonical_engine');
  }

  const symbol = String(body.symbol || body.ticker || '');
  if (!symbol) throw new Error('missing_symbol');

  const rawDirection = String(body.direction || body.action || '').toUpperCase();
  const action = rawDirection === 'LONG' ? 'LONG' : rawDirection === 'SHORT' ? 'SHORT' : '';
  if (!action) throw new Error('invalid_direction');

  const entry = toNumber(body.entry ?? body.entry_estimate);
  const stop = toNumber(body.stop);
  const target = toNumber(body.target ?? body.target_estimate);
  const rr = toNumber(body.rr ?? body.target_r);
  if ([entry, stop, target, rr].some((v) => v === null)) {
    throw new Error('missing_trade_levels');
  }

  return {
    schema: SCHEMA,
    event: 'signal',
    engine: ENGINE,
    signal_id: String(body.signal_id || ''),
    received_at: new Date().toISOString(),
    source: String(body.source || 'rr10-canonical'),
    symbol,
    timeframe: String(body.timeframe || '15'),
    direction: action.toLowerCase(),
    action,
    technique: 'RR10 Canonical',
    router_mode: String(body.router_mode || ''),
    entry,
    entry_estimate: entry,
    stop,
    target,
    target_estimate: target,
    rr,
    target_r: rr,
    risk_pct: toNumber(body.risk_pct) ?? 5,
    h1_bias: toNumber(body.h1_bias),
    h4_bias: toNumber(body.h4_bias),
    h4_adx: toNumber(body.h4_adx),
    support: toNumber(body.support),
    align_count: toNumber(body.align_count),
    signal_time: body.signal_time ?? body.bar_time ?? body.entry_time_utc ?? body.signal_bar_open_utc ?? null,
    bar_time: body.bar_time ?? body.signal_time ?? body.entry_time_utc ?? body.signal_bar_open_utc ?? null,
  };
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
