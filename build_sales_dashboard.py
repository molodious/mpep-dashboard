#!/usr/bin/env python3
"""
Build sales dashboard with real Stripe + Thinkific data.
Uses manual data for Jan/Feb 2026, API data for March 2026+.
"""

import json
import requests
import os
from datetime import datetime, timedelta
from collections import defaultdict

# Load from environment variables
STRIPE_KEY = os.environ.get("STRIPE_READONLY_KEY", "")
THINKIFIC_KEY = os.environ.get("THINKIFIC_API_KEY", "")
THINKIFIC_SUBDOMAIN = "mechanicalpeexamprep"

if not STRIPE_KEY or not THINKIFIC_KEY:
    print("ERROR: Missing API keys. Set STRIPE_READONLY_KEY and THINKIFIC_API_KEY env vars.")
    exit(1)

# Manual data for Jan/Feb 2026
MANUAL_DATA_JAN_FEB = [
    ("2026-02-26", "FE", 599),
    ("2026-02-22", "FE", 249),
    ("2026-02-21", "HVAC", 1999),
    ("2026-02-20", "TFS", 1999),
    ("2026-02-20", "TFS", 649),
    ("2026-02-20", "Other", 99),  # Daily Insights Premium
    ("2026-02-17", "TFS", 1899),
    ("2026-02-17", "TFS", 1999),
    ("2026-02-15", "FE", 599),
    ("2026-02-13", "FE", 149),
    ("2026-02-11", "FE", 249),
    ("2026-02-06", "FE", 249),
    ("2026-02-06", "HVAC", 1899),
    ("2026-02-05", "TFS", 1999),
    ("2026-02-03", "HVAC", 1999),
    ("2026-02-02", "HVAC", 1999),
    ("2026-02-02", "TFS", 1999),
    ("2026-02-02", "HVAC", 1999),
    ("2026-02-01", "TFS", 1999),
    ("2026-02-01", "HVAC", 1999),
    ("2026-01-30", "HVAC", 1999),
    ("2026-01-26", "HVAC", 1999),
    ("2026-01-25", "HVAC", 1999),
    ("2026-01-24", "HVAC", 1999),
    ("2026-01-22", "FE", 249),
    ("2026-01-21", "HVAC", 1899),
    ("2026-01-21", "HVAC", 1899),
    ("2026-01-20", "HVAC", 649),
    ("2026-01-17", "HVAC", 1999),
    ("2026-01-16", "HVAC", 1999),
    ("2026-01-15", "HVAC", 1999),
    ("2026-01-14", "HVAC", 1999),
    ("2026-01-14", "HVAC", 1999),
    ("2026-01-14", "HVAC", 1999),
    ("2026-01-14", "Other", 399),  # Mechanical PE Fundamentals
    ("2026-01-13", "FE", 149),
    ("2026-01-11", "FE", 249),
    ("2026-01-08", "Other", 399),  # Critical Systems Engineering
    ("2026-01-07", "HVAC", 649),
    ("2026-01-06", "HVAC", 649),
    ("2026-01-05", "HVAC", 1999),
    ("2026-01-05", "FE", 249),
    ("2026-01-05", "TFS", 1899),
    ("2026-01-05", "TFS", 1999),
    ("2026-01-05", "HVAC", 1999),
    ("2026-01-04", "FE", 599),
    ("2026-01-04", "HVAC", 1999),
    ("2026-01-04", "HVAC", 1999),
    ("2026-01-03", "HVAC", 1999),
]

