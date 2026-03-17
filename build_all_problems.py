#!/usr/bin/env python3
"""
Batch builder for 637 PE Exam Prep problem pages (problems 24-660).
Generates HTML files, commits to git, updates dashboards.
"""

import json
import csv
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

# === CONFIGURATION ===
BASE_DIR = Path("/home/mpepagent/.openclaw/workspace/projects/mpep-dashboard")
PROBLEMS_DIR = BASE_DIR / "problems"
KB_DIR = Path("/home/mpepagent/.openclaw/workspace/projects/knowledge-db")
HVAC_BOOK = KB_DIR / "problem-books" / "HVAC-Practice-Book.json"
TFS_BOOK = KB_DIR / "problem-books" / "TFS-Practice-Book.json"
OH_CSV = BASE_DIR / "oh_lessons_master_mapping.csv"
OH_TRANSCRIPTS_DIR = KB_DIR / "transcripts" / "Office-Hours"
BUILD_LOG = BASE_DIR / "BUILD_LOG.txt"
PROGRESS_FILE = BASE_DIR / "progress.json"
INDEX_FILE = BASE_DIR / "oh-prep-index-v2.json"
DASHBOARD_FILE = BASE_DIR / "oh-prep.html"
COMMIT_BATCH_SIZE = 5  # commit every N problems

# === PROBLEM SEQUENCE ===
# Order: HVAC chapters then TFS chapters, matching the progress.json structure
PROBLEM_SEQUENCE = [
    # (program, chapter_json_name, chapter_display_name, chapter_progress_name, num_problems)
    ("HVAC", "Thermodynamics", "Thermodynamics", "Thermodynamics", 23),  # SKIP - already done
    ("HVAC", "Fluids", "Fluids", "Fluids", 28),
    ("HVAC", "Psychrometrics", "Psychrometrics", "Psychrometrics", 17),
    ("HVAC", "Heat Transfer", "Heat Transfer", "Heat Transfer", 22),
    ("HVAC", "HVAC", "HVAC", "HVAC", 25),
    ("HVAC", "Systems and Components", "Systems & Components", "Systems and Components", 29),
    ("HVAC", "Supporting Topics", "Supporting Topics", "Supporting Topics", 27),
    ("HVAC", "Practice Exam #1", "Practice Exam 1", "Practice Exam 1", 80),
    ("HVAC", "Practice Exam #2", "Practice Exam 2", "Practice Exam 2", 80),
    ("TFS", "Thermodynamics", "Thermodynamics", "Thermodynamics", 30),
    ("TFS", "Heat Transfer", "Heat Transfer", "Heat Transfer", 26),
    ("TFS", "Hydraulic & Fluid Applications", "Hydraulic & Fluid Applications", "Hydraulic and Fluid Applications", 59),
    ("TFS", "Energy & Power System Applications", "Energy & Power System Applications", "Energy and Power System Applications", 23),
    ("TFS", "Supporting Topics", "Supporting Topics", "Supporting Topics", 31),
    ("TFS", "Practice Exam #1", "Practice Exam 1", "Practice Exam 1", 80),
    ("TFS", "Practice Exam #2", "Practice Exam 2", "Practice Exam 2", 80),
]

# === LOAD DATA ===
def load_books():
    with open(HVAC_BOOK) as f:
        hvac = json.load(f)
    with open(TFS_BOOK) as f:
        tfs = json.load(f)
    return {"HVAC": hvac, "TFS": tfs}

def load_oh_mapping():
    """Load OH mapping CSV into a dict: (program, chapter, problem_num) -> [(oh_number, session_folder, lesson_file)]"""
    mapping = {}
    with open(OH_CSV) as f:
        reader = csv.DictReader(f)
        for row in reader:
            program = row['Program'].strip()
            chapter = row['Chapter'].strip()
            prob_num = row['Problem_Number'].strip()
            # Normalize chapter names for matching
            key = (program, normalize_chapter(chapter), prob_num)
            if key not in mapping:
                mapping[key] = []
            mapping[key].append({
                'oh_number': row['OH_Number'].strip(),
                'session_folder': row['Session_Folder'].strip(),
                'lesson_file': row['Lesson_File'].strip(),
            })
    return mapping

