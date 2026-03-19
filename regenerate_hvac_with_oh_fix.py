#!/usr/bin/env python3
"""
Regenerate all 331 HVAC problem HTML files with CORRECTLY DISTRIBUTED office hours sessions.
Extracts which OH sessions apply to each problem from oh_lookup_v2.json.
"""

import json
import re
from pathlib import Path

DASHBOARD_DIR = Path(__file__).parent
PROBLEMS_DIR = DASHBOARD_DIR / 'problems'

# Map chapter names to section codes and problem counts
HVAC_CHAPTERS = {
    'Thermodynamics': (39, 23),
    'Fluids': (40, 28),
    'Psychrometrics': (41, 17),
    'Heat-Transfer': (42, 22),
    'HVAC': (43, 25),
    'Systems-and-Components': (44, 29),
    'Supporting-Topics': (45, 27),
    'Practice-Exam-1': (46, 80),
    'Practice-Exam-2': (47, 80),
}

def load_oh_lookup():
    """Load office hours lookup from JSON."""
    lookup_path = DASHBOARD_DIR / 'oh_lookup_v2.json'
    with open(lookup_path, 'r') as f:
        return json.load(f)

def extract_video_synthesis(html_path):
    """Extract video synthesis content from existing HTML."""
    try:
        with open(html_path, 'r') as f:
            html = f.read()
        
        # Look for video-box content
        match = re.search(r'<div class="video-box">(.*?)</div>\s*</div>', html, re.DOTALL)
        if match:
            return match.group(1).strip()
        return '<ul><li>Video synthesis will be populated here once available.</li></ul>'
    except:
        return '<ul><li>Video synthesis will be populated here once available.</li></ul>'

def build_oh_html(oh_sessions, chapter_name, problem_num):
    """Build OH HTML showing which sessions cover this problem."""
    if not oh_sessions:
        return '''<div class="oh-section-title">Office Hours<span class="oh-count">0</span></div>
<div class="oh-subtitle">Student questions asked in live office hours about this problem</div>
<p style="color:#999;font-size:13px;">No office hours coverage for this problem.</p>'''
    
    oh_count = len(oh_sessions)
    oh_html = f'''<div class="oh-section-title">
      Office Hours
      <span class="oh-count">{oh_count}</span>
    </div>
    <div class="oh-subtitle">Student questions asked in live office hours about this problem</div>
    
    <div class='qa-groups'>
'''
    
    for session_id in sorted(oh_sessions):
        oh_html += f'''            <div class='qa-group'>
                <div class='qa-session'>OH {session_id}: {chapter_name.replace("-", " ")} · Problem {problem_num}</div>
                <div class='qa-answer'><em>Full transcript available in office hours archive. Click to expand for details.</em></div>
            </div>
'''
    
    oh_html += '''    </div>'''
    return oh_html

