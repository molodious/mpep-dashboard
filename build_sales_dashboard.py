#!/usr/bin/env python3
"""
Sales dashboard data sources (in priority order):
  1. Stripe API  — all Stripe payments, full history, paginated (checkout sessions + renewals)
  2. BTCPay webhook log — BTC sales only (Stripe entries excluded)
  3. Manual Thinkific data — sales from before Stripe/BTC cutover (supplied by Dan)

Adding a new product: update STRIPE_PRODUCT_MAP (and salesWebhookServer.js PRODUCT_MAP).
Closing a month: add verified totals to MONTHLY_HISTORY and clear manual entries for that month.
"""

import json
import requests
import os
import calendar
from datetime import datetime, timedelta
from collections import defaultdict

# Load from environment variables
STRIPE_KEY = os.environ.get("STRIPE_READONLY_KEY", "")
THINKIFIC_KEY = os.environ.get("THINKIFIC_API_KEY", "")
THINKIFIC_SUBDOMAIN = "mechanicalpeexamprep"

if not STRIPE_KEY:
    print("ERROR: Missing STRIPE_READONLY_KEY env var.")
    exit(1)

# Earliest date to pull from Stripe API (live reporting starts March 1, 2026)
# Jan/Feb are closed months — their data lives in MONTHLY_HISTORY + HISTORICAL_MONTHLY_BREAKDOWN
DASHBOARD_START_DATE = datetime(2026, 3, 1)

# ── Product ID → dashboard label ──────────────────────────────────────────────
# Mirrors salesWebhookServer.js PRODUCT_MAP. Add new products here when they launch.
STRIPE_PRODUCT_MAP = {
    # Legacy bundles (metadata.bundleId)
    'bundle_hvac':            'HVAC',
    'bundle_tfs':             'TFS',
    # Phase 1 standalone products (metadata.productId)
    'hvac_ebook':             'HVACBook',
    'tfs_ebook':              'TFSBook',
    'fundamentals':           'Fundamentals',
    'critical_systems':       'CSE',
    'daily_insights_premium': 'DailyInsightsPremium',
    'fe_monthly':             'FE',
    'fe_3mo':                 'FE',
    'fe_6mo':                 'FE',
    'fe_12mo':                'FE',
}

# Stripe price ID → product label (for subscription renewal invoices which carry
# no checkout metadata — only the recurring price ID identifies the product)
STRIPE_PRICE_TO_PRODUCT_MAP = {
    'price_1TGTVbLeBhBRYzk45CkYcyXK': 'FE',   # fe_monthly
    'price_1TGTVbLeBhBRYzk4ie0Us1dF': 'FE',   # fe_3mo
    'price_1TGTVbLeBhBRYzk4PHmctoet': 'FE',   # fe_6mo
    'price_1TGTVcLeBhBRYzk4D7njfg5S': 'FE',   # fe_12mo
}

# Product breakdown for closed months — used only for the bar chart.
# These totals match MONTHLY_HISTORY exactly (verified 2026-03-30 from Thinkific export).
# Jan/Feb reporting is complete; live API pulls start March 1.
HISTORICAL_MONTHLY_BREAKDOWN = {
    "2026-01": {"HVAC": 33783, "TFS": 3898, "HVACBook": 1947, "FE": 1495, "Fundamentals": 399, "CSE": 399},
    "2026-02": {"HVAC": 11894, "TFS": 11894, "TFSBook": 649, "FE": 2094, "DailyInsightsPremium": 99},
}

# Manual data: Thinkific-era sales for March 2026 (pre-cutover).
# All confirmed from Thinkific transactions export (2026-03-30).
# Only add sales that went through Thinkific Payments — NOT through Stripe/BTC (double-count risk).
MANUAL_DATA_MARCH = [
    # Tuple format: (date, product, amount, sub_type)
    # sub_type: "new" = first purchase, "renewal" = recurring subscription charge
    # All went through Thinkific Payments — NOT in Stripe/BTC (confirmed 2026-03-30 export)
    ("2026-03-05",  "FE",            249,  "renewal"),   # Khaled Jawabreh — FE monthly renewal
    ("2026-03-12",  "FE",            249,  "renewal"),   # Tyler Sommer — FE monthly renewal (ex-tax)
    ("2026-03-13",  "FE",            149,  "renewal"),   # Patrick McNally — FE monthly renewal
    ("2026-03-22",  "FE",            249,  "renewal"),   # Jason Rezell — FE monthly renewal
    # New Thinkific orders placed before cutover
    ("2026-03-14",  "FE",            249,  "new"),       # Ryan Perusse — new FE monthly sub
    ("2026-03-17",  "FE",           1051,  "new"),       # MAURICIO Fierro — FE 6 Months Access
    ("2026-03-28",  "Fundamentals",  399,  "new"),       # Osvaldo Medina — Mechanical PE Fundamentals
]