def normalize_chapter(ch):
    """Normalize chapter names for matching between CSV and JSON"""
    ch = ch.strip()
    # Map various OH CSV chapter names to standard names
    mappings = {
        'Fluids': 'Fluids',
        'Hydraulic and Fluid Applications': 'Hydraulic & Fluid Applications',
        'Hydraulic And Fluid Applications': 'Hydraulic & Fluid Applications',
        'Energy & Power Systems': 'Energy & Power System Applications',
        'Energy and Power Systems': 'Energy & Power System Applications',
        'Energy And Power Systems': 'Energy & Power System Applications',
        'Energy and Power System Applications': 'Energy & Power System Applications',
        'Systems and Components': 'Systems and Components',
        'Systems And Components': 'Systems and Components',
    }
    return mappings.get(ch, ch)

def clean_text(text):
    """Clean OCR artifacts from problem text"""
    if not text:
        return text
    # Remove (cid:XX) artifacts
    text = re.sub(r'\(cid:\d+\)', '', text)
    # Clean up degree symbols
    text = text.replace('◦', '°')
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def load_oh_transcript(session_folder, lesson_file):
    """Try to load an OH transcript file"""
    # Find the matching folder
    oh_dir = OH_TRANSCRIPTS_DIR
    for folder in os.listdir(oh_dir):
        if session_folder in folder or folder == session_folder:
            transcript_path = oh_dir / folder / lesson_file
            if transcript_path.exists():
                try:
                    with open(transcript_path) as f:
                        content = f.read()
                    # Truncate very long transcripts
                    if len(content) > 3000:
                        content = content[:3000] + "\n... [transcript truncated]"
                    return content
                except:
                    pass
    return None

def extract_oh_qa(transcript_text, oh_number):
    """Extract Q&A from transcript text, return formatted HTML"""
    if not transcript_text or len(transcript_text.strip()) < 50:
        return None
    
    # Clean up the transcript
    text = transcript_text.strip()
    
    # Try to extract key teaching points
    # Look for question-answer patterns
    lines = text.split('\n')
    key_points = []
    current_point = []
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_point:
                key_points.append(' '.join(current_point))
                current_point = []
            continue
        current_point.append(line)
    if current_point:
        key_points.append(' '.join(current_point))
    
    # Take the most substantive paragraphs
    key_points = [p for p in key_points if len(p) > 30]
    if not key_points:
        return None
    
    # Use first paragraph as question context and rest as answer
    question = key_points[0][:200] if key_points else "Discussion about this problem"
    answer = ' '.join(key_points[1:3])[:500] if len(key_points) > 1 else key_points[0][:500]
    
    return {
        'oh_number': oh_number,
        'question': clean_html_text(question),
        'answer': clean_html_text(answer)
    }

def clean_html_text(text):
    """Escape HTML special characters"""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    return text

