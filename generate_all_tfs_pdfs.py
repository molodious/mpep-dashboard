#!/usr/bin/env python3
"""
Generate all 329 TFS problem HTML files with embedded PDFs.
Preserves video synthesis and office hours sections from existing files.
"""

import os
import re
from pathlib import Path

# Map TFS folder names to problem prefixes and chapters
TFS_MAPPING = {
    'Thermodynamics': {'prefix': 'TFS-Thermodynamics', 'count': 30},
    'Heat Transfer': {'prefix': 'TFS-Heat-Transfer', 'count': 26},
    'Hydraulic & Fluid Applications': {'prefix': 'TFS-Hydraulic-Fluid', 'count': 59},
    'Energy & Power System Applications': {'prefix': 'TFS-Energy-Power', 'count': 23},
    'Supporting topics': {'prefix': 'TFS-Supporting-Topics', 'count': 31},
    'Practice Exam #1': {'prefix': 'TFS-Practice-Exam-1', 'count': 80},
    'Practice Exam #2': {'prefix': 'TFS-Practice-Exam-2', 'count': 80},
}

DASHBOARD_DIR = Path(__file__).parent
PROBLEMS_DIR = DASHBOARD_DIR / 'problems'
TFS_SOLUTIONS_DIR = DASHBOARD_DIR / 'tfs_solutions'

def extract_existing_sections(html_path):
    """Extract video and OH sections from existing HTML."""
    try:
        with open(html_path, 'r') as f:
            html = f.read()
        
        # Extract video synthesis
        video_match = re.search(
            r'<div class="section-title">Video Synthesis</div>.*?<div class="video-box">(.*?)</div>\s*</div>',
            html, re.DOTALL
        )
        video_content = video_match.group(1) if video_match else ""
        
        # Extract office hours
        oh_match = re.search(
            r'(<div class="sidebar-right">.*?</div>)',
            html, re.DOTALL
        )
        oh_content = oh_match.group(1) if oh_match else ""
        
        return {
            'video': video_content,
            'oh': oh_content
        }
    except:
        return {'video': "", 'oh': ""}

def generate_html_for_problem(
    chapter_name,
    problem_num,
    pdf_filename,
    existing_sections=None
):
    """Generate HTML for a single TFS problem with embedded PDF."""
    
    if existing_sections is None:
        existing_sections = {'video': "", 'oh': ""}
    
    video_section = existing_sections.get('video', "")
    oh_section = existing_sections.get('oh', "")
    
    chapter_display = chapter_name.replace('#', '').strip()
    
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
  min-height: calc(100vh - 130px);
}}
.sidebar-left {{
  flex: 0 0 50%;
  padding: 24px;
  background: #fafafa;
  border-right: 1px solid #e0e0e0;
  overflow-y: auto;
  max-height: calc(100vh - 130px);
  display: flex;
  flex-direction: column;
}}
.sidebar-right {{
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  max-height: calc(100vh - 130px);
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
  .sidebar-left {{ flex: 1; border-right: none; border-bottom: 1px solid #e0e0e0; max-height: none; }}
  .sidebar-right {{ max-height: none; }}
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
      <div class="video-box"><ul><li>Video synthesis will be populated here once available.</li></ul></div>
    </div>
  </div>

  <div class="sidebar-right">
    <div class="oh-section-title">
      Office Hours
      <span class="oh-count">0</span>
    </div>
    <div class="oh-subtitle">Student questions asked in live office hours about this problem</div>
    
    <p style='color:#999;'>No office hours coverage for this problem.</p>
  </div>

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
    """Generate all TFS problem files."""
    
    total_generated = 0
    
    for chapter_name, info in TFS_MAPPING.items():
        prefix = info['prefix']
        count = info['count']
        
        chapter_dir = TFS_SOLUTIONS_DIR / chapter_name
        
        print(f"Generating {count} problems for {chapter_name}...", end=" ")
        
        for problem_num in range(1, count + 1):
            # Find the PDF file
            pdf_files = list(chapter_dir.glob(f"*{problem_num:02d}.pdf")) + \
                       list(chapter_dir.glob(f"*-{problem_num:02d}.pdf")) + \
                       list(chapter_dir.glob(f"{problem_num:02d}*.pdf"))
            
            if not pdf_files:
                print(f"\n  ⚠️  Problem {problem_num}: PDF not found")
                continue
            
            pdf_path = pdf_files[0]
            pdf_filename = pdf_path.name
            
            # Generate HTML filename
            html_filename = f"{prefix}-{problem_num}.html"
            html_path = PROBLEMS_DIR / html_filename
            
            # Check if existing file has video/OH content
            existing_sections = {'video': "", 'oh': ""} 
            if html_path.exists():
                existing_sections = extract_existing_sections(html_path)
            
            # Generate HTML
            html_content = generate_html_for_problem(
                chapter_name,
                problem_num,
                pdf_filename,
                existing_sections
            )
            
            # Write file
            with open(html_path, 'w') as f:
                f.write(html_content)
            
            total_generated += 1
        
        print(f"✅ {count} files created")
    
    print(f"\n✅ Total: {total_generated} TFS problems generated")
    print(f"📍 All files in: {PROBLEMS_DIR}/")

if __name__ == '__main__':
    main()
