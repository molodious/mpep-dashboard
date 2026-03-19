#!/usr/bin/env python3
"""
Restore original OH content from commit 29a01166 (before PDF embedding).
Extract full Q&A pairs and inject into current regenerated files.
"""

import subprocess
import re
from pathlib import Path

DASHBOARD_DIR = Path(__file__).parent
PROBLEMS_DIR = DASHBOARD_DIR / 'problems'
HVAC_FILES = sorted(PROBLEMS_DIR.glob('HVAC-*.html'))

def get_original_oh_section(chapter_name, problem_num):
    """
    Fetch original OH content from commit 29a01166.
    Returns the <div class="sidebar-right"> section.
    """
    html_filename = f"problems/HVAC-{chapter_name}-{problem_num}.html"
    
    try:
        result = subprocess.run(
            ['git', 'show', f'29a01166:{html_filename}'],
            cwd=DASHBOARD_DIR,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return None
        
        html = result.stdout
        
        # Extract the sidebar-right section
        match = re.search(
            r'<div class="sidebar-right">(.*?)</div>\s*</div>\s*<div class="footer">',
            html,
            re.DOTALL
        )
        
        if match:
            return match.group(1).strip()
        return None
    except Exception as e:
        print(f"Error fetching {html_filename}: {e}")
        return None

def inject_oh_content(html_path, oh_content):
    """
    Replace the sidebar-right OH section in current file with original content.
    """
    with open(html_path, 'r') as f:
        html = f.read()
    
    # Replace the entire sidebar-right section
    new_html = re.sub(
        r'<div class="sidebar-right">(.*?)</div>\s*</div>\s*<div class="footer">',
        f'<div class="sidebar-right">{oh_content}</div>\n  </div>\n\n  <div class="footer">',
        html,
        flags=re.DOTALL
    )
    
    with open(html_path, 'w') as f:
        f.write(new_html)

def main():
    print("🔄 RESTORING ORIGINAL OH CONTENT FROM COMMIT 29a01166\n")
    print("=" * 70 + "\n")
    
    restored = 0
    failed = 0
    
    for hvac_file in HVAC_FILES:
        # Extract chapter and problem from filename
        match = re.match(r'HVAC-(.+?)-(\d+)\.html', hvac_file.name)
        if not match:
            continue
        
        chapter_name = match.group(1)
        problem_num = int(match.group(2))
        
        # Fetch original OH section
        oh_content = get_original_oh_section(chapter_name, problem_num)
        
        if oh_content:
            try:
                inject_oh_content(hvac_file, oh_content)
                restored += 1
                if restored % 50 == 0:
                    print(f"  ✅ {restored} files restored...", flush=True)
            except Exception as e:
                print(f"❌ Error updating {hvac_file.name}: {e}")
                failed += 1
        else:
            failed += 1
    
    print(f"\n{'=' * 70}")
    print(f"✅ RESTORATION COMPLETE")
    print(f"{'=' * 70}")
    print(f"Restored: {restored} files with original OH content")
    print(f"Failed:   {failed} files")
    print(f"\nNext: git add -A && git commit -m 'Restore original OH content' && git push")

if __name__ == '__main__':
    main()
