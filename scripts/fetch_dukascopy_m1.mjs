import fs from 'node:fs';
import path from 'node:path';
import { getHistoricalRates } from 'dukascopy-node';

function arg(name, fallback = null) {
  const i = process.argv.indexOf(name);
  return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : fallback;
}
function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

async function fetchChunk(from, to, priceType, batchSize, pauseMs) {
  for (let attempt = 1; attempt <= 6; attempt += 1) {
    try {
      return await getHistoricalRates({
        instrument: 'xauusd',
        dates: { from, to },
        timeframe: 'm1',
        format: 'json',
        priceType,
        volumes: true,
        utcOffset: 0,
        ignoreFlats: true,
        batchSize,
        pauseBetweenBatchesMs: pauseMs,
        retryCount: 5,
        pauseBetweenRetriesMs: 2500,
        retryOnEmpty: false,
      });
    } catch (error) {
      if (attempt === 6) throw error;
      const message = String(error?.message ?? error);
      const waitMs = message.includes('429') ? 20000 * attempt : 4000 * attempt;
      console.warn(`M1 chunk failed attempt ${attempt}: ${message}; wait ${waitMs}ms`);
      await sleep(waitMs);
    }
  }
}

const fromArg = arg('--from');
const toArg = arg('--to');
const output = arg('--output', 'tmp/xauusd_m1.csv');
const priceType = arg('--price-type', 'bid');
const batchSize = Number(arg('--batch-size', '8'));
const pauseMs = Number(arg('--batch-pause-ms', '300'));

if (!fromArg || !toArg) throw new Error('--from and --to are required');
const from = new Date(fromArg);
const to = new Date(toArg);
if (Number.isNaN(from.getTime()) || Number.isNaN(to.getTime()) || from >= to) throw new Error('Invalid date range');

fs.mkdirSync(path.dirname(output), { recursive: true });
const stream = fs.createWriteStream(output, { encoding: 'utf8' });
stream.write('timestamp,open,high,low,close,volume\n');

const chunkMs = 14 * 24 * 60 * 60 * 1000;
let cursor = new Date(from);
let rows = 0;
let chunks = 0;

while (cursor < to) {
  const chunkEnd = new Date(Math.min(cursor.getTime() + chunkMs, to.getTime()));
  console.log(`Fetching XAUUSD M1 ${priceType}: ${cursor.toISOString()} -> ${chunkEnd.toISOString()}`);
  const data = await fetchChunk(cursor, chunkEnd, priceType, batchSize, pauseMs);
  for (const bar of data) {
    if (!bar || !Number.isFinite(Number(bar.timestamp))) continue;
    const ts = new Date(Number(bar.timestamp)).toISOString().replace('.000Z', 'Z');
    const vals = [bar.open, bar.high, bar.low, bar.close].map(Number);
    if (vals.some(v => !Number.isFinite(v))) continue;
    const volume = Number.isFinite(Number(bar.volume)) ? Number(bar.volume) : 0;
    stream.write(`${ts},${vals[0]},${vals[1]},${vals[2]},${vals[3]},${volume}\n`);
    rows += 1;
  }
  cursor = chunkEnd;
  chunks += 1;
  if (cursor < to) await sleep(400);
}

await new Promise((resolve, reject) => {
  stream.end(resolve);
  stream.on('error', reject);
});
if (rows === 0) throw new Error('Dukascopy returned zero M1 bars');
console.log(`Wrote ${rows} XAUUSD M1 bars from ${chunks} chunks to ${output}`);
