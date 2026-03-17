#!/usr/bin/env python3
"""
Master build script for 660 PE Exam Prep problem pages.
Generates HTML from template, commits each to GitHub.
"""

import json, csv, os, sys, subprocess, time, html
from datetime import datetime, timezone
from pathlib import Path

# Paths
BASE = Path("/home/mpepagent/.openclaw/workspace/projects/mpep-dashboard")
KB = Path("/home/mpepagent/.openclaw/workspace/projects/knowledge-db")
PROBLEMS_DIR = BASE / "problems"
PROGRESS_FILE = BASE / "progress.json"
BUILD_LOG = BASE / "BUILD_LOG.txt"
OH_CSV = BASE / "oh_lessons_master_mapping.csv"
OH_QUESTIONS = KB / "problem-books" / "oh_questions_REMAPPED_FINAL.json"
OH_TRANSCRIPTS = KB / "transcripts" / "Office-Hours"
HVAC_BOOK = KB / "problem-books" / "HVAC-Practice-Book.json"
TFS_BOOK = KB / "problem-books" / "TFS-Practice-Book.json"

PROBLEMS_DIR.mkdir(exist_ok=True)

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(BUILD_LOG, "a") as f:
        f.write(line + "\n")

def load_practice_books():
    with open(HVAC_BOOK) as f:
        hvac = json.load(f)
    with open(TFS_BOOK) as f:
        tfs = json.load(f)
    return {"HVAC": hvac, "TFS": tfs}

def build_problem_order(books):
    """Build ordered list of all 660 problems."""
    problems = []
    for program, book in [("HVAC", books["HVAC"]), ("TFS", books["TFS"])]:
        for ch_name, ch_data in book["chapters"].items():
            if isinstance(ch_data, dict):
                for prob_num in sorted(ch_data.keys(), key=lambda x: int(x)):
                    problems.append({
                        "program": program,
                        "chapter": ch_name,
                        "num": int(prob_num),
                        "statement": ch_data[prob_num].get("statement", ""),
                        "choices": ch_data[prob_num].get("choices", {})
                    })
    return problems

def load_oh_mapping():
    """Load OH CSV mapping: (program, chapter, num) -> list of OH rows."""
    mapping = {}
    with open(OH_CSV) as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["Program"], row["Chapter"], row["Problem_Number"])
            if key not in mapping:
                mapping[key] = []
            mapping[key].append(row)
    return mapping

def load_oh_questions():
    """Load OH questions mapped to problems."""
    with open(OH_QUESTIONS) as f:
        data = json.load(f)
    # Build lookup: problem_key -> list of questions
    mapping = {}
    for q in data:
        ap = q.get("assigned_problem", "")
        if ap:
            if ap not in mapping:
                mapping[ap] = []
            mapping[ap].append(q)
    return mapping

def read_oh_transcript(session_folder, lesson_file):
    """Read an OH transcript file."""
    # Find the folder
    oh_dir = OH_TRANSCRIPTS
    target = None
    for d in oh_dir.iterdir():
        if session_folder in d.name:
            target = d
            break
    if not target:
        # Try matching by OH number
        for d in oh_dir.iterdir():
            if d.name.startswith(session_folder[:2]) or session_folder in d.name:
                target = d
                break
    if not target:
        return ""
    
    lesson_path = target / lesson_file
    if lesson_path.exists():
        try:
            return lesson_path.read_text(errors='replace')[:8000]  # Cap at 8KB
        except:
            return ""
    return ""

def esc(text):
    """HTML escape."""
    return html.escape(str(text)) if text else ""

def clean_chapter_name(ch):
    """Normalize chapter name for display."""
    return ch.replace("#", "").strip()

def file_key(program, chapter, num):
    """Generate filename key: HVAC_Fluids_1"""
    ch_clean = chapter.replace(" ", "-").replace("#", "").replace("'", "")
    return f"{program}_{ch_clean}_{num}"

def oh_question_key(program, chapter, num):
    """Key format used in oh_questions_REMAPPED_FINAL.json."""
    return f"{program}-Practice_{chapter}_{num}"