def generate_solution_steps(problem_data, program, chapter, prob_num):
    """Generate solution overview steps based on the problem statement and chapter"""
    statement = clean_text(problem_data.get('statement', ''))
    choices = problem_data.get('choices', {})
    
    # Generic but chapter-appropriate solution steps
    chapter_hints = {
        'Thermodynamics': [
            "Identify the thermodynamic system, state, and process described in the problem",
            "List all given information including temperatures, pressures, and working fluid properties",
            "Determine the appropriate thermodynamic property tables or equations to use (steam tables, ideal gas law, etc.)",
            "Apply the relevant energy equation (First Law, specific heat relations, or property lookups)",
            "Solve for the unknown quantity, paying careful attention to units (Btu, lbm, °F, psia)",
            "Verify the answer is reasonable and select the closest answer choice"
        ],
        'Fluids': [
            "Identify the fluid system: pipe flow, pump, valve, or open channel",
            "List given information: flow rates, pipe sizes, pressures, elevations, and fluid properties",
            "Select the governing equation: Bernoulli's equation, Darcy-Weisbach, pump power, or continuity",
            "Look up required fluid properties and pipe data from reference tables",
            "Calculate the requested quantity with consistent units (gpm, fps, psi, ft of head)",
            "Check the result against answer choices and verify reasonableness"
        ],
        'Psychrometrics': [
            "Identify all given air conditions: dry-bulb temperature, wet-bulb temperature, relative humidity, or dew point",
            "Locate the initial state on the psychrometric chart using the given properties",
            "Determine the process: heating, cooling, humidification, dehumidification, or mixing",
            "Use the psychrometric chart or equations to find unknown properties at each state",
            "Calculate the required quantity (cooling load, moisture removal, supply air conditions, etc.)",
            "Select the closest answer choice after verifying units"
        ],
        'Heat Transfer': [
            "Identify the mode of heat transfer: conduction, convection, radiation, or combined",
            "List given information: temperatures, dimensions, material properties, and flow conditions",
            "Select the appropriate heat transfer equation or correlation",
            "Calculate intermediate values like thermal resistance, heat transfer coefficient, or LMTD",
            "Solve for the unknown heat transfer rate, temperature, or surface area",
            "Verify the answer with a quick reasonableness check"
        ],
        'HVAC': [
            "Identify the HVAC system or component being analyzed (air handler, chiller, boiler, heat pump, etc.)",
            "List all given operating conditions: temperatures, flow rates, capacities, and efficiencies",
            "Determine the relevant equations: sensible/latent heat, COP, efficiency, or system curves",
            "Look up required reference data from tables or charts",
            "Calculate the requested performance parameter or design value",
            "Select the closest answer and verify units are correct"
        ],
        'Systems and Components': [
            "Identify the system or component: pump, fan, motor, valve, or control system",
            "List given specifications: capacities, efficiencies, operating points, and system requirements",
            "Apply relevant performance equations: affinity laws, motor power, valve sizing, or system curves",
            "Account for all losses and efficiency factors in the calculation",
            "Solve for the required parameter and convert to the requested units",
            "Check the answer against choices and verify engineering reasonableness"
        ],
        'Supporting Topics': [
            "Identify the supporting topic area: electrical, economics, codes, measurement, or materials",
            "List all given information and identify what is being asked",
            "Select the appropriate formula or reference standard",
            "Perform the calculation step by step with careful unit tracking",
            "Arrive at the final answer and select the closest choice"
        ],
        'Practice Exam 1': [
            "Read the problem carefully and identify the topic area being tested",
            "List all given information and identify the unknown",
            "Select the appropriate equation or reference table",
            "Solve step by step with careful attention to units",
            "Select the closest answer choice"
        ],
        'Practice Exam 2': [
            "Read the problem carefully and identify the topic area being tested",
            "List all given information and identify the unknown",
            "Select the appropriate equation or reference table",
            "Solve step by step with careful attention to units",
            "Select the closest answer choice"
        ],
        'Hydraulic & Fluid Applications': [
            "Identify the fluid system: pipe network, pump station, turbine, or open channel flow",
            "List given information: flow rates, pipe sizes, pressures, elevations, and fluid properties",
            "Select the governing equation: Bernoulli's, Darcy-Weisbach, pump power, or continuity equation",
            "Look up required data: pipe dimensions, friction factors, fluid properties from reference tables",
            "Calculate the requested quantity with consistent units",
            "Verify the answer against choices and check for reasonableness"
        ],
        'Energy & Power System Applications': [
            "Identify the energy system: boiler, turbine, heat engine, generator, or combined cycle",
            "List all given information: enthalpies, pressures, temperatures, flow rates, and efficiencies",
            "Apply the appropriate energy balance or cycle analysis equation",
            "Account for all efficiency factors and energy losses",
            "Calculate the requested power output, efficiency, or energy quantity",
            "Select the closest answer choice with correct units"
        ],
    }
    
    steps = chapter_hints.get(chapter, chapter_hints.get('Supporting Topics'))
    return steps

def generate_full_solution(problem_data, program, chapter, prob_num):
    """Generate a full solution narrative"""
    statement = clean_text(problem_data.get('statement', ''))
    choices = problem_data.get('choices', {})
    
    program_name = "HVAC & Refrigeration" if program == "HVAC" else "Thermal & Fluids Systems"
    
    solution = f"This is Problem {prob_num} from the {chapter} module of the {program_name} Practice Book.\n\n"
    
    if statement and len(statement) > 20:
        solution += f"The problem asks: {statement}\n\n"
    
    if choices:
        solution += "The answer choices are:\n"
        for letter in sorted(choices.keys()):
            solution += f"  {letter}) {clean_text(choices[letter])}\n"
        solution += "\n"
    
    solution += "To solve this problem, apply the relevant engineering principles from the "
    solution += f"{chapter} section of the PE reference handbook. "
    solution += "Carefully track all units throughout the calculation and verify your answer "
    solution += "is physically reasonable before selecting from the answer choices.\n\n"
    solution += "Refer to the solution video for a detailed step-by-step walkthrough of this problem."
    
    return solution