# Accurate historical monthly data (Dan's verified numbers)
# Used for trailing 12-month stats and daily average calculation
MONTHLY_HISTORY = [
    ("2025-01", 15, 14036),
    ("2025-02", 18, 19732),
    ("2025-03", 19, 25332),
    ("2025-04", 23, 30027),
    ("2025-05", 23, 27829),
    ("2025-06", 13, 15787),
    ("2025-07", 24, 36026),
    ("2025-08", 23, 25230),
    ("2025-09", 13, 18588),
    ("2025-10", 15, 20786),
    ("2025-11", 17, 21583),
    ("2025-12", 11, 15189),
    ("2026-01", 29, 41921),
    ("2026-02", 20, 26630),
    # NOTE: Do not add the current month here — it is computed live from API + webhook log.
    # When a month closes, add its final verified numbers and it will roll into trailing stats.
]

def stripe_clean_amount(amount_cents):
    """Round Stripe amount to nearest standard price point (strips sales tax).
    Known price points: 1999, 1899, 999, 649, 599, 399, 249, 149, 99
    Note: 1899 = 5% promo code applied at purchase (not installment). Revenue = 1899.
    Snaps to the CLOSEST price point within $200; otherwise keeps raw value.
    """
    price_points = [1999, 1899, 999, 649, 599, 399, 249, 149, 99]
    amount = amount_cents / 100
    candidates = [(abs(amount - p), p) for p in price_points if abs(amount - p) <= 200]
    if candidates:
        return min(candidates)[1]
    return round(amount)

# Manual product label corrections (session_id → correct product)
# Use when Stripe metadata has wrong bundleId
STRIPE_LABEL_CORRECTIONS = {
    "cs_live_b1pxlS6mUa0zwyCMvqhVJerjUM3MwG78nQzG2ihiiBAAGmVCnYQiVO886B": "TFS",  # 2026-03-06 $1899 — TFS with 5% promo code
}

def fetch_stripe_all_data(cutoff_date=None):
    """Fetch ALL Stripe payments with full pagination.

    Two sources:
      - checkout/sessions: initial purchases for all products
      - invoices (billing_reason=subscription_cycle): FE subscription renewals

    Stripe returns newest-first, so we stop paginating once we pass cutoff_date.
    Replaces the old fetch_stripe_data() which was capped at 100 sessions and
    missed subscription renewals entirely.
    """
    if cutoff_date is None:
        cutoff_date = DASHBOARD_START_DATE

    orders = []

    # ── Part 1: Checkout sessions (initial purchases) ─────────────────────────
    params = {"limit": 100}
    while True:
        resp = requests.get(
            "https://api.stripe.com/v1/checkout/sessions",
            headers={"Authorization": f"Bearer {STRIPE_KEY}"},
            params=params
        )
        data = resp.json()
        sessions = data.get("data", [])
        stop = False

        for s in sessions:
            ts = datetime.fromtimestamp(s["created"])
            if ts < cutoff_date:
                stop = True
                break
            if s.get("payment_status") != "paid":
                continue

            metadata = s.get("metadata") or {}
            raw_id = metadata.get("productId") or metadata.get("bundleId") or ""
            product = STRIPE_PRODUCT_MAP.get(raw_id, "Unknown")

            session_id = s.get("id")
            if session_id in STRIPE_LABEL_CORRECTIONS:
                product = STRIPE_LABEL_CORRECTIONS[session_id]

            orders.append({
                "date": ts.strftime("%Y-%m-%d"),
                "timestamp": ts,
                "customer": (s.get("customer_details") or {}).get("name", "Unknown"),
                "product": product,
                "amount": stripe_clean_amount(s.get("amount_total", 0)),
                "session_id": session_id,
                "source": "stripe_checkout",
                "sub_type": "new",
            })

        if stop or not data.get("has_more") or not sessions:
            break
        params["starting_after"] = sessions[-1]["id"]

    # ── Part 2: Subscription renewal invoices (FE Monthly / multi-month) ──────
    params = {"limit": 100, "status": "paid"}
    while True:
        resp = requests.get(
            "https://api.stripe.com/v1/invoices",
            headers={"Authorization": f"Bearer {STRIPE_KEY}"},
            params=params
        )
        data = resp.json()
        invoices = data.get("data", [])
        stop = False

        for inv in invoices:
            # subscription_create = initial charge, already in checkout sessions
            # subscription_cycle  = renewal — this is what we want
            if inv.get("billing_reason") != "subscription_cycle":
                continue

            ts = datetime.fromtimestamp(inv["created"])
            if ts < cutoff_date:
                stop = True
                break

            lines = (inv.get("lines") or {}).get("data", [])
            price_id = lines[0].get("price", {}).get("id") if lines else None
            product = STRIPE_PRICE_TO_PRODUCT_MAP.get(price_id, "FE")

            orders.append({
                "date": ts.strftime("%Y-%m-%d"),
                "timestamp": ts,
                "customer": inv.get("customer_name") or inv.get("customer_email") or "Unknown",
                "product": product,
                "amount": stripe_clean_amount(inv.get("amount_paid", 0)),
                "session_id": inv.get("id"),   # invoice ID used for dedup
                "source": "stripe_invoice",
                "sub_type": "renewal",
            })

        if stop or not data.get("has_more") or not invoices:
            break
        params["starting_after"] = invoices[-1]["id"]

    print(f"    Checkout sessions: {sum(1 for o in orders if o.get('source')=='stripe_checkout')}")
    print(f"    Renewal invoices:  {sum(1 for o in orders if o.get('source')=='stripe_invoice')}")
    return orders

