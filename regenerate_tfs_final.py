#!/usr/bin/env python3
"""
FINAL TFS Problem Regeneration with:
1. Original HTML naming (TFS-Energy-and-Power-System-Applications-1.html)
2. PDF embedding
3. Video Synthesis injection (from solutions-video-summaries/)
4. Office Hours injection (from office-hours-consolidated-summaries/)
"""

import json
import re
import os
from pathlib import Path

# Mapping of PDF folder names to HTML prefixes (original naming)
PDF_TO_HTML_PREFIX = {
    'Thermodynamics': 'TFS-Thermodynamics',
    'Heat Transfer': 'TFS-Heat-Transfer',
    'Hydraulic & Fluid Applications': 'TFS-Hydraulic-and-Fluid-Applications',
    'Energy & Power System Applications': 'TFS-Energy-and-Power-System-Applications',
    'Supporting topics': 'TFS-Supporting-Topics',
    'Practice Exam #1': 'TFS-Practice-Exam-1',
    'Practice Exam #2': 'TFS-Practice-Exam-2',
}

# Video summary naming variations (how they're named in JSON)
VIDEO_MAPPING = {
    'TFS-Thermodynamics': 'TFS-Thermodynamics',
    'TFS-Heat-Transfer': 'TFS-Heat-Transfer',
    'TFS-Hydraulic-and-Fluid-Applications': 'TFS-Hydraulic-and-Fluids-Applications',
    'TFS-Energy-and-Power-System-Applications': 'TFS-Energy-and-Power-Systems',
    'TFS-Supporting-Topics': 'TFS-Supporting-Topics',
    'TFS-Practice-Exam-1': 'TFS-Practice-Exam-I',
    'TFS-Practice-Exam-2': 'TFS-Practice-Exam-II',
}

# Office hours mapping (underscore naming → HTML prefix)
OH_MAPPING = {
    'TFS_Thermodynamics': 'TFS-Thermodynamics',
    'TFS_Heat_Transfer': 'TFS-Heat-Transfer',
    'TFS_Fluids': 'TFS-Hydraulic-and-Fluid-Applications',
    'TFS_Energy_&_Power_Systems': 'TFS-Energy-and-Power-System-Applications',
    'TFS_Supporting_Topics': 'TFS-Supporting-Topics',
    'TFS_Practice_Exam_1': 'TFS-Practice-Exam-1',
    'TFS_Practice_Exam_2': 'TFS-Practice-Exam-2',
}

DASHBOARD_DIR = Path(__file__).parent
PROBLEMS_DIR = DASHBOARD_DIR / 'problems'
TFS_SOLUTIONS_DIR = DASHBOARD_DIR / 'tfs_solutions'
MPEP_ASSETS = DASHBOARD_DIR.parent / 'mpep-assets'

VIDEO_SUMMARIES_DIR = MPEP_ASSETS / 'solutions-video-summaries'
OH_SUMMARIES_DIR = MPEP_ASSETS / 'office-hours-consolidated-summaries'

def load_json_file(path):
    """Safely load JSON file."""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        return None

def get_video_content(html_prefix, problem_num):
    """Load video synthesis from JSON."""
    video_prefix = VIDEO_MAPPING.get(html_prefix, html_prefix)
    video_json_path = VIDEO_SUMMARIES_DIR / f'{video_prefix}-{problem_num}.json'
    
    data = load_json_file(video_json_path)
    if not data or 'summary' not in data:
        return ""
    
    # Format summary array as HTML list items
    summary_items = data.get('summary', [])
    if not summary_items:
        return ""
    
    html = '<ul>'
    for item in summary_items:
        html += f'<li>{item}</li>'
    html += '</ul>'
    return html

def get_oh_content(html_prefix, problem_num):
    """Load office hours content from JSON."""
    oh_prefix = None
    for oh_key, html_key in OH_MAPPING.items():
        if html_key == html_prefix:
            oh_prefix = oh_key
            break
    
    if not oh_prefix:
        return None
    
    oh_json_path = OH_SUMMARIES_DIR / f'{oh_prefix}_{problem_num}.json'
    
    data = load_json_file(oh_json_path)
    if not data:
        return None
    
    # Build OH section from JSON
    discussions = data.get('office_hours_discussions', [])
    if not discussions:
        return None
    
    oh_html = f'<div class="oh-section-title">\n      Office Hours\n      <span class="oh-count">{len(discussions)}</span>\n    </div>\n'
    oh_html += '    <div class="oh-subtitle">Student questions asked in live office hours about this problem</div>\n'
    
    for discussion in discussions:
        oh_html += '    <div class="qa-group">\n'
        oh_html += f'      <div class="qa-session">OH {discussion.get("oh_session", "")}</div>\n'
        oh_html += f'      <div class="qa-question"><strong>Q:</strong> {discussion.get("student_question", "")}</div>\n'
        oh_html += f'      <div class="qa-answer"><strong>A:</strong> {discussion.get("dan_answer", "")}</div>\n'
        oh_html += '    </div>\n'
    
    return oh_html

