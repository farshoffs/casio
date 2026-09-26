import fs from 'node:fs';
import path from 'node:path';
import { getHistoricalRates } from 'dukascopy-node';

function arg(name, fallback = null) {
  const i = process.argv.indexOf(name);
  return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : fallback;
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function isoFloorToClosedM5(value) {
  const d = value ? new Date(value) : new Date();
  if (Number.isNaN(d.getTime())) throw new Error(`Invalid --to date: ${value}`);
  const ms5 = 5 * 60 * 1000;
  const floored = Math.floor(d.getTime() / ms5) * ms5;
  return new Date(floored - ms5);
}

const instrument = String(arg('--instrument', 'xauusd')).toLowerCase();
const fromArg = arg('--from');
const output = arg('--output', `tmp/dukascopy_${instrument}_m5.csv`);
const priceType = arg('--price-type', 'bid');
const batchSize = Number(arg('--batch-size', '5'));
const batchPauseMs = Number(arg('--batch-pause-ms', '500'));
const to = isoFloorToClosedM5(arg('--to'));

async function fetchChunk(from, to, priceType) {
  const maxAttempts = 6;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      return await getHistoricalRates({
        instrument,
        dates: { from, to },
        timeframe: 'm5',
        format: 'json',
        priceType,
        volumes: true,
        utcOffset: 0,
        ignoreFlats: true,
        batchSize,
        pauseBetweenBatchesMs: batchPauseMs,
        retryCount: 5,
        pauseBetweenRetriesMs: 2500,
        retryOnEmpty: false,
      });
    } catch (error) {
      if (attempt === maxAttempts) throw error;
      const message = String(error && error.message ? error.message : error);
      const rateLimited = message.includes('429');
      const waitMs = rateLimited ? 30000 * attempt : 5000 * attempt;
      console.warn(`Dukascopy chunk failed (attempt ${attempt}/${maxAttempts}): ${message}. Waiting ${Math.round(waitMs / 1000)}s.`);
      await sleep(waitMs);
    }
  }
}

if (!fromArg) throw new Error('--from is required');
if (!/^[a-z0-9]+$/.test(instrument)) throw new Error('--instrument must be an alphanumeric Dukascopy symbol');
const from = new Date(fromArg);
if (Number.isNaN(from.getTime())) throw new Error(`Invalid --from date: ${fromArg}`);
if (from >= to) throw new Error(`Nothing to fetch: from=${from.toISOString()} to=${to.toISOString()}`);
if (!['bid', 'ask'].includes(priceType)) throw new Error('--price-type must be bid or ask');
if (!Number.isInteger(batchSize) || batchSize < 1 || batchSize > 20) throw new Error('--batch-size must be an integer from 1 to 20');
if (!Number.isFinite(batchPauseMs) || batchPauseMs < 0) throw new Error('--batch-pause-ms must be >= 0');

fs.mkdirSync(path.dirname(output), { recursive: true });
const stream = fs.createWriteStream(output, { encoding: 'utf8' });
stream.write('timestamp,open,high,low,close,volume\n');

const chunkMs = 31 * 24 * 60 * 60 * 1000;
let cursor = new Date(from);
let rows = 0;
let chunks = 0;

while (cursor < to) {
  const chunkEnd = new Date(Math.min(cursor.getTime() + chunkMs, to.getTime()));
  console.log(`Fetching ${instrument.toUpperCase()} M5 ${priceType}: ${cursor.toISOString()} -> ${chunkEnd.toISOString()}`);

  const data = await fetchChunk(cursor, chunkEnd, priceType);
  for (const bar of data) {
    if (!bar || !Number.isFinite(Number(bar.timestamp))) continue;
    const timestamp = new Date(Number(bar.timestamp)).toISOString().replace('.000Z', 'Z');
    const values = [bar.open, bar.high, bar.low, bar.close].map(Number);
    if (values.some(v => !Number.isFinite(v))) continue;
    const volume = Number.isFinite(Number(bar.volume)) ? Number(bar.volume) : 0;
    stream.write(`${timestamp},${values[0]},${values[1]},${values[2]},${values[3]},${volume}\n`);
    rows += 1;
  }

  cursor = chunkEnd;
  chunks += 1;
  if (cursor < to) await sleep(1000);
}

await new Promise((resolve, reject) => {
  stream.end(resolve);
  stream.on('error', reject);
});

if (rows === 0) throw new Error(`Dukascopy returned zero ${instrument.toUpperCase()} M5 bars`);
console.log(`Wrote ${rows} ${instrument.toUpperCase()} M5 ${priceType} bars from ${chunks} chunks to ${output}`);
