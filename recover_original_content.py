#!/usr/bin/env python3
"""
Recover video synthesis + office hours content from original commit (29a01166).
Saves to original_content.json for use by generator script.
"""

import re
import json
import subprocess
from pathlib import Path

# TFS problem file patterns
TFS_PATTERNS = [
    'TFS-Thermodynamics-',
    'TFS-Heat-Transfer-',
    'TFS-Hydraulic-Fluid-',
    'TFS-Energy-Power-',
    'TFS-Supporting-Topics-',
    'TFS-Practice-Exam-1-',
    'TFS-Practice-Exam-2-',
]

ORIGINAL_COMMIT = '29a01166'  # Commit with original video/OH content

def extract_video_and_oh(html):
    """Extract video synthesis and OH sections from HTML."""
    
    # Extract video content
    video_match = re.search(
        r'<div class="video-box">(.*?)</div>\s*</div>\s*</div>\s*<div class="sidebar-right">',
        html, re.DOTALL
    )
    video_content = video_match.group(1).strip() if video_match else ""
    
    # Extract OH section
    oh_match = re.search(
        r'(<div class="sidebar-right">.*?</div>\s*</div>)',
        html, re.DOTALL
    )
    oh_content = oh_match.group(1) if oh_match else ""
    
    return video_content, oh_content

def main():
    print(f"Recovering original content from commit {ORIGINAL_COMMIT}...\n")
    
    content_map = {}
    
    # Get list of all files in that commit
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", ORIGINAL_COMMIT, "problems/"],
        capture_output=True, text=True
    )
    
    all_files = result.stdout.strip().split('\n')
    tfs_files = [f for f in all_files if any(pattern in f for pattern in TFS_PATTERNS)]
    
    print(f"Found {len(tfs_files)} TFS problem files\n")
    
    for i, filepath in enumerate(tfs_files):
        filename = Path(filepath).stem
        
        try:
            result = subprocess.run(
                ["git", "show", f"{ORIGINAL_COMMIT}:{filepath}"],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode != 0:
                print(f"❌ {filename}: git show failed")
                continue
            
            html = result.stdout
            video_content, oh_content = extract_video_and_oh(html)
            
            if video_content or oh_content:
                content_map[filename] = {
                    'video': video_content,
                    'oh': oh_content
                }
                print(f"✅ {filename}: video={bool(video_content)}, oh={bool(oh_content)}")
            else:
                print(f"⚠️  {filename}: No content found")
                
        except subprocess.TimeoutExpired:
            print(f"❌ {filename}: Timeout")
        except Exception as e:
            print(f"❌ {filename}: {e}")
    
    print(f"\n{'='*60}")
    print(f"Saving {len(content_map)} problems to original_content.json...")
    
    with open('original_content.json', 'w') as f:
        json.dump(content_map, f, indent=2)
    
    print(f"✅ Saved to: original_content.json")
    print(f"\nNext: Use with updated generator script")

if __name__ == '__main__':
    main()