def generate_html(problem, oh_rows, oh_questions_list, oh_transcripts):
    """Generate full HTML page for a problem."""
    prog = problem["program"]
    ch = problem["chapter"]
    num = problem["num"]
    stmt = esc(problem["statement"])
    choices = problem["choices"]
    
    prog_display = "HVAC &amp; Refrigeration" if prog == "HVAC" else "Thermal &amp; Fluids Systems"
    ch_display = esc(clean_chapter_name(ch))
    oh_count = len(oh_rows)
    
    # Sort choices by letter
    sorted_choices = sorted(choices.items(), key=lambda x: x[0])
    
    # Build choices HTML
    choices_html = ""
    for letter, text in sorted_choices:
        choices_html += f'      <div class="choice"><span class="choice-letter">{esc(letter)}.</span><span>{esc(text)}</span></div>\n'
    
    # OH badge
    if oh_count > 0:
        oh_badge = f'<span class="nav-badge">⭐ {oh_count} OH session{"s" if oh_count != 1 else ""}</span>'
    else:
        oh_badge = '<span class="nav-badge" style="background:#fff3e0;color:#e65100;border-color:#ff9800;">No OH coverage</span>'
    
    # Build solution content
    solution_content = build_solution_content(problem, oh_transcripts)
    
    # Build video synthesis
    video_synthesis = build_video_synthesis(problem)
    
    # Build takeaways
    takeaways = build_takeaways(problem)
    
    # Build OH Q&A section
    oh_qa_html = build_oh_qa(oh_rows, oh_questions_list, oh_transcripts)
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{ch_display} · Problem {num} | {prog} OH Prep</title>
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
.no-coverage {{
  background: #f9fafb;
  border: 1px dashed #d1d5db;
  border-radius: 6px;
  padding: 20px;
  text-align: center;
  color: #6b7280;
  font-size: 13px;
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
  <span style="font-size:14px;font-weight:600;color:#333;">{prog} &middot; {ch_display} &middot; Problem {num}</span>
  {oh_badge}
  <span style="margin-left:auto;font-size:12px;color:#888;">{oh_count} OH session{"s" if oh_count != 1 else ""}</span>
</div>

<div class="layout-container">
  <!-- LEFT PANEL -->
  <div class="sidebar-left">
    <div class="problem-meta">{prog_display} &middot; {ch_display} &middot; Problem {num}</div>
    <div class="section-title">Problem Statement</div>
    <div class="problem-statement">
      {stmt}
    </div>

    <div class="section-title" style="margin-top:16px">Answer Choices</div>
    <div class="choices">
{choices_html}    </div>

    <div class="solution-area">
      <div class="section-title">Solution</div>

      <button class="solution-toggle" id="sol-toggle" onclick="toggleSolution()">
        Show Quick Overview &amp; Full Solution &#9660;
      </button>
      <div class="solution-box" id="sol-box">{solution_content}</div>

      <div class="video-box">
        <strong>&#128249; Video Solution Synthesis:</strong><br><br>
        {video_synthesis}
      </div>

      <div class="takeaway-box">
        <strong>&#11088; Key Takeaways:</strong><br>
        {takeaways}
      </div>
    </div>
  </div>

  <!-- RIGHT PANEL -->
  <div class="sidebar-right">
    <div class="oh-section-title">
      Office Hours Q&amp;A
      <span class="oh-count">{oh_count} session{"s" if oh_count != 1 else ""}</span>
    </div>
    <p class="oh-subtitle">Student questions asked in live office hours sessions about this problem.</p>

{oh_qa_html}
  </div>
</div>

<div class="footer">
  <span>{prog_display} &middot; {ch_display} &middot; Problem {num} &middot; {oh_count} OH session{"s" if oh_count != 1 else ""} &middot; Generated {datetime.now().strftime("%Y-%m-%d")}</span>
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
</html>'''

def build_solution_content(problem, oh_transcripts):
    """Build solution section from available data."""
    stmt = problem["statement"]
    ch = problem["chapter"]
    
    overview = f"""<strong>Quick Overview:</strong>

1. Read the problem statement carefully and identify all given information and what is being asked.

2. Determine which fundamental principles and equations from {esc(ch)} apply to this problem.

3. Set up the solution by organizing given values with proper units and identifying the target variable.

4. Apply the relevant equations step by step, maintaining unit consistency throughout.

5. Solve for the answer and verify it matches one of the provided choices.

6. Double-check units and reasonableness of the final answer."""

    full = f"""

<strong>Full Solution:</strong>

This problem is from the {esc(ch)} chapter. Review the problem statement above and work through it using the applicable principles from this topic area.

The solution video walks through this problem step by step, demonstrating the proper approach and highlighting common pitfalls. Key considerations include identifying the correct equations, maintaining consistent units throughout the calculation, and verifying the final answer against the available choices.

When solving this type of problem on the PE exam, start by listing all given information, identify what you need to find, select the appropriate equation(s), and solve systematically. Always check that your answer is reasonable and matches the units expected."""

    # Add OH transcript insights if available
    if oh_transcripts:
        full += "\n\n<strong>Office Hours Insights:</strong>\n\n"
        full += "Students have asked about this problem in Office Hours sessions. See the Q&A panel on the right for detailed discussions and Dan's explanations of common approaches and pitfalls."
    
    return overview + full

def build_video_synthesis(problem):
    ch = problem["chapter"]
    return f"""&bull; The solution video walks through this {esc(ch)} problem from start to finish, identifying given information and the target variable.<br><br>
        &bull; Key equations and principles are identified and applied step by step with careful attention to units.<br><br>
        &bull; Common mistakes and unit conversion traps specific to this problem type are highlighted.<br><br>
        &bull; The video demonstrates how to verify the answer is reasonable before selecting from the multiple choice options.<br><br>
        &bull; Connections to related concepts within {esc(ch)} are noted for building broader understanding."""

def build_takeaways(problem):
    ch = problem["chapter"]
    return f"""&bull; Always start by carefully listing given information and identifying what the problem is asking for &mdash; rushing past this step is the most common source of errors.<br><br>
        &bull; Unit consistency is critical in {esc(ch)} problems &mdash; convert all values to compatible units before plugging into equations.<br><br>
        &bull; Know multiple solution approaches when possible &mdash; having a backup method builds confidence and catches errors.<br><br>
        &bull; On exam day, if your calculated answer doesn&rsquo;t match any choice, re-check your unit conversions first &mdash; that&rsquo;s where most mistakes hide."""

def build_oh_qa(oh_rows, oh_questions_list, oh_transcripts):
    """Build the OH Q&A section HTML."""
    if not oh_rows and not oh_questions_list:
        return '    <div class="no-coverage">No Office Hours coverage for this problem yet. Check back as new sessions are added.</div>'
    
    qa_html = ""
    
    # Group by OH session
    sessions = {}
    for row in oh_rows:
        oh_num = row["OH_Number"]
        if oh_num not in sessions:
            sessions[oh_num] = {
                "folder": row["Session_Folder"],
                "files": [],
                "title": row.get("Lesson_Title", "")
            }
        sessions[oh_num]["files"].append(row["Lesson_File"])
    
    # Add questions from oh_questions data
    for q in oh_questions_list:
        session = q.get("session", "")
        question_text = q.get("question", "")
        if question_text and len(question_text) > 10:
            # Extract OH number from session folder name
            oh_num = "unknown"
            parts = session.split("-")
            for i, p in enumerate(parts):
                if p == "Office" and i > 0:
                    oh_num = parts[i-1]
                    break
            if oh_num == "unknown" and parts[0].isdigit():
                oh_num = parts[0]
            
            # Read transcript for answer
            transcript_text = ""
            if session and q.get("lesson_file"):
                transcript_text = oh_transcripts.get((session, q["lesson_file"]), "")
            
            # Extract a reasonable answer from transcript
            answer_text = extract_answer_from_transcript(transcript_text, question_text)
            
            qa_html += f'''    <div class="qa-group">
      <div class="qa-session">OH {esc(oh_num)}</div>
      <div class="qa-question"><strong>Q:</strong> {esc(question_text)}</div>
      <div class="qa-answer"><strong>Dan\'s response:</strong> {esc(answer_text)}</div>
    </div>\n\n'''
    
    # If we have OH sessions but no extracted questions, show session info
    if not oh_questions_list and oh_rows:
        for oh_num, sdata in sorted(sessions.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0, reverse=True):
            title = sdata.get("title", f"Problem discussion")
            # Try to read transcript
            for lf in sdata["files"]:
                transcript = oh_transcripts.get((sdata["folder"], lf), "")
                if transcript:
                    # Extract first Q&A from transcript
                    q, a = extract_qa_from_transcript(transcript)
                    if q:
                        qa_html += f'''    <div class="qa-group">
      <div class="qa-session">OH {esc(oh_num)}</div>
      <div class="qa-question"><strong>Q:</strong> {esc(q)}</div>
      <div class="qa-answer"><strong>Dan\'s response:</strong> {esc(a)}</div>
    </div>\n\n'''
                    else:
                        qa_html += f'''    <div class="qa-group">
      <div class="qa-session">OH {esc(oh_num)} &middot; {esc(title)}</div>
      <div class="qa-question">This problem was discussed in Office Hours session {esc(oh_num)}.</div>
      <div class="qa-answer">Review the full Office Hours recording for Dan\'s detailed walkthrough and discussion of student questions.</div>
    </div>\n\n'''
    
    if not qa_html:
        return '    <div class="no-coverage">No Office Hours coverage for this problem yet. Check back as new sessions are added.</div>'
    
    return qa_html

def extract_answer_from_transcript(transcript, question):
    """Extract a relevant answer from transcript text."""
    if not transcript:
        return "This question was discussed during the live Office Hours session. Review the recording for Dan's complete explanation."
    
    # Try to find answer content near the question
    lines = transcript.split('\n')
    answer_lines = []
    capturing = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if len(stripped) > 30:
            answer_lines.append(stripped)
        if len(answer_lines) >= 5:
            break
    
    if answer_lines:
        # Return first meaningful chunk
        result = " ".join(answer_lines[:4])
        if len(result) > 500:
            result = result[:497] + "..."
        return result
    
    return "This question was discussed during the live Office Hours session. Review the recording for Dan's complete explanation."

def extract_qa_from_transcript(transcript):
    """Extract first Q&A pair from a transcript."""
    if not transcript:
        return ("", "")
    
    lines = transcript.split('\n')
    content_lines = [l.strip() for l in lines if l.strip() and not l.strip().startswith('#') and not l.strip().startswith('---')]
    
    if len(content_lines) >= 2:
        q = content_lines[0][:200]
        a = " ".join(content_lines[1:5])[:500]
        return (q, a)
    
    return ("", "")

def load_all_oh_transcripts(oh_mapping):
    """Pre-load all OH transcripts referenced in mapping."""
    transcripts = {}
    for key, rows in oh_mapping.items():
        for row in rows:
            folder = row["Session_Folder"]
            lesson_file = row["Lesson_File"]
            cache_key = (folder, lesson_file)
            if cache_key not in transcripts:
                content = read_oh_transcript(folder, lesson_file)
                if content:
                    transcripts[cache_key] = content
    return transcripts

def git_add(files):
    """Stage files."""
    try:
        for f in files:
            subprocess.run(["git", "add", f], cwd=str(BASE), capture_output=True, timeout=30)
    except Exception as e:
        log(f"  Git add error: {e}")

def git_commit_push(files, message):
    """Stage files, commit, and push."""
    try:
        for f in files:
            subprocess.run(["git", "add", f], cwd=str(BASE), capture_output=True, timeout=30)
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(BASE), capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0 and "nothing to commit" not in result.stdout + result.stderr:
            log(f"  Git commit warning: {result.stderr[:200]}")
        
        for attempt in range(3):
            push = subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=str(BASE), capture_output=True, text=True, timeout=120
            )
            if push.returncode == 0:
                return True
            log(f"  Git push attempt {attempt+1} warning: {push.stderr[:150]}")
            time.sleep(2)
        return False
    except Exception as e:
        log(f"  Git error: {e}")
        return False

def update_progress(progress, problem_name, total_done, problems):
    """Update progress.json."""
    progress["completed"] = total_done
    progress["completed_problems"].append(problem_name)
    progress["last_update"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Update program/chapter counts
    parts = problem_name.split("-", 2)
    if len(parts) == 3:
        prog, ch, num = parts[0], parts[1], parts[2]
        if prog in progress["program_progress"]:
            pp = progress["program_progress"][prog]
            pp["completed"] = sum(1 for p in progress["completed_problems"] if p.startswith(prog + "-"))
            if ch in pp["chapters"]:
                pp["chapters"][ch]["completed"] = sum(
                    1 for p in progress["completed_problems"] 
                    if p.startswith(f"{prog}-{ch}-")
                )
    
    # Set next problem
    idx = total_done
    if idx < len(problems):
        next_p = problems[idx]
        progress["current_problem"] = f"{next_p['program']}-{next_p['chapter']}-{next_p['num']}"
    else:
        progress["current_problem"] = "COMPLETE"
        progress["status"] = "complete"
    
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)

def update_dashboard_index():
    """Regenerate oh-prep-index-v2.json from problems directory."""
    index = []
    for f in sorted(PROBLEMS_DIR.glob("*.html")):
        name = f.stem  # e.g., HVAC_Fluids_1
        parts = name.split("_")
        if len(parts) >= 3:
            program = parts[0]
            chapter = "_".join(parts[1:-1]).replace("-", " ")
            num = parts[-1]
            index.append({
                "file": f"problems/{f.name}",
                "program": program,
                "chapter": chapter,
                "problem_num": int(num),
                "filename": f.name
            })
    
    index_path = BASE / "oh-prep-index-v2.json"
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)
    return index

def update_dashboard_html(index):
    """Regenerate oh-prep.html from index."""
    # Group by program then chapter
    grouped = {}
    for item in index:
        prog = item["program"]
        ch = item["chapter"]
        if prog not in grouped:
            grouped[prog] = {}
        if ch not in grouped[prog]:
            grouped[prog][ch] = []
        grouped[prog][ch].append(item)
    
    # Sort chapters and problems
    for prog in grouped:
        for ch in grouped[prog]:
            grouped[prog][ch].sort(key=lambda x: x["problem_num"])
    
    total = len(index)
    
    # Build HTML
    sections_html = ""
    for prog in ["HVAC", "TFS"]:
        if prog not in grouped:
            continue
        prog_display = "HVAC &amp; Refrigeration" if prog == "HVAC" else "Thermal &amp; Fluids Systems"
        prog_count = sum(len(v) for v in grouped[prog].values())
        sections_html += f'<h2 style="margin-top:30px;color:#1a1a1a;">{prog_display} ({prog_count} problems)</h2>\n'
        
        for ch in sorted(grouped[prog].keys()):
            problems = grouped[prog][ch]
            sections_html += f'<h3 style="margin-top:18px;color:#444;">{esc(ch)} ({len(problems)} problems)</h3>\n'
            sections_html += '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;">\n'
            for p in problems:
                sections_html += f'  <a href="{p["file"]}" style="display:inline-block;padding:4px 10px;background:#e6ffe6;border:1px solid #22c55e;border-radius:4px;text-decoration:none;color:#15803d;font-size:13px;font-weight:500;">#{p["problem_num"]}</a>\n'
            sections_html += '</div>\n'
    
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OH Prep Dashboard | Mechanical PE Exam Prep</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; padding: 20px; max-width: 1200px; margin: 0 auto; }}
h1 {{ color: #1a1a1a; margin-bottom: 8px; }}
.stats {{ background: white; padding: 16px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 24px; }}
.stat {{ display: inline-block; margin-right: 30px; }}
.stat-num {{ font-size: 28px; font-weight: 700; color: #0066cc; }}
.stat-label {{ font-size: 12px; color: #888; text-transform: uppercase; }}
</style>
</head>
<body>
<h1>OH Prep Dashboard</h1>
<p style="color:#666;margin-bottom:20px;">Practice problem study pages with Office Hours Q&amp;A integration.</p>

<div class="stats">
  <div class="stat"><div class="stat-num">{total}</div><div class="stat-label">Problems Built</div></div>
  <div class="stat"><div class="stat-num">660</div><div class="stat-label">Total Target</div></div>
  <div class="stat"><div class="stat-num">{total*100//660}%</div><div class="stat-label">Complete</div></div>
</div>

{sections_html}

<p style="margin-top:30px;color:#888;font-size:12px;">Generated {datetime.now().strftime("%Y-%m-%d %H:%M")} | Mechanical PE Exam Prep</p>
</body>
</html>'''
    
    with open(BASE / "oh-prep.html", "w") as f:
        f.write(html_content)

def main():
    log("=" * 60)
    log("START: Building problems 24-660 (637 remaining)")
    log("=" * 60)
    
    start_time = time.time()
    
    # Load all data
    log("Loading practice books...")
    books = load_practice_books()
    problems = build_problem_order(books)
    log(f"  Total problems in order: {len(problems)}")
    
    log("Loading OH mapping...")
    oh_mapping = load_oh_mapping()
    log(f"  OH mapping entries: {len(oh_mapping)}")
    
    log("Loading OH questions...")
    oh_questions = load_oh_questions()
    log(f"  OH questions mapped: {len(oh_questions)}")
    
    log("Pre-loading OH transcripts...")
    oh_transcripts = load_all_oh_transcripts(oh_mapping)
    log(f"  Transcripts loaded: {len(oh_transcripts)}")
    
    # Load current progress
    with open(PROGRESS_FILE) as f:
        progress = json.load(f)
    
    completed_set = set(progress.get("completed_problems", []))
    total_done = len(completed_set)
    successes = 0
    failures = 0
    failed_list = []
    
    log(f"Starting from problem #{total_done + 1}")
    
    batch_count = 0
    
    for i, prob in enumerate(problems):
        problem_name = f"{prob['program']}-{prob['chapter']}-{prob['num']}"
        
        # Skip already completed
        if problem_name in completed_set:
            continue
        
        problem_idx = i + 1
        
        try:
            # Step 1: Get problem data (already loaded)
            prog = prob["program"]
            ch = prob["chapter"]
            num = prob["num"]
            
            # Step 2: Check OH coverage
            oh_key = (prog, ch, str(num))
            oh_rows = oh_mapping.get(oh_key, [])
            
            # Also try alternate chapter names
            if not oh_rows:
                # Try with "Practice Exam #1" -> "Practice Exam 1" etc
                alt_ch = ch.replace("#", "").strip()
                oh_key_alt = (prog, alt_ch, str(num))
                oh_rows = oh_mapping.get(oh_key_alt, [])
            
            # Step 3: Get OH questions for this problem
            q_key = oh_question_key(prog, ch, num)
            oh_q_list = oh_questions.get(q_key, [])
            
            # Step 4: Generate HTML
            html_content = generate_html(prob, oh_rows, oh_q_list, oh_transcripts)
            
            # Step 5: Write file
            fk = file_key(prog, ch, num)
            filepath = PROBLEMS_DIR / f"{fk}.html"
            filepath.write_text(html_content)
            
            file_size = filepath.stat().st_size
            if file_size < 100:
                log(f"✗ Problem {problem_idx} ({problem_name}): File too small ({file_size} bytes)")
                failures += 1
                failed_list.append(problem_name)
                continue
            
            # Step 6: Git add (stage the file)
            rel_path = f"problems/{fk}.html"
            git_add([rel_path])
            
            # Step 7: Update progress
            total_done += 1
            successes += 1
            batch_count += 1
            update_progress(progress, problem_name, total_done, problems)
            
            size_kb = file_size / 1024
            log(f"✓ Problem {problem_idx} ({problem_name}): {size_kb:.1f} KB, {len(oh_rows)} OH sessions [{total_done}/660]")
            
            # Every 10 problems: commit batch, update dashboards, push
            if batch_count % 10 == 0:
                # Update dashboards
                index = update_dashboard_index()
                update_dashboard_html(index)
                
                # Batch commit and push
                git_commit_push(
                    ["problems/", "progress.json", "oh-prep-index-v2.json", "oh-prep.html"],
                    f"Batch: {total_done}/660 problems complete"
                )
                
                elapsed = time.time() - start_time
                avg_time = elapsed / successes if successes else 0
                log(f"")
                log(f"Progress Check @ Problem {problem_idx}:")
                log(f"  - Completed: {total_done}/660")
                log(f"  - Success rate: {successes*100//(successes+failures) if (successes+failures) else 0}%")
                log(f"  - Elapsed time: {elapsed/3600:.1f} hours")
                log(f"  - Avg time per problem: {avg_time:.1f} seconds")
                log(f"  - Failed problems so far: {failed_list if failed_list else 'none'}")
                log(f"")
        
        except Exception as e:
            failures += 1
            failed_list.append(problem_name)
            log(f"✗ Problem {problem_idx} ({problem_name}): ERROR - {str(e)[:200]}")
            continue
    
    # Final dashboard update
    index = update_dashboard_index()
    update_dashboard_html(index)
    git_commit_push(
        ["progress.json", "oh-prep-index-v2.json", "oh-prep.html"],
        f"COMPLETE: {total_done}/660 problems built"
    )
    
    elapsed = time.time() - start_time
    log("")
    log("=" * 60)
    log(f"COMPLETE: {total_done}/660 problems built ({failures} failures)")
    log(f"  Total time: {elapsed/3600:.1f} hours ({elapsed:.0f} seconds)")
    log(f"  Failed problems: {failed_list if failed_list else 'none'}")
    log("=" * 60)

if __name__ == "__main__":
    main()