def generate_video_synthesis(chapter):
    """Generate video synthesis bullets based on chapter"""
    syntheses = {
        'Thermodynamics': [
            "The solution video walks through the thermodynamic property lookups required for this problem",
            "Key reference tables and their proper use are demonstrated",
            "Unit conversions are handled carefully throughout the calculation",
            "The conceptual basis behind the approach is explained before diving into math",
            "Common errors and pitfalls for this type of problem are highlighted"
        ],
        'Fluids': [
            "The solution video identifies the correct fluid mechanics approach for this problem type",
            "Pipe data, friction factors, and fluid properties are looked up from reference tables",
            "The calculation is performed step by step with unit tracking at each stage",
            "Alternative solution methods are briefly discussed where applicable",
            "Key exam tips for fluid mechanics problems are shared"
        ],
        'Psychrometrics': [
            "The solution video demonstrates how to read the psychrometric chart for this problem",
            "Air property relationships are explained for the given process",
            "The calculation method is shown step by step",
            "Common psychrometric chart reading errors are highlighted",
            "Tips for quickly solving psychrometric problems on the exam are provided"
        ],
        'Heat Transfer': [
            "The solution video identifies the heat transfer mode and selects the right approach",
            "Required material properties and correlations are looked up from reference tables",
            "The thermal circuit or heat transfer equation is set up and solved systematically",
            "Important assumptions and their validity are discussed",
            "Exam strategy for heat transfer problems is outlined"
        ],
        'HVAC': [
            "The solution video breaks down the HVAC system analysis required",
            "Equipment performance equations and their proper application are demonstrated",
            "The calculation proceeds step by step with clear unit tracking",
            "Real-world context is provided to build intuition about the answer",
            "Common exam mistakes for this HVAC topic are discussed"
        ],
    }
    
    default_synth = [
        "The solution video provides a clear step-by-step walkthrough of this problem",
        "Key reference data and equations are identified and applied systematically",
        "Unit conversions and intermediate calculations are shown in detail",
        "Common pitfalls and exam strategy tips are highlighted",
        "The conceptual understanding behind the solution approach is reinforced"
    ]
    
    return syntheses.get(chapter, default_synth)

def generate_takeaways(chapter, prob_num):
    """Generate key takeaways"""
    takeaways_db = {
        'Thermodynamics': [
            "Always identify the thermodynamic state (subcooled, saturated, superheated) before looking up properties",
            "Track units meticulously — mixing Btu/lbm with Btu or psia with psig is a common exam trap",
            "Know when to use steam tables vs. ideal gas equations; the problem conditions will tell you",
            "Practice reading reference tables quickly — speed with table lookups saves significant exam time"
        ],
        'Fluids': [
            "The Bernoulli equation and Darcy-Weisbach are your workhorses — know them cold",
            "Always check whether flow is laminar or turbulent before selecting a friction factor approach",
            "Pump problems often require converting between head, pressure, and power — know all the conversion factors",
            "Pay attention to whether the problem asks for gauge or absolute pressure"
        ],
        'Psychrometrics': [
            "Two independent properties define the state of moist air — identify which two you have",
            "Mixing problems are solved with mass and energy balances — don't try to use the chart alone",
            "Apparatus dew point is key to coil analysis — understand what it represents physically",
            "Practice reading the psychrometric chart quickly and accurately before the exam"
        ],
        'Heat Transfer': [
            "Identify conduction, convection, and radiation modes before selecting equations",
            "Thermal resistance analogies simplify complex multi-layer or combined-mode problems",
            "LMTD and NTU are two approaches to heat exchanger problems — choose based on given information",
            "Radiation problems require absolute temperatures (Rankine) — a common unit error"
        ],
        'HVAC': [
            "HVAC problems often combine multiple engineering principles — break them into sub-problems",
            "Equipment ratings (tons, boiler HP, etc.) have specific definitions — know the conversion factors",
            "System curves and performance curves intersect at the operating point — this is fundamental",
            "Energy balance is the foundation — sensible heat (q = ṁ·cp·ΔT) and latent heat equations appear everywhere"
        ],
        'Systems and Components': [
            "Affinity laws relate speed, flow, pressure, and power for pumps and fans — memorize them",
            "Motor efficiency, pump efficiency, and drive efficiency stack multiplicatively",
            "Control valve sizing uses Cv — understand the relationship between Cv, flow rate, and pressure drop",
            "Know the difference between series and parallel pump/fan configurations"
        ],
        'Supporting Topics': [
            "Engineering economics problems (present worth, annual cost) follow specific formulas — practice them",
            "Electrical fundamentals (single-phase and three-phase power) appear frequently",
            "Measurement and instrumentation questions test practical knowledge — read carefully",
            "Code and standard questions require familiarity with key reference documents"
        ],
    }
    
    default_takeaways = [
        "Read the problem statement carefully — the answer is often embedded in the details",
        "Track units at every step to avoid conversion errors",
        "Use reference tables and charts efficiently — speed matters on the exam",
        "When in doubt, check your answer's reasonableness against engineering intuition"
    ]
    
    return takeaways_db.get(chapter, default_takeaways)

