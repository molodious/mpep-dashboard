#!/usr/bin/env python3
"""
Regenerate progress.html from progress.json
Reads current progress and builds a visual dashboard
"""

import json
import os
from datetime import datetime

def generate_progress_html():
    """Generate progress.html from progress.json"""
    
    # Load progress.json
    progress_file = os.path.join(os.path.dirname(__file__), '..', 'progress.json')
    with open(progress_file, 'r') as f:
        progress = json.load(f)
    
    completed = progress.get('completed', 0)
    total = progress.get('total_problems', 660)
    percent = int((completed / total) * 100) if total > 0 else 0
    
    # Build program progress sections
    program_sections = ""
    for program, data in progress.get('program_progress', {}).items():
        prog_completed = data.get('completed', 0)
        prog_total = data.get('total', 0)
        prog_percent = int((prog_completed / prog_total) * 100) if prog_total > 0 else 0
        
        chapters_html = ""
        for chapter, ch_data in data.get('chapters', {}).items():
            ch_completed = ch_data.get('completed', 0)
            ch_total = ch_data.get('total', 0)
            ch_percent = int((ch_completed / ch_total) * 100) if ch_total > 0 else 0
            
            chapters_html += f"""
            <div class="chapter-item">
                <div class="chapter-name">{chapter}</div>
                <div class="progress-bar-small">
                    <div class="progress-fill-small" style="width: {ch_percent}%"></div>
                </div>
                <div class="chapter-count">{ch_completed}/{ch_total}</div>
            </div>
            """
        
        program_sections += f"""
        <div class="program-box">
            <h3>{program} ({prog_percent}%)</h3>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {prog_percent}%; background-color: {'#4CAF50' if prog_percent == 100 else '#2196F3'};"></div>
            </div>
            <div class="progress-text">{prog_completed}/{prog_total} chapters complete</div>
            <div class="chapters-container">
                {chapters_html}
            </div>
        </div>
        """
    
    # Build failed problems section if any
    failed_html = ""
    failed = progress.get('failed_problems', [])
    if failed:
        failed_html = f"""
        <div class="failed-section">
            <h3>Failed Problems ({len(failed)})</h3>
            <ul>
                {''.join([f'<li>{p}</li>' for p in failed[:20]])}
                {f'<li>... and {len(failed) - 20} more</li>' if len(failed) > 20 else ''}
            </ul>
        </div>
        """
    
    # Build the HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>MPEP Dashboard — Build Progress</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
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
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        
        h1 {{
            color: #333;
            margin-bottom: 10px;
            text-align: center;
        }}
        
        .overall-stats {{
            text-align: center;
            margin-bottom: 40px;
            padding: 20px;
            background: #f5f5f5;
            border-radius: 8px;
        }}
        
        .big-number {{
            font-size: 48px;
            font-weight: bold;
            color: #2196F3;
            margin: 10px 0;
        }}
        
        .big-text {{
            font-size: 18px;
            color: #666;
        }}
        
        .overall-progress {{
            width: 100%;
            height: 40px;
            background: #eee;
            border-radius: 20px;
            overflow: hidden;
            margin: 20px 0;
        }}
        
        .overall-fill {{
            height: 100%;
            background: linear-gradient(90deg, #2196F3, #4CAF50);
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }}
        
        .programs {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 40px;
        }}
        
        @media (max-width: 768px) {{
            .programs {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .program-box {{
            background: #f9f9f9;
            border: 2px solid #eee;
            border-radius: 8px;
            padding: 20px;
        }}
        
        .program-box h3 {{
            color: #333;
            margin-bottom: 15px;
            font-size: 20px;
        }}
        
        .progress-bar {{
            width: 100%;
            height: 30px;
            background: #ddd;
            border-radius: 15px;
            overflow: hidden;
            margin-bottom: 10px;
        }}
        
        .progress-fill {{
            height: 100%;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 10px;
            color: white;
            font-weight: bold;
            font-size: 12px;
        }}
        
        .progress-text {{
            color: #666;
            font-size: 14px;
            margin-bottom: 15px;
        }}
        
        .chapters-container {{
            background: white;
            border-radius: 6px;
            padding: 15px;
            max-height: 400px;
            overflow-y: auto;
        }}
        
        .chapter-item {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 12px;
            padding-bottom: 12px;
            border-bottom: 1px solid #eee;
        }}
        
        .chapter-item:last-child {{
            border-bottom: none;
        }}
        
        .chapter-name {{
            min-width: 150px;
            font-size: 13px;
            color: #555;
            font-weight: 500;
        }}
        
        .progress-bar-small {{
            flex: 1;
            height: 20px;
            background: #eee;
            border-radius: 10px;
            overflow: hidden;
        }}
        
        .progress-fill-small {{
            height: 100%;
            background: #2196F3;
            transition: width 0.3s ease;
        }}
        
        .chapter-count {{
            min-width: 60px;
            text-align: right;
            font-size: 12px;
            color: #999;
            font-weight: 500;
        }}
        
        .last-update {{
            text-align: center;
            color: #999;
            font-size: 12px;
            margin-top: 20px;
        }}
        
        .failed-section {{
            background: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 8px;
            padding: 20px;
            margin-top: 30px;
        }}
        
        .failed-section h3 {{
            color: #856404;
            margin-bottom: 10px;
        }}
        
        .failed-section ul {{
            margin-left: 20px;
            color: #856404;
            font-size: 13px;
        }}
        
        .failed-section li {{
            margin-bottom: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 MPEP Build Dashboard</h1>
        
        <div class="overall-stats">
            <div class="big-text">Overall Progress</div>
            <div class="big-number">{percent}%</div>
            <div class="big-text">{completed} of {total} problems complete</div>
            <div class="overall-progress">
                <div class="overall-fill" style="width: {percent}%">{percent}%</div>
            </div>
        </div>
        
        <div class="programs">
            {program_sections}
        </div>
        
        {failed_html}
        
        <div class="last-update">
            Last updated: {progress.get('last_update', 'unknown')}<br>
            Status: {progress.get('status', 'unknown')}
        </div>
    </div>
    
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
"""
    
    # Write progress.html
    output_file = os.path.join(os.path.dirname(__file__), '..', 'progress.html')
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"✅ progress.html regenerated ({completed}/{total} problems)")
    return True

if __name__ == '__main__':
    generate_progress_html()
