const CASIO_SCHEMAS = ['casio.tv.v2', 'casio.tv.v3'];
const CASIO_MARKET_SCHEMA = 'casio.market.v1';
const DEFAULT_EMAIL = 'farhanshoffi@moe.gov.my';
const QUEUE_PROPERTY = 'CASIO_EMAIL_QUEUE';
const QUEUE_HANDLER = 'processEmailQueue_';
const MARKET_SHEET_NAME = 'XAUUSD_M5';
const MARKET_SHEET_ID_PROPERTY = 'CASIO_MARKET_SHEET_ID';
const LAST_M5_BAR_PROPERTY = 'CASIO_LAST_M5_BAR_TIME';
const RR10_STATE_SCHEMA = 'casio.regime-router.rr10.state.v1';
const RR10_STATE_PROPERTY = 'CASIO_RR10_LIVE_STATE';
const RR10_LAST_EMAIL_SIGNAL_PROPERTY = 'CASIO_RR10_LAST_EMAIL_SIGNAL';

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
  if (action === 'state') {
    const callback = e && e.parameter ? String(e.parameter.callback || '') : '';
    return rr10StateResponse_(callback);
  }
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

    if (String(payload.schema || '') === RR10_STATE_SCHEMA && payload.event === 'state') {
      return handleRr10State_(payload);
    }

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
        if (String(payload && payload.schema || '') === RR10_STATE_SCHEMA) {
          sendRr10SignalEmail_(payload);
        } else {
          sendSignalEmail_(payload);
        }
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

function handleRr10State_(p) {
  validateRr10State_(p);
  const state = normalizeRr10State_(p);
  const props = PropertiesService.getScriptProperties();
  props.setProperty(RR10_STATE_PROPERTY, JSON.stringify(state));

  let queued = false;
  if (String(p.transition || '') === 'signal' && state.active_signal) {
    const signalId = String(state.active_signal.signal_id || '');
    const previous = props.getProperty(RR10_LAST_EMAIL_SIGNAL_PROPERTY) || '';
    if (signalId && signalId !== previous) {
      props.setProperty(RR10_LAST_EMAIL_SIGNAL_PROPERTY, signalId);
      enqueueSignal_(state);
      ensureQueueTrigger_();
      queued = true;
    }
  }

  return jsonResponse_({
    ok: true,
    accepted: true,
    engine: 'RR10',
    schema: RR10_STATE_SCHEMA,
    portfolio: state.portfolio,
    signal_email_queued: queued,
    bar_time: state.bar_time
  });
}

function validateRr10State_(p) {
  if (!p || typeof p !== 'object') throw new Error('JSON body must be an object');
  if (String(p.schema || '') !== RR10_STATE_SCHEMA) throw new Error('Unsupported RR10 state schema');
  if (String(p.engine || '').toUpperCase() !== 'RR10') throw new Error('RR10 only');
  if (String(p.event || '') !== 'state') throw new Error('RR10 state event required');

  const symbol = String(p.symbol || p.ticker || '').toUpperCase();
  const feed = String(p.feed || '');
  if (symbol.indexOf('XAUUSD') === -1 && feed.toUpperCase().indexOf('XAUUSD') === -1) {
    throw new Error('XAUUSD only');
  }
  if (String(p.timeframe || '') !== '15') throw new Error('M15 only');

  const portfolio = String(p.portfolio || '').toUpperCase();
  if (['WAIT', 'LONG', 'SHORT'].indexOf(portfolio) === -1) throw new Error('Invalid portfolio state');
  if (!isFinite(Number(p.bar_time))) throw new Error('Invalid bar_time');
  if (Number(p.target_r) !== 3) throw new Error('RR10 target must be 3R');
  if (Number(p.risk_pct) !== 5) throw new Error('RR10 risk model must be 5%');

  if (portfolio !== 'WAIT') {
    ['entry', 'stop', 'target', 'signal_time'].forEach(function (key) {
      if (p[key] === undefined || p[key] === null || p[key] === '' || !isFinite(Number(p[key]))) {
        throw new Error('Missing active ' + key);
      }
    });
  }
}

