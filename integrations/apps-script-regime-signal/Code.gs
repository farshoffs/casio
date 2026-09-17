const CASIO_SHEET_NAME = 'Signals';

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

    return json_({ ok: true, stored: true, signal: signal });
  } catch (err) {
    return json_({ ok: false, error: String(err && err.message ? err.message : err) });
  }
}

function doGet() {
  const raw = PropertiesService.getScriptProperties().getProperty('LATEST_SIGNAL');
  return json_({
    ok: true,
    latest: raw ? JSON.parse(raw) : null,
    now: new Date().toISOString(),
  });
}

function validateRelaySecret_(body) {
  const props = PropertiesService.getScriptProperties();
  const expected = props.getProperty('RELAY_SECRET') || '';
  if (expected && String(body.relay_secret || '') !== expected) {
    throw new Error('invalid_relay_secret');
  }
}

function normalizeSignal_(body) {
  const required = ['source', 'symbol', 'action', 'technique'];
  required.forEach(function(key) {
    if (body[key] === undefined || body[key] === null || body[key] === '') {
      throw new Error('missing_' + key);
    }
  });

  const action = String(body.action).toUpperCase();
  if (action !== 'LONG' && action !== 'SHORT') throw new Error('invalid_action');

  return {
    received_at: String(body.received_at || new Date().toISOString()),
    source: String(body.source),
    symbol: String(body.symbol),
    timeframe: String(body.timeframe || ''),
    action: action,
    technique: String(body.technique),
    router_mode: String(body.router_mode || ''),
    entry_estimate: numberOrBlank_(body.entry_estimate),
    stop: numberOrBlank_(body.stop),
    target_estimate: numberOrBlank_(body.target_estimate),
    target_r: numberOrBlank_(body.target_r),
    risk_pct: numberOrBlank_(body.risk_pct),
    h1_bias: numberOrBlank_(body.h1_bias),
    h4_bias: numberOrBlank_(body.h4_bias),
    h4_adx: numberOrBlank_(body.h4_adx),
    bar_time: numberOrBlank_(body.bar_time),
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

  const subject = '[CASIO] ' + signal.action + ' ' + signal.symbol + ' · ' + signal.technique;
  const body = [
    'CASIO Regime Router signal',
    '',
    'Action: ' + signal.action,
    'Symbol: ' + signal.symbol,
    'Timeframe: ' + signal.timeframe,
    'Technique: ' + signal.technique,
    'Router mode: ' + signal.router_mode,
    'Entry estimate: ' + signal.entry_estimate,
    'Stop: ' + signal.stop,
    'Target: ' + signal.target_estimate,
    'Target R: ' + signal.target_r,
    'Risk %: ' + signal.risk_pct,
    'H1 bias: ' + signal.h1_bias,
    'H4 bias: ' + signal.h4_bias,
    'H4 ADX: ' + signal.h4_adx,
    '',
    'Received: ' + signal.received_at,
  ].join('\n');

  MailApp.sendEmail(email, subject, body);
}

function numberOrBlank_(value) {
  if (value === undefined || value === null || value === '') return '';
  const n = Number(value);
  return isFinite(n) ? n : '';
}

function json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
