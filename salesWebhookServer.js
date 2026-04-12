require('dotenv').config();
const express = require('express');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 3002;
const LOG_FILE = path.join(__dirname, 'sales_webhook_log.json');
const LOG_SECRET = process.env.SALES_WEBHOOK_SECRET;

// Init log file
if (!fs.existsSync(LOG_FILE)) {
  fs.writeFileSync(LOG_FILE, JSON.stringify([], null, 2));
}

// Stripe needs raw body for signature verification
app.use('/stripe-webhook', express.raw({ type: 'application/json' }));
app.use(express.json());

// ── Helpers ──────────────────────────────────────────────────────────────────

function loadLog() {
  try { return JSON.parse(fs.readFileSync(LOG_FILE, 'utf8')); }
  catch { return []; }
}

function appendEntry(entry) {
  const log = loadLog();
  const key = entry.source === 'stripe_webhook'
    ? entry.session_id
    : `${entry.order_id}_${entry.event}`;
  const exists = log.some(e => {
    const k = e.source === 'stripe_webhook' ? e.session_id : `${e.order_id}_${e.event}`;
    return k === key;
  });
  if (exists) return false;
  log.push(entry);
  fs.writeFileSync(LOG_FILE, JSON.stringify(log, null, 2));
  return true;
}

function normalizeProduct(name) {
  const n = (name || '').toUpperCase();
  if (n.includes('FE MECHANICAL') || n.includes('FE EXAM')) return 'FE';
  if (n.includes('HVAC')) return 'HVAC';
  if (n.includes('THERMAL') || n.includes('FLUIDS') || n.includes('TFS')) return 'TFS';
  return 'Other';
}

const PRICE_POINTS = [1999, 1899, 999, 649, 599, 399, 249, 149, 99];
function snapToPrice(dollars) {
  return PRICE_POINTS.find(p => Math.abs(dollars - p) <= 200) || Math.round(dollars);
}

// ── Dashboard rebuild trigger ────────────────────────────────────────────────

const https = require('https');
const GH_PAT = process.env.GITHUB_PAT;

