export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  return res.status(410).json({
    ok: false,
    retired: true,
    engine: 'RR10',
    message: 'This independent live relay is retired. TradingView FxPro RR10 publishes directly to the canonical Apps Script state store.'
  });
}
