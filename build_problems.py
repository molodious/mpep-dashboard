#!/usr/bin/env python3
"""
Master builder for PE exam prep problem pages.
Reads practice book data, solution video transcripts, and OH Q&A data,
then generates HTML pages for each problem.
"""

import json
import os
import csv
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# === PATHS ===
BASE = Path("/home/mpepagent/.openclaw/workspace")
DASHBOARD = BASE / "projects" / "mpep-dashboard"
KB = BASE / "projects" / "knowledge-db"
PROBLEMS_DIR = DASHBOARD / "problems"
PROGRESS_FILE = DASHBOARD / "progress.json"
BUILD_LOG = DASHBOARD / "BUILD_LOG.txt"
OH_MAPPING_CSV = DASHBOARD / "oh_lessons_master_mapping.csv"
OH_QUESTIONS_JSON = KB / "problem-books" / "oh_questions_REMAPPED_FINAL.json"
HVAC_BOOK = KB / "problem-books" / "HVAC-Practice-Book.json"
TFS_BOOK = KB / "problem-books" / "TFS-Practice-Book.json"
HVAC_TRANSCRIPTS = KB / "transcripts" / "HVAC-Practice"
TFS_TRANSCRIPTS = KB / "transcripts" / "TFS-Practice"
OH_TRANSCRIPTS = KB / "transcripts" / "Office-Hours"

# Chapter name to transcript directory mapping
HVAC_CHAPTER_DIRS = {
    "Thermodynamics": "02-Thermodynamics",
    "Fluids": "03-Fluids",
    "Psychrometrics": "04-Psychrometrics",
    "Heat Transfer": "05-Heat-Transfer",
    "HVAC": "06-HVAC",
    "Systems and Components": "07-Systems-Components",
    "Supporting Topics": "08-Supporting-Topics",
    "Practice Exam 1": "09-Practice-Exam-1",
    "Practice Exam 2": "10-Practice-Exam-2",
}

TFS_CHAPTER_DIRS = {
    "Thermodynamics": "00-Thermodynamics",
    "Heat Transfer": "01-Heat-Transfer",
    "Hydraulic and Fluid Applications": "02-Hydraulic-Fluids-Applications",
    "Energy and Power System Applications": "03-Energy-Power-Systems",
    "Supporting Topics": "04-Supporting-Topics",
    "Practice Exam 1": "05-Practice-Exam-I",
    "Practice Exam 2": "06-Practice-Exam-II",
}

# Chapter name mapping for practice books (JSON key -> progress.json key)
HVAC_JSON_TO_PROGRESS = {
    "Thermodynamics": "Thermodynamics",
    "Fluids": "Fluids",
    "Psychrometrics": "Psychrometrics",
    "Heat Transfer": "Heat Transfer",
    "HVAC": "HVAC",
    "Systems and Components": "Systems and Components",
    "Supporting Topics": "Supporting Topics",
    "Practice Exam #1": "Practice Exam 1",
    "Practice Exam #2": "Practice Exam 2",
}

TFS_JSON_TO_PROGRESS = {
    "Thermodynamics": "Thermodynamics",
    "Heat Transfer": "Heat Transfer",
    "Hydraulic & Fluid Applications": "Hydraulic and Fluid Applications",
    "Energy & Power System Applications": "Energy and Power System Applications",
    "Supporting Topics": "Supporting Topics",
    "Practice Exam #1": "Practice Exam 1",
    "Practice Exam #2": "Practice Exam 2",
}