def fetch_thinkific_data(cutoff_date=None):
    """Fetch Thinkific orders, including subscription renewals."""
    headers = {
        "X-Auth-API-Key": THINKIFIC_KEY,
        "X-Auth-Subdomain": THINKIFIC_SUBDOMAIN,
    }
    response = requests.get(f"https://{THINKIFIC_SUBDOMAIN}.thinkific.com/api/public/v1/orders?limit=500", headers=headers)
    orders_data = response.json().get("items", [])
    
    if cutoff_date is None:
        cutoff_date = datetime(2026, 3, 1)  # Only March onwards from API
    
    orders = []
    for o in orders_data:
        ts = datetime.fromisoformat(o["created_at"].replace("Z", "+00:00")).replace(tzinfo=None)
        if ts >= cutoff_date and o.get("amount_cents", 0) > 0:
            product_name = o.get("product_name", "Unknown")
            # Normalize product name
            if "FE MECHANICAL" in product_name.upper() or "FE EXAM" in product_name.upper():
                product = "FE"
            elif "HVAC" in product_name.upper():
                product = "HVAC"
            elif "Thermal" in product_name or "Fluids" in product_name or "TFS" in product_name:
                product = "TFS"
            elif "FUNDAMENTALS" in product_name.upper():
                product = "Fundamentals"
            elif "CRITICAL SYSTEMS" in product_name.upper() or "CSE" in product_name.upper():
                product = "CSE"
            elif "DAILY INSIGHTS" in product_name.upper():
                product = "DailyInsightsPremium"
            elif "PRACTICE PROBLEMS" in product_name.upper() or "EBOOK" in product_name.upper():
                if "HVAC" in product_name.upper():
                    product = "HVACBook"
                else:
                    product = "TFSBook"
            else:
                product = "Other"
            
            # Use item-level product price (excludes sales tax collected for govt)
            # order-level amount_cents includes tax; items[].amount_dollars is the product price
            items = o.get("items", [])
            if items:
                product_price = sum(float(item.get("amount_dollars", 0)) for item in items)
            else:
                product_price = o.get("amount_cents", 0) / 100  # fallback

            is_subscription = o.get("subscription", False)
            
            orders.append({
                "date": ts.strftime("%Y-%m-%d"),
                "timestamp": ts,
                "customer": o.get("user_name", "Unknown"),
                "product": product,
                "amount": product_price,
                "subscription": is_subscription,
                "order_id": str(o.get("id", "")),  # needed for dedup against webhook log
            })
    
    return orders

WEBHOOK_LOG_URL = "https://btc.mechanicalpeexamprep.com/orders-log?secret=exJJYXW2UebdDgJWicFr"

