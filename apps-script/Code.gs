const CASIO_SCHEMAS = ['casio.tv.v2', 'casio.tv.v3'];
const CASIO_MARKET_SCHEMA = 'casio.market.v1';
const DEFAULT_EMAIL = 'farhanshoffi@moe.gov.my';
const QUEUE_PROPERTY = 'CASIO_EMAIL_QUEUE';
const QUEUE_HANDLER = 'processEmailQueue_';
const MARKET_SHEET_NAME = 'XAUUSD_M5';
const MARKET_SHEET_ID_PROPERTY = 'CASIO_MARKET_SHEET_ID';
const LAST_M5_BAR_PROPERTY = 'CASIO_LAST_M5_BAR_TIME';

function setupCasio() {
  const props = PropertiesService.getScriptProperties();
  if (!props.getProperty('CASIO_EMAIL')) {
    props.setProperty('CASIO_EMAIL', DEFAULT_EMAIL);
  }
  if (!props.getProperty('CASIO_TOKEN')) {
    const token = Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '');
    props.setProperty('CASIO_TOKEN', token);
  }

  const sheet = getOrCreateMarketSheet_();
  const spreadsheet = sheet.getParent();

  const result = {
    email: props.getProperty('CASIO_EMAIL'),
    token: props.getProperty('CASIO_TOKEN'),
    marketSpreadsheetId: spreadsheet.getId(),
    marketSpreadsheetUrl: spreadsheet.getUrl(),
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

function doGet(e) {
  const action = e && e.parameter ? String(e.parameter.action || '') : '';
  if (action === 'csv') {
    if (!authorized_(e)) {
      return jsonResponse_({ ok: false, error: 'unauthorized' });
    }
    return marketCsvResponse_();
  }

  const props = PropertiesService.getScriptProperties();
  return jsonResponse_({
    ok: true,
    service: 'casio-email-marketdata',
    schemas: CASIO_SCHEMAS.concat([CASIO_MARKET_SCHEMA]),
    recipient: props.getProperty('CASIO_EMAIL') || DEFAULT_EMAIL,
    marketSheetConfigured: Boolean(props.getProperty(MARKET_SHEET_ID_PROPERTY))
  });
}

function doPost(e) {
  try {
    if (!authorized_(e)) {
      return jsonResponse_({ ok: false, error: 'unauthorized' });
    }
    if (!e || !e.postData || !e.postData.contents) {
      return jsonResponse_({ ok: false, error: 'empty body' });
    }

    const payload = JSON.parse(e.postData.contents);

    if (payload.event === 'bar') {
      validateMarketBar_(payload);
      const stored = storeMarketBar_(payload);
      return jsonResponse_({
        ok: true,
        accepted: true,
        event: 'bar',
        stored: stored,
        duplicate: !stored,
        schema: payload.schema,
        timeframe: payload.timeframe,
        bar_time: payload.bar_time
      });
    }

    validateSignal_(payload);

    const dedupeKey = ['casio', payload.bar_time, payload.mode, payload.direction, payload.entry].join(':');
    const cache = CacheService.getScriptCache();
    if (cache.get(dedupeKey)) {
      return jsonResponse_({ ok: true, accepted: true, duplicate: true });
    }
    cache.put(dedupeKey, '1', 21600);

    enqueueSignal_(payload);
    ensureQueueTrigger_();

    return jsonResponse_({
      ok: true,
      accepted: true,
      queued: true,
      duplicate: false,
      schema: payload.schema,
      mode: payload.mode,
      direction: payload.direction,
      bar_time: payload.bar_time
    });
  } catch (err) {
    console.error(err && err.stack ? err.stack : err);
    return jsonResponse_({ ok: false, error: String(err && err.message ? err.message : err) });
  }
}

function authorized_(e) {
  const props = PropertiesService.getScriptProperties();
  const expectedToken = props.getProperty('CASIO_TOKEN');
  const suppliedToken = e && e.parameter ? String(e.parameter.token || '') : '';
  return Boolean(expectedToken && suppliedToken && suppliedToken === expectedToken);
}

function getOrCreateMarketSheet_() {
  const props = PropertiesService.getScriptProperties();
  let spreadsheet = null;
  const existingId = props.getProperty(MARKET_SHEET_ID_PROPERTY);

  if (existingId) {
    try {
      spreadsheet = SpreadsheetApp.openById(existingId);
    } catch (err) {
      console.warn('Could not open existing market sheet; creating a new one. ' + err);
    }
  }

  if (!spreadsheet) {
    spreadsheet = SpreadsheetApp.create('CASIO XAUUSD M5 Data');
    props.setProperty(MARKET_SHEET_ID_PROPERTY, spreadsheet.getId());
  }

  let sheet = spreadsheet.getSheetByName(MARKET_SHEET_NAME);
  if (!sheet) {
    sheet = spreadsheet.insertSheet(MARKET_SHEET_NAME);
  }

  if (sheet.getLastRow() === 0) {
    sheet.appendRow(['timestamp', 'open', 'high', 'low', 'close', 'volume', 'symbol']);
    sheet.setFrozenRows(1);
  }

  return sheet;
}

function validateMarketBar_(p) {
  if (!p || typeof p !== 'object') throw new Error('JSON body must be an object');
  if (String(p.schema) !== CASIO_MARKET_SCHEMA) throw new Error('Unsupported market schema');
  if (p.event !== 'bar') throw new Error('Unsupported market event');

  const ticker = String(p.ticker || '').toUpperCase();
  const symbol = String(p.symbol || '').toUpperCase();
  if (ticker !== 'XAUUSD' && symbol.indexOf('XAUUSD') === -1) throw new Error('XAUUSD only');
  if (['5', '5m', '5M'].indexOf(String(p.timeframe)) === -1) throw new Error('M5 only');

  ['bar_time', 'open', 'high', 'low', 'close'].forEach(function (key) {
    if (p[key] === undefined || p[key] === null || p[key] === '') throw new Error('Missing ' + key);
    if (!isFinite(Number(p[key]))) throw new Error('Invalid ' + key);
  });
}

function storeMarketBar_(p) {
  const lock = LockService.getScriptLock();
  lock.waitLock(5000);
  try {
    const props = PropertiesService.getScriptProperties();
    const barTime = Number(p.bar_time);
    const lastTime = Number(props.getProperty(LAST_M5_BAR_PROPERTY) || 0);

    // TradingView alerts are chronological. Ignore retries/duplicates and stale out-of-order bars.
    if (lastTime && barTime <= lastTime) {
      return false;
    }

    const sheet = getOrCreateMarketSheet_();
    sheet.appendRow([
      new Date(barTime).toISOString(),
      Number(p.open),
      Number(p.high),
      Number(p.low),
      Number(p.close),
      isFinite(Number(p.volume)) ? Number(p.volume) : 0,
      String(p.symbol || p.ticker || 'XAUUSD')
    ]);

    props.setProperty(LAST_M5_BAR_PROPERTY, String(barTime));
    return true;
  } finally {
    lock.releaseLock();
  }
}

function marketCsvResponse_() {
  const sheet = getOrCreateMarketSheet_();
  const rows = sheet.getDataRange().getValues();
  const wanted = rows.map(function (row, index) {
    if (index === 0) return ['timestamp', 'open', 'high', 'low', 'close', 'volume'];
    return row.slice(0, 6);
  });

  const csv = wanted.map(function (row) {
    return row.map(csvCell_).join(',');
  }).join('\n');

  return ContentService.createTextOutput(csv).setMimeType(ContentService.MimeType.CSV);
}

function csvCell_(value) {
  const text = String(value === null || value === undefined ? '' : value);
  if (/[",\n]/.test(text)) {
    return '"' + text.replace(/"/g, '""') + '"';
  }
  return text;
}

function enqueueSignal_(payload) {
  const lock = LockService.getScriptLock();
  lock.waitLock(3000);
  try {
    const props = PropertiesService.getScriptProperties();
    let queue = [];
    const raw = props.getProperty(QUEUE_PROPERTY);
    if (raw) {
      try {
        queue = JSON.parse(raw);
        if (!Array.isArray(queue)) queue = [];
      } catch (err) {
        queue = [];
      }
    }
    queue.push(payload);
    if (queue.length > 20) queue = queue.slice(queue.length - 20);
    props.setProperty(QUEUE_PROPERTY, JSON.stringify(queue));
  } finally {
    lock.releaseLock();
  }
}

function ensureQueueTrigger_() {
  const exists = ScriptApp.getProjectTriggers().some(function (trigger) {
    return trigger.getHandlerFunction() === QUEUE_HANDLER;
  });
  if (!exists) {
    ScriptApp.newTrigger(QUEUE_HANDLER).timeBased().after(1000).create();
  }
}

function processEmailQueue_() {
  try {
    const lock = LockService.getScriptLock();
    lock.waitLock(5000);
    let queue = [];
    try {
      const props = PropertiesService.getScriptProperties();
      const raw = props.getProperty(QUEUE_PROPERTY);
      if (raw) {
        queue = JSON.parse(raw);
        if (!Array.isArray(queue)) queue = [];
      }
      props.deleteProperty(QUEUE_PROPERTY);
    } finally {
      lock.releaseLock();
    }

    queue.forEach(function (payload) {
      try {
        sendSignalEmail_(payload);
      } catch (err) {
        console.error('CASIO email failed: ' + (err && err.stack ? err.stack : err));
      }
    });
  } finally {
    ScriptApp.getProjectTriggers().forEach(function (trigger) {
      if (trigger.getHandlerFunction() === QUEUE_HANDLER) {
        ScriptApp.deleteTrigger(trigger);
      }
    });
  }
}

function validateSignal_(p) {
  if (!p || typeof p !== 'object') throw new Error('JSON body must be an object');
  if (CASIO_SCHEMAS.indexOf(String(p.schema)) === -1) throw new Error('Unsupported schema');
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
  const version = String(p.schema || '').replace('casio.tv.', '').toUpperCase() || 'CASIO';

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
      '<div style="font-size:12px;letter-spacing:1.5px;color:#94a3b8">CASIO XAUUSD ' + html_(version) + '</div>' +
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