function triggerRebuild(reason) {
  if (!GH_PAT) {
    console.error('[rebuild] GITHUB_PAT not set, skipping dispatch');
    return;
  }
  console.log(`[rebuild] Triggering dashboard rebuild: ${reason}`);
  const body = JSON.stringify({ event_type: 'new-order', client_payload: { reason } });
  const req = https.request({
    hostname: 'api.github.com',
    path: '/repos/molodious/mpep-dashboard/dispatches',
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${GH_PAT}`,
      'Accept': 'application/vnd.github+json',
      'User-Agent': 'mpep-webhook-server',
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(body),
    },
  }, (res) => {
    console.log(`[rebuild] GitHub dispatch: ${res.statusCode}`);
  });
  req.on('error', (err) => console.error(`[rebuild] Dispatch failed:`, err.message));
  req.write(body);
  req.end();
}

// ── GET /orders-log (polled by dashboard build script) ────────────────────────

app.get('/orders-log', (req, res) => {
  if (req.query.secret !== LOG_SECRET) return res.status(401).json({ error: 'unauthorized' });
  res.json(loadLog());
});

// ── POST /thinkific-webhook ───────────────────────────────────────────────────

app.post('/thinkific-webhook', (req, res) => {
  const event = req.body;
  const topic = `${event.resource}.${event.action}`;
  console.log(`[Thinkific] ${new Date().toISOString()} ${topic}`);

  const payload = event.payload || {};
  let entry = null;

  if (topic === 'order.created') {
    const items = payload.items || [];
    const amount = items.length
      ? items.reduce((s, i) => s + (parseFloat(i.amount_dollars) || 0), 0)
      : (parseFloat(payload.amount_dollars) || 0);
    const user = payload.user || {};
    entry = {
      source: 'thinkific_webhook', event: topic,
      order_id: payload.id,
      date: (payload.created_at || event.created_at || '').slice(0, 10),
      product: normalizeProduct(payload.product_name),
      product_name: payload.product_name,
      customer: payload.billing_name || `${user.first_name || ''} ${user.last_name || ''}`.trim(),
      email: user.email || '',
      amount, payment_type: payload.payment_type || 'one-time',
      sub_type: 'new',
      received_at: new Date().toISOString(),
    };

  } else if (topic === 'order_transaction.succeeded') {
    const order = payload.order || {};
    const items = order.items || [];
    const amount = items.length
      ? items.reduce((s, i) => s + (parseFloat(i.amount_dollars) || 0), 0)
      : (parseFloat(order.amount_dollars) || 0);
    const user = order.user || {};
    entry = {
      source: 'thinkific_webhook', event: topic,
      order_id: order.id, transaction_id: payload.id,
      date: (payload.created_at || event.created_at || '').slice(0, 10),
      product: normalizeProduct(order.product_name),
      product_name: order.product_name,
      customer: order.billing_name || `${user.first_name || ''} ${user.last_name || ''}`.trim(),
      email: user.email || '',
      amount, payment_type: order.payment_type || 'subscription',
      sub_type: 'renewal',
      received_at: new Date().toISOString(),
    };

  } else if (topic === 'order_transaction.refunded') {
    const order = payload.order || {};
    const user = order.user || {};
    entry = {
      source: 'thinkific_webhook', event: topic,
      order_id: order.id, transaction_id: payload.id,
      date: (payload.created_at || event.created_at || '').slice(0, 10),
      product: normalizeProduct(order.product_name),
      product_name: order.product_name,
      customer: order.billing_name || '',
      email: user.email || '',
      amount: -(Math.abs(parseFloat(payload.amount) || 0)),
      payment_type: 'refund',
      received_at: new Date().toISOString(),
    };
  }

  if (entry) {
    const added = appendEntry(entry);
    console.log(`[Thinkific] ${added ? '✓ logged' : '⚠ duplicate'}: ${topic} order_id=${entry.order_id} $${entry.amount}`);
    if (added && entry.amount > 0) triggerRebuild(`Thinkific ${topic} $${entry.amount}`);
  } else {
    console.log(`[Thinkific] ignored: ${topic}`);
  }

  res.json({ status: 'ok' });
});

// ── POST /stripe-webhook ──────────────────────────────────────────────────────

app.post('/stripe-webhook', (req, res) => {
  const sig = req.headers['stripe-signature'];
  const secret = process.env.SALES_STRIPE_WEBHOOK_SECRET;

  // Verify Stripe signature
  try {
    const body = req.body.toString();
    const parts = sig.split(',');
    const t = parts.find(p => p.startsWith('t=')).split('=')[1];
    const v1 = parts.find(p => p.startsWith('v1=')).split('=')[1];
    const signed = crypto.createHmac('sha256', secret).update(`${t}.${body}`).digest('hex');
    if (signed !== v1) throw new Error('signature mismatch');
  } catch (err) {
    console.error('[Stripe] Sig verification failed:', err.message);
    return res.status(400).send('Bad signature');
  }

  let event;
  try { event = JSON.parse(req.body.toString()); }
  catch { return res.status(400).send('Parse error'); }

  console.log(`[Stripe] ${new Date().toISOString()} ${event.type}`);

  if (event.type === 'checkout.session.completed') {
    const session = event.data && event.data.object ? event.data.object : {};
    if (session.payment_status !== 'paid') return res.json({ status: 'ignored' });

    const metadata = session.metadata || {};
    const bundleId = (metadata.bundleId || '').replace('bundle_', '').toUpperCase();
    let product = 'Unknown';
    if (bundleId.includes('HVAC')) product = 'HVAC';
    else if (bundleId.includes('TFS')) product = 'TFS';

    const amount = snapToPrice((session.amount_total || 0) / 100);
    const customer = session.customer_details || {};
    const date = new Date((session.created || 0) * 1000).toISOString().slice(0, 10);

    const entry = {
      source: 'stripe_webhook', event: event.type,
      session_id: session.id, order_id: session.id,
      date, product, product_name: bundleId,
      customer: customer.name || 'Unknown',
      email: customer.email || '',
      amount, payment_type: 'one-time',
      received_at: new Date().toISOString(),
    };

    const added = appendEntry(entry);
    console.log(`[Stripe] ${added ? '✓ logged' : '⚠ duplicate'}: ${session.id} $${amount}`);
    if (added) triggerRebuild(`Stripe checkout $${amount}`);
  }

  res.json({ status: 'ok' });
});

app.listen(PORT, () => console.log(`Sales webhook server running on port ${PORT}`));
