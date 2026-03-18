#!/usr/bin/env python3
"""
Regenerate oh-prep.html from problem-status.json
Ensures dashboard matches the actual problem status data
"""

import json
from pathlib import Path
from datetime import datetime

status_file = Path("/home/mpepagent/.openclaw/workspace/projects/mpep-dashboard/problem-status.json")
output_file = Path("/home/mpepagent/.openclaw/workspace/projects/mpep-dashboard/oh-prep.html")

# Read status data
with open(status_file) as f:
    status_data = json.load(f)

# Count statuses
green_count = sum(1 for v in status_data.values() if v == "green")
amber_count = sum(1 for v in status_data.values() if v == "amber")
red_count = sum(1 for v in status_data.values() if v == "red")

# Build problem cards
problem_cards = []
for problem_key, status in sorted(status_data.items()):
    # Parse problem key: e.g., "HVAC_Thermodynamics_6"
    parts = problem_key.rsplit('_', 1)
    if len(parts) == 2:
        name_part = parts[0].replace('_', ' ')
        number = parts[1]
        
        status_icons = {"green": "✓", "amber": "⏳", "red": "—"}
        status_labels = {"green": "Approved", "amber": "Awaiting Review", "red": "Not Started"}
        
        card = f'''
    <div class="problem-card {status}">
        <div class="problem-info">
            <div class="problem-name">{name_part} {number}</div>
            <div class="problem-chapter">{name_part}</div>
        </div>
        <div class="status-badge {status}">
            <span class="status-icon">{status_icons[status]}</span>
            {status_labels[status]}
        </div>
    </div>'''
        problem_cards.append(card)

cards_html = "".join(problem_cards)

# Build the complete HTML
html_template = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OH Prep Dashboard — Problem Status</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        
        h1 {{
            color: #333;
            margin-bottom: 30px;
            text-align: center;
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .summary-card {{
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            color: white;
            font-weight: bold;
        }}
        
        .summary-card.green {{
            background: linear-gradient(135deg, #4CAF50, #45a049);
        }}
        
        .summary-card.amber {{
            background: linear-gradient(135deg, #FFC107, #FFB300);
            color: #333;
        }}
        
        .summary-card.red {{
            background: linear-gradient(135deg, #F44336, #E53935);
        }}
        
        .summary-number {{
            font-size: 36px;
            margin-bottom: 5px;
        }}
        
        .summary-label {{
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .controls {{
            display: flex;
            gap: 15px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}
        
        .filter-btn {{
            padding: 10px 20px;
            border: 2px solid #ddd;
            background: white;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s ease;
        }}
        
        .problems-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 15px;
        }}
        
        .problem-card {{
            border: 2px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.3s ease;
            cursor: pointer;
        }}
        
        .problem-card:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }}
        
        .problem-card.green {{
            background: #f1f8f6;
            border-left: 5px solid #4CAF50;
        }}
        
        .problem-card.amber {{
            background: #fffbf0;
            border-left: 5px solid #FFC107;
        }}
        
        .problem-card.red {{
            background: #fef5f5;
            border-left: 5px solid #F44336;
        }}
        
        .problem-info {{
            flex: 1;
        }}
        
        .problem-name {{
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }}
        
        .problem-chapter {{
            font-size: 13px;
            color: #666;
        }}
        
        .status-badge {{
            padding: 8px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        
        .status-badge.green {{
            background: #4CAF50;
            color: white;
        }}
        
        .status-badge.amber {{
            background: #FFC107;
            color: #333;
        }}
        
        .status-badge.red {{
            background: #F44336;
            color: white;
        }}
        
        .status-icon {{
            font-size: 14px;
        }}
        
        .legend {{
            margin-top: 40px;
            padding: 20px;
            background: #f5f5f5;
            border-radius: 8px;
        }}
        
        .legend h3 {{
            margin-bottom: 15px;
            color: #333;
        }}
        
        .legend-items {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .legend-box {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
        }}
        
        .legend-box.green {{
            background: #4CAF50;
        }}
        
        .legend-box.amber {{
            background: #FFC107;
        }}
        
        .legend-box.red {{
            background: #F44336;
        }}
        
        .last-updated {{
            text-align: center;
            color: #999;
            font-size: 12px;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 OH Prep Dashboard — Problem Status</h1>
        
        <div class="summary">
            <div class="summary-card green">
                <div class="summary-number">{green_count}</div>
                <div class="summary-label">Approved</div>
            </div>
            <div class="summary-card amber">
                <div class="summary-number">{amber_count}</div>
                <div class="summary-label">Awaiting Review</div>
            </div>
            <div class="summary-card red">
                <div class="summary-number">{red_count}</div>
                <div class="summary-label">Not Started</div>
            </div>
        </div>
        
        <div class="problems-grid" id="problems-grid">
            {cards_html}
        </div>
        
        <div class="legend">
            <h3>Status Legend</h3>
            <div class="legend-items">
                <div class="legend-item">
                    <div class="legend-box green"></div>
                    <div><strong>Green (Approved):</strong> Reviewed and approved by Dan</div>
                </div>
                <div class="legend-item">
                    <div class="legend-box amber"></div>
                    <div><strong>Amber (Awaiting Review):</strong> Built by agent, pending Dan's review</div>
                </div>
                <div class="legend-item">
                    <div class="legend-box red"></div>
                    <div><strong>Red (Not Started):</strong> Not yet built</div>
                </div>
            </div>
        </div>
        
        <div class="last-updated">
            Last updated: <span id="timestamp">{datetime.now().strftime("%Y-%m-%d %H:%M EDT")}</span>
        </div>
    </div>
</body>
</html>'''

# Write to file
with open(output_file, 'w') as f:
    f.write(html_template)

print(f"✅ oh-prep.html regenerated")
print(f"   Green: {green_count}, Amber: {amber_count}, Red: {red_count}")
print(f"   Total: {green_count + amber_count + red_count}/660")