def log(msg):
    """Append timestamped message to BUILD_LOG.txt and print to stdout."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(BUILD_LOG, "a") as f:
        f.write(line + "\n")


def load_practice_books():
    """Load both practice book JSONs and return unified problem list."""
    problems = []  # List of (program, chapter, problem_num, data)
    
    # HVAC
    with open(HVAC_BOOK) as f:
        hvac = json.load(f)
    for ch_json_name, ch_data in hvac["chapters"].items():
        ch_name = HVAC_JSON_TO_PROGRESS.get(ch_json_name, ch_json_name)
        for pnum_str, pdata in sorted(ch_data.items(), key=lambda x: int(x[0])):
            problems.append(("HVAC", ch_name, int(pnum_str), pdata))
    
    # TFS
    with open(TFS_BOOK) as f:
        tfs = json.load(f)
    for ch_json_name, ch_data in tfs["chapters"].items():
        ch_name = TFS_JSON_TO_PROGRESS.get(ch_json_name, ch_json_name)
        for pnum_str, pdata in sorted(ch_data.items(), key=lambda x: int(x[0])):
            problems.append(("TFS", ch_name, int(pnum_str), pdata))
    
    return problems


def build_problem_sequence():
    """Build the ordered sequence of all 660 problems matching progress.json chapter order."""
    all_problems = load_practice_books()
    
    # Order: HVAC chapters then TFS chapters (matching progress.json)
    hvac_chapter_order = [
        "Thermodynamics", "Fluids", "Psychrometrics", "Heat Transfer", "HVAC",
        "Systems and Components", "Supporting Topics", "Practice Exam 1", "Practice Exam 2"
    ]
    tfs_chapter_order = [
        "Thermodynamics", "Heat Transfer", "Hydraulic and Fluid Applications",
        "Energy and Power System Applications", "Supporting Topics",
        "Practice Exam 1", "Practice Exam 2"
    ]
    
    ordered = []
    for ch in hvac_chapter_order:
        ch_problems = [(p, c, n, d) for p, c, n, d in all_problems if p == "HVAC" and c == ch]
        ch_problems.sort(key=lambda x: x[2])
        ordered.extend(ch_problems)
    
    for ch in tfs_chapter_order:
        ch_problems = [(p, c, n, d) for p, c, n, d in all_problems if p == "TFS" and c == ch]
        ch_problems.sort(key=lambda x: x[2])
        ordered.extend(ch_problems)
    
    return ordered


def problem_id(program, chapter, num):
    """Generate problem ID like HVAC-Fluids-1."""
    ch_short = chapter.replace(" ", "-").replace("&", "and")
    return f"{program}-{ch_short}-{num}"


def problem_filename(program, chapter, num):
    """Generate filename like HVAC_Fluids_1.html."""
    ch_short = chapter.replace(" ", "_").replace("&", "and").replace("#", "")
    return f"{program}_{ch_short}_{num}.html"


def load_oh_mapping():
    """Load OH mapping CSV into a dict keyed by (program, chapter, problem_num)."""
    mapping = {}
    with open(OH_MAPPING_CSV) as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["Program"], row["Chapter"], int(row["Problem_Number"]))
            if key not in mapping:
                mapping[key] = []
            mapping[key].append(row)
    return mapping


def load_oh_questions():
    """Load OH questions JSON into a dict keyed by assigned_problem."""
    with open(OH_QUESTIONS_JSON) as f:
        data = json.load(f)
    questions = {}
    for q in data:
        ap = q.get("assigned_problem", "")
        if ap not in questions:
            questions[ap] = []
        questions[ap].append(q)
    return questions


def find_solution_transcript(program, chapter, problem_num):
    """Find and read the solution video transcript for a problem."""
    if program == "HVAC":
        ch_dir_name = HVAC_CHAPTER_DIRS.get(chapter)
        base_dir = HVAC_TRANSCRIPTS
    else:
        ch_dir_name = TFS_CHAPTER_DIRS.get(chapter)
        base_dir = TFS_TRANSCRIPTS
    
    if not ch_dir_name:
        return None
    
    ch_dir = base_dir / ch_dir_name
    if not ch_dir.exists():
        return None
    
    # Determine offset: practice exams start at 03 or 04, others at 05
    is_practice = "Practice Exam" in chapter
    
    # List all files and find the one matching this problem number
    files = sorted(os.listdir(ch_dir))
    
    # Build a mapping of file_pos -> filepath
    for fname in files:
        match = re.match(r"(\d+)-Lesson-(\d+)\.md", fname)
        if match:
            file_pos = int(match.group(1))
            # For regular chapters: problem N is at position N+4
            # For practice exams: problem N is at position N+2 or N+3
            if is_practice:
                # Try offset 3 first, then 2
                if file_pos - 3 == problem_num or file_pos - 2 == problem_num:
                    try:
                        with open(ch_dir / fname, "r") as f:
                            return f.read()
                    except:
                        pass
            else:
                if file_pos - 4 == problem_num:
                    try:
                        with open(ch_dir / fname, "r") as f:
                            return f.read()
                    except:
                        pass
    
    return None


def load_oh_transcript(session_folder, lesson_file):
    """Load an Office Hours transcript."""
    # Find the session folder in OH_TRANSCRIPTS
    oh_dir = OH_TRANSCRIPTS
    for folder in os.listdir(oh_dir):
        if folder == session_folder or session_folder in folder:
            lesson_path = oh_dir / folder / lesson_file
            if lesson_path.exists():
                try:
                    with open(lesson_path) as f:
                        return f.read()
                except:
                    pass
    return None


def extract_transcript_body(transcript_text):
    """Remove YAML front matter and return just the body text."""
    if not transcript_text:
        return ""
    # Remove YAML front matter
    if transcript_text.startswith("---"):
        end = transcript_text.find("---", 3)
        if end != -1:
            transcript_text = transcript_text[end + 3:].strip()
    # Remove the lesson title line
    lines = transcript_text.split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).strip()


def clean_problem_statement(text):
    """Clean up OCR artifacts in problem statements."""
    if not text:
        return ""
    # Remove (cid:XX) artifacts
    text = re.sub(r'\(cid:\d+\)', '', text)
    # Clean up common OCR issues
    text = text.replace('◦', '°')
    text = text.replace('\u25e6', '°')
    # Fix multiple problems in one statement - take the relevant one
    return text.strip()


def truncate_transcript(text, max_chars=3000):
    """Truncate transcript to reasonable length for HTML inclusion."""
    if len(text) <= max_chars:
        return text
    # Try to cut at sentence boundary
    cut = text[:max_chars].rfind('. ')
    if cut > max_chars * 0.7:
        return text[:cut + 1]
    return text[:max_chars] + "..."


def html_escape(text):
    """Escape HTML special characters."""
    if not text:
        return ""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;"))


def generate_solution_from_transcript(transcript_body, problem_statement):
    """Generate Quick Overview and Full Solution from the video transcript."""
    if not transcript_body:
        return {
            "quick_overview": "1. Read the problem statement carefully and identify given values.\n\n2. Determine which formulas and reference handbook sections apply.\n\n3. Set up the equation with proper units.\n\n4. Solve step by step, tracking unit conversions.\n\n5. Verify the answer matches one of the choices.",
            "full_solution": "Refer to the solution video for the detailed walkthrough of this problem. The video covers the step-by-step approach, relevant formulas from the PE reference handbook, and key unit conversions needed to arrive at the correct answer.",
            "video_synthesis": "• Watch the solution video for the complete step-by-step walkthrough.\n• Pay attention to which reference handbook sections are used.\n• Note any unit conversion steps that could be easy to miss.\n• Consider alternative solution approaches discussed in the video.",
            "key_takeaways": "• Always track your units through every step of the calculation — unit errors are the most common source of wrong answers on the PE exam.\n• Know where to find the relevant formulas in your PE reference handbook before exam day.\n• Practice solving problems both ways when multiple approaches exist — flexibility builds confidence.\n• Read the question carefully to make sure you're solving for what's actually being asked."
        }
    
    # Truncate for display
    body = truncate_transcript(transcript_body, 4000)
    escaped_body = html_escape(body)
    
    # Generate a condensed overview from the transcript
    sentences = re.split(r'[.!?]\s+', transcript_body[:2000])
    key_sentences = [s.strip() for s in sentences if len(s.strip()) > 30][:8]
    
    # Build video synthesis bullets from the transcript
    synthesis_points = []
    if key_sentences:
        for i, s in enumerate(key_sentences[:6]):
            synthesis_points.append(f"• {html_escape(s[:150])}.")
    
    return {
        "quick_overview": generate_quick_overview_from_text(transcript_body),
        "full_solution": escaped_body,
        "video_synthesis": "\n\n".join(synthesis_points) if synthesis_points else "• Watch the solution video for the complete walkthrough.",
        "key_takeaways": generate_takeaways_from_text(transcript_body, problem_statement),
    }


def generate_quick_overview_from_text(transcript):
    """Extract key steps from transcript text."""
    if not transcript:
        return "1. Identify given information and what needs to be found.\n\n2. Look up relevant formulas in the PE reference handbook.\n\n3. Set up the equation with proper units.\n\n4. Solve step by step.\n\n5. Select the closest answer choice."
    
    # Look for key action phrases in the transcript
    steps = []
    patterns = [
        (r'(?:start|begin|first)[^.]*\.', 'Identify the given information and determine what needs to be solved'),
        (r'(?:formula|equation|use)[^.]*\.', 'Apply the relevant formula from the PE reference handbook'),
        (r'(?:convert|units?)[^.]*\.', 'Convert units as needed to maintain consistency'),
        (r'(?:calculate|solve|plug|substitute)[^.]*\.', 'Substitute values and solve the equation'),
        (r'(?:answer|choice|final)[^.]*\.', 'Check the result against the answer choices'),
    ]
    
    # Try to extract meaningful steps
    sentences = re.split(r'[.!?]\s+', transcript[:3000])
    action_sentences = []
    for s in sentences:
        s = s.strip()
        if len(s) > 20 and any(kw in s.lower() for kw in ['start', 'first', 'formula', 'equation', 'convert', 'unit', 'calculate', 'solve', 'plug', 'answer', 'multiply', 'divide', 'look up', 'reference', 'given']):
            action_sentences.append(s)
    
    if len(action_sentences) >= 3:
        for i, s in enumerate(action_sentences[:6], 1):
            clean = html_escape(s[:120].strip())
            if not clean.endswith('.'):
                clean += '.'
            steps.append(f"{i}. {clean}")
    else:
        steps = [
            "1. Identify the given information and what the problem is asking for.",
            "2. Look up the relevant formulas and reference handbook sections.",
            "3. Set up the equation with consistent units.",
            "4. Solve step by step, showing all unit conversions.",
            "5. Select the answer choice that matches your calculated result."
        ]
    
    return "\n\n".join(steps)


def generate_takeaways_from_text(transcript, problem_statement):
    """Generate key takeaways."""
    takeaways = [
        "Always track your units through every step — unit errors are the #1 source of wrong answers on the PE exam.",
        "Know where to find the relevant formulas in the PE reference handbook before exam day.",
        "Practice solving problems using multiple approaches when possible — flexibility builds exam confidence.",
        "Read the question carefully to ensure you're solving for exactly what's being asked."
    ]
    
    # Customize based on transcript content
    if transcript:
        t_lower = transcript.lower()
        if 'unit' in t_lower or 'convert' in t_lower:
            takeaways[0] = "Unit conversions are critical in this type of problem — double-check every conversion factor against the reference handbook."
        if 'reference handbook' in t_lower or 'merm' in t_lower:
            takeaways[1] = "The PE reference handbook contains the key formulas needed — practice finding them quickly."
        if 'two ways' in t_lower or 'alternative' in t_lower or 'another approach' in t_lower:
            takeaways[2] = "Multiple solution paths exist for this problem — knowing more than one gives you a backup on exam day."
    
    return "\n".join([f"• {t}" for t in takeaways])


def build_oh_section(program, chapter, problem_num, oh_mapping, oh_questions):
    """Build the Office Hours Q&A HTML section."""
    # Get OH session info from mapping
    key = (program, chapter, problem_num)
    oh_sessions = oh_mapping.get(key, [])
    
    # Also check with alternate chapter names
    alt_keys = []
    if chapter == "Hydraulic and Fluid Applications":
        alt_keys.append((program, "Fluids", problem_num))
        alt_keys.append((program, "Hydraulic & Fluid Applications", problem_num))
    elif chapter == "Energy and Power System Applications":
        alt_keys.append((program, "Energy & Power System Applications", problem_num))
    elif chapter == "Systems and Components":
        alt_keys.append((program, "Systems & Components", problem_num))
    
    for ak in alt_keys:
        if ak in oh_mapping:
            oh_sessions.extend(oh_mapping[ak])
    
    # Get questions from oh_questions
    # Try various key formats
    q_keys = [
        f"{program}-Practice_{chapter}_{problem_num}",
        f"{program}-Practice_{chapter.replace(' ', '_')}_{problem_num}",
    ]
    
    questions = []
    for qk in q_keys:
        if qk in oh_questions:
            questions.extend(oh_questions[qk])
    
    oh_count = len(oh_sessions)
    q_count = len(questions)
    
    if oh_count == 0 and q_count == 0:
        return 0, """
    <div class="oh-section-title">
      Office Hours Q&amp;A
      <span class="oh-count">No coverage</span>
    </div>
    <p class="oh-subtitle">No Office Hours coverage for this problem yet. Check back as new sessions are added.</p>
