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
            
            orders.append({
                "date": ts.strftime("%Y-%m-%d"),
                "timestamp": ts,
                "customer": customer_details.get("name", "Unknown"),
                "product": product,
                "amount": s.get("amount_total", 0) / 100,
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
            
            orders.append({
                "date": ts.strftime("%Y-%m-%d"),
                "timestamp": ts,
                "customer": o.get("user_name", "Unknown"),
                "product": product,
                "amount": o.get("amount_cents", 0) / 100,
            })
    
    return orders

def build_dashboard():
    """Build the sales dashboard HTML with live data."""
    today = datetime.now()
    
    # Manual data for Jan/Feb
    manual_orders = [
        {
            "date": date,
            "timestamp": datetime.strptime(date, "%Y-%m-%d"),
            "customer": "Manual",
            "product": product,
            "amount": amount,
        }
        for date, product, amount in MANUAL_DATA_JAN_FEB
    ]
    
    # API data for March onwards
    print("Fetching API data (March 2026+)...")
    stripe_orders = fetch_stripe_data(datetime(2026, 3, 1))
    thinkific_orders = fetch_thinkific_data(datetime(2026, 3, 1))
    print(f"  Stripe: {len(stripe_orders)} orders")
    print(f"  Thinkific: {len(thinkific_orders)} orders")
    
    # Combine all
    all_orders = manual_orders + stripe_orders + thinkific_orders
    all_orders.sort(key=lambda x: x["timestamp"])
    
    # Calculate statistics (YTD 2026)
    total_revenue_ytd = sum(o["amount"] for o in all_orders)
    days_in_period = (today - datetime(2026, 1, 1)).days + 1
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
    
    sorted_months = sorted(monthly_data.keys())
    
    print(f"\nStatistics (2026 YTD):")
    print(f"  YTD revenue: ${round(total_revenue_ytd):,}")
    print(f"  Days elapsed: {days_in_period}")
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
    
    # Bar chart data
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
            bar_datasets[product].append(round(monthly_data[month].get(product, 0)))
    
    # Build HTML
    html_top = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sales Dashboard - Mechanical PE Exam Prep</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        /* Auth overlay styles */
        #auth-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            width: 100%;
            height: 100%;
            background: #0d1117;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        }
        .auth-box {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 14px;
            padding: 40px 36px;
            width: 100%;
            max-width: 380px;
            text-align: center;
        }
        .auth-logo { font-size: 36px; margin-bottom: 12px; }
        .auth-title { font-size: 20px; font-weight: 700; color: #e6edf3; margin-bottom: 4px; }
        .auth-sub { font-size: 13px; color: #8b949e; margin-bottom: 28px; }
        .auth-box input {
            width: 100%;
            background: #0d1117;
            border: 1px solid #30363d;
            color: #e6edf3;
            border-radius: 8px;
            padding: 11px 14px;
            font-size: 15px;
            letter-spacing: 0.08em;
            outline: none;
            margin-bottom: 12px;
            transition: border-color 0.15s;
        }
        .auth-box input:focus { border-color: #58a6ff; }
        .auth-box button {
            width: 100%;
            background: #58a6ff;
            color: #0d1117;
            border: none;
            border-radius: 8px;
            padding: 11px;
            font-size: 14px;
            font-weight: 700;
            cursor: pointer;
            transition: opacity 0.15s;
        }
        .auth-box button:hover { opacity: 0.88; }
        .auth-box button:disabled { opacity: 0.55; cursor: default; }
        #pwd-error { display: none; color: #f85149; font-size: 12px; margin-bottom: 10px; }
        #main-content { display: none; }
    </style>
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
    <!-- Auth overlay -->
    <div id="auth-overlay">
        <div class="auth-box">
            <div class="auth-logo">♠️</div>
            <div class="auth-title">Sales Dashboard</div>
            <div class="auth-sub">Enter password to view</div>
            <form id="auth-form">
                <input type="password" id="pwd-input" placeholder="Password" autocomplete="current-password" />
                <div id="pwd-error"></div>
                <button type="submit" id="pwd-btn">Unlock</button>
            </form>
        </div>
    </div>

    <!-- Main content -->
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
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 20px;">
                <div>
                    <div class="metric-label" style="color: rgba(255,255,255,0.8);">This Month (So Far)</div>
                    <div class="metric-value" style="color: white;">$""" + f"{round(march_revenue):,}" + """</div>
                </div>
                <div>
                    <div class="metric-label" style="color: rgba(255,255,255,0.8);">Daily Average (2026 YTD)</div>
                    <div class="metric-value" style="color: white;">$""" + f"{round(avg_daily):,}" + """</div>
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
                Based on 2026 YTD average daily revenue ($""" + f"{round(avg_daily):,}" + """/day over """ + str(days_in_period) + """ days)
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
    </div>

    <script src="auth.js"></script>
    <script>
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
                        max: marchMax * 1.2
                    }
                }
            },
            plugins: [totalLabelsPlugin]
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