function normalizeRr10State_(p) {
  const portfolio = String(p.portfolio || 'WAIT').toUpperCase();
  const barTime = Number(p.bar_time);
  const signalTime = p.signal_time === null || p.signal_time === undefined || p.signal_time === '' ? null : Number(p.signal_time);
  const sourceFeed = String(p.feed || p.source || 'TradingView FxPro XAUUSD');
  const generatedMs = isFinite(Number(p.generated_at_ms)) ? Number(p.generated_at_ms) : Date.now();
  const signalId = portfolio === 'WAIT' || signalTime === null ? '' :
    'RR10:' + String(signalTime) + ':' + (portfolio === 'LONG' ? '1' : '-1');

  const active = portfolio === 'WAIT' ? null : {
    signal_id: signalId,
    direction: portfolio,
    entry_time_utc: new Date(signalTime).toISOString(),
    signal_bar_open_utc: '',
    entry: Number(p.entry),
    stop: Number(p.stop),
    target: Number(p.target),
    rr: 3,
    support: isFinite(Number(p.support)) ? Number(p.support) : null,
    align_count: isFinite(Number(p.align_count)) ? Number(p.align_count) : null,
    router_mode: String(p.active_router_mode || p.router_mode || '')
  };

  return {
    ok: true,
    schema: RR10_STATE_SCHEMA,
    engine: 'RR10',
    build: 'RR10-TV-LIVE',
    generated_at_utc: new Date(generatedMs).toISOString(),
    symbol: 'XAUUSD',
    timeframe: 'M15',
    portfolio: portfolio,
    router_mode: String(p.router_mode || ''),
    h1_bias: Number(p.h1_bias),
    h4_bias: Number(p.h4_bias),
    h4_adx: isFinite(Number(p.h4_adx)) ? Number(p.h4_adx) : null,
    target_r: 3,
    risk_pct: 5,
    active_signal: active,
    last_m15_open_utc: new Date(barTime - 15 * 60 * 1000).toISOString(),
    last_m15_close_utc: new Date(barTime).toISOString(),
    bar_time: barTime,
    data_age_minutes: Math.max(0, (Date.now() - barTime) / 60000),
    stale: false,
    feed_adapter: sourceFeed,
    data_source: 'TradingView FxPro RR10 live state · ' + sourceFeed,
    execution_source: 'FxPro/cTrader live quote overlay when available',
    transition: String(p.transition || 'state'),
    close_reason: String(p.close_reason || '')
  };
}

function rr10StateResponse_(callback) {
  const props = PropertiesService.getScriptProperties();
  const raw = props.getProperty(RR10_STATE_PROPERTY);
  let state;
  if (raw) {
    try {
      state = JSON.parse(raw);
    } catch (err) {
      state = null;
    }
  }

  if (!state) {
    state = {
      ok: false,
      schema: RR10_STATE_SCHEMA,
      engine: 'RR10',
      build: 'RR10-TV-LIVE',
      portfolio: 'WAIT',
      router_mode: '',
      h1_bias: 0,
      h4_bias: 0,
      h4_adx: null,
      target_r: 3,
      risk_pct: 5,
      active_signal: null,
      last_m15_open_utc: null,
      last_m15_close_utc: null,
      bar_time: null,
      data_age_minutes: null,
      stale: true,
      data_source: 'Waiting for TradingView FxPro RR10 heartbeat',
      execution_source: 'FxPro/cTrader live quote overlay when available'
    };
  } else {
    const barTime = Number(state.bar_time || 0);
    const age = barTime ? Math.max(0, (Date.now() - barTime) / 60000) : null;
    state.data_age_minutes = age;
    state.stale = age === null || age > 35;
    state.server_now_utc = new Date().toISOString();
  }

  const json = JSON.stringify(state);
  if (callback && /^[A-Za-z_$][A-Za-z0-9_$.]*$/.test(callback)) {
    return ContentService
      .createTextOutput(callback + '(' + json + ');')
      .setMimeType(ContentService.MimeType.JAVASCRIPT);
  }
  return jsonResponse_(state);
}

function sendRr10SignalEmail_(state) {
  if (!state || !state.active_signal) return;
  const props = PropertiesService.getScriptProperties();
  const to = props.getProperty('CASIO_EMAIL') || DEFAULT_EMAIL;
  const a = state.active_signal;
  const direction = String(state.portfolio || a.direction || '').toUpperCase();
  const subject = '[CASIO RR10] XAUUSD ' + direction + ' · TradingView FxPro';

  const rows = [
    ['Signal', direction],
    ['Engine', 'RR10'],
    ['Source', state.data_source || 'TradingView FxPro'],
    ['Router mode', a.router_mode || state.router_mode || '—'],
    ['Entry', fmt_(a.entry)],
    ['Stop', fmt_(a.stop)],
    ['Target', fmt_(a.target)],
    ['R:R', '1:3'],
    ['Risk model', '5%'],
    ['H1 bias', String(state.h1_bias)],
    ['H4 bias', String(state.h4_bias)],
    ['H4 ADX', fmt_(state.h4_adx)],
    ['Support', String(a.support === null ? '—' : a.support)],
    ['HTF alignment', String(a.align_count === null ? '—' : a.align_count)],
    ['TradingView close', state.last_m15_close_utc || '—']
  ];

  const plainBody = rows.map(function (row) { return row[0] + ': ' + row[1]; }).join('\n');
  const tableRows = rows.map(function (row) {
    return '<tr><td style="padding:7px 10px;color:#94a3b8;border-bottom:1px solid #1f2937">' + html_(row[0]) + '</td>' +
      '<td style="padding:7px 10px;font-weight:700;border-bottom:1px solid #1f2937">' + html_(row[1]) + '</td></tr>';
  }).join('');

  MailApp.sendEmail({
    to: to,
    subject: subject,
    body: plainBody,
    htmlBody: '<div style="background:#090d14;color:#f8fafc;padding:22px;font-family:Arial,sans-serif;max-width:620px">' +
      '<div style="font-size:12px;letter-spacing:1.5px;color:#94a3b8">CASIO RR10 · SINGLE LIVE OWNER</div>' +
      '<h1 style="margin:8px 0 14px;color:' + (direction === 'LONG' ? '#22c55e' : '#ef4444') + '">' + html_(direction) + '</h1>' +
      '<table style="border-collapse:collapse;width:100%;background:#111827">' + tableRows + '</table>' +
      '</div>',
    name: 'CASIO RR10'
  });
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
