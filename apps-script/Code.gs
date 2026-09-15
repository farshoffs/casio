const CASIO_SCHEMA = 'casio.tv.v2';
const DEFAULT_EMAIL = 'farhanshoffi@moe.gov.my';

function setupCasio() {
  const props = PropertiesService.getScriptProperties();
  if (!props.getProperty('CASIO_EMAIL')) {
    props.setProperty('CASIO_EMAIL', DEFAULT_EMAIL);
  }
  if (!props.getProperty('CASIO_TOKEN')) {
    const token = Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '');
    props.setProperty('CASIO_TOKEN', token);
  }

  const result = {
    email: props.getProperty('CASIO_EMAIL'),
    token: props.getProperty('CASIO_TOKEN'),
    webAppUrl: ScriptApp.getService().getUrl() || 'Deploy as Web App first, then run printWebhookUrl().'
  };
  console.log(JSON.stringify(result, null, 2));
  return result;
}

function printWebhookUrl() {
  const props = PropertiesService.getScriptProperties();
  const token = props.getProperty('CASIO_TOKEN');
  const url = ScriptApp.getService().getUrl();
  if (!token) throw new Error('Run setupCasio() first.');
  if (!url) throw new Error('Deploy this Apps Script as a Web App first.');
  const webhook = url + '?token=' + encodeURIComponent(token);
  console.log(webhook);
  return webhook;
}

function sendTestEmail() {
  const props = PropertiesService.getScriptProperties();
  const to = props.getProperty('CASIO_EMAIL') || DEFAULT_EMAIL;
  MailApp.sendEmail({
    to: to,
    subject: '[CASIO] Email connection test',
    body: 'CASIO Google Apps Script email alerts are connected.',
    htmlBody: '<div style="font-family:Arial,sans-serif"><h2>CASIO connected</h2><p>TradingView signal emails are ready.</p></div>',
    name: 'CASIO XAUUSD'
  });
  return 'Test email sent to ' + to;
}

function doGet() {
  const props = PropertiesService.getScriptProperties();
  return jsonResponse_({
    ok: true,
    service: 'casio-email-alerts',
    schema: CASIO_SCHEMA,
    recipient: props.getProperty('CASIO_EMAIL') || DEFAULT_EMAIL
  });
}

function doPost(e) {
  try {
    const props = PropertiesService.getScriptProperties();
    const expectedToken = props.getProperty('CASIO_TOKEN');
    const suppliedToken = e && e.parameter ? String(e.parameter.token || '') : '';

    if (!expectedToken) return jsonResponse_({ ok: false, error: 'CASIO_TOKEN not configured' });
    if (!suppliedToken || suppliedToken !== expectedToken) return jsonResponse_({ ok: false, error: 'unauthorized' });
    if (!e || !e.postData || !e.postData.contents) return jsonResponse_({ ok: false, error: 'empty body' });

    const payload = JSON.parse(e.postData.contents);
    validateSignal_(payload);

    const dedupeKey = [
      'casio', payload.bar_time, payload.mode, payload.direction, payload.entry
    ].join(':');
    const cache = CacheService.getScriptCache();
    if (cache.get(dedupeKey)) {
      return jsonResponse_({ ok: true, accepted: true, duplicate: true });
    }
    cache.put(dedupeKey, '1', 21600);

    sendSignalEmail_(payload);
    return jsonResponse_({
      ok: true,
      accepted: true,
      duplicate: false,
      mode: payload.mode,
      direction: payload.direction,
      bar_time: payload.bar_time
    });
  } catch (err) {
    console.error(err && err.stack ? err.stack : err);
    return jsonResponse_({ ok: false, error: String(err && err.message ? err.message : err) });
  }
}

