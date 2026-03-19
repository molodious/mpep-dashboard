# TFS Batch Generation Guide

## Overview

Script: `generate_all_tfs_pdfs_v2.py`  
Purpose: Convert all 329 TFS problems from HTML text to PDF-embedded format  
Status: Ready to run (awaiting approval)

## What It Does

✅ Scans all 7 TFS solution directories  
✅ Matches each problem number to its PDF file  
✅ Generates clean HTML with embedded PDF viewer  
✅ Preserves video synthesis + office hours sections from existing files  
✅ Writes all files to `problems/TFS-*.html`  
✅ Reports progress + any missing PDFs  

## Before Running

### Step 1: Preview (Dry Run)
```bash
cd /home/mpepagent/.openclaw/workspace/projects/mpep-dashboard
python3 generate_all_tfs_pdfs_v2.py --dry-run
```

This will:
- Scan all TFS directories
- List all problems that will be generated
- Show any missing PDFs
- **Does NOT modify any files**

### Step 2: Run (Generate)
```bash
python3 generate_all_tfs_pdfs_v2.py --confirm
```

This will:
- Generate all 329 HTML files
- Replace existing TFS-*.html files
- Show progress bar by chapter
- Report final count + success

### Step 3: Deploy
```bash
git add -A
git commit -m "Convert all 329 TFS problems to PDF-embedded format"
git push origin main
```

Live on GitHub Pages within 30-60 seconds.

---

## Scope: 329 Problems

| Chapter | Count | Files | Example |
|---------|-------|-------|---------|
| Thermodynamics | 30 | `tfs_solutions/Thermodynamics/*.pdf` | `TFS-Thermodynamics-1.html` |
| Heat Transfer | 26 | `tfs_solutions/Heat Transfer/*.pdf` | `TFS-Heat-Transfer-1.html` |
| Hydraulic & Fluid | 59 | `tfs_solutions/Hydraulic & Fluid Applications/*.pdf` | `TFS-Hydraulic-Fluid-1.html` |
| Energy & Power | 23 | `tfs_solutions/Energy & Power System Applications/*.pdf` | `TFS-Energy-Power-1.html` |
| Supporting Topics | 31 | `tfs_solutions/Supporting topics/*.pdf` | `TFS-Supporting-Topics-1.html` |
| Practice Exam #1 | 80 | `tfs_solutions/Practice Exam #1/*.pdf` | `TFS-Practice-Exam-1-1.html` |
| Practice Exam #2 | 80 | `tfs_solutions/Practice Exam #2/*.pdf` | `TFS-Practice-Exam-2-1.html` |
| **TOTAL** | **329** | — | — |

---

## Output Format

Each generated file will have:

```html
<div class="layout-container">
  <div class="sidebar-left">
    <!-- PDF viewer: 50% width, 1000px height -->
    <iframe src="../tfs_solutions/Thermodynamics/Thermodynamics-01.pdf"></iframe>
    <!-- Video Synthesis section (scrollable) -->
  </div>
  
  <div class="sidebar-right">
    <!-- Office Hours section (preserved from existing file) -->
  </div>
</div>
```

**Left side (50%):**
- PDF viewer (embedded)
- Video synthesis (below, scrollable)

**Right side (50%):**
- Office hours Q&A

---

## Preservation Logic

The script extracts these sections from existing files:
- `<div class="section-title">Video Synthesis</div>` → Injected into new HTML
- `<div class="sidebar-right">...</div>` → Injected into new HTML

If a file doesn't exist yet, these are left as placeholders.

---

## Timeline

- **Dry Run:** <10 seconds
- **Full Generation:** ~30-60 seconds (329 files)
- **Deployment:** <30 seconds (git push to GitHub Pages)
- **Live:** 30-60 seconds after push

**Total time from run to live: ~3-4 minutes**

---

## Rollback

If anything goes wrong:
```bash
git reset --hard HEAD~1
git push origin main --force
```

This reverts to the benchmark commit.

---

## Success Criteria

✅ All 329 TFS-*.html files created  
✅ Each file has embedded PDF viewer  
✅ Video synthesis sections preserved  
✅ Office hours sections preserved  
✅ Files deployed to GitHub Pages  
✅ Dashboard URLs work (e.g., `/problems/TFS-Thermodynamics-1.html`)  

---

## Next Steps (Once Approved)

1. Run dry-run to verify
2. Run confirmation to generate
3. Commit and push
4. Test a few problems on live site
5. Update OH Prep dashboard main page with TFS problems visible

---

**Status:** Script is ready. Awaiting your approval to proceed.
