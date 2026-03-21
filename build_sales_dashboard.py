#!/usr/bin/env python3
"""
Build sales dashboard with real Stripe + Thinkific data.
Pulls 2026 YTD data + March, generates HTML dashboard.
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

def fetch_stripe_data(cutoff_date=None):
    """Fetch Stripe checkout sessions."""
    response = requests.get(
        "https://api.stripe.com/v1/checkout/sessions",
        headers={"Authorization": f"Bearer {STRIPE_KEY}"},
        params={"limit": 100}
    )
    sessions = response.json().get("data", [])
    
    if cutoff_date is None:
        cutoff_date = datetime(2026, 1, 1)  # Jan 1, 2026
    
    orders = []
    for s in sessions:
        ts = datetime.fromtimestamp(s["created"])
        if ts >= cutoff_date and s.get("payment_status") == "paid":
            customer_details = s.get("customer_details") or {}
            orders.append({
                "date": ts.strftime("%Y-%m-%d"),
                "timestamp": ts,
                "customer": customer_details.get("name", "Unknown"),
                "product": s.get("metadata", {}).get("bundleId", "").replace("bundle_", "").upper() or "Unknown",
                "amount": s.get("amount_total", 0) / 100,
                "source": "Stripe"
            })
    
    return orders

def fetch_thinkific_data(cutoff_date=None):
    """Fetch Thinkific orders."""
    headers = {
        "X-Auth-API-Key": THINKIFIC_KEY,
        "X-Auth-Subdomain": THINKIFIC_SUBDOMAIN,
    }
    response = requests.get(f"https://{THINKIFIC_SUBDOMAIN}.thinkific.com/api/public/v1/orders?limit=500", headers=headers)
    orders_data = response.json().get("items", [])
    
    if cutoff_date is None:
        cutoff_date = datetime(2026, 1, 1)  # Jan 1, 2026
    
    orders = []
    for o in orders_data:
        ts = datetime.fromisoformat(o["created_at"].replace("Z", "+00:00")).replace(tzinfo=None)
        if ts >= cutoff_date and o.get("amount_cents", 0) > 0:
            orders.append({
                "date": ts.strftime("%Y-%m-%d"),
                "timestamp": ts,
                "customer": o.get("user_name", "Unknown"),
                "product": o.get("product_name", "Unknown"),
                "amount": o.get("amount_cents", 0) / 100,
                "source": "Thinkific"
            })
    
    return orders

def build_dashboard():
    """Build the sales dashboard HTML with live data."""
    today = datetime.now()
    year_start = datetime(2026, 1, 1)
    
    print("Fetching Stripe data (Jan 2026+)...")
    stripe_orders = fetch_stripe_data(year_start)
    print(f"  {len(stripe_orders)} orders")
    
    print("Fetching Thinkific data (Jan 2026+)...")
    thinkific_orders = fetch_thinkific_data(year_start)
    print(f"  {len(thinkific_orders)} orders")
    
    all_orders = stripe_orders + thinkific_orders
    all_orders.sort(key=lambda x: x["timestamp"])
    
    # Calculate statistics (YTD 2026)
    total_revenue_ytd = sum(o["amount"] for o in all_orders)
    days_in_period = (today - year_start).days + 1  # +1 to include today
    avg_daily = total_revenue_ytd / days_in_period
    
    # March 2026 data
    march_orders = [o for o in all_orders if o["timestamp"].month == 3 and o["timestamp"].year == 2026]
    march_orders.sort(key=lambda x: x["timestamp"])
    march_revenue = sum(o["amount"] for o in march_orders)
    
    # Days remaining in March
    march_end = datetime(2026, 3, 31)
    days_remaining = max(0, (march_end - today).days + 1)
    projected_march = march_revenue + (avg_daily * days_remaining)
    
    # Monthly breakdown
    monthly_data = defaultdict(lambda: defaultdict(float))
    for o in all_orders:
        month_key = o["timestamp"].strftime("%Y-%m")
        month_key_display = o["timestamp"].strftime("%b %y")
        monthly_data[month_key][o["product"]] += o["amount"]
    
    # Sort monthly data chronologically
    sorted_months = sorted(monthly_data.keys())
    
    # Build JavaScript data
    js_data = {
        "marchOrders": [
            {
                "date": o["date"],
                "product": o["product"],
                "amount": o["amount"]
            }
            for o in march_orders
        ],
        "monthlyData": {
            month: dict(monthly_data[month])
            for month in sorted_months
        },
        "projection": {
            "avgDaily": round(avg_daily, 2),
            "daysRemaining": days_remaining,
            "marchSoFar": round(march_revenue, 2),
            "projectedTotal": round(projected_march, 2)
        },
        "today": today.strftime("%Y-%m-%d")
    }
    
    print(f"\nStatistics (2026 YTD):")
    print(f"  YTD revenue: ${total_revenue_ytd:,.2f}")
    print(f"  Days elapsed: {days_in_period}")
    print(f"  Daily average: ${avg_daily:,.2f}")
    print(f"  March revenue so far: ${march_revenue:,.2f}")
    print(f"  Days remaining in March: {days_remaining}")
    print(f"  Projected March total: ${projected_march:,.2f}")
    
    # Read template
    with open("/home/mpepagent/.openclaw/workspace/projects/mpep-dashboard/sales_template.html", "r") as f:
        template = f.read()
    
    # Replace placeholder
    html = template.replace(
        "const dashboardData = {};",
        f"const dashboardData = {json.dumps(js_data, indent=4)};"
    )
    
    # Write output
    output_path = "/home/mpepagent/.openclaw/workspace/projects/mpep-dashboard/sales.html"
    with open(output_path, "w") as f:
        f.write(html)
    
    print(f"\n✅ Dashboard built: {output_path}")
    return output_path

if __name__ == "__main__":
    build_dashboard()
