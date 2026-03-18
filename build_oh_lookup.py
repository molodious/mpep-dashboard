#!/usr/bin/env python3
"""
Build OH Lookup File — One-Time Preprocessing

Reads:
  - oh_lessons_master_mapping.csv (problem -> OH sessions mapping)
  - Transcripts from knowledge-db/transcripts/Office-Hours/

Outputs:
  - oh_lookup_v2.json (problem_id -> {"oh_sessions": [115, 88, ...], "transcripts": {oh_num: transcript_text}})

Usage:
  python3 build_oh_lookup.py
"""

import json
import csv
import os
from pathlib import Path
from collections import defaultdict

# Paths
WORKSPACE = Path("/home/mpepagent/.openclaw/workspace")
CSV_PATH = WORKSPACE / "projects/mpep-dashboard/oh_lessons_master_mapping.csv"
TRANSCRIPTS_DIR = WORKSPACE / "projects/knowledge-db/transcripts/Office-Hours"
OUTPUT_PATH = WORKSPACE / "projects/mpep-dashboard/oh_lookup_v2.json"

# Result structure: problem_id -> {"oh_sessions": [115, 88], "transcripts": {115: "...", 88: "..."}}
lookup = defaultdict(lambda: {"oh_sessions": [], "transcripts": {}})

# Step 1: Read CSV and build problem -> OH mapping
print("[*] Reading OH mapping CSV...")
problem_to_oh = defaultdict(set)

try:
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                oh_num = int(row["OH_Number"])
                program = row["Program"].strip()
                chapter = row["Chapter"].strip()
                problem_num = int(row["Problem_Number"])
                
                problem_id = f"{program}_{chapter}_{problem_num}"
                problem_to_oh[problem_id].add(oh_num)
            except (ValueError, KeyError):
                continue

    print(f"[+] Found {len(problem_to_oh)} unique problems with OH coverage")
    
    # Show example
    example = "HVAC_Thermodynamics_13"
    if example in problem_to_oh:
        print(f"[+] Example: {example} -> OH sessions: {sorted(problem_to_oh[example], reverse=True)}")
except Exception as e:
    print(f"[-] Error reading CSV: {e}")
    exit(1)

# Step 2: Load transcripts for each OH session
print("[*] Loading OH transcripts...")
oh_transcripts = {}
oh_files_loaded = 0

for oh_num in sorted(set(oh for sessions in problem_to_oh.values() for oh in sessions)):
    # Find OH folder matching pattern: *-Office-Hours-{oh_num}-*
    oh_pattern = f"*-Office-Hours-{oh_num}-*"
    matching_folders = list(TRANSCRIPTS_DIR.glob(oh_pattern))
    
    if not matching_folders:
        print(f"  [-] OH {oh_num} folder not found")
        continue
    
    oh_folder = matching_folders[0]
    lesson_files = sorted(list(oh_folder.glob("*.md")))
    
    if not lesson_files:
        print(f"  [-] No lesson files in {oh_folder.name}")
        continue
    
    # Read first lesson file (00-Lesson-*.md if it exists, else first .md)
    primary_file = None
    for lf in lesson_files:
        if "00-Lesson" in lf.name:
            primary_file = lf
            break
    if not primary_file:
        primary_file = lesson_files[0]
    
    try:
        with open(primary_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        oh_transcripts[oh_num] = content
        oh_files_loaded += 1
        print(f"  [+] OH {oh_num}: loaded {len(content)} chars from {primary_file.name}")
    except Exception as e:
        print(f"  [-] Error reading {primary_file}: {e}")
        continue

print(f"[+] Loaded {oh_files_loaded} OH transcripts")

# Step 3: Build final lookup
print("[*] Building lookup structure...")
for problem_id, oh_numbers in problem_to_oh.items():
    # Sort OH numbers descending (newest first)
    sorted_oh = sorted(list(oh_numbers), reverse=True)
    lookup[problem_id]["oh_sessions"] = sorted_oh
    
    # Add transcripts for each OH session
    for oh_num in sorted_oh:
        if oh_num in oh_transcripts:
            lookup[problem_id]["transcripts"][oh_num] = oh_transcripts[oh_num]

# Step 4: Write output JSON
print(f"[*] Writing lookup file to {OUTPUT_PATH}...")
try:
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(dict(lookup), f, indent=2)
    print(f"[+] Lookup file created: {OUTPUT_PATH}")
    print(f"[+] Total problems with OH coverage: {len(lookup)}")
    print(f"[+] Total OH sessions: {len(oh_transcripts)}")
    
    # Show example
    if "HVAC_Thermodynamics_13" in lookup:
        print(f"[+] Example: HVAC_Thermodynamics_13")
        print(f"    OH sessions: {lookup['HVAC_Thermodynamics_13']['oh_sessions']}")
        print(f"    Transcripts loaded: {list(lookup['HVAC_Thermodynamics_13']['transcripts'].keys())}")
except Exception as e:
    print(f"[-] Error writing output: {e}")
    exit(1)

print("[+] Build complete!")