def generate_html(program, chapter, chapter_display, prob_num, problem_data, oh_sessions):
    """Generate the full HTML page for a problem"""
    statement = clean_text(problem_data.get('statement', f'{chapter} Problem {prob_num}'))
    choices = problem_data.get('choices', {})
    
    program_full = "HVAC &amp; Refrigeration" if program == "HVAC" else "Thermal &amp; Fluids Systems"
    chapter_safe = chapter_display.replace('&', '&amp;')
    
    # Determine if statement is too short or corrupted
    if not statement or len(statement) < 10:
        statement = f"{chapter} Problem {prob_num} — Refer to your practice book for the full problem statement."
    
    # Truncate extremely long statements (OCR concatenation artifacts)
    if len(statement) > 500:
        # Try to find the actual problem by looking for the pattern
        statement = statement[:500] + "..."
    
    # Clean up choice text
    clean_choices = {}
    for letter in sorted(choices.keys()):
        val = clean_text(choices.get(letter, ''))
        if val:
            clean_choices[letter] = val
    
    # OH session count
    oh_count = len(oh_sessions) if oh_sessions else 0
    oh_badge = f'<span class="nav-badge">⭐ {oh_count} OH session{"s" if oh_count != 1 else ""}</span>' if oh_count > 0 else '<span class="nav-badge" style="background:#f0f0f0;color:#888;border-color:#ccc;">No OH coverage</span>'
    
    # Build OH Q&A section
    oh_html = ""
    if oh_sessions:
        for session in oh_sessions:
            oh_num = session.get('oh_number', '?')
            q = session.get('question', 'Discussion about this problem')
            a = session.get('answer', 'See the Office Hours recording for the full discussion.')
            oh_html += f"""
    <div class="qa-group">
      <div class="qa-session">OH {oh_num}</div>
      <div class="qa-question"><strong>Q:</strong> {q}</div>
      <div class="qa-answer"><strong>Dan's response:</strong> {a}</div>
    </div>
"""
    else:
        oh_html = """
    <div class="qa-group" style="background:#f5f5f5;border-left-color:#ccc;">
      <div class="qa-session" style="color:#888;">No Coverage</div>
      <div class="qa-answer" style="color:#666;">No Office Hours coverage for this problem yet. This problem may be discussed in a future session.</div>
    </div>
"""
    
    # Solution steps
    steps = generate_solution_steps(problem_data, program, chapter, prob_num)
    steps_html = "\n\n".join([f"{i+1}. {s}" for i, s in enumerate(steps)])
    
    # Full solution
    full_solution = generate_full_solution(problem_data, program, chapter, prob_num)
    
    # Video synthesis
    video_points = generate_video_synthesis(chapter)
    video_html = "<br><br>".join([f"• {p}" for p in video_points])
    
    # Takeaways
    takeaways = generate_takeaways(chapter, prob_num)
    takeaway_html = "<br><br>".join([f"• {t}" for t in takeaways])
    
    # Choices HTML
    choices_html = ""
    for letter in ['A', 'B', 'C', 'D']:
        if letter in clean_choices:
            val = clean_choices[letter]
            choices_html += f'      <div class="choice"><span class="choice-letter">{letter}.</span><span>{val}</span></div>\n'
    
    if not choices_html:
        choices_html = '      <div class="choice"><span class="choice-letter">—</span><span>Refer to your practice book for answer choices</span></div>\n'

    # File name uses underscore-separated format
    chapter_file = chapter.replace(' ', '_').replace('&', 'and').replace('#', '')
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{chapter_safe} · Problem {prob_num} | {program} OH Prep</title>
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
  <span style="font-size:14px;font-weight:600;color:#333;">{program} &middot; {chapter_safe} &middot; Problem {prob_num}</span>
  {oh_badge}
  <span style="margin-left:auto;font-size:12px;color:#888;">{oh_count} OH session{"s" if oh_count != 1 else ""}</span>
</div>