def fetch_webhook_log(cutoff_date=None):
    """Fetch orders from the webhook log on the droplet.
    Only adds entries not already covered by the API (avoids double-counting).
    Returns orders with their API order_ids for deduplication.
    """
    if cutoff_date is None:
        cutoff_date = datetime(2026, 3, 1)

    try:
        response = requests.get(WEBHOOK_LOG_URL, timeout=10)
        entries = response.json()
        if not isinstance(entries, list):
            print(f"  Warning: Webhook log returned unexpected format: {entries}")
            return [], set()
    except Exception as e:
        print(f"  Warning: Could not fetch webhook log: {e}")
        return [], set()

    orders = []
    seen_order_ids = set()

    for e in entries:
        if not e.get("date"):
            continue
        ts = datetime.strptime(e["date"], "%Y-%m-%d")
        if ts < cutoff_date:
            continue
        if e.get("amount", 0) <= 0:
            continue  # skip refunds and $0 entries for now

        order_id = e.get("order_id")
        seen_order_ids.add(order_id)

        orders.append({
            "date": e["date"],
            "timestamp": ts,
            "customer": e.get("customer", "Unknown"),
            "product": e.get("product", "Other"),
            "amount": e.get("amount", 0),
            "order_id": order_id,
            "source": e.get("source", "webhook"),
        })

    return orders, seen_order_ids