# Manual data for March 2026 (FE subscriptions missing from Thinkific API)
MANUAL_DATA_MARCH = [
    ("2026-03-13", "FE", 149),   # FE Mechanical Exam Prep Course 1mo (missing from API)
    ("2026-03-12", "FE", 249),   # FE Mechanical Exam Prep Course 1mo (missing from API)
    ("2026-03-05", "FE", 249),   # FE Mechanical Exam Prep Course 1mo (missing from API)
    ("2026-03-22", "FE", 249),   # FE Mechanical Exam Prep Course 1mo (missing from API)
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
    ("2026-03", 15, 21685),  # complete manual data
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

def fetch_stripe_data(cutoff_date=None):
    """Fetch Stripe checkout sessions."""
    response = requests.get(
        "https://api.stripe.com/v1/checkout/sessions",
        headers={"Authorization": f"Bearer {STRIPE_KEY}"},
        params={"limit": 100}
    )
    sessions = response.json().get("data", [])
    
    if cutoff_date is None:
        cutoff_date = datetime(2026, 3, 1)  # Only March onwards from API
    
    orders = []
    for s in sessions:
        ts = datetime.fromtimestamp(s["created"])
        if ts >= cutoff_date and s.get("payment_status") == "paid":
            customer_details = s.get("customer_details") or {}
            product = s.get("metadata", {}).get("bundleId", "").replace("bundle_", "").upper() or "Unknown"
            # Normalize
            if "HVAC" in product:
                product = "HVAC"
            elif "TFS" in product:
                product = "TFS"
            
            session_id = s.get("id")
            # Apply manual corrections for wrong metadata
            if session_id in STRIPE_LABEL_CORRECTIONS:
                product = STRIPE_LABEL_CORRECTIONS[session_id]

            orders.append({
                "date": ts.strftime("%Y-%m-%d"),
                "timestamp": ts,
                "customer": customer_details.get("name", "Unknown"),
                "product": product,
                "amount": stripe_clean_amount(s.get("amount_total", 0)),
                "session_id": session_id,  # used for webhook dedup
            })
    
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
            if "FE" in product_name.upper():
                product = "FE"
            elif "HVAC" in product_name.upper():
                product = "HVAC"
            elif "Thermal" in product_name or "Fluids" in product_name or "TFS" in product_name:
                product = "TFS"
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
            })
    
    return orders

