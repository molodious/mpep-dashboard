#!/usr/bin/env python3
"""
Regenerate oh-prep.html with all 660 problems (dynamic from index)
"""

import json
from pathlib import Path
from collections import defaultdict

DASHBOARD_DIR = Path(__file__).parent
INDEX_FILE = DASHBOARD_DIR / 'oh-prep-index.json'

def generate_oh_prep_html():
    """Generate oh-prep.html from index."""
    
    # Load index
    with open(INDEX_FILE, 'r') as f:
        index = json.load(f)
    
    # Define chapter order for each program
    hvac_order = [
        'HVAC-Thermodynamics',
        'HVAC-Heat-Transfer',
        'HVAC-Fluids',
        'HVAC-HVAC',
        'HVAC-Systems-and-Components',
        'HVAC-Supporting-Topics',
        'HVAC-Psychrometrics',
        'HVAC-Practice-Exam-1',
        'HVAC-Practice-Exam-2',
    ]
    
    tfs_order = [
        'TFS-Thermodynamics',
        'TFS-Heat-Transfer',
        'TFS-Hydraulic-and-Fluid-Applications',
        'TFS-Energy-and-Power-System-Applications',
        'TFS-Supporting-Topics',
        'TFS-Practice-Exam-1',
        'TFS-Practice-Exam-2',
    ]
    
    # Create category lookup
    categories_by_name = {cat['name']: cat for cat in index['categories']}
    
    # Build HTML
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OH Prep Dashboard — All Problems</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        h1 {
            color: #333;
            text-align: center;
        }
        
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .program-section {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            max-height: calc(100vh - 150px);
            overflow-y: auto;
        }
        
        .program-title {
            font-size: 24px;
            font-weight: 700;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #0066cc;
        }
        
        .program-title.tfs {
            border-bottom-color: #f59e0b;
        }
        
        .chapter-group {
            margin-bottom: 18px;
        }
        
        .chapter-name {
            font-size: 13px;
            font-weight: 600;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
            padding-left: 2px;
        }
        
        .problems-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(40px, 1fr));
            gap: 6px;
            margin-bottom: 14px;
        }
        
        .problem-card {
            aspect-ratio: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
            font-weight: 600;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
            color: inherit;
            background: #f0f0f0;
            border: 1px solid #ddd;
        }
        
        .problem-card:hover {
            background: #0066cc;
            color: white;
            border-color: #0066cc;
        }
        
        .problem-card.has-oh {
            background: #fff3cd;
            border-color: #f59e0b;
        }
        
        .problem-card.has-oh:hover {
            background: #f59e0b;
            color: white;
        }
    </style>
</head>
<body>

<div class="container">
    <div class="header">
        <h1>📚 OH Prep Dashboard</h1>
        <p style="text-align: center; color: #666; margin-top: 10px;">660 problems across HVAC and TFS exams</p>
    </div>
    
    <div class="main-grid">
        <!-- HVAC SECTION -->
        <div class="program-section">
            <div class="program-title">HVAC & Refrigeration</div>
'''
    
    # HVAC problems (in order)
    for cat_name in hvac_order:
        if cat_name not in categories_by_name:
            continue
        cat = categories_by_name[cat_name]
        cat_name = cat['name'].replace('HVAC-', '')
        html += f'''            <div class="chapter-group">
                <div class="chapter-name">{cat_name}</div>
                <div class="problems-grid">
'''
        
        for problem in sorted(cat['problems'], key=lambda p: p['problem_number']):
            problem_id = problem['id']
            problem_num = problem['problem_number']
            has_oh_class = ' has-oh' if problem['has_oh'] else ''
            
            html += f'''                    <a href="problems/{problem_id}.html" class="problem-card{has_oh_class}" title="{problem_id}">{problem_num}</a>
'''
        
        html += '''                </div>
            </div>
'''
    
    html += '''        </div>
        
        <!-- TFS SECTION -->
        <div class="program-section">
            <div class="program-title tfs">Thermal & Fluids Systems</div>
'''
    
    # TFS problems (in order)
    for cat_name in tfs_order:
        if cat_name not in categories_by_name:
            continue
        cat = categories_by_name[cat_name]
        cat_name = cat['name'].replace('TFS-', '')
        html += f'''            <div class="chapter-group">
                <div class="chapter-name">{cat_name}</div>
                <div class="problems-grid">
'''
        
        for problem in sorted(cat['problems'], key=lambda p: p['problem_number']):
            problem_id = problem['id']
            problem_num = problem['problem_number']
            has_oh_class = ' has-oh' if problem['has_oh'] else ''
            
            html += f'''                    <a href="problems/{problem_id}.html" class="problem-card{has_oh_class}" title="{problem_id}">{problem_num}</a>
'''
        
        html += '''                </div>
            </div>
'''
    
    html += '''        </div>
    </div>
</div>

</body>
</html>'''
    
    return html

def main():
    print("🔨 REGENERATING oh-prep.html\n")
    
    html_content = generate_oh_prep_html()
    
    output_file = DASHBOARD_DIR / 'oh-prep.html'
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"✅ Generated {output_file}")
    print(f"   Size: {len(html_content)} bytes")
    print(f"\nNext: git add oh-prep.html && git commit && git push")

if __name__ == '__main__':
    main()