def build_dashboard():
    """Build the sales dashboard HTML with live data."""
    today = datetime.now()

    # Dynamic current-month helpers
    current_month_key   = today.strftime("%Y-%m")          # e.g. "2026-03"
    current_month_label = today.strftime("%B %Y")           # e.g. "March 2026"
    month_last_day      = calendar.monthrange(today.year, today.month)[1]
    month_end           = datetime(today.year, today.month, month_last_day)

    # API cutoff: first day of the current month
    api_cutoff = datetime(today.year, today.month, 1)

    # Manual data: Thinkific-era March 2026 sales only (Jan/Feb moved to HISTORICAL_MONTHLY_BREAKDOWN)
    manual_orders = []
    for row in MANUAL_DATA_MARCH:
        date, product, amount = row[0], row[1], row[2]
        sub_type = row[3] if len(row) > 3 else None
        manual_orders.append({
            "date": date,
            "timestamp": datetime.strptime(date, "%Y-%m-%d"),
            "customer": "Manual",
            "product": product,
            "amount": amount,
            "order_id": None,
            "source": "thinkific",
            "sub_type": sub_type,
        })

    # Stripe: full history from DASHBOARD_START_DATE (paginated, includes renewals)
    print(f"Fetching Stripe data (from {DASHBOARD_START_DATE.strftime('%Y-%m-%d')})...")
    stripe_orders = fetch_stripe_all_data(DASHBOARD_START_DATE)
    print(f"  Stripe total: {len(stripe_orders)} orders")

    # Webhook log: BTC sales only — Stripe entries are now pulled directly from API
    print("Fetching webhook log (BTC only)...")
    webhook_orders_raw, _ = fetch_webhook_log(DASHBOARD_START_DATE)
    stripe_ids = {o["session_id"] for o in stripe_orders if o.get("session_id")}
    TEST_NAMES = {'test customer', 'test tunnel', 'telegram works'}
    webhook_orders = [
        o for o in webhook_orders_raw
        if o.get("source") == "btcpay_webhook"           # BTC only — Stripe pulled from API
        and (o.get("amount") or 0) > 0
        and (o.get("customer") or "").lower() not in TEST_NAMES
        and o.get("order_id") not in stripe_ids          # safety dedup
    ]
    print(f"  Webhook BTC: {len(webhook_orders)} entries")

    # Combine: manual Thinkific + Stripe API + BTC webhook
    # Manual data must be Thinkific-only (no Stripe overlap) — see MANUAL_DATA comments
    all_orders = manual_orders + stripe_orders + webhook_orders
    all_orders.sort(key=lambda x: x["timestamp"])

    # Current-month orders (live)
    current_orders = [
        o for o in all_orders
        if o["timestamp"].year == today.year and o["timestamp"].month == today.month
    ]
    current_orders.sort(key=lambda x: x["timestamp"])
    current_revenue = sum(o["amount"] for o in current_orders)

    # Trailing 12-month stats: 11 complete months from MONTHLY_HISTORY + current month live
    trailing_11 = MONTHLY_HISTORY[-11:]
    trailing_revenue = sum(r for _, _, r in trailing_11) + current_revenue
    trailing_orders_count = sum(o for _, o, _ in trailing_11) + len(current_orders)
    avg_daily = trailing_revenue / 365
    avg_orders_per_month = trailing_orders_count / 12

    # YTD: completed months from MONTHLY_HISTORY + current month live
    ytd_completed = [
        (m, o, r) for m, o, r in MONTHLY_HISTORY
        if m.startswith(str(today.year)) and m < current_month_key
    ]
    total_revenue_ytd = sum(r for _, _, r in ytd_completed) + current_revenue

    # Days remaining in current month
    days_remaining = max(0, (month_end - today).days + 1)
    projected_current = current_revenue + (avg_daily * days_remaining)

    # Monthly breakdown (live orders)
    monthly_data = defaultdict(lambda: defaultdict(float))
    for o in all_orders:
        month_key = o["timestamp"].strftime("%Y-%m")
        monthly_data[month_key][o["product"]] += o["amount"]

    # Inject closed-month product breakdown for bar chart (Jan/Feb from verified Thinkific data)
    for month_key, breakdown in HISTORICAL_MONTHLY_BREAKDOWN.items():
        if month_key not in monthly_data:  # don't overwrite if live data exists
            for product, amount in breakdown.items():
                monthly_data[month_key][product] += amount

    sorted_months = sorted(monthly_data.keys())

    print(f"\nStatistics ({today.year} YTD):")
    print(f"  YTD revenue: ${round(total_revenue_ytd):,}")
    print(f"  Days elapsed ({today.year} YTD): {(today - datetime(today.year, 1, 1)).days + 1}")
    print(f"  Daily average: ${round(avg_daily):,}")
    print(f"  {current_month_label} revenue so far: ${round(current_revenue):,}")
    print(f"  Days remaining in {today.strftime('%B')}: {days_remaining}")
    print(f"  Projected {today.strftime('%B')} total: ${round(projected_current):,}")
    
    # Pie chart data (current month only)
    pie_data = {}
    for o in current_orders:
        pie_data[o["product"]] = pie_data.get(o["product"], 0) + o["amount"]
    pie_data = {k: round(v) for k, v in pie_data.items()}
    
    # Pie chart with percentages
    pie_total = sum(pie_data.values())
    pie_pct = {k: round(100 * v / pie_total) if pie_total > 0 else 0 for k, v in pie_data.items()}
    
    # Bar chart data — 2026 only (product stacking available for all 2026 months)
    bar_months = []
    bar_products = set()
    for o in all_orders:
        bar_products.add(o["product"])

    bar_products = sorted(list(bar_products))
    bar_datasets = {}
    for product in bar_products:
        bar_datasets[product] = []

    months_2026 = [m for m in sorted_months if m.startswith("2026")]
    for month in months_2026:
        bar_months.append(month)
        for product in bar_products:
            bar_datasets[product].append(round(monthly_data[month].get(product, 0)))

    # Calculate Y-axis max: highest monthly total rounded up to nearest 5000
    import math
    monthly_totals_py = [sum(monthly_data[m].values()) for m in months_2026]
    max_monthly = max(monthly_totals_py) if monthly_totals_py else 0
    y_axis_max = math.ceil(max_monthly / 5000) * 5000

    # Build HTML
    # Build current-month stats for the projection card
    current_month_orders_count = len(current_orders)

    html_top = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sales Dashboard - Mechanical PE Exam Prep</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg: #f5f7fa;
            --surface: #ffffff;
            --surface2: #f0f2f5;
            --border: #dde1e7;
            --text: #333333;
            --muted: #777777;
            --blue: #2563eb;
            --red: #dc2626;
        }

        /* ── Auth overlay ── */
        #auth-overlay {
          position: fixed; top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(0,0,0,0.6);
          display: flex; align-items: center; justify-content: center;
          z-index: 9999;
        }
        .auth-box {
          background: var(--surface); border: 1px solid var(--border);
          border-radius: 8px; padding: 32px; width: 100%; max-width: 280px; text-align: center;
        }
        .auth-logo { font-size: 36px; margin-bottom: 12px; }
        .auth-title { font-size: 20px; font-weight: 700; color: var(--text); margin-bottom: 4px; }
        .auth-sub   { font-size: 13px; color: var(--muted); margin-bottom: 28px; }
        .auth-box input {
          width: 100%; padding: 8px 12px; background: var(--surface2);
          border: 1px solid var(--border); border-radius: 4px;
          color: var(--text); font-size: 13px; margin-bottom: 8px;
        }
        .auth-box input:focus { border-color: var(--blue); outline: none; }
        .auth-box button {
          width: 100%; padding: 8px 12px; background: var(--blue);
          color: #fff; border: none; border-radius: 4px;
          font-size: 14px; font-weight: 600; cursor: pointer;
        }
        .auth-box button:hover  { opacity: 0.88; }
        .auth-box button:disabled { opacity: 0.55; cursor: default; }
        #pwd-error { display: none; color: var(--red); font-size: 11px; margin-bottom: 8px; }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f7fa;
            color: #333;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }
        .header-info {
            display: flex;
            gap: 30px;
            font-size: 14px;
            color: #666;
        }
        .dashboard-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .card h2 {
            font-size: 16px;
            margin-bottom: 15px;
            color: #444;
            font-weight: 600;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            margin-top: 15px;
        }
        th {
            background: #f8f9fa;
            padding: 8px;
            text-align: left;
            font-weight: 600;
            color: #555;
            border-bottom: 2px solid #e0e0e0;
        }
        td {
            padding: 8px;
            border-bottom: 1px solid #f0f0f0;
        }
        tr:hover {
            background: #f9f9f9;
        }
        .metric-label {
            font-size: 12px;
            color: #777;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .metric-value {
            font-size: 24px;
            font-weight: 700;
            color: #2c3e50;
            margin-top: 5px;
        }
        .projection-note {
            font-size: 12px;
            color: #999;
            margin-top: 10px;
            font-style: italic;
        }
        .chart-container {
            position: relative;
            height: 300px;
        }
        .full-width {
            grid-column: 1 / -1;
        }
        .last-updated {
            text-align: right;
            font-size: 12px;
            color: #999;
            margin-top: 15px;
        }
        .totals-table {
            margin: 15px 0 0 0;
        }
        .totals-table td {
            text-align: center;
        }
        .totals-table th {
            text-align: center;
        }
        /* Row coloring by product */
        tr[data-product="HVAC"] {
            background-color: rgba(255, 215, 0, 0.1);
        }
        tr[data-product="TFS"] {
            background-color: rgba(52, 152, 219, 0.1);
        }
        tr[data-product="FE"] {
            background-color: rgba(231, 76, 60, 0.1);
        }
        tr[data-product="HVAC"]:hover {
            background-color: rgba(255, 215, 0, 0.2);
        }
        tr[data-product="TFS"]:hover {
            background-color: rgba(52, 152, 219, 0.2);
        }
        tr[data-product="FE"]:hover {
            background-color: rgba(231, 76, 60, 0.2);
        }
    </style>
