#!/usr/bin/env python3
"""
Fix two issues:
1. Distribute Practice Exam OH across referenced problems (not all on problem 1)
2. URL-encode PDF paths (spaces + # character)
"""

import json
import re
from pathlib import Path
from urllib.parse import quote

DASHBOARD_DIR = Path(__file__).parent
PROBLEMS_DIR = DASHBOARD_DIR / 'problems'
OH_SUMMARIES_DIR = DASHBOARD_DIR.parent / 'mpep-assets' / 'office-hours-consolidated-summaries'

def url_encode_path(path):
    """URL encode path, handling spaces and special chars."""
    # Split path by /, encode each part, rejoin
    parts = path.split('/')
    encoded_parts = [quote(part, safe='') for part in parts]
    return '/'.join(encoded_parts)

def parse_practice_exam_oh_problems(json_data):
    """Extract which problems are discussed in the OH data."""
    problems_discussed = set()
    
    for discussion in json_data.get('office_hours_discussions', []):
        lesson_title = discussion.get('lesson_title', '')
        
        # Parse lesson title for problem numbers
        # Formats: "TFS: Practice Exam 1 - 50", "TFS: Practice Exam #1-23", "TFS: Full Practice Exam 1 #66"
        # Extract LAST number sequence as problem number
        all_numbers = re.findall(r'\d+', lesson_title)
        if all_numbers:
            # Last number is usually the problem number
            problem_num = int(all_numbers[-1])
            problems_discussed.add(problem_num)
    
    return problems_discussed

def get_practice_exam_oh_subset(json_data, problem_num):
    """Get OH discussions relevant to a specific problem number."""
    relevant = []
    
    for discussion in json_data.get('office_hours_discussions', []):
        lesson_title = discussion.get('lesson_title', '')
        
        # Extract last number from lesson title (the problem number)
        numbers = re.findall(r'\d+', lesson_title)
        if numbers:
            last_num = int(numbers[-1])
            if last_num == problem_num:
                relevant.append(discussion)
    
    return relevant

def fix_pdf_path_in_html(html_path):
    """Fix URL encoding in PDF iframe src."""
    try:
        with open(html_path, 'r') as f:
            html = f.read()
        
        # Check if already has double-encoding (%25) and fix it
        if '%2520' in html or '%253' in html:
            # Decode once to get single encoding
            html = html.replace('%2520', '%20').replace('%2523', '%23')
            with open(html_path, 'w') as f:
                f.write(html)
            return True
        
        # For any still unencoded spaces, add encoding
        # Pattern: ../tfs_solutions/Practice Exam #1/...
        def encode_match(match):
            old_path = match.group(1)
            new_path = url_encode_path(old_path)
            return f'src="{new_path}"'
        
        new_html = re.sub(
            r'src="(\.\./tfs_solutions/[^"]*\.pdf)"',
            encode_match,
            html
        )
        
        if new_html != html:
            with open(html_path, 'w') as f:
                f.write(new_html)
            return True
        return False
    except Exception as e:
        print(f"Error fixing {html_path}: {e}")
        return False

def fix_practice_exam_oh():
    """Distribute Practice Exam OH across relevant problems."""
    
    # Load the consolidated Practice Exam 1 OH data
    pe1_json_path = OH_SUMMARIES_DIR / 'TFS_Practice_Exam_1_1.json'
    pe2_json_path = OH_SUMMARIES_DIR / 'TFS_Practice_Exam_2_2.json'
    
    print("🔧 FIXING OFFICE HOURS DISTRIBUTION\n")
    
    for exam_num, json_path in [(1, pe1_json_path), (2, pe2_json_path)]:
        if not json_path.exists():
            print(f"⚠️  {json_path.name} not found, skipping")
            continue
        
        with open(json_path, 'r') as f:
            json_data = json.load(f)
        
        # Get all problems discussed
        problems_discussed = parse_practice_exam_oh_problems(json_data)
        
        print(f"Practice Exam {exam_num}:")
        print(f"  OH discussions reference problems: {sorted(problems_discussed)}")
        
        # For each problem, update its HTML with relevant OH
        for problem_num in range(1, 81):
            html_filename = f"TFS-Practice-Exam-{exam_num}-{problem_num}.html"
            html_path = PROBLEMS_DIR / html_filename
            
            if not html_path.exists():
                continue
            
            # Get subset of OH for this problem
            relevant_oh = get_practice_exam_oh_subset(json_data, problem_num)
            
            if relevant_oh:
                # Update HTML with OH content
                try:
                    with open(html_path, 'r') as f:
                        html = f.read()
                    
                    # Build OH section
                    oh_html = f'<div class="oh-section-title">\n      Office Hours\n      <span class="oh-count">{len(relevant_oh)}</span>\n    </div>\n'
                    oh_html += '    <div class="oh-subtitle">Student questions asked in live office hours about this problem</div>\n'
                    
                    for discussion in relevant_oh:
                        oh_html += '    <div class="qa-group">\n'
                        oh_html += f'      <div class="qa-session">OH {discussion.get("oh_session", "")}</div>\n'
                        oh_html += f'      <div class="qa-question"><strong>Q:</strong> {discussion.get("student_question", "")}</div>\n'
                        oh_html += f'      <div class="qa-answer"><strong>A:</strong> {discussion.get("dan_answer", "")}</div>\n'
                        oh_html += '    </div>\n'
                    
                    oh_section = f'<div class="sidebar-right">\n    {oh_html}  </div>'
                    
                    # Replace OH section
                    new_html = re.sub(
                        r'<div class="sidebar-right">.*?</div>(?=\s*</div>\s*<div class="footer">)',
                        oh_section,
                        html,
                        flags=re.DOTALL
                    )
                    
                    with open(html_path, 'w') as f:
                        f.write(new_html)
                    
                except Exception as e:
                    print(f"    Error updating problem {problem_num}: {e}")
        
        print(f"  ✅ Updated Practice Exam {exam_num}\n")

def fix_pdf_paths():
    """Fix all PDF iframe paths with URL encoding."""
    print("🔧 FIXING PDF PATHS\n")
    
    practice_exam_files = list(PROBLEMS_DIR.glob('TFS-Practice-Exam-*-*.html'))
    
    fixed_count = 0
    for html_path in sorted(practice_exam_files):
        if fix_pdf_path_in_html(html_path):
            fixed_count += 1
    
    print(f"✅ Fixed PDF paths in {fixed_count} Practice Exam files")

def main():
    print("=" * 60)
    print("FIXING TFS PRACTICE EXAM ISSUES")
    print("=" * 60 + "\n")
    
    fix_practice_exam_oh()
    print()
    fix_pdf_paths()
    
    print(f"\n{'=' * 60}")
    print("✅ COMPLETE")
    print("=" * 60)
    print("\nNext: git add -A && git commit -m '...' && git push")

if __name__ == '__main__':
    main()