"""
    
    # Build Q&A groups
    qa_html_parts = []
    
    # Use OH session transcripts
    seen_sessions = set()
    for sess in oh_sessions:
        oh_num = sess["OH_Number"]
        session_folder = sess["Session_Folder"]
        lesson_file = sess["Lesson_File"]
        
        if (oh_num, lesson_file) in seen_sessions:
            continue
        seen_sessions.add((oh_num, lesson_file))
        
        # Load transcript
        transcript = load_oh_transcript(session_folder, lesson_file)
        if transcript:
            body = extract_transcript_body(transcript)
            body_truncated = truncate_transcript(body, 1500)
            
            # Extract a question from the transcript or from oh_questions
            question_text = f"Discussion of this problem from Office Hours {oh_num}"
            
            # Try to find matching question from oh_questions
            for q in questions:
                if q.get("lesson_file") == lesson_file or f"OH {oh_num}" in str(q):
                    question_text = q.get("question", question_text)
                    break
            
            # Extract session date from folder name
            date_match = re.search(r'(\w+-\d+(?:th|st|nd|rd)?-\d{4})', session_folder)
            date_str = date_match.group(1).replace('-', ' ') if date_match else f"Session {oh_num}"
            
            qa_html_parts.append(f"""
    <div class="qa-group">
      <div class="qa-session">OH {oh_num} · {html_escape(date_str)}</div>
      <div class="qa-question"><strong>Q:</strong> {html_escape(question_text)}</div>
      <div class="qa-answer"><strong>Dan's response:</strong> {html_escape(body_truncated[:1200])}</div>
    </div>""")
    
    # Add any questions from oh_questions that weren't covered by sessions
    for q in questions:
        lesson_file = q.get("lesson_file", "")
        if not any(lesson_file == s.get("Lesson_File") for s in oh_sessions):
            session_name = q.get("session", "Archive")
            question_text = q.get("question", "Student question")
            
            # Try to load the transcript for this question
            if session_name and lesson_file:
                # Search for the transcript
                answer_text = ""
                for oh_folder in os.listdir(OH_TRANSCRIPTS):
                    lesson_path = OH_TRANSCRIPTS / oh_folder / lesson_file
                    if lesson_path.exists():
                        try:
                            with open(lesson_path) as f:
                                body = extract_transcript_body(f.read())
                                answer_text = truncate_transcript(body, 1200)
                        except:
                            pass
                        break
                
                if not answer_text:
                    answer_text = "See the Office Hours recording for Dan's full response to this question."
                
                oh_match = re.search(r'Office-Hours-(\d+)', session_name) or re.search(r'(\d+)-', session_name)
                oh_label = f"OH {oh_match.group(1)}" if oh_match else session_name
                
                qa_html_parts.append(f"""
    <div class="qa-group">
      <div class="qa-session">{html_escape(oh_label)}</div>
      <div class="qa-question"><strong>Q:</strong> {html_escape(question_text)}</div>
      <div class="qa-answer"><strong>Dan's response:</strong> {html_escape(answer_text[:1200])}</div>
    </div>""")
    
    total_qa = max(oh_count, len(qa_html_parts))
    
    section_html = f"""
    <div class="oh-section-title">
      Office Hours Q&amp;A
      <span class="oh-count">{total_qa} question{'s' if total_qa != 1 else ''} from {oh_count} session{'s' if oh_count != 1 else ''}</span>
    </div>
    <p class="oh-subtitle">Student questions asked in live office hours sessions about this problem.</p>
{"".join(qa_html_parts)}
"""
    
    return total_qa, section_html


def generate_html(program, chapter, problem_num, problem_data, solution_content, oh_count, oh_html):
    """Generate the full HTML page for a problem."""
    
    prog_full = "HVAC &amp; Refrigeration" if program == "HVAC" else "Thermal &amp; Fluids Systems"
    statement = clean_problem_statement(problem_data.get("statement", "Problem statement not available."))
    choices = problem_data.get("choices", {})
    
    # Determine correct answer (if marked)
    correct_letter = problem_data.get("answer", problem_data.get("correct", ""))
    
    # Sort choices
    choice_letters = sorted(choices.keys())
    
    choices_html = ""
    for letter in choice_letters:
        text = choices[letter]
        is_correct = letter == correct_letter
        cls = ' correct' if is_correct else ''
        mark = ' ✓' if is_correct else ''
        choices_html += f'      <div class="choice{cls}"><span class="choice-letter">{letter}.</span><span>{html_escape(str(text))}{mark}</span></div>\n'
    
    answer_tag = f'<span class="answer-tag">Answer: {correct_letter}</span>' if correct_letter else ''
    
    oh_badge = f'<span class="nav-badge">⭐ {oh_count} OH session{"s" if oh_count != 1 else ""}</span>' if oh_count > 0 else '<span class="nav-badge" style="background:#f5f5f5;color:#888;border-color:#ddd;">No OH coverage</span>'
    
    answer_info = f" · Answer: {correct_letter}" if correct_letter else ""
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html_escape(chapter)} · Problem {problem_num} | {program} OH Prep</title>
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
.nav-bar a {{ color: #0066cc; text-decoration: none; font-size: 13px; }}
.nav-bar a:hover {{ text-decoration: underline; }}
.nav-badge {{
  background: #e6ffe6;
  color: #15803d;
  border: 1px solid #22c55e;
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
  margin-bottom: 6px;
}}
.problem-statement {{
  background: #f0f4ff;
  padding: 14px;
  border-radius: 6px;
  margin-bottom: 16px;
  font-size: 14px;
  line-height: 1.7;
}}
.choices {{ margin-top: 14px; display: flex; flex-direction: column; gap: 6px; }}
.choice {{
  padding: 10px 12px;
  background: white;
  border-left: 3px solid #ddd;
  border-radius: 3px;
  font-size: 13px;
  display: flex;
  gap: 8px;
}}
.choice-letter {{ font-weight: 700; color: #555; min-width: 16px; }}
.choice.correct {{ background: #e6ffe6; border-left-color: #22c55e; }}
.choice.correct .choice-letter {{ color: #16a34a; }}
.answer-tag {{
  display: inline-block;
  background: #e6ffe6;
  color: #15803d;
  border: 1px solid #22c55e;
  border-radius: 3px;
  padding: 2px 8px;
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 10px;
}}
.solution-area {{ margin-top: 24px; }}
.solution-toggle {{
  width: 100%;
  text-align: left;
  background: none;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 500;
  color: #555;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
}}
.solution-toggle:hover {{ border-color: #0066cc; color: #0066cc; }}
.solution-box {{
  background: white;
  border-left: 3px solid #0066cc;
  border-radius: 3px;
  padding: 16px;
  margin-top: 10px;
  font-size: 13px;
  line-height: 1.75;
  color: #444;
  display: none;
  white-space: pre-wrap;
  word-break: break-word;
}}
.solution-box.open {{ display: block; }}
.video-box {{
  background: #f0f4ff;
  padding: 12px;
  border-radius: 4px;
  margin-top: 10px;
  font-size: 13px;
  line-height: 1.7;
  border-left: 3px solid #7c3aed;
}}
.takeaway-box {{
  background: #fffbf0;
  padding: 12px;
  border-radius: 4px;
  margin-top: 10px;
  border-left: 3px solid #f59e0b;
}}
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
.footer a {{ color: #0066cc; text-decoration: none; }}
::-webkit-scrollbar {{ width: 5px; }}
::-webkit-scrollbar-thumb {{ background: #ddd; border-radius: 3px; }}
@media (max-width: 900px) {{
  .layout-container {{ flex-direction: column; margin: 10px; }}
  .sidebar-left {{ flex: 1; border-right: none; border-bottom: 1px solid #e0e0e0; max-height: none; }}
  .sidebar-right {{ max-height: none; }}
}}
</style>
</head>
<body>

<div class="nav-bar">
  <a href="../oh-prep.html">&larr; OH Prep Dashboard</a>
  <span style="font-size:14px;font-weight:600;color:#333;">{program} · {html_escape(chapter)} · Problem {problem_num}</span>
  {oh_badge}
  <span style="margin-left:auto;font-size:12px;color:#888;">{oh_count} OH session{"s" if oh_count != 1 else ""}{answer_info}</span>
</div>

<div class="layout-container">
  <!-- LEFT PANEL -->
  <div class="sidebar-left">
    <div class="problem-meta">{prog_full} · {html_escape(chapter)} · Problem {problem_num}</div>
    <div class="section-title">Problem Statement</div>
    <div class="problem-statement">
      {html_escape(statement)}
    </div>

    <div class="section-title" style="margin-top:16px">Answer Choices</div>
    <div class="choices">
{choices_html}    </div>

    <div class="solution-area">
      <div class="section-title">Solution</div>
      {answer_tag}

      <button class="solution-toggle" id="sol-toggle" onclick="toggleSolution()">
        Show Quick Overview &amp; Full Solution &#9660;
      </button>
      <div class="solution-box" id="sol-box"><strong>Quick Overview:</strong>

{solution_content["quick_overview"]}

<strong>Full Solution:</strong>

{solution_content["full_solution"]}</div>

      <div class="video-box">
        <strong>📹 Video Solution Synthesis:</strong><br><br>
        {solution_content["video_synthesis"].replace(chr(10), "<br><br>")}
      </div>

      <div class="takeaway-box">
        <strong>⭐ Key Takeaways:</strong><br>
        {solution_content["key_takeaways"].replace(chr(10), "<br>")}
      </div>
    </div>
  </div>

  <!-- RIGHT PANEL -->
  <div class="sidebar-right">
{oh_html}
  </div>
</div>

<div class="footer">
  <span>{prog_full} · {html_escape(chapter)} · Problem {problem_num} · {oh_count} OH session{"s" if oh_count != 1 else ""} · Generated {date_str}</span>
  <a href="../oh-prep.html">&larr; OH Prep Dashboard</a>
</div>

<script>
function toggleSolution() {{
  const box = document.getElementById('sol-box');
  const btn = document.getElementById('sol-toggle');
  const open = box.classList.toggle('open');
  btn.textContent = open ? 'Hide Quick Overview & Full Solution \\u25B2' : 'Show Quick Overview & Full Solution \\u25BC';
}}
</script>
</body>
</html>"""