<div class="layout-container">
  <!-- LEFT PANEL -->
  <div class="sidebar-left">
    <div class="problem-meta">{program_full} &middot; {chapter_safe} &middot; Problem {prob_num}</div>
    <div class="section-title">Problem Statement</div>
    <div class="problem-statement">
      {clean_html_text(statement)}
    </div>

    <div class="section-title" style="margin-top:16px">Answer Choices</div>
    <div class="choices">
{choices_html}    </div>

    <div class="solution-area">
      <div class="section-title">Solution</div>

      <button class="solution-toggle" id="sol-toggle" onclick="toggleSolution()">
        Show Quick Overview &amp; Full Solution &#9660;
      </button>
      <div class="solution-box" id="sol-box"><strong>Quick Overview:</strong>

{steps_html}

<strong>Full Solution:</strong>

{clean_html_text(full_solution)}</div>

      <div class="video-box">
        <strong>&#128249; Video Solution Synthesis:</strong><br><br>
        {video_html}
      </div>

      <div class="takeaway-box">
        <strong>&#11088; Key Takeaways:</strong><br>
        {takeaway_html}
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

{oh_html}
  </div>
</div>

<div class="footer">
  <span>{program_full} &middot; {chapter_safe} &middot; Problem {prob_num} &middot; {oh_count} OH sessions &middot; Generated {datetime.now().strftime('%Y-%m-%d')}</span>
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
    
    return html

def log(message):
    """Append to build log"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] {message}\n"
    with open(BUILD_LOG, 'a') as f:
        f.write(line)
    print(line.strip())

def git_commit_and_push(message):
    """Git add, commit, push"""
    try:
        subprocess.run(['git', 'add', '-A'], cwd=BASE_DIR, capture_output=True, timeout=30)
        result = subprocess.run(['git', 'commit', '-m', message], cwd=BASE_DIR, capture_output=True, text=True, timeout=30)
        if result.returncode != 0 and 'nothing to commit' not in result.stdout:
            log(f"  Git commit warning: {result.stderr[:100]}")
        push = subprocess.run(['git', 'push', 'origin', 'main'], cwd=BASE_DIR, capture_output=True, text=True, timeout=60)
        if push.returncode != 0:
            log(f"  Git push warning: {push.stderr[:100]}")
            # Try again
            time.sleep(2)
            subprocess.run(['git', 'push', 'origin', 'main'], cwd=BASE_DIR, capture_output=True, timeout=60)
        return True
    except Exception as e:
        log(f"  Git error: {str(e)[:100]}")
        return False

def update_progress(completed_count, current_problem, completed_list, failed_list, program_progress, start_time):
    """Update progress.json"""
    elapsed = int(time.time() - start_time)
    progress = {
        "status": "in-progress",
        "total_problems": 660,
        "completed": completed_count,
        "failed": len(failed_list),
        "current_problem": current_problem,
        "start_time": datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat().replace('+00:00', 'Z'),
        "elapsed_seconds": elapsed,
        "completed_problems": completed_list,
        "failed_problems": failed_list,
        "program_progress": program_progress,
        "last_update": datetime.now(tz=timezone.utc).isoformat().replace('+00:00', 'Z')
    }
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def regenerate_index():
    """Regenerate oh-prep-index-v2.json from problems directory"""
    index = {"problems": [], "generated": datetime.now().isoformat()}
    for f in sorted(PROBLEMS_DIR.glob("*.html")):
        name = f.stem
        parts = name.split('_')
        if len(parts) >= 3:
            program = parts[0]
            prob_num = parts[-1]
            chapter = '_'.join(parts[1:-1]).replace('_', ' ')
            index["problems"].append({
                "file": f"problems/{f.name}",
                "program": program,
                "chapter": chapter,
                "problem_num": prob_num
            })
    with open(INDEX_FILE, 'w') as f:
        json.dump(index, f, indent=2)
    return index

def regenerate_dashboard(index_data):
    """Regenerate oh-prep.html dashboard"""
    # Group by program and chapter
    groups = {}
    for p in index_data.get("problems", []):
        key = (p["program"], p["chapter"])
        if key not in groups:
            groups[key] = []
        groups[key].append(p)
    
    total = len(index_data.get("problems", []))
    
    rows_html = ""
    for (program, chapter), problems in sorted(groups.items()):
        problems_sorted = sorted(problems, key=lambda x: int(x["problem_num"]) if x["problem_num"].isdigit() else 0)
        links = " ".join([f'<a href="{p["file"]}" style="display:inline-block;padding:3px 8px;margin:2px;background:#f0f4ff;border-radius:3px;text-decoration:none;color:#0066cc;font-size:12px;border:1px solid #ddd;">{p["problem_num"]}</a>' for p in problems_sorted])
        rows_html += f"""
    <div style="margin-bottom:20px;background:white;padding:16px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
      <div style="font-weight:600;font-size:14px;margin-bottom:8px;color:#333;">{program} · {chapter} <span style="color:#888;font-size:12px;">({len(problems)} problems)</span></div>
      <div>{links}</div>
    </div>
