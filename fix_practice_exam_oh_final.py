#!/usr/bin/env python3
"""
Fix Practice Exam OH distribution - properly route to correct problems
"""

import json
import re
from pathlib import Path

DASHBOARD_DIR = Path(__file__).parent
PROBLEMS_DIR = DASHBOARD_DIR / 'problems'
OH_SUMMARIES_DIR = DASHBOARD_DIR.parent / 'mpep-assets' / 'office-hours-consolidated-summaries'

def get_practice_exam_oh_by_problem():
    """Build mapping of problem number -> OH discussions."""
    problem_oh = {}
    
    # Load both practice exam files
    for exam_num in [1, 2]:
        json_path = OH_SUMMARIES_DIR / f'TFS_Practice_Exam_{exam_num}_{exam_num}.json'
        
        if not json_path.exists():
            continue
        
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        for discussion in data.get('office_hours_discussions', []):
            lesson_title = discussion['lesson_title']
            
            # Extract ALL numbers from lesson title
            numbers = re.findall(r'\d+', lesson_title)
            if not numbers:
                continue
            
            # Last number is the problem number
            problem_num = int(numbers[-1])
            
            # Store by (exam_num, problem_num) tuple
            key = (exam_num, problem_num)
            if key not in problem_oh:
                problem_oh[key] = []
            
            problem_oh[key].append(discussion)
    
    return problem_oh

def build_oh_html(discussions):
    """Build OH HTML section for a list of discussions."""
    if not discussions:
        return '''<div class="sidebar-right">
    <div class="oh-section-title">
      Office Hours
      <span class="oh-count">0</span>
    </div>
    <div class="oh-subtitle">Student questions asked in live office hours about this problem</div>
    
    <p style='color:#999;'>No office hours coverage for this problem.</p>
  </div>'''
    
    oh_html = f'<div class="oh-section-title">\n      Office Hours\n      <span class="oh-count">{len(discussions)}</span>\n    </div>\n'
    oh_html += '    <div class="oh-subtitle">Student questions asked in live office hours about this problem</div>\n'
    
    for discussion in discussions:
        oh_html += '    <div class="qa-group">\n'
        oh_html += f'      <div class="qa-session">OH {discussion.get("oh_session", "")}</div>\n'
        oh_html += f'      <div class="qa-question"><strong>Q:</strong> {discussion.get("student_question", "")}</div>\n'
        oh_html += f'      <div class="qa-answer"><strong>A:</strong> {discussion.get("dan_answer", "")}</div>\n'
        oh_html += '    </div>\n'
    
    return f'<div class="sidebar-right">\n    {oh_html}  </div>'

def fix_all_practice_exams():
    """Fix all Practice Exam problems with correct OH."""
    
    # Get problem->OH mapping
    problem_oh = get_practice_exam_oh_by_problem()
    
    print("🔧 FIXING PRACTICE EXAM OFFICE HOURS DISTRIBUTION\n")
    
    total_fixed = 0
    
    for exam_num in [1, 2]:
        print(f"Practice Exam {exam_num}:")
        
        # Problems with OH coverage
        covered_problems = {p for (e, p) in problem_oh.keys() if e == exam_num}
        print(f"  Problems with OH: {sorted(covered_problems)}")
        
        # Fix all 80 problems in this exam
        for problem_num in range(1, 81):
            html_filename = f"TFS-Practice-Exam-{exam_num}-{problem_num}.html"
            html_path = PROBLEMS_DIR / html_filename
            
            if not html_path.exists():
                continue
            
            # Get OH discussions for this problem
            key = (exam_num, problem_num)
            discussions = problem_oh.get(key, [])
            
            # Read and update HTML
            try:
                with open(html_path, 'r') as f:
                    html = f.read()
                
                # Replace entire sidebar-right section
                new_oh_section = build_oh_html(discussions)
                
                # Find and replace the sidebar-right section
                new_html = re.sub(
                    r'<div class="sidebar-right">.*?</div>\s*</div>\s*<div class="footer">',
                    new_oh_section + '\n\n</div>\n\n<div class="footer">',
                    html,
                    flags=re.DOTALL
                )
                
                # Write back
                with open(html_path, 'w') as f:
                    f.write(new_html)
                
                total_fixed += 1
                
                if discussions:
                    print(f"    ✅ Problem {problem_num:2d}: {len(discussions)} discussion(s)")
                    
            except Exception as e:
                print(f"    ❌ Problem {problem_num}: {e}")
        
        print()
    
    print(f"✅ Fixed {total_fixed} Practice Exam files")

if __name__ == '__main__':
    print("=" * 70)
    print("FINAL FIX: PRACTICE EXAM OFFICE HOURS")
    print("=" * 70 + "\n")
    
    fix_all_practice_exams()
    
    print("\n" + "=" * 70)
    print("NEXT: git add -A && git commit && git push")
    print("=" * 70)