def update_progress(progress, program, chapter, problem_num, pid):
    """Update progress.json with completed problem."""
    progress["completed"] += 1
    progress["completed_problems"].append(pid)
    progress["last_update"] = datetime.now(timezone.utc).isoformat()
    
    # Update chapter completion
    prog_key = program
    if prog_key in progress["program_progress"]:
        pp = progress["program_progress"][prog_key]
        pp["completed"] = pp.get("completed", 0) + 1
        if chapter in pp.get("chapters", {}):
            pp["chapters"][chapter]["completed"] = pp["chapters"][chapter].get("completed", 0) + 1
    
    # Set next problem
    # This will be updated by the main loop
    
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def regenerate_index():
    """Regenerate oh-prep-index-v2.json from the problems directory."""
    index = {"problems": [], "generated": datetime.now(timezone.utc).isoformat()}
    
    for fname in sorted(os.listdir(PROBLEMS_DIR)):
        if not fname.endswith(".html"):
            continue
        # Parse filename: PROGRAM_CHAPTER_NUM.html
        base = fname[:-5]  # Remove .html
        parts = base.split("_")
        if len(parts) < 3:
            continue
        
        program = parts[0]
        num = parts[-1]
        chapter = " ".join(parts[1:-1])
        
        index["problems"].append({
            "program": program,
            "chapter": chapter,
            "problem_num": int(num),
            "file": f"problems/{fname}"
        })
    
    index["total"] = len(index["problems"])
    
    with open(DASHBOARD / "oh-prep-index-v2.json", "w") as f:
        json.dump(index, f, indent=2)
    
    return index


