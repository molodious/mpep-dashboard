#!/usr/bin/env python3
"""
Extract problem statement, choices, and solution from TFS solution PDFs.
Preserves video synthesis and office hours sections from existing dashboard HTML.
"""

import pdfplumber
import os
import re
from pathlib import Path
from html import escape

def extract_pdf_content(pdf_path):
    """Extract problem, choices, and solution from PDF."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return None

def clean_pdf_text(text):
    """Clean up PDF extraction artifacts (cid codes, etc)."""
    if not text:
        return ""
    
    # Remove cid codes
    text = re.sub(r'\(cid:\d+\)', '', text)
    
    # Clean up multiple spaces
    text = re.sub(r' +', ' ', text)
    
    # Clean up multiple newlines
    text = re.sub(r'\n\n+', '\n\n', text)
    
    return text.strip()

def parse_problem_content(raw_text):
    """Parse problem statement, choices (A-D), and solution from raw text."""
    
    clean_text = clean_pdf_text(raw_text)
    
    # This is a rough extraction - PDFs vary in format
    # Return raw extracted text for manual review
    return {
        'raw_text': clean_text[:2000],  # First 2000 chars for preview
        'full_text': clean_text
    }

def update_html_with_pdf_content(html_path, pdf_content):
    """Update HTML file with PDF content while preserving OH/video sections."""
    
    try:
        with open(html_path, 'r') as f:
            html = f.read()
        
        # Extract video synthesis and office hours sections
        video_match = re.search(r'<div class="video-box"[^>]*>.*?</div>', html, re.DOTALL)
        oh_match = re.search(r'<div class="oh-section"[^>]*>.*?(?=<h3>|<div class="sidebar-right">|$)', html, re.DOTALL)
        
        video_section = video_match.group(0) if video_match else ""
        oh_section = oh_match.group(0) if oh_match else ""
        
        return {
            'video_section': video_section,
            'oh_section': oh_section,
            'full_html': html
        }
    except Exception as e:
        print(f"Error reading HTML: {e}")
        return None

# Test extraction on first TFS PDF
pdf_path = "/home/mpepagent/.openclaw/workspace/tfs_solutions/Thermodynamics/Thermodynamics-01.pdf"
print("Extracting: Thermodynamics-01.pdf\n")

content = extract_pdf_content(pdf_path)
if content:
    parsed = parse_problem_content(content)
    print("=== EXTRACTED TEXT (first 2000 chars) ===\n")
    print(parsed['raw_text'])
    print("\n=== FULL TEXT LENGTH ===")
    print(f"{len(parsed['full_text'])} characters")