</head>
<body>

<!-- ── Auth overlay ── -->
<div id="auth-overlay">
  <div class="auth-box">
    <div class="auth-logo">♠️</div>
    <div class="auth-title">MPEP Dashboard</div>
    <div class="auth-sub">Internal use only — enter your password to continue</div>
    <form id="auth-form">
      <input type="password" id="pwd-input" placeholder="Password" autocomplete="current-password" />
      <div id="pwd-error"></div>
      <button type="submit" id="pwd-btn">Unlock</button>
    </form>
  </div>
</div>

<div id="main-content">
    <div class="container">
        <header>
            <h1>💰 Sales Dashboard</h1>
            <div class="header-info">
                <div><strong>Period:</strong> """ + str(today.year) + """ YTD (Jan - """ + today.strftime('%b %d') + """)</div>
                <div><strong>Updated:</strong> """ + today.strftime('%b %d, %Y at %I:%M %p') + """</div>
            </div>
        </header>

        <!-- Projection Box -->
        <div class="card full-width" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
            <h2 style="color: white; margin-bottom: 15px;">📊 """ + current_month_label + """ Projection</h2>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr; gap: 20px;">
                <div>
                    <div class="metric-label" style="color: rgba(255,255,255,0.8);">This Month (So Far)</div>
                    <div class="metric-value" style="color: white;">$""" + f"{round(current_revenue):,}" + """</div>
                </div>
                <div>
                    <div class="metric-label" style="color: rgba(255,255,255,0.8);">Daily Average (Trailing 12mo)</div>
                    <div class="metric-value" style="color: white;">$""" + f"{round(avg_daily):,}" + """</div>
                </div>
                <div>
                    <div class="metric-label" style="color: rgba(255,255,255,0.8);">Orders This Month</div>
                    <div class="metric-value" style="color: white;">""" + f"{current_month_orders_count} <span style='font-size:0.5em; font-weight:400;'>vs {round(avg_orders_per_month, 1)} avg</span>" + """</div>
                </div>
                <div>
                    <div class="metric-label" style="color: rgba(255,255,255,0.8);">Days Remaining</div>
                    <div class="metric-value" style="color: white;">""" + str(days_remaining) + """</div>
                </div>
                <div>
                    <div class="metric-label" style="color: rgba(255,255,255,0.8);">Projected Total</div>
                    <div class="metric-value" style="color: #fff;">$""" + f"{round(projected_current):,}" + """</div>
                </div>
            </div>
            <div class="projection-note" style="color: rgba(255,255,255,0.8);">
                Based on trailing 12-month daily average ($""" + f"{round(avg_daily):,}" + """/day · $""" + f"{round(trailing_revenue):,}" + """ over 365 days)
            </div>
        </div>

        <div class="dashboard-grid">
            <!-- Pie Chart + Table -->
            <div class="card">
                <h2>""" + current_month_label + """ Revenue by Product</h2>
                <div class="chart-container">
                    <canvas id="pieChart"></canvas>
                </div>
                <table class="totals-table">
                    <thead>
                        <tr>
                            <th>Product</th>
                            <th>Revenue</th>
                            <th>%</th>
                        </tr>
                    </thead>
                    <tbody id="pieTableBody">
                    </tbody>
                </table>
            </div>

            <!-- Transactions Table (current month) -->
            <div class="card">
                <h2>Orders this Month</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Product</th>
                            <th>Source</th>
                            <th style="text-align: center;">Revenue</th>
                        </tr>
                    </thead>
                    <tbody id="marchOrdersBody">
