import handler from './api/signal.js';

function mockRes() {
  return {
    statusCode: 200,
    headers: {},
    body: null,
    setHeader(k, v) { this.headers[k] = v; },
    status(code) { this.statusCode = code; return this; },
    json(value) { this.body = value; return this; },
    end() { return this; },
  };
}

async function run() {
  delete process.env.SIGNAL_SECRET;
  delete process.env.APPS_SCRIPT_WEBHOOK_URL;

  const okRes = mockRes();
  await handler({
    method: 'POST',
    body: {
      source: 'CASIO_REGIME_ROUTER_V1',
      symbol: 'XAUUSD',
      timeframe: '15',
      action: 'LONG',
      technique: 'M15-0591 MTF',
      router_mode: 'TREND',
      entry_estimate: 2500,
      stop: 2490,
      target_estimate: 2530,
      target_r: 3,
      risk_pct: 5,
      h1_bias: 1,
      h4_bias: 1,
      h4_adx: 25,
      bar_time: 1760000000000,
    },
  }, okRes);
  if (okRes.statusCode !== 200 || !okRes.body?.accepted) {
    throw new Error(`valid signal failed: ${JSON.stringify(okRes)}`);
  }

  const badRes = mockRes();
  await handler({
    method: 'POST',
    body: {
      source: 'CASIO_REGIME_ROUTER_V1',
      symbol: 'XAUUSD',
      action: 'WAIT',
      technique: 'test',
      bar_time: 1,
    },
  }, badRes);
  if (badRes.statusCode !== 400) {
    throw new Error(`invalid action was not rejected: ${JSON.stringify(badRes)}`);
  }

  const healthRes = mockRes();
  await handler({ method: 'GET' }, healthRes);
  if (healthRes.statusCode !== 200 || healthRes.body?.service !== 'casio-regime-router-signal') {
    throw new Error(`health check failed: ${JSON.stringify(healthRes)}`);
  }

  console.log('CASIO Vercel signal webhook smoke test passed.');
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
