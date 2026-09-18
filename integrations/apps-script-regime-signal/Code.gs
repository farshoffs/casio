const CASIO_SHEET_NAME = 'Signals';
const CASIO_ENGINE = 'RR10';
const CASIO_SCHEMA = 'casio.regime-router.rr10';

function doPost(e) {
  try {
    const body = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    validateRelaySecret_(body);
    const signal = normalizeSignal_(body);

    const sheet = getSignalSheet_();
    ensureHeader_(sheet);
    sheet.appendRow([
      new Date(),
      signal.received_at,
      signal.source,
      signal.symbol,
      signal.timeframe,
      signal.action,
      signal.technique,
      signal.router_mode,
      signal.entry_estimate,
      signal.stop,
      signal.target_estimate,
      signal.target_r,
      signal.risk_pct,
      signal.h1_bias,
      signal.h4_bias,
      signal.h4_adx,
      signal.bar_time,
    ]);

    PropertiesService.getScriptProperties().setProperty('LATEST_SIGNAL', JSON.stringify(signal));
    sendEmailIfConfigured_(signal);
    return json_({ ok: true, stored: true, engine: CASIO_ENGINE, signal: signal });
  } catch (err) {
    return json_({ ok: false, engine: CASIO_ENGINE, error: String(err && err.message ? err.message : err) });
  }
}

function doGet() {
  const raw = PropertiesService.getScriptProperties().getProperty('LATEST_SIGNAL');
  return json_({
    ok: true,
    service: 'casio-regime-router-email',
    engine: CASIO_ENGINE,
    schema: CASIO_SCHEMA,
    latest: raw ? JSON.parse(raw) : null,
    now: new Date().toISOString(),
  });
}

function validateRelaySecret_(body) {
  const expected = PropertiesService.getScriptProperties().getProperty('RELAY_SECRET') || '';
  if (!expected) return;
  const supplied = String(body.relay_secret || body.secret || '');
  if (supplied !== expected) throw new Error('invalid_relay_secret');
}

function normalizeSignal_(body) {
  const engine = String(body.engine || (body.schema === CASIO_SCHEMA ? CASIO_ENGINE : '')).toUpperCase();
  const schema = String(body.schema || '');
  if (engine !== CASIO_ENGINE || (schema && schema !== CASIO_SCHEMA)) {
    throw new Error('non_canonical_engine');
  }

  const symbol = String(body.symbol || body.ticker || '');
  if (!symbol) throw new Error('missing_symbol');

  const rawDirection = String(body.direction || body.action || '').toUpperCase();
  const action = rawDirection === 'LONG' ? 'LONG' : rawDirection === 'SHORT' ? 'SHORT' : '';
  if (!action) throw new Error('invalid_direction');

  const entry = numberOrBlank_(body.entry !== undefined ? body.entry : body.entry_estimate);
  const stop = numberOrBlank_(body.stop);
  const target = numberOrBlank_(body.target !== undefined ? body.target : body.target_estimate);
  const rr = numberOrBlank_(body.rr !== undefined ? body.rr : body.target_r);
  if (entry === '' || stop === '' || target === '' || rr === '') throw new Error('missing_trade_levels');

  return {
    engine: CASIO_ENGINE,
    schema: CASIO_SCHEMA,
    signal_id: String(body.signal_id || ''),
    received_at: String(body.received_at || new Date().toISOString()),
    source: String(body.source || 'rr10-canonical'),
    symbol: symbol,
    timeframe: String(body.timeframe || '15'),
    action: action,
    direction: action.toLowerCase(),
    technique: 'RR10 Canonical',
    router_mode: String(body.router_mode || ''),
    entry_estimate: entry,
    stop: stop,
    target_estimate: target,
    target_r: rr,
    risk_pct: numberOrDefault_(body.risk_pct, 5),
    h1_bias: numberOrBlank_(body.h1_bias),
    h4_bias: numberOrBlank_(body.h4_bias),
    h4_adx: numberOrBlank_(body.h4_adx),
    bar_time: timeOrBlank_(body.bar_time !== undefined ? body.bar_time :
      body.signal_time !== undefined ? body.signal_time :
      body.entry_time_utc || body.signal_bar_open_utc || ''),
  };
}

function getSignalSheet_() {
  const props = PropertiesService.getScriptProperties();
  const id = props.getProperty('SPREADSHEET_ID');
  if (!id) throw new Error('SPREADSHEET_ID_not_configured');
  const ss = SpreadsheetApp.openById(id);
  let sheet = ss.getSheetByName(CASIO_SHEET_NAME);
  if (!sheet) sheet = ss.insertSheet(CASIO_SHEET_NAME);
  return sheet;
}

function ensureHeader_(sheet) {
  if (sheet.getLastRow() > 0) return;
  sheet.appendRow([
    'stored_at', 'received_at', 'source', 'symbol', 'timeframe', 'action',
    'technique', 'router_mode', 'entry_estimate', 'stop', 'target_estimate',
    'target_r', 'risk_pct', 'h1_bias', 'h4_bias', 'h4_adx', 'bar_time'
  ]);
  sheet.setFrozenRows(1);
}

function sendEmailIfConfigured_(signal) {
  const email = PropertiesService.getScriptProperties().getProperty('NOTIFY_EMAIL') || '';
  if (!email) return;

  const subject = '[CASIO RR10] ' + signal.action + ' ' + signal.symbol;
  const body = [
    'CASIO RR10 canonical Regime Router signal',
    '',
    'Engine: ' + signal.engine,
    'Action: ' + signal.action,
    'Symbol: ' + signal.symbol,
    'Timeframe: ' + signal.timeframe,
    'Technique: ' + signal.technique,
    'Router mode: ' + signal.router_mode,
    'Entry: ' + signal.entry_estimate,
    'Stop: ' + signal.stop,
    'Target: ' + signal.target_estimate,
    'Target R: ' + signal.target_r,
    'Risk %: ' + signal.risk_pct,
    'H1 bias: ' + signal.h1_bias,
    'H4 bias: ' + signal.h4_bias,
    'H4 ADX: ' + signal.h4_adx,
    '',
    'Signal time: ' + signal.bar_time,
    'Received: ' + signal.received_at,
  ].join('\n');

  MailApp.sendEmail(email, subject, body);
}

function numberOrBlank_(value) {
  if (value === undefined || value === null || value === '') return '';
  const n = Number(value);
  return isFinite(n) ? n : '';
}

function numberOrDefault_(value, fallback) {
  const n = numberOrBlank_(value);
  return n === '' ? fallback : n;
}

function timeOrBlank_(value) {
  if (value === undefined || value === null || value === '') return '';
  const n = Number(value);
  if (isFinite(n)) return n;
  return String(value);
}

function json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
