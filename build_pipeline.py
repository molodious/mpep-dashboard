#!/usr/bin/env python3
"""
MPEP Dashboard Problem Builder v2
Rebuilds HTML pages for problems 24-660 with proper content.
Uses actual solution text and properly formatted OH transcripts.
"""

import json
import csv
import os
import sys
import subprocess
import time
import html as html_mod
import re
from datetime import datetime, timezone

# Paths
BASE = "/home/mpepagent/.openclaw/workspace/projects/mpep-dashboard"
KB = "/home/mpepagent/.openclaw/workspace/projects/knowledge-db/problem-books"
TRANSCRIPTS = "/home/mpepagent/.openclaw/workspace/projects/knowledge-db/transcripts/Office-Hours"
PROBLEMS_DIR = os.path.join(BASE, "problems")
PROGRESS_FILE = os.path.join(BASE, "progress.json")
BUILD_LOG = os.path.join(BASE, "BUILD_LOG.txt")
ORDER_FILE = os.path.join(BASE, "problem_order.json")
OH_MAPPING = os.path.join(BASE, "oh_lessons_master_mapping.csv")

os.makedirs(PROBLEMS_DIR, exist_ok=True)

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(BUILD_LOG, "a") as f:
        f.write(line + "\n")

def load_json(path):
    with open(path) as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# Load all data upfront
log("=" * 60)
log("MPEP Dashboard Builder v2 - Starting fresh rebuild")
log("=" * 60)
log("Loading problem books...")
hvac_book = load_json(os.path.join(KB, "HVAC-Practice-Book.json"))
tfs_book = load_json(os.path.join(KB, "TFS-Practice-Book.json"))
solutions = load_json(os.path.join(KB, "solutions_extracted.json"))
problem_order = load_json(ORDER_FILE)

log(f"Total problems in order: {len(problem_order)}")

# Load OH mapping: key -> list of entries
oh_map = {}
with open(OH_MAPPING, "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        prog = row["Program"]
        chap = row["Chapter"]
        num = row["Problem_Number"]
        key = f"{prog}_{chap}_{num}"
        if key not in oh_map:
            oh_map[key] = []
        oh_map[key].append({
            "oh_number": row["OH_Number"],
            "session_folder": row["Session_Folder"],
            "lesson_file": row["Lesson_File"],
            "lesson_title": row.get("Lesson_Title", ""),
        })

log(f"OH mapping: {len(oh_map)} problems have OH coverage")

def get_problem_data(program, chapter, num):
    book = hvac_book if program == "HVAC" else tfs_book
    chapters = book.get("chapters", {})
    ch_data = chapters.get(chapter, {})
    return ch_data.get(str(num), None)

def strip_frontmatter(content):
    """Strip YAML frontmatter and lesson heading from transcript."""
    if not content:
        return ""
    text = content.strip()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2].strip()
    # Remove leading markdown heading
    lines = text.split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).strip()

def load_oh_transcript(session_folder, lesson_file):
    """Load and clean OH transcript."""
    path = os.path.join(TRANSCRIPTS, session_folder, lesson_file)
    if os.path.exists(path):
        with open(path) as f:
            return strip_frontmatter(f.read())
    return None

def get_oh_data(program, chapter, num):
    key = f"{program}_{chapter}_{num}"
    entries = oh_map.get(key, [])
    sessions = []
    for entry in entries:
        transcript = load_oh_transcript(entry["session_folder"], entry["lesson_file"])
        if transcript and len(transcript) > 20:
            # Extract OH session info from folder name
            folder = entry["session_folder"]
            # Parse "02-Office-Hours-15-May-28-2021" -> "OH 15 · May 28, 2021"
            oh_num = entry["oh_number"]
            # Try to extract date from folder name
            date_match = re.search(r'(\w+)-(\d+)(?:st|nd|rd|th)?-(\d{4})', folder)
            date_str = ""
            if date_match:
                month, day, year = date_match.group(1), date_match.group(2), date_match.group(3)
                date_str = f" · {month} {day}, {year}"
            
            sessions.append({
                "oh_number": oh_num,
                "date_str": date_str,
                "title": entry["lesson_title"],
                "transcript": transcript,
            })
    return sessions

def esc(text):
    return html_mod.escape(str(text)) if text else ""

def clean_solution_text(raw_text):
    """Clean solution text - remove the problem statement that's often prepended."""
    if not raw_text:
        return ""
    text = raw_text.strip()
    # The solution text often starts with the problem statement + choices, then the actual solution
    # Look for common solution starters
    starters = [
        "Start by", "First,", "The key", "This problem", "We need", "Begin by",
        "Using", "From", "Given:", "Given ", "Solution:", "Step 1", "The answer",
        "Apply", "Calculate", "To solve", "To find", "Consider", "Recall",
        "Note that", "Recognize", "Set up", "Write", "For this",
    ]
    
    # Try to find where the actual solution starts (after choices like "A.", "B.", "C.", "D.")
    # Look for the last answer choice marker
    last_choice = -1
    for marker in ["D.", "D)", "(D)"]:
        idx = text.find(marker)
        if idx > last_choice:
            # Find the end of that line
            newline = text.find("\n", idx)
            if newline == -1:
                newline = idx + 50
            last_choice = newline
    
    if last_choice > 0 and last_choice < len(text) - 100:
        text = text[last_choice:].strip()
    
    return text