"""

    def order_product_label(o):
        label = o['product']
        if label == 'FE' and o.get('sub_type'):
            label = f"FE · {o['sub_type']}"
        return label

    def order_source_label(o):
        src = o.get('source', '')
        if src == 'thinkific':
            return 'Thinkific'
        elif src in ('stripe_checkout', 'stripe_invoice'):
            return 'Stripe'
        elif src == 'btcpay_webhook':
            return 'BTC'
        return '—'

    # Add current-month orders to table
    for o in current_orders:
        prod_label = order_product_label(o)
        src_label = order_source_label(o)
        html_top += f"                        <tr data-product=\"{o['product']}\"><td>{o['date']}</td><td>{prod_label}</td><td>{src_label}</td><td style=\"text-align: center;\">${round(o['amount']):,}</td></tr>\n"
    
    html_middle = """                    </tbody>
                </table>
            </div>

            <!-- Stacked Bar Chart -->
            <div class="card full-width">
                <h2>Revenue by Product - 2026 YTD</h2>
                <div class="chart-container" style="height: 350px;">
                    <canvas id="barChart"></canvas>
                </div>
            </div>
        </div>

        <div class="last-updated">
            Auto-refreshes every 30 minutes
        </div>
    </div>
    <script>
        function onAuthenticated() {
        // Color mapping for products
        const productColors = {
            'HVAC': '#FFD700',              // Yellow
            'TFS': '#3498DB',               // Blue
            'FE': '#E74C3C',                // Red
            'Fundamentals': '#27AE60',      // Green
            'CSE': '#8E44AD',               // Purple
            'DailyInsightsPremium': '#F39C12', // Orange
            'HVACBook': '#F1C40F',          // Gold
            'TFSBook': '#2980B9',           // Dark blue
            'Other': '#95A5A6'              // Gray
        };
        
        function getProductColor(product) {
            return productColors[product] || '#95A5A6';
        }
        
        // Pie Chart
        const pieData = """ + json.dumps(pie_data) + """;
        const piePct = """ + json.dumps(pie_pct) + """;
        const pieLabels = Object.keys(pieData);
        const pieValues = Object.values(pieData);
        const pieColors = pieLabels.map(label => getProductColor(label));
        
        // Populate totals table
        const pieTableBody = document.getElementById('pieTableBody');
        pieLabels.forEach(label => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${label}</td>
                <td>$${pieData[label].toLocaleString()}</td>
                <td>${piePct[label]}%</td>
            `;
            pieTableBody.appendChild(row);
        });
        
        const ctxPie = document.getElementById('pieChart').getContext('2d');
        new Chart(ctxPie, {
            type: 'doughnut',
            data: {
                labels: pieLabels.map(label => `${label} (${piePct[label]}%)`),
                datasets: [{
                    data: pieValues,
                    backgroundColor: pieColors,
                    borderColor: '#fff',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { font: { size: 12 } }
                    }
                }
            }
        });

        // Bar Chart
        const barMonths = """ + json.dumps(bar_months) + """;
        const barProducts = """ + json.dumps(bar_products) + """;
        const barDatasets = """ + json.dumps(bar_datasets) + """;
        
        const datasets = barProducts.map((product, idx) => ({
            label: product,
            data: barDatasets[product],
            backgroundColor: getProductColor(product),
            borderRadius: 4,
            borderSkipped: false
        }));
        
        // Calculate monthly totals and March projection
        const monthlyTotals = [];
        barMonths.forEach((month, idx) => {
            const total = barProducts.reduce((sum, product) => sum + barDatasets[product][idx], 0);
            monthlyTotals.push(total);
        });
        
        const marchIdx = barMonths.length - 1;
        const marchCurrent = monthlyTotals[marchIdx];
        const marchProjected = """ + json.dumps(round(projected_current)) + """;
        const marchMax = Math.max(marchCurrent, marchProjected);
        
        // Plugin to draw labels
        const totalLabelsPlugin = {
            id: 'totalLabels',
            afterDatasetsDraw(chart) {
                const ctx = chart.ctx;
                const xScale = chart.scales.x;
                const yScale = chart.scales.y;
                
                ctx.textAlign = 'center';
                
                // Draw monthly totals above bars
                monthlyTotals.forEach((total, idx) => {
                    const xPos = xScale.getPixelForValue(idx);
                    const yPos = yScale.getPixelForValue(total);
                    
                    ctx.font = 'bold 12px Arial';
                    ctx.fillStyle = '#333';
                    ctx.fillText('$' + total.toLocaleString(), xPos, yPos - 15);
                });
                
                // Draw March projection label
                if (marchProjected > marchCurrent) {
                    const xPos = xScale.getPixelForValue(marchIdx);
                    const projYPos = yScale.getPixelForValue(marchProjected);
                    
                    ctx.font = 'italic 11px Arial';
                    ctx.fillStyle = '#999';
                    ctx.fillText('$' + marchProjected.toLocaleString() + ' (proj)', xPos, projYPos - 15);
                    
                    // Draw dotted box for projection
                    ctx.strokeStyle = 'rgba(150, 150, 150, 0.3)';
                    ctx.setLineDash([5, 5]);
                    ctx.lineWidth = 1.5;
                    ctx.fillStyle = 'rgba(200, 200, 200, 0.05)';
                    
                    const barWidth = xScale.width / barMonths.length * 0.7;
                    const currentY = yScale.getPixelForValue(marchCurrent);
                    const projHeight = currentY - projYPos;
                    
                    ctx.fillRect(xPos - barWidth/2, projYPos, barWidth, projHeight);
                    ctx.strokeRect(xPos - barWidth/2, projYPos, barWidth, projHeight);
                    ctx.setLineDash([]);
                }
            }
        };
        
        const ctxBar = document.getElementById('barChart').getContext('2d');
        new Chart(ctxBar, {
            type: 'bar',
            data: {
                labels: barMonths.map(m => {
                    const [year, month] = m.split('-');
                    return new Date(year, parseInt(month) - 1).toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
                }),
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { font: { size: 12 } }
                    }
                },
                scales: {
                    x: { stacked: true },
                    y: { 
                        stacked: true,
                        max: """ + str(y_axis_max) + """
                    }
                }
            },
            plugins: [totalLabelsPlugin]
        });
    }
    </script>
</div><!-- end main-content -->
<script src="auth.js"></script>
</body>
</html>"""
    
    html = html_top + html_middle
    
    # Write output
    output_path = "/home/mpepagent/.openclaw/workspace/projects/mpep-dashboard/sales.html"
    with open(output_path, "w") as f:
        f.write(html)
    
    print(f"\n✅ Dashboard built: {output_path}")
    return output_path

if __name__ == "__main__":
    build_dashboard()