WEBHOOK_LOG_URL = "http://btc.mechanicalpeexamprep.com:3002/orders-log?secret=exJJYXW2UebdDgJWicFr"

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
    
    # Manual data for Jan/Feb + March (missing API entries — legacy, webhook replaces going forward)
    all_manual_data = MANUAL_DATA_JAN_FEB + MANUAL_DATA_MARCH
    manual_orders = [
        {
            "date": date,
            "timestamp": datetime.strptime(date, "%Y-%m-%d"),
            "customer": "Manual",
            "product": product,
            "amount": amount,
            "order_id": None,
        }
        for date, product, amount in all_manual_data
    ]
    
    # API data for March onwards
    print("Fetching API data (March 2026+)...")
    stripe_orders = fetch_stripe_data(datetime(2026, 3, 1))
    thinkific_orders = fetch_thinkific_data(datetime(2026, 3, 1))
    print(f"  Stripe: {len(stripe_orders)} orders")
    print(f"  Thinkific: {len(thinkific_orders)} orders")

    # Webhook log — adds subscription renewals and anything the API missed
    print("Fetching webhook log...")
    webhook_orders_raw, webhook_order_ids = fetch_webhook_log(datetime(2026, 3, 1))

    # Collect order IDs already known from API to avoid double-counting
    api_order_ids = set()
    for o in thinkific_orders:
        if o.get("order_id"):
            api_order_ids.add(o["order_id"])
    for o in stripe_orders:
        if o.get("session_id"):
            api_order_ids.add(o["session_id"])

    # Only keep webhook entries not already in API data
    webhook_orders = [o for o in webhook_orders_raw if o.get("order_id") not in api_order_ids]
    print(f"  Webhook: {len(webhook_orders_raw)} total, {len(webhook_orders)} new (not in API)")

    # Combine all
    all_orders = manual_orders + stripe_orders + thinkific_orders + webhook_orders
    all_orders.sort(key=lambda x: x["timestamp"])
    
    # March 2026 data calculated live from all_orders (includes API + manual entries)
    march_orders = [o for o in all_orders if o["timestamp"].month == 3 and o["timestamp"].year == 2026]
    march_orders.sort(key=lambda x: x["timestamp"])
    march_revenue = sum(o["amount"] for o in march_orders)
    current_month_orders = len(march_orders)
    current_month_revenue = march_revenue

    # --- Trailing 12-month stats: 11 complete months from history + March live ---
    trailing_12 = MONTHLY_HISTORY[-12:-1]  # 11 completed months (2025-04 through 2026-02)
    trailing_revenue = sum(r for _, _, r in trailing_12) + march_revenue
    trailing_orders = sum(o for _, o, _ in trailing_12) + len(march_orders)
    avg_daily = trailing_revenue / 365
    avg_orders_per_month = trailing_orders / 12

    # YTD 2026: Jan + Feb from MONTHLY_HISTORY (complete months) + March live
    ytd_completed = [(m, o, r) for m, o, r in MONTHLY_HISTORY if m.startswith("2026") and m < "2026-03"]
    total_revenue_ytd = sum(r for _, _, r in ytd_completed) + march_revenue

    # Days remaining in March
    march_end = datetime(2026, 3, 31)
    days_remaining = max(0, (march_end - today).days + 1)
    projected_march = march_revenue + (avg_daily * days_remaining)
    
    # Monthly breakdown
    monthly_data = defaultdict(lambda: defaultdict(float))
    for o in all_orders:
        month_key = o["timestamp"].strftime("%Y-%m")
        monthly_data[month_key][o["product"]] += o["amount"]
    
    sorted_months = sorted(monthly_data.keys())
    
    print(f"\nStatistics (2026 YTD):")
    print(f"  YTD revenue: ${round(total_revenue_ytd):,}")
    print(f"  Days elapsed (2026 YTD): {(today - datetime(2026, 1, 1)).days + 1}")
    print(f"  Daily average: ${round(avg_daily):,}")
    print(f"  March revenue so far: ${round(march_revenue):,}")
    print(f"  Days remaining in March: {days_remaining}")
    print(f"  Projected March total: ${round(projected_march):,}")
    
    # Pie chart data (March only)
    pie_data = {}
    for o in march_orders:
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
                <div><strong>Period:</strong> 2026 YTD (Jan - Mar 21)</div>
                <div><strong>Updated:</strong> """ + today.strftime('%b %d, %Y at %I:%M %p') + """</div>
            </div>
        </header>

        <!-- Projection Box -->
        <div class="card full-width" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
            <h2 style="color: white; margin-bottom: 15px;">📊 March 2026 Projection</h2>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr; gap: 20px;">
                <div>
                    <div class="metric-label" style="color: rgba(255,255,255,0.8);">This Month (So Far)</div>
                    <div class="metric-value" style="color: white;">$""" + f"{round(march_revenue):,}" + """</div>
                </div>
                <div>
                    <div class="metric-label" style="color: rgba(255,255,255,0.8);">Daily Average (Trailing 12mo)</div>
                    <div class="metric-value" style="color: white;">$""" + f"{round(avg_daily):,}" + """</div>
                </div>
                <div>
                    <div class="metric-label" style="color: rgba(255,255,255,0.8);">Orders This Month</div>
                    <div class="metric-value" style="color: white;">""" + f"{current_month_orders} <span style='font-size:0.5em; font-weight:400;'>vs {round(avg_orders_per_month, 1)} avg</span>" + """</div>
                </div>
                <div>
                    <div class="metric-label" style="color: rgba(255,255,255,0.8);">Days Remaining</div>
                    <div class="metric-value" style="color: white;">""" + str(days_remaining) + """</div>
                </div>
                <div>
                    <div class="metric-label" style="color: rgba(255,255,255,0.8);">Projected Total</div>
                    <div class="metric-value" style="color: #fff;">$""" + f"{round(projected_march):,}" + """</div>
                </div>
            </div>
            <div class="projection-note" style="color: rgba(255,255,255,0.8);">
                Based on trailing 12-month daily average ($""" + f"{round(avg_daily):,}" + """/day · $""" + f"{round(trailing_revenue):,}" + """ over 365 days)
            </div>
        </div>

        <div class="dashboard-grid">
            <!-- Pie Chart + Table -->
            <div class="card">
                <h2>March Revenue by Product</h2>
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

            <!-- Transactions Table (March) -->
            <div class="card">
                <h2>Orders this Month</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Product</th>
                            <th style="text-align: center;">Revenue</th>
                        </tr>
                    </thead>
                    <tbody id="marchOrdersBody">
"""
    
    # Add March orders to table (will use JavaScript for row coloring)
    for o in march_orders:
        html_top += f"                        <tr data-product=\"{o['product']}\"><td>{o['date']}</td><td>{o['product']}</td><td style=\"text-align: center;\">${round(o['amount']):,}</td></tr>\n"
    
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
            'HVAC': '#FFD700',    // Yellow
            'TFS': '#3498DB',      // Blue
            'FE': '#E74C3C',       // Red
            'Other': '#95A5A6'     // Gray
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
        const marchProjected = """ + json.dumps(round(projected_march)) + """;
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