def format_solution_html(solution_text, answer):
    """Format solution text into readable HTML content."""
    if not solution_text:
        return f"<strong>Answer: {esc(answer)}</strong>\n\nDetailed solution not yet available for this problem."
    
    cleaned = clean_solution_text(solution_text)
    if not cleaned:
        return f"<strong>Answer: {esc(answer)}</strong>\n\nDetailed solution not yet available for this problem."
    
    return esc(cleaned)

def truncate_transcript(text, max_chars=4000):
    """Truncate long transcripts sensibly at sentence boundaries."""
    if len(text) <= max_chars:
        return text
    # Find last sentence end before max_chars
    truncated = text[:max_chars]
    last_period = truncated.rfind(".")
    if last_period > max_chars * 0.7:
        return truncated[:last_period + 1] + " [...]"
    return truncated + " [...]"

def generate_html(program, chapter, num, problem_data, solution_data, oh_sessions):
    statement = problem_data.get("statement", "Problem statement not available.") if problem_data else "Problem statement not available."
    choices = problem_data.get("choices", {}) if problem_data else {}
    
    answer = solution_data.get("answer", "N/A") if solution_data else "N/A"
    sol_text = solution_data.get("text", "") if solution_data else ""
    
    program_full = "HVAC &amp; Refrigeration" if program == "HVAC" else "Thermal &amp; Fluids Systems"
    oh_count = len(oh_sessions)
    oh_badge = f'<span class="nav-badge">⭐ {oh_count} OH session{"s" if oh_count != 1 else ""}</span>' if oh_count > 0 else ""
    
    # Build choices HTML
    choices_html = ""
    for letter in ["A", "B", "C", "D"]:
        choice_text = choices.get(letter, "")
        if not choice_text:
            continue
        is_correct = letter == answer
        cls = ' correct' if is_correct else ''
        check = ' ✓' if is_correct else ''
        choices_html += f'      <div class="choice{cls}"><span class="choice-letter">{letter}.</span><span>{esc(choice_text)}{check}</span></div>\n'
    
    # Build solution content
    sol_html = format_solution_html(sol_text, answer)
    
    # Build OH Q&A section
    if oh_sessions:
        qa_groups = ""
        for sess in oh_sessions:
            transcript = truncate_transcript(sess["transcript"])
            qa_groups += f'''    <div class="qa-group">
      <div class="qa-session">OH {esc(sess["oh_number"])}{esc(sess["date_str"])}</div>
      <div class="qa-transcript">{esc(transcript)}</div>
    </div>\n'''
        
        oh_html = f'''<div class="oh-section-title">
      Office Hours Q&amp;A
      <span class="oh-count">{oh_count} session{"s" if oh_count != 1 else ""}</span>
    </div>
    <p class="oh-subtitle">Dan&#39;s live office hours discussions about this problem.</p>
    {qa_groups}'''
    else:
        oh_html = '''<div class="oh-section-title">
      Office Hours Q&amp;A
      <span class="oh-count">No sessions</span>
    </div>
    <p class="oh-subtitle">This problem has not yet been covered in office hours.</p>'''
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(chapter)} · Problem {num} | {program} OH Prep</title>
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
.qa-transcript {{
  font-size: 12px;
  line-height: 1.6;
  color: #444;
  white-space: pre-wrap;
  word-break: break-word;
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
  <a href="../oh-prep.html">← OH Prep Dashboard</a>
  <span style="font-size:14px;font-weight:600;color:#333;">{program} · {esc(chapter)} · Problem {num}</span>
  {oh_badge}
  <span style="margin-left:auto;font-size:12px;color:#888;">{oh_count} OH session{"s" if oh_count != 1 else ""} · Answer: {esc(answer)}</span>
</div>

<div class="layout-container">
  <div class="sidebar-left">
    <div class="problem-meta">{program_full} · {esc(chapter)} · Problem {num}</div>
    <div class="section-title">Problem Statement</div>
    <div class="problem-statement">
      {esc(statement)}
    </div>

    <div class="section-title" style="margin-top:16px">Answer Choices</div>
    <div class="choices">
{choices_html}    </div>

    <div class="solution-area">
      <div class="section-title">Solution</div>
      <span class="answer-tag">Answer: {esc(answer)}</span>

      <button class="solution-toggle" id="sol-toggle" onclick="toggleSolution()">
        Show Solution ▼
      </button>
      <div class="solution-box" id="sol-box">{sol_html}</div>
    </div>
  </div>

  <div class="sidebar-right">
    {oh_html}
  </div>
</div>

<div class="footer">
  <span>{program_full} · {esc(chapter)} · Problem {num} · {oh_count} OH session{"s" if oh_count != 1 else ""} · Generated {date_str}</span>
  <a href="../oh-prep.html">← OH Prep Dashboard</a>
</div>

<script>
function toggleSolution() {{
  const box = document.getElementById('sol-box');
  const btn = document.getElementById('sol-toggle');
  const open = box.classList.toggle('open');
  btn.textContent = open ? 'Hide Solution ▲' : 'Show Solution ▼';
}}
</script>
</body>
</html>'''

def make_filename(program, chapter, num):
    """Create filename matching existing convention (spaces -> underscores, # removed)."""
    ch = chapter.replace(" ", "_").replace("#", "").replace("&", "and")
    # Clean up double underscores
    while "__" in ch:
        ch = ch.replace("__", "_")
    return f"{program}_{ch}_{num}.html"

def make_problem_id(program, chapter, num):
    ch = chapter.replace(" ", "-").replace("&", "and").replace("#", "")
    while "--" in ch:
        ch = ch.replace("--", "-")
    return f"{program}-{ch}-{num}"

# ===== MAIN BUILD LOOP =====
def main():
    # Reset progress for rebuild starting at problem 24
    START_IDX = 23  # 0-indexed, problem 24 is index 23
    total = len(problem_order)
    
    # Load current progress and reset for rebuild
    progress = load_json(PROGRESS_FILE)
    progress["completed"] = START_IDX
    progress["current_problem"] = make_problem_id(*problem_order[START_IDX])
    progress["completed_problems"] = progress["completed_problems"][:START_IDX]
    progress["failed"] = 0
    progress["failed_problems"] = []
    progress["start_time"] = datetime.now(timezone.utc).isoformat()
    save_json(PROGRESS_FILE, progress)
    
    log(f"Rebuilding problems {START_IDX + 1} to {total} ({total - START_IDX} problems)")
    
    built = 0
    failed = 0
    
    for idx in range(START_IDX, total):
        program, chapter, num = problem_order[idx]
        sol_key = f"{program}_{chapter}_{num}"
        
        try:
            # Get data
            problem_data = get_problem_data(program, chapter, num)
            solution_data = solutions.get(sol_key)
            oh_sessions = get_oh_data(program, chapter, num)
            
            # Generate HTML
            html_content = generate_html(program, chapter, num, problem_data, solution_data, oh_sessions)
            
            # Write file
            filename = make_filename(program, chapter, num)
            filepath = os.path.join(PROBLEMS_DIR, filename)
            with open(filepath, "w") as f:
                f.write(html_content)
            
            # Update progress
            built += 1
            progress["completed"] = idx + 1
            if idx + 1 < total:
                progress["current_problem"] = make_problem_id(*problem_order[idx + 1])
            else:
                progress["current_problem"] = "COMPLETE"
            progress["completed_problems"].append(make_problem_id(program, chapter, num))
            
            # Update chapter progress
            prog_prog = progress.get("program_progress", {}).get(program, {})
            if prog_prog:
                prog_prog["completed"] = prog_prog.get("completed", 0) + 1
                # Try to update chapter count
                for ck, cv in prog_prog.get("chapters", {}).items():
                    # Fuzzy match chapter names
                    if ck.lower().replace(" ", "").replace("&", "and") == chapter.lower().replace(" ", "").replace("&", "and"):
                        cv["completed"] = cv.get("completed", 0) + 1
                        break
            
            oh_info = f"{len(oh_sessions)}OH" if oh_sessions else "noOH"
            sol_info = "sol" if solution_data else "noSol"
            
            if built % 50 == 0:
                log(f"[{idx+1}/{total}] Built {built} so far... ({program} {chapter} {num}) [{sol_info},{oh_info}]")
                save_json(PROGRESS_FILE, progress)
            
        except Exception as e:
            failed += 1
            progress["failed"] = failed
            progress["failed_problems"].append(sol_key)
            log(f"[{idx+1}/{total}] FAILED {sol_key}: {e}")
            continue
    
    # Save final progress
    progress["status"] = "complete" if failed == 0 else "complete-with-errors"
    progress["last_update"] = datetime.now(timezone.utc).isoformat()
    save_json(PROGRESS_FILE, progress)
    
    log(f"BUILD COMPLETE: {built} built, {failed} failed out of {total - START_IDX}")
    
    # Git operations
    log("Running git add + commit + push...")
    try:
        subprocess.run(["git", "add", "problems/", "progress.json"], cwd=BASE, capture_output=True, timeout=60)
        result = subprocess.run(
            ["git", "commit", "-m", f"Rebuild {built} problem pages (24-660) with proper content"],
            cwd=BASE, capture_output=True, text=True, timeout=60
        )
        log(f"Git commit: {result.stdout.strip()[:200]}")
        
        result = subprocess.run(["git", "push"], cwd=BASE, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            log("Git push: SUCCESS")
        else:
            log(f"Git push: {result.stderr.strip()[:200]}")
    except Exception as e:
        log(f"Git error: {e}")

if __name__ == "__main__":
    main()