def generate_html(chapter_name, problem_num, pdf_filename, video_content, oh_html):
    """Generate HTML for a single HVAC problem with embedded PDF."""
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HVAC · {chapter_name} · Problem {problem_num} | OH Prep</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f5f5;
  color: #333;
  line-height: 1.6;
  min-height: 100vh;
}}
.nav-bar {{
  background: white;
  border-bottom: 1px solid #e0e0e0;
  padding: 12px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  flex-wrap: wrap;
}}
.nav-badge {{
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #fbbf24;
  border-radius: 3px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 700;
}}
.layout-container {{
  display: flex;
  gap: 0;
  margin: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  overflow: hidden;
}}
.sidebar-left {{
  flex: 0 0 50%;
  padding: 24px;
  background: #fafafa;
  border-right: 1px solid #e0e0e0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}}
.sidebar-right {{
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}}
.section-title {{
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #1a1a1a;
  border-bottom: 2px solid #0066cc;
  padding-bottom: 8px;
}}
.problem-meta {{
  font-size: 12px;
  color: #888;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}}
.pdf-container {{
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-bottom: 24px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  overflow: hidden;
  background: white;
}}
.pdf-viewer {{
  flex: 1;
  min-height: 1000px;
  border: none;
}}
.pdf-footer {{
  background: #f9f9f9;
  border-top: 1px solid #e0e0e0;
  padding: 8px 12px;
  font-size: 11px;
  color: #666;
  text-align: center;
}}
.video-box {{
  background: #f0f4ff;
  padding: 12px;
  border-radius: 4px;
  margin-top: 12px;
  font-size: 13px;
  line-height: 1.7;
  border-left: 3px solid #7c3aed;
}}
.video-box ul {{ margin-left: 20px; }}
.video-box li {{ margin-bottom: 6px; }}
.oh-section-title {{
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 6px;
  color: #1a1a1a;
  border-bottom: 2px solid #f59e0b;
  padding-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
}}
.oh-count {{
  font-size: 12px;
  background: #fef3c7;
  color: #92400e;
  border-radius: 10px;
  padding: 1px 8px;
  font-weight: 600;
}}
.oh-subtitle {{
  font-size: 13px;
  color: #666;
  margin-bottom: 14px;
}}
.qa-group {{
  background: #fffbf0;
  border-left: 3px solid #f59e0b;
  padding: 12px 14px;
  margin-bottom: 14px;
  border-radius: 4px;
}}
.qa-session {{
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: #d97706;
  margin-bottom: 6px;
  letter-spacing: 0.5px;
}}
.qa-answer {{
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.5;
  color: #444;
}}
.footer {{
  background: white;
  border-top: 1px solid #e0e0e0;
  padding: 10px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 12px;
  color: #888;
  flex-wrap: wrap;
}}
@media (max-width: 900px) {{
  .layout-container {{ flex-direction: column; margin: 10px; }}
  .sidebar-left {{ flex: 1; border-right: none; border-bottom: 1px solid #e0e0e0; }}
  .pdf-viewer {{ min-height: 800px; }}
}}
</style>
</head>
<body>

<div class="nav-bar">
  <span style="font-size:14px;font-weight:600;color:#333;">HVAC · {chapter_name} · Problem {problem_num}</span>
  <span class="nav-badge">PDF</span>
  <span style="margin-left:auto;font-size:12px;color:#888;">Solution in PDF ↓</span>
</div>

<div class="layout-container">
  
  <div class="sidebar-left">
    <div class="problem-meta">HVAC · {chapter_name} · Problem {problem_num}</div>
    
    <div class="section-title">Problem & Solution</div>
    <div class="pdf-container">
      <iframe 
        class="pdf-viewer"
        src="../hvac_solutions/{pdf_filename}"
        title="Problem {problem_num}"
        allowfullscreen
      ></iframe>
      <div class="pdf-footer">PDF: {pdf_filename}</div>
    </div>

    <div style="margin-top:16px;">
      <div class="section-title">Video Synthesis</div>
      <div class="video-box">{video_content}</div>
    </div>
  </div>

  <div class="sidebar-right">
    {oh_html}
  </div>

</div>

<div class="footer">
  <span>MPEP OH Prep Dashboard</span>
  <span>Problem {problem_num} · {chapter_name}</span>
  <span style="margin-left: auto; color: #aaa;">PDF-Embedded Format</span>
</div>

</body>
</html>'''
    
    return html

def main():
    print("🔄 REGENERATING HVAC PROBLEMS WITH CORRECT OH DISTRIBUTION\n")
    print("=" * 70 + "\n")
    
    # Load OH lookup
    oh_lookup = load_oh_lookup()
    
    total_regenerated = 0
    oh_distributed = 0
    
    for chapter_name, (section_code, count) in HVAC_CHAPTERS.items():
        print(f"{chapter_name} ({section_code}): {count} problems...", end=" ", flush=True)
        chapter_count = 0
        chapter_oh_distributed = 0
        
        for problem_num in range(1, count + 1):
            # Generate filenames
            pdf_filename = f"HVAC-{chapter_name}-{problem_num:02d}.pdf"
            html_filename = f"HVAC-{chapter_name}-{problem_num}.html"
            html_path = PROBLEMS_DIR / html_filename
            
            # Extract video synthesis from existing file
            video_content = extract_video_synthesis(html_path)
            
            # Look up OH sessions for this specific problem
            # Try different naming conventions
            for lookup_key_candidate in [
                f"HVAC_{chapter_name}_{problem_num}",
                f"HVAC_{chapter_name.replace('-', '_')}_{problem_num}",
                f"HVAC_{chapter_name.replace('-', ' ')}_{problem_num}",
            ]:
                if lookup_key_candidate in oh_lookup:
                    oh_sessions = oh_lookup[lookup_key_candidate].get('oh_sessions', [])
                    break
            else:
                oh_sessions = []
            
            if oh_sessions:
                chapter_oh_distributed += 1
            
            # Generate OH HTML
            oh_html = build_oh_html(oh_sessions, chapter_name, problem_num)
            
            # Generate problem HTML
            html_content = generate_html(chapter_name, problem_num, pdf_filename, video_content, oh_html)
            
            # Write file
            try:
                with open(html_path, 'w') as f:
                    f.write(html_content)
                chapter_count += 1
                total_regenerated += 1
            except Exception as e:
                print(f"\n  ❌ {html_filename}: {e}")
        
        oh_distributed += chapter_oh_distributed
        print(f"✅ {chapter_count}/{count} ({chapter_oh_distributed} with OH)")
    
    print(f"\n{'=' * 70}")
    print(f"✅ REGENERATION COMPLETE")
    print(f"{'=' * 70}")
    print(f"Regenerated: {total_regenerated} files")
    print(f"Problems with OH: {oh_distributed}/331")
    print(f"Location:     {PROBLEMS_DIR}/")

if __name__ == '__main__':
    main()
