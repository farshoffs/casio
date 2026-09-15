import fs from 'node:fs';
import path from 'node:path';
import { getHistoricalRates } from 'dukascopy-node';

function arg(name, fallback = null) {
  const i = process.argv.indexOf(name);
  return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : fallback;
}

function isoFloorToClosedM5(value) {
  const d = value ? new Date(value) : new Date();
  if (Number.isNaN(d.getTime())) throw new Error(`Invalid --to date: ${value}`);
  const ms5 = 5 * 60 * 1000;
  const floored = Math.floor(d.getTime() / ms5) * ms5;
  return new Date(floored - ms5);
}

const fromArg = arg('--from');
const output = arg('--output', 'tmp/dukascopy_xauusd_m5.csv');
const priceType = arg('--price-type', 'bid');
const to = isoFloorToClosedM5(arg('--to'));

if (!fromArg) throw new Error('--from is required');
const from = new Date(fromArg);
if (Number.isNaN(from.getTime())) throw new Error(`Invalid --from date: ${fromArg}`);
if (from >= to) throw new Error(`Nothing to fetch: from=${from.toISOString()} to=${to.toISOString()}`);
if (!['bid', 'ask'].includes(priceType)) throw new Error('--price-type must be bid or ask');

fs.mkdirSync(path.dirname(output), { recursive: true });
const stream = fs.createWriteStream(output, { encoding: 'utf8' });
stream.write('timestamp,open,high,low,close,volume\n');

const chunkMs = 31 * 24 * 60 * 60 * 1000;
let cursor = new Date(from);
let rows = 0;

while (cursor < to) {
  const chunkEnd = new Date(Math.min(cursor.getTime() + chunkMs, to.getTime()));
  console.log(`Fetching XAUUSD M5 ${priceType}: ${cursor.toISOString()} -> ${chunkEnd.toISOString()}`);

  const data = await getHistoricalRates({
    instrument: 'xauusd',
    dates: { from: cursor, to: chunkEnd },
    timeframe: 'm5',
    format: 'json',
    priceType,
    volumes: true,
    utcOffset: 0,
    ignoreFlats: true,
    batchSize: 10,
    pauseBetweenBatchesMs: 250,
    retryCount: 3,
    pauseBetweenRetriesMs: 1000,
    retryOnEmpty: false,
  });

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
}

await new Promise((resolve, reject) => {
  stream.end(resolve);
  stream.on('error', reject);
});

if (rows === 0) throw new Error('Dukascopy returned zero XAUUSD M5 bars');
console.log(`Wrote ${rows} XAUUSD M5 ${priceType} bars to ${output}`);