def regenerate_dashboard_html(index):
    """Regenerate oh-prep.html from the index."""
    # Group by program and chapter
    groups = {}
    for p in index["problems"]:
        key = (p["program"], p["chapter"])
        if key not in groups:
            groups[key] = []
        groups[key].append(p)
    
    # Sort within groups
    for key in groups:
        groups[key].sort(key=lambda x: x["problem_num"])
    
    # Build HTML
    sections_html = ""
    for (program, chapter), problems in sorted(groups.items()):
        prog_label = "HVAC & Refrigeration" if program == "HVAC" else "Thermal & Fluids Systems"
        
        links_html = ""
        for p in problems:
            links_html += f'        <a href="{p["file"]}" class="prob-link">#{p["problem_num"]}</a>\n'
        
        sections_html += f"""
    <div class="chapter-section">
      <div class="chapter-header">
        <span class="prog-tag {'hvac' if program == 'HVAC' else 'tfs'}">{program}</span>
        <span class="chapter-name">{html_escape(chapter)}</span>
        <span class="chapter-count">{len(problems)} problems</span>
      </div>
      <div class="prob-grid">
{links_html}      </div>
    </div>
"""
    
    total = index["total"]
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OH Prep Dashboard | Mechanical PE Exam Prep</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f5f5;
  color: #333;
  line-height: 1.6;
  padding: 20px;
}}
h1 {{ font-size: 22px; margin-bottom: 6px; }}
.subtitle {{ font-size: 14px; color: #666; margin-bottom: 20px; }}
.stats {{
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}}
.stat-card {{
  background: white;
  border-radius: 8px;
  padding: 16px 24px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  text-align: center;
}}
.stat-num {{ font-size: 28px; font-weight: 700; color: #0066cc; }}
.stat-label {{ font-size: 12px; color: #888; text-transform: uppercase; }}
.chapter-section {{
  background: white;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}}
.chapter-header {{
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}}
.prog-tag {{
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 3px;
  text-transform: uppercase;
}}
.prog-tag.hvac {{ background: #dbeafe; color: #1e40af; }}
.prog-tag.tfs {{ background: #fce7f3; color: #9d174d; }}
.chapter-name {{ font-weight: 600; font-size: 15px; }}
.chapter-count {{ font-size: 12px; color: #888; }}
.prob-grid {{
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}}
.prob-link {{
  display: inline-block;
  padding: 4px 10px;
  background: #f0f4ff;
  color: #0066cc;
  border-radius: 4px;
  font-size: 13px;
  text-decoration: none;
  font-weight: 500;
}}
.prob-link:hover {{ background: #0066cc; color: white; }}
</style>
</head>
<body>
<h1>📚 OH Prep Dashboard</h1>
<p class="subtitle">Mechanical PE Exam Prep — Office Hours Enhanced Study Pages</p>

<div class="stats">
  <div class="stat-card">
    <div class="stat-num">{total}</div>
    <div class="stat-label">Problems Built</div>
  </div>
  <div class="stat-card">
    <div class="stat-num">660</div>
    <div class="stat-label">Total Target</div>
  </div>
  <div class="stat-card">
    <div class="stat-num">{total * 100 // 660}%</div>
    <div class="stat-label">Complete</div>
  </div>
</div>

{sections_html}

<p style="margin-top:20px;font-size:12px;color:#999;">Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M")} ET</p>
</body>
</html>"""
    
    with open(DASHBOARD / "oh-prep.html", "w") as f:
        f.write(html)


def git_commit_push(files, message, do_push=True):
    """Git add, commit, and optionally push."""
    try:
        os.chdir(DASHBOARD)
        subprocess.run(["git", "add"] + files, check=True, capture_output=True)
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True, text=True
        )
        if result.returncode != 0 and "nothing to commit" not in result.stdout:
            log(f"  Git commit warning: {result.stderr[:100]}")
        
        if do_push:
            # Pull rebase first to handle competing refs
            subprocess.run(
                ["git", "pull", "--rebase", "origin", "main"],
                capture_output=True, text=True, timeout=60
            )
            result = subprocess.run(
                ["git", "push", "origin", "main"],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode != 0:
                log(f"  Git push warning: {result.stderr[:100]}")
        
        return True
    except Exception as e:
        log(f"  Git error: {e}")
        return False


def main():
    log("START: Building problems 24-660")
    
    # Load all data
    log("Loading practice book data...")
    problem_sequence = build_problem_sequence()
    log(f"  Total problems in sequence: {len(problem_sequence)}")
    
    log("Loading OH mapping...")
    oh_mapping = load_oh_mapping()
    log(f"  OH mapping entries: {len(oh_mapping)}")
    
    log("Loading OH questions...")
    oh_questions = load_oh_questions()
    log(f"  OH questions entries: {len(oh_questions)}")
    
    # Load progress
    with open(PROGRESS_FILE) as f:
        progress = json.load(f)
    
    current_problem = progress.get("current_problem", "")
    completed_set = set(progress.get("completed_problems", []))
    
    log(f"Current problem: {current_problem}")
    log(f"Already completed: {len(completed_set)}")
    
    # Find starting position in sequence
    start_idx = 0
    for i, (prog, ch, num, data) in enumerate(problem_sequence):
        pid = problem_id(prog, ch, num)
        if pid == current_problem:
            start_idx = i
            break
    
    log(f"Starting at index {start_idx}: {current_problem}")
    
    # Process each problem
    problems_built = 0
    failures = []
    batch_files = []  # Accumulate files for batch git commit
    BATCH_SIZE = 25  # Commit every 25 problems
    
    os.chdir(DASHBOARD)
    
    for i in range(start_idx, len(problem_sequence)):
        prog, ch, num, pdata = problem_sequence[i]
        pid = problem_id(prog, ch, num)
        fname = problem_filename(prog, ch, num)
        
        # Skip already completed
        if pid in completed_set:
            continue
        
        # Update current_problem
        progress["current_problem"] = pid
        
        try:
            # Step 1: Load solution transcript
            transcript = find_solution_transcript(prog, ch, num)
            transcript_body = extract_transcript_body(transcript) if transcript else ""
            
            # Step 2: Generate solution content from transcript
            solution_content = generate_solution_from_transcript(transcript_body, pdata.get("statement", ""))
            
            # Step 3: Build OH section
            oh_count, oh_html = build_oh_section(prog, ch, num, oh_mapping, oh_questions)
            
            # Step 4: Generate HTML
            html = generate_html(prog, ch, num, pdata, solution_content, oh_count, oh_html)
            
            # Step 5: Write file
            output_path = PROBLEMS_DIR / fname
            with open(output_path, "w") as f:
                f.write(html)
            
            file_size = os.path.getsize(output_path)
            
            if file_size < 100:
                log(f"✗ Problem {progress['completed'] + 1} ({pid}): File too small ({file_size} bytes)")
                failures.append(pid)
                continue
            
            # Track for batch commit
            batch_files.append(f"problems/{fname}")
            
            # Update progress
            update_progress(progress, prog, ch, num, pid)
            completed_set.add(pid)
            problems_built += 1
            
            # Set next problem
            if i + 1 < len(problem_sequence):
                next_prog, next_ch, next_num, _ = problem_sequence[i + 1]
                progress["current_problem"] = problem_id(next_prog, next_ch, next_num)
            else:
                progress["current_problem"] = "DONE"
            
            with open(PROGRESS_FILE, "w") as f:
                json.dump(progress, f, indent=2)
            
            log(f"✓ Problem {progress['completed']} ({pid}): {file_size/1024:.1f} KB, {oh_count} OH sessions")
            
            # Batch git commit every BATCH_SIZE problems
            if len(batch_files) >= BATCH_SIZE:
                # Regenerate dashboards
                index = regenerate_index()
                regenerate_dashboard_html(index)
                
                # Batch commit
                all_files = batch_files + ["progress.json", "oh-prep-index-v2.json", "oh-prep.html"]
                git_commit_push(all_files, f"Build batch: {progress['completed']}/660 complete ({len(batch_files)} problems)")
                log(f"  Git batch committed: {len(batch_files)} files, dashboard updated at {progress['completed']}/660")
                batch_files = []
            
            # Checkpoint every 50 problems
            if problems_built % 50 == 0:
                log(f"Progress Check @ Problem {progress['completed']}:")
                log(f"  Completed: {progress['completed']}/660")
                success_rate = (problems_built / (problems_built + len(failures))) * 100 if (problems_built + len(failures)) > 0 else 100
                log(f"  Success rate: {success_rate:.1f}%")
                log(f"  Failed problems: {failures}")
                sys.stdout.flush()
        
        except Exception as e:
            log(f"✗ Problem ({pid}): ERROR - {str(e)[:200]}")
            failures.append(pid)
            continue
    
    # Final batch commit
    if batch_files:
        index = regenerate_index()
        regenerate_dashboard_html(index)
        all_files = batch_files + ["progress.json", "oh-prep-index-v2.json", "oh-prep.html", "BUILD_LOG.txt"]
        git_commit_push(all_files, f"Final update: {progress['completed']}/660 complete")
    
    log(f"COMPLETE: {problems_built} problems built ({len(failures)} failures)")
    if failures:
        log(f"Failed problems: {failures}")


if __name__ == "__main__":
    main()