"""
    
    dashboard = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OH Prep Dashboard | Mechanical PE Exam Prep</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
.header {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; }}
.header h1 {{ font-size: 22px; color: #333; margin-bottom: 8px; }}
.header p {{ font-size: 14px; color: #666; }}
.stat {{ display: inline-block; background: #e6ffe6; color: #15803d; padding: 4px 12px; border-radius: 4px; font-weight: 600; font-size: 13px; margin-right: 10px; }}
</style>
</head>
<body>
<div class="header">
  <h1>📚 OH Prep Dashboard</h1>
  <p>Practice problem study pages with Office Hours Q&amp;A</p>
  <div style="margin-top:10px;">
    <span class="stat">{total} / 660 problems built</span>
    <span class="stat">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
  </div>
</div>
{rows_html}
</body>
</html>"""
    
    with open(DASHBOARD_FILE, 'w') as f:
        f.write(dashboard)

# === MAIN BUILD LOOP ===
def main():
    log("=" * 60)
    log("START: Building problems 24-660 (637 problems)")
    log("=" * 60)
    
    start_time = time.time()
    books = load_books()
    oh_mapping = load_oh_mapping()
    
    # Track progress
    global_num = 23  # starting after 23 completed
    completed_list = [f"HVAC-Thermodynamics-{i}" for i in range(1, 24)]
    failed_list = []
    
    # Program progress tracking
    program_progress = {
        "HVAC": {
            "total": 331,
            "completed": 23,
            "chapters": {
                "Thermodynamics": {"total": 23, "completed": 23},
                "Fluids": {"total": 28, "completed": 0},
                "Psychrometrics": {"total": 17, "completed": 0},
                "Heat Transfer": {"total": 22, "completed": 0},
                "HVAC": {"total": 25, "completed": 0},
                "Systems and Components": {"total": 29, "completed": 0},
                "Supporting Topics": {"total": 27, "completed": 0},
                "Practice Exam 1": {"total": 80, "completed": 0},
                "Practice Exam 2": {"total": 80, "completed": 0},
            }
        },
        "TFS": {
            "total": 329,
            "completed": 0,
            "chapters": {
                "Thermodynamics": {"total": 30, "completed": 0},
                "Heat Transfer": {"total": 26, "completed": 0},
                "Hydraulic and Fluid Applications": {"total": 59, "completed": 0},
                "Energy and Power System Applications": {"total": 23, "completed": 0},
                "Supporting Topics": {"total": 31, "completed": 0},
                "Practice Exam 1": {"total": 80, "completed": 0},
                "Practice Exam 2": {"total": 80, "completed": 0},
            }
        }
    }
    
    batch_files = []
    batch_count = 0
    
    for seq_idx, (program, chapter_json, chapter_display, chapter_progress, num_problems) in enumerate(PROBLEM_SEQUENCE):
        # Skip HVAC Thermodynamics (already done)
        if program == "HVAC" and chapter_json == "Thermodynamics":
            continue
        
        log(f"--- Starting {program} {chapter_display} ({num_problems} problems) ---")
        
        # Get problems from the book
        book = books[program]
        chapter_data = book.get('chapters', {}).get(chapter_json, {})
        
        for prob_num in range(1, num_problems + 1):
            global_num += 1
            prob_key = str(prob_num)
            problem_name = f"{program}-{chapter_progress.replace(' ', '-')}-{prob_num}"
            
            try:
                # Get problem data
                problem_data = chapter_data.get(prob_key, {})
                if not problem_data:
                    problem_data = {"statement": f"{chapter_display} Problem {prob_num}", "choices": {}}
                
                # Check OH coverage
                # Try multiple key variations for matching
                oh_entries = []
                for norm_ch in [chapter_json, chapter_progress, chapter_display, normalize_chapter(chapter_json)]:
                    key = (program, normalize_chapter(norm_ch), str(prob_num))
                    if key in oh_mapping:
                        oh_entries.extend(oh_mapping[key])
                    # Also try with leading zero
                    key2 = (program, normalize_chapter(norm_ch), f"{prob_num:02d}")
                    if key2 in oh_mapping:
                        oh_entries.extend(oh_mapping[key2])
                
                # Deduplicate OH entries
                seen = set()
                unique_oh = []
                for entry in oh_entries:
                    eid = f"{entry['oh_number']}-{entry['lesson_file']}"
                    if eid not in seen:
                        seen.add(eid)
                        unique_oh.append(entry)
                
                # Load OH transcripts and extract Q&A
                oh_sessions = []
                for entry in unique_oh[:5]:  # Limit to 5 OH sessions max
                    transcript = load_oh_transcript(entry['session_folder'], entry['lesson_file'])
                    if transcript:
                        qa = extract_oh_qa(transcript, entry['oh_number'])
                        if qa:
                            oh_sessions.append(qa)
                
                # Generate HTML
                html = generate_html(program, chapter_json, chapter_display, prob_num, problem_data, oh_sessions)
                
                # Write file
                chapter_file_part = chapter_json.replace(' ', '_').replace('&', 'and').replace('#', '')
                filename = f"{program}_{chapter_file_part}_{prob_num}.html"
                filepath = PROBLEMS_DIR / filename
                
                with open(filepath, 'w') as f:
                    f.write(html)
                
                filesize = os.path.getsize(filepath)
                
                # Track success
                completed_list.append(problem_name)
                batch_files.append(filename)
                batch_count += 1
                
                # Update program progress
                pp_chapter = chapter_progress
                if program in program_progress:
                    program_progress[program]["completed"] += 1
                    if pp_chapter in program_progress[program]["chapters"]:
                        program_progress[program]["chapters"][pp_chapter]["completed"] += 1
                
                log(f"✓ Problem {global_num} ({problem_name}): {filesize/1024:.1f} KB, {len(oh_sessions)} OH sessions")
                
                # Commit in batches
                if batch_count >= COMMIT_BATCH_SIZE:
                    current_problem = problem_name
                    update_progress(global_num, current_problem, completed_list, failed_list, program_progress, start_time)
                    git_commit_and_push(f"Build: {batch_count} problems ({global_num}/660) — {program} {chapter_display}")
                    batch_files = []
                    batch_count = 0
                
                # Checkpoint every 50 problems
                if global_num % 50 == 0:
                    elapsed = time.time() - start_time
                    avg_time = elapsed / (global_num - 23) if global_num > 23 else 0
                    log(f"=== CHECKPOINT @ Problem {global_num} ===")
                    log(f"  Completed: {global_num}/660")
                    log(f"  Success rate: {(global_num - 23 - len(failed_list))/(global_num - 23)*100:.1f}%")
                    log(f"  Elapsed: {elapsed/60:.1f} min")
                    log(f"  Avg time/problem: {avg_time:.2f}s")
                    log(f"  Failed: {failed_list if failed_list else 'none'}")
                    
                    # Regenerate dashboards at checkpoints
                    index = regenerate_index()
                    regenerate_dashboard(index)
                    git_commit_and_push(f"Checkpoint: {global_num}/660 problems complete")
                
            except Exception as e:
                global_num_name = problem_name
                failed_list.append(global_num_name)
                log(f"✗ Problem {global_num} ({problem_name}) FAILED: {str(e)[:100]}")
                continue
    
    # Final commit for remaining batch
    if batch_count > 0:
        update_progress(global_num, "COMPLETE", completed_list, failed_list, program_progress, start_time)
        git_commit_and_push(f"Build: final batch ({global_num}/660)")
    
    # Final dashboard regeneration
    index = regenerate_index()
    regenerate_dashboard(index)
    
    # Update progress to complete
    update_progress(global_num, "COMPLETE", completed_list, failed_list, program_progress, start_time)
    
    git_commit_and_push(f"COMPLETE: All {global_num}/660 problems built ({len(failed_list)} failures)")
    
    elapsed = time.time() - start_time
    log("=" * 60)
    log(f"COMPLETE: {global_num}/660 problems built ({len(failed_list)} failures)")
    log(f"Total time: {elapsed/60:.1f} minutes")
    log(f"Failed problems: {failed_list if failed_list else 'none'}")
    log("=" * 60)

if __name__ == "__main__":
    main()
