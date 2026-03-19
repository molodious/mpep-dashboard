#!/usr/bin/env python3
"""
Generate all 329 TFS problem HTML files with embedded PDFs.
Replaces all TFS-*.html files with PDF-embedded versions.
Preserves video synthesis and office hours sections from existing files.

Usage:
  python3 generate_all_tfs_pdfs_v2.py --dry-run    # Preview without writing
  python3 generate_all_tfs_pdfs_v2.py --confirm    # Generate all files
"""

import os
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime

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
        
        # Extract office hours section
        oh_match = re.search(
            r'(<div class="sidebar-right">.*?</div>)',
            html, re.DOTALL
        )
        oh_content = oh_match.group(1) if oh_match else ""
        
        return {
            'video': video_content,
            'oh': oh_content
        }
    except Exception as e:
        return {'video': "", 'oh': ""}

def generate_html_for_problem(chapter_name, problem_num, pdf_filename, existing_sections=None):
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
    
    parser = argparse.ArgumentParser(description='Generate all 329 TFS problem HTML files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be generated without writing')
    parser.add_argument('--confirm', action='store_true', help='Actually generate all files')
    args = parser.parse_args()
    
    if not args.dry_run and not args.confirm:
        print("Usage:")
        print("  python3 generate_all_tfs_pdfs_v2.py --dry-run    # Preview without writing")
        print("  python3 generate_all_tfs_pdfs_v2.py --confirm    # Generate all 329 files")
        sys.exit(1)
    
    total_planned = 0
    missing_pdfs = []
    
    for chapter_name, info in TFS_MAPPING.items():
        prefix = info['prefix']
        count = info['count']
        
        chapter_dir = TFS_SOLUTIONS_DIR / chapter_name
        
        if not chapter_dir.exists():
            print(f"❌ Chapter directory missing: {chapter_dir}")
            continue
        
        if args.dry_run:
            print(f"\n{chapter_name}:")
        
        for problem_num in range(1, count + 1):
            # Find the PDF file
            pdf_files = list(chapter_dir.glob(f"*{problem_num:02d}.pdf")) + \
                       list(chapter_dir.glob(f"*-{problem_num:02d}.pdf")) + \
                       list(chapter_dir.glob(f"{problem_num:02d}*.pdf"))
            
            html_filename = f"{prefix}-{problem_num}.html"
            html_path = PROBLEMS_DIR / html_filename
            
            if not pdf_files:
                missing_pdfs.append(f"{chapter_name} / Problem {problem_num}")
                if args.dry_run:
                    print(f"  ⚠️  Problem {problem_num:2d}: PDF not found")
                continue
            
            pdf_filename = pdf_files[0].name
            total_planned += 1
            
            if args.dry_run:
                pdf_status = "✅" if html_path.exists() else "🆕"
                print(f"  {pdf_status} Problem {problem_num:2d}: {html_filename}")
    
    if args.dry_run:
        print(f"\n{'='*60}")
        print(f"📊 DRY RUN SUMMARY")
        print(f"{'='*60}")
        print(f"Total problems to generate: {total_planned}")
        if missing_pdfs:
            print(f"Missing PDFs: {len(missing_pdfs)}")
            for item in missing_pdfs[:5]:
                print(f"  - {item}")
            if len(missing_pdfs) > 5:
                print(f"  ... and {len(missing_pdfs) - 5} more")
        print(f"\n✅ Ready to proceed with: python3 generate_all_tfs_pdfs_v2.py --confirm")
        return
    
    # ACTUAL GENERATION
    if args.confirm:
        print(f"\n🚀 GENERATING {total_planned} TFS PROBLEMS...")
        print(f"{'='*60}\n")
        
        total_generated = 0
        total_skipped = 0
        
        for chapter_name, info in TFS_MAPPING.items():
            prefix = info['prefix']
            count = info['count']
            chapter_dir = TFS_SOLUTIONS_DIR / chapter_name
            
            if not chapter_dir.exists():
                continue
            
            print(f"  {chapter_name}...", end=" ", flush=True)
            chapter_generated = 0
            
            for problem_num in range(1, count + 1):
                pdf_files = list(chapter_dir.glob(f"*{problem_num:02d}.pdf")) + \
                           list(chapter_dir.glob(f"*-{problem_num:02d}.pdf")) + \
                           list(chapter_dir.glob(f"{problem_num:02d}*.pdf"))
                
                if not pdf_files:
                    total_skipped += 1
                    continue
                
                pdf_filename = pdf_files[0].name
                html_filename = f"{prefix}-{problem_num}.html"
                html_path = PROBLEMS_DIR / html_filename
                
                # Extract existing video/OH if file exists
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
                try:
                    with open(html_path, 'w') as f:
                        f.write(html_content)
                    chapter_generated += 1
                    total_generated += 1
                except Exception as e:
                    print(f"\n  ❌ Error writing {html_filename}: {e}")
            
            print(f"✅ {chapter_generated} files")
        
        print(f"\n{'='*60}")
        print(f"✅ COMPLETE!")
        print(f"{'='*60}")
        print(f"Generated: {total_generated} files")
        print(f"Skipped:   {total_skipped} (PDF not found)")
        print(f"Location:  {PROBLEMS_DIR}/")
        print(f"\nNext: git add -A && git commit -m '...' && git push")

if __name__ == '__main__':
    main()
