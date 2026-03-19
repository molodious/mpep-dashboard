#!/usr/bin/env python3
"""
Rebuild oh-prep-index.json with all available problems
"""

import json
import re
from pathlib import Path
from collections import defaultdict

DASHBOARD_DIR = Path(__file__).parent
PROBLEMS_DIR = DASHBOARD_DIR / 'problems'

def extract_metadata_from_html(html_path):
    """Extract metadata from HTML file."""
    try:
        with open(html_path, 'r') as f:
            content = f.read()
        
        # Extract title
        title_match = re.search(r'<title>(.*?)</title>', content)
        title = title_match.group(1) if title_match else ""
        
        # Extract problem meta
        meta_match = re.search(r'<div class="problem-meta">(.*?)</div>', content)
        meta = meta_match.group(1) if meta_match else ""
        
        # Check if PDF is present
        has_pdf = 'class="pdf-viewer"' in content
        
        # Check if OH is present
        has_oh = 'No office hours coverage' not in content and 'oh-count' in content
        
        return {
            'title': title,
            'meta': meta,
            'has_pdf': has_pdf,
            'has_oh': has_oh
        }
    except Exception as e:
        return None

def main():
    print("🔨 REBUILDING OH PREP INDEX\n")
    
    # Scan all problem files
    problems_by_category = defaultdict(list)
    
    for html_file in sorted(PROBLEMS_DIR.glob('*.html')):
        filename = html_file.stem
        
        # Skip benchmark files
        if 'BENCHMARK' in filename.upper():
            continue
        
        metadata = extract_metadata_from_html(html_file)
        if not metadata:
            continue
        
        # Parse filename to category
        # Examples: HVAC-Thermodynamics-1, TFS-Heat-Transfer-5
        parts = filename.rsplit('-', 1)
        if len(parts) == 2:
            category = parts[0]
            problem_num = int(parts[1])
        else:
            continue
        
        problems_by_category[category].append({
            'id': filename,
            'problem_number': problem_num,
            'title': metadata['title'],
            'has_pdf': metadata['has_pdf'],
            'has_oh': metadata['has_oh']
        })
    
    # Sort problems within each category
    for category in problems_by_category:
        problems_by_category[category].sort(key=lambda x: x['problem_number'])
    
    # Build index structure
    index = {
        'version': '2',
        'last_updated': '2026-03-19',
        'categories': []
    }
    
    for category in sorted(problems_by_category.keys()):
        problems = problems_by_category[category]
        
        category_obj = {
            'name': category,
            'problem_count': len(problems),
            'problems': problems
        }
        
        index['categories'].append(category_obj)
        
        print(f"✅ {category}: {len(problems)} problems")
    
    # Write index
    output_path = DASHBOARD_DIR / 'oh-prep-index.json'
    with open(output_path, 'w') as f:
        json.dump(index, f, indent=2)
    
    total_problems = sum(len(cat['problems']) for cat in index['categories'])
    
    print(f"\n{'='*60}")
    print(f"✅ INDEX REBUILT")
    print(f"{'='*60}")
    print(f"Total problems: {total_problems}")
    print(f"Categories: {len(index['categories'])}")
    print(f"Output: {output_path}")

if __name__ == '__main__':
    main()