function validateSignal_(p) {
  if (!p || typeof p !== 'object') throw new Error('JSON body must be an object');
  if (p.schema !== CASIO_SCHEMA) throw new Error('Unsupported schema');
  if (p.event !== 'signal') throw new Error('Unsupported event');
  const ticker = String(p.ticker || '').toUpperCase();
  const symbol = String(p.symbol || '').toUpperCase();
  if (ticker !== 'XAUUSD' && symbol.indexOf('XAUUSD') === -1) throw new Error('XAUUSD only');
  if (['intraday', 'scalping'].indexOf(String(p.mode)) === -1) throw new Error('Invalid mode');
  if (['long', 'short'].indexOf(String(p.direction)) === -1) throw new Error('Invalid direction');
  ['entry', 'stop', 'target', 'rr', 'score', 'bar_time'].forEach(function (key) {
    if (p[key] === undefined || p[key] === null || p[key] === '') throw new Error('Missing ' + key);
  });
}

function sendSignalEmail_(p) {
  const props = PropertiesService.getScriptProperties();
  const to = props.getProperty('CASIO_EMAIL') || DEFAULT_EMAIL;
  const direction = String(p.direction).toUpperCase();
  const mode = String(p.mode).toUpperCase();
  const score = Number(p.score);
  const rr = Number(p.rr);
  const timestamp = new Date(Number(p.bar_time));

  const subject = '[CASIO] XAUUSD ' + direction + ' • ' + mode + ' • Score ' + score;

  const rows = [
    ['Signal', direction],
    ['Mode', mode],
    ['Regime', String(p.regime || '—').toUpperCase()],
    ['Session', String(p.session || '—')],
    ['Score', String(score) + '/100'],
    ['Entry', fmt_(p.entry)],
    ['Stop', fmt_(p.stop)],
    ['Target', fmt_(p.target)],
    ['R:R', '1:' + (isFinite(rr) ? rr.toFixed(2) : '—')],
    ['H4 bias', String(p.h4_bias || '—').toUpperCase()],
    ['H1 bias', String(p.h1_bias || '—').toUpperCase()],
    ['M15 ADX', fmt_(p.m15_adx)],
    ['Rolling win rate', pct_(p.win_rate)],
    ['Expectancy', r_(p.expectancy_r)],
    ['Profit factor', fmt_(p.profit_factor)],
    ['Audit', String(p.audit_status || '—').toUpperCase()],
    ['TradingView bar', Utilities.formatDate(timestamp, 'Asia/Kuala_Lumpur', 'yyyy-MM-dd HH:mm:ss') + ' MYT']
  ];

  const tableRows = rows.map(function (row) {
    return '<tr><td style="padding:7px 10px;color:#94a3b8;border-bottom:1px solid #1f2937">' + html_(row[0]) + '</td>' +
      '<td style="padding:7px 10px;font-weight:700;border-bottom:1px solid #1f2937">' + html_(row[1]) + '</td></tr>';
  }).join('');

  const signalColor = direction === 'LONG' ? '#22c55e' : '#ef4444';
  const htmlBody =
    '<div style="background:#090d14;color:#f8fafc;padding:22px;font-family:Arial,sans-serif;max-width:620px">' +
      '<div style="font-size:12px;letter-spacing:1.5px;color:#94a3b8">CASIO XAUUSD v2</div>' +
      '<h1 style="margin:8px 0 4px;color:' + signalColor + '">' + html_(direction) + ' ' + html_(mode) + '</h1>' +
      '<div style="color:#cbd5e1;margin-bottom:18px">Confirmed TradingView setup • Score ' + html_(score) + '/100</div>' +
      '<table style="border-collapse:collapse;width:100%;background:#111827">' + tableRows + '</table>' +
      '<p style="margin-top:18px;color:#94a3b8;font-size:12px">Research signal generated by CASIO. Verify current market conditions before execution.</p>' +
    '</div>';

  const plainBody = rows.map(function (row) { return row[0] + ': ' + row[1]; }).join('\n');

  MailApp.sendEmail({
    to: to,
    subject: subject,
    body: plainBody,
    htmlBody: htmlBody,
    name: 'CASIO XAUUSD'
  });
}

function fmt_(value) {
  const n = Number(value);
  return isFinite(n) ? n.toFixed(2) : '—';
}

function pct_(value) {
  const n = Number(value);
  return isFinite(n) ? n.toFixed(1) + '%' : '—';
}

function r_(value) {
  const n = Number(value);
  return isFinite(n) ? n.toFixed(2) + 'R' : '—';
}

function html_(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function jsonResponse_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
