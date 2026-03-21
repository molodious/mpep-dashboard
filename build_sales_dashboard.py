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
        cutoff_date = datetime(2026, 1, 1)
    
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
        cutoff_date = datetime(2026, 1, 1)
    
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
    days_in_period = (today - year_start).days + 1
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
        monthly_data[month_key][o["product"]] += o["amount"]
    
    # Sort monthly data chronologically
    sorted_months = sorted(monthly_data.keys())
    
    print(f"\nStatistics (2026 YTD):")
    print(f"  YTD revenue: ${total_revenue_ytd:,.2f}")
    print(f"  Days elapsed: {days_in_period}")
    print(f"  Daily average: ${avg_daily:,.2f}")
    print(f"  March revenue so far: ${march_revenue:,.2f}")
    print(f"  Days remaining in March: {days_remaining}")
    print(f"  Projected March total: ${projected_march:,.2f}")
    
    # Prepare chart data
    # Pie chart - March revenue by product
    pie_data = {}
    for o in march_orders:
        pie_data[o["product"]] = pie_data.get(o["product"], 0) + o["amount"]
    
    # Bar chart - monthly by product
    bar_months = []
    bar_products = set()
    for o in all_orders:
        bar_products.add(o["product"])
    
    bar_products = sorted(list(bar_products))
    bar_datasets = {}
    for product in bar_products:
        bar_datasets[product] = []
    
    for month in sorted_months:
        bar_months.append(month)
        for product in bar_products:
            bar_datasets[product].append(monthly_data[month].get(product, 0))
    
    # Build HTML - use string concatenation to avoid f-string issues
    html_top = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sales Dashboard - Mechanical PE Exam Prep</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
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
            font-size: 14px;
        }
        th {
            background: #f8f9fa;
            padding: 10px;
            text-align: left;
            font-weight: 600;
            color: #555;
            border-bottom: 2px solid #e0e0e0;
        }
        td {
            padding: 10px;
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
    </style>
</head>
<body>
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
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 20px;">
                <div>
                    <div class="metric-label" style="color: rgba(255,255,255,0.8);">This Month (So Far)</div>
                    <div class="metric-value" style="color: white;">$""" + f"{march_revenue:,.2f}" + """</div>
                </div>
                <div>
                    <div class="metric-label" style="color: rgba(255,255,255,0.8);">Daily Average (2026 YTD)</div>
                    <div class="metric-value" style="color: white;">$""" + f"{avg_daily:,.2f}" + """</div>
                </div>
                <div>
                    <div class="metric-label" style="color: rgba(255,255,255,0.8);">Days Remaining</div>
                    <div class="metric-value" style="color: white;">""" + str(days_remaining) + """</div>
                </div>
                <div>
                    <div class="metric-label" style="color: rgba(255,255,255,0.8);">Projected Total</div>
                    <div class="metric-value" style="color: #fff;">$""" + f"{projected_march:,.2f}" + """</div>
                </div>
            </div>
            <div class="projection-note" style="color: rgba(255,255,255,0.8);">
                Based on 2026 YTD average daily revenue ($""" + f"{avg_daily:,.2f}" + """/day over """ + str(days_in_period) + """ days)
            </div>
        </div>

        <div class="dashboard-grid">
            <!-- Pie Chart -->
            <div class="card">
                <h2>Revenue by Product (March)</h2>
                <div class="chart-container">
                    <canvas id="pieChart"></canvas>
                </div>
            </div>

            <!-- Transactions Table (March) -->
            <div class="card">
                <h2>Recent Orders (March)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Product</th>
                            <th style="text-align: right;">Revenue</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    # Add March orders to table
    for o in march_orders:
        html_top += f"                        <tr><td>{o['date']}</td><td>{o['product']}</td><td style=\"text-align: right;\">${o['amount']:,.2f}</td></tr>\n"
    
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
        const colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE'];
        
        // Pie Chart
        const pieData = """ + json.dumps(pie_data) + """;
        const pieLabels = Object.keys(pieData);
        const pieValues = Object.values(pieData);
        
        const ctxPie = document.getElementById('pieChart').getContext('2d');
        new Chart(ctxPie, {
            type: 'doughnut',
            data: {
                labels: pieLabels,
                datasets: [{
                    data: pieValues,
                    backgroundColor: colors.slice(0, pieLabels.length),
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
            backgroundColor: colors[idx % colors.length],
            borderRadius: 4,
            borderSkipped: false
        }));
        
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
                    y: { stacked: true }
                }
            }
        });
    </script>
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
