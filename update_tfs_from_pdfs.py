#!/usr/bin/env python3
"""
Update TFS OH Prep dashboard problems with content extracted from TFS solution PDFs.
Preserves video synthesis and office hours sections.
"""

import pdfplumber
import re
import json
from pathlib import Path
from html import escape
from typing import Optional, Dict

def extract_pdf_content(pdf_path: str) -> Optional[Dict]:
    """Extract problem content from PDF."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return parse_problem_text(text)
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return None

def parse_problem_text(raw_text: str) -> Dict:
    """Parse problem statement, choices, and solution from raw PDF text."""
    
    # Remove cid codes and clean up
    text = re.sub(r'\(cid:\d+\)', '', raw_text)
    text = re.sub(r' +', ' ', text)
    text = text.strip()
    
    # Try to identify sections by looking for patterns
    # Most PDFs have: problem statement, then A/B/C/D choices, then solution
    
    lines = text.split('\n')
    
    # Simple heuristic: find lines with "A)" "B)" "C)" "D)"
    choice_indices = []
    for i, line in enumerate(lines):
        if re.match(r'^\s*[A-D]\)\s*', line) or re.match(r'^\s*[A-D]\s+\d', line):
            choice_indices.append(i)
    
    result = {
        'raw_text': text[:500],  # First 500 chars for reference
        'full_text': text,
        'estimated_choices_start': choice_indices[0] if choice_indices else -1,
        'estimated_choices_count': len(choice_indices)
    }
    
    return result

def extract_sections_from_html(html_path: str) -> Dict:
    """Extract video synthesis and office hours sections from existing HTML."""
    try:
        with open(html_path, 'r') as f:
            html = f.read()
        
        # Extract video synthesis section
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
            'video_content': video_content,
            'oh_content': oh_content,
            'full_html': html
        }
    except Exception as e:
        print(f"Error reading HTML: {e}")
        return {}

def create_formatted_solution(pdf_text: str) -> str:
    """Create a nicely formatted solution from PDF text."""
    
    # Clean up the text
    text = re.sub(r'\(cid:\d+\)', '', pdf_text)
    text = re.sub(r'^\s*[A-D]\)\s*.*?(?=[A-D]\)|$)', '', text, flags=re.MULTILINE | re.DOTALL)
    
    # Split into sentences and wrap in paragraphs
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    
    solution_html = ""
    for sentence in sentences:
        if sentence.strip():
            # Check if it looks like math/calculation
            if any(char in sentence for char in ['=', '+', '×', '÷', 'Btu', 'lb']):
                solution_html += f'<p style="font-family: \'Courier New\', monospace; background: #f9f9f9; padding: 10px; border-radius: 3px; margin: 10px 0; line-height: 1.6;">{escape(sentence.strip())}</p>\n'
            else:
                solution_html += f'<p>{escape(sentence.strip())}</p>\n'
    
    return solution_html

def update_problem_html(
    html_path: str,
    statement: str,
    choices: list,
    solution: str,
    answer_letter: str = "D"
) -> bool:
    """Update HTML file with new problem content."""
    
    try:
        with open(html_path, 'r') as f:
            html = f.read()
        
        # Extract existing video and OH sections
        sections = extract_sections_from_html(html_path)
        
        # Build choices HTML
        choices_html = ""
        for choice in choices:
            # Parse choice format "A) 630Btu" or similar
            letter, text = choice['letter'], choice['text']
            choices_html += f"      <div class='choice'><span class='choice-letter'>{letter}</span> {escape(text)}</div>\n"
        
        # Build solution section
        solution_box = f"""<div class="solution-box" id="sol-box">{solution}</div>"""
        
        # Replace problem statement
        html = re.sub(
            r'<div class="problem-statement">.*?</div>',
            f'<div class="problem-statement">{escape(statement)}</div>',
            html,
            flags=re.DOTALL
        )
        
        # Replace choices
        html = re.sub(
            r'<div class="choices">.*?</div>',
            f'<div class="choices">\n{choices_html}    </div>',
            html,
            flags=re.DOTALL
        )
        
        # Replace answer tag
        html = re.sub(
            r'<span class="answer-tag">Answer: [A-D]</span>',
            f'<span class="answer-tag">Answer: {answer_letter}</span>',
            html
        )
        
        # Replace solution box
        html = re.sub(
            r'<div class="solution-box" id="sol-box">.*?</div>',
            solution_box,
            html,
            flags=re.DOTALL
        )
        
        # Write updated HTML
        with open(html_path, 'w') as f:
            f.write(html)
        
        return True
    except Exception as e:
        print(f"Error updating HTML: {e}")
        return False

# Test with first TFS PDF
pdf_path = "/home/mpepagent/.openclaw/workspace/tfs_solutions/Thermodynamics/Thermodynamics-01.pdf"
html_path = "/home/mpepagent/.openclaw/workspace/projects/mpep-dashboard/problems/TFS-Thermodynamics-1.html"

print("=== EXTRACTION TEST ===\n")

content = extract_pdf_content(pdf_path)
if content:
    print(f"PDF: {pdf_path}\n")
    print(f"Estimated choices found: {content['estimated_choices_count']}")
    print(f"First 500 characters:\n")
    print(content['raw_text'])
    print("\n" + "="*50 + "\n")

# Check what's currently in the HTML
sections = extract_sections_from_html(html_path)
print(f"Current HTML structure:")
print(f"  - Video content length: {len(sections.get('video_content', ''))}")
print(f"  - OH content length: {len(sections.get('oh_content', ''))}")
print("\nTo proceed with update, we need:")
print("  1. Clean problem statement extracted from PDF")
print("  2. Answer choices (A, B, C, D) identified")
print("  3. Solution text properly formatted")
print("\nThe PDF text is messy from extraction. Ready to:")
print("  → Manually clean and structure it, OR")
print("  → Use AI to parse and reformat the PDF content")