def generate_html(html_prefix, problem_num, chapter_name, pdf_filename):
    """Generate complete HTML file with all content."""
    
    chapter_display = chapter_name.replace('#', '').strip()
    video_content = get_video_content(html_prefix, problem_num)
    oh_content = get_oh_content(html_prefix, problem_num)
    
    # Build video section
    video_section = f'<div class="video-box">{video_content}</div>' if video_content else '<div class="video-box"><ul><li>Video synthesis not available for this problem.</li></ul></div>'
    
    # Build OH section
    if oh_content:
        oh_section = f'''<div class="sidebar-right">
    {oh_content}
  </div>'''
    else:
        oh_section = '''<div class="sidebar-right">
    <div class="oh-section-title">
      Office Hours
      <span class="oh-count">0</span>
    </div>
    <div class="oh-subtitle">Student questions asked in live office hours about this problem</div>
    
    <p style='color:#999;'>No office hours coverage for this problem.</p>
  </div>'''
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TFS · {chapter_display} · Problem {problem_num} | OH Prep</title>
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
.qa-question {{
  font-weight: 500;
  color: #333;
  font-size: 13px;
  line-height: 1.6;
  margin-bottom: 4px;
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
  <span style="font-size:14px;font-weight:600;color:#333;">TFS · {chapter_display} · Problem {problem_num}</span>
  <span class="nav-badge">PDF</span>
  <span style="margin-left:auto;font-size:12px;color:#888;">Solution in PDF ↓</span>
</div>

<div class="layout-container">
  
  <div class="sidebar-left">
    <div class="problem-meta">TFS · {chapter_display} · Problem {problem_num}</div>
    
    <div class="section-title">Problem & Solution</div>
    <div class="pdf-container">
      <iframe 
        class="pdf-viewer"
        src="../tfs_solutions/{chapter_name}/{pdf_filename}"
        title="Problem {problem_num}"
        allowfullscreen
      ></iframe>
      <div class="pdf-footer">PDF: {pdf_filename}</div>
    </div>

    <div style="margin-top:16px;">
      <div class="section-title">Video Synthesis</div>
      {video_section}
    </div>
  </div>

  {oh_section}

</div>

<div class="footer">
  <span>MPEP OH Prep Dashboard</span>
  <span>Problem {problem_num} · {chapter_display}</span>
  <span style="margin-left: auto; color: #aaa;">PDF-Embedded Format</span>
</div>

</body>
</html>'''
    
    return html

def main():
    print("🚀 REGENERATING ALL 329 TFS PROBLEMS\n")
    print("With: PDF embedding + Video Synthesis + Office Hours\n")
    print("=" * 60 + "\n")
    
    total = 0
    video_count = 0
    oh_count = 0
    
    for pdf_chapter, html_prefix in PDF_TO_HTML_PREFIX.items():
        chapter_dir = TFS_SOLUTIONS_DIR / pdf_chapter
        
        if not chapter_dir.exists():
            print(f"❌ {pdf_chapter}: Directory not found")
            continue
        
        print(f"{pdf_chapter}...", end=" ", flush=True)
        chapter_video = 0
        chapter_oh = 0
        chapter_generated = 0
        
        # Count problems in folder
        pdf_files = list(chapter_dir.glob("*.pdf"))
        
        for pdf_path in sorted(pdf_files):
            # Extract problem number from PDF filename
            pdf_name = pdf_path.stem
            
            # Parse number (last part after hyphen/space)
            import re as regex
            match = regex.search(r'(\d+)$', pdf_name)
            if not match:
                continue
            
            problem_num = int(match.group(1))
            pdf_filename = pdf_path.name
            
            # Generate HTML filename
            html_filename = f"{html_prefix}-{problem_num}.html"
            html_path = PROBLEMS_DIR / html_filename
            
            # Generate HTML
            html_content = generate_html(html_prefix, problem_num, pdf_chapter, pdf_filename)
            
            # Write file
            try:
                with open(html_path, 'w') as f:
                    f.write(html_content)
                chapter_generated += 1
                total += 1
                
                # Check if video/OH were injected
                if f'<ul><li>Video synthesis not available' not in html_content:
                    chapter_video += 1
                    video_count += 1
                
                if 'No office hours coverage' not in html_content:
                    chapter_oh += 1
                    oh_count += 1
                    
            except Exception as e:
                print(f"\n❌ {html_filename}: {e}")
        
        print(f"✅ {chapter_generated} files (video: {chapter_video}, oh: {chapter_oh})")
    
    print(f"\n{'=' * 60}")
    print(f"✅ COMPLETE!")
    print(f"{'=' * 60}")
    print(f"Generated:      {total} files")
    print(f"With video:     {video_count} problems")
    print(f"With OH:        {oh_count} problems")
    print(f"\nNext: git add -A && git commit && git push")

if __name__ == '__main__':
    main()
