# HTML Template Placeholder Guide

**Location:** `/home/mpepagent/.openclaw/workspace/projects/mpep-dashboard/HTML_TEMPLATE_SKELETON.html`

This document explains every placeholder in the HTML template and what content should fill it.

---

## Navigation Bar Placeholders

### `{{PROGRAM}}`
- **Value:** E.g., "HVAC & Refrigeration", "Thermal & Fluids Systems"
- **Example:** `HVAC & Refrigeration`
- **Location:** Nav bar + metadata

### `{{CHAPTER}}`
- **Value:** E.g., "Thermodynamics", "Fluids", "Psychrometrics"
- **Example:** `Thermodynamics`
- **Location:** Nav bar + metadata

### `{{PROBLEM_NUM}}`
- **Value:** Integer, e.g., 15, 27, 106
- **Example:** `15`
- **Location:** Nav bar + metadata + title + footer

### `{{OH_SESSIONS_BADGE}}`
- **Format:** Icon + count
- **Example:** `⭐ 3 OH sessions` or `⭐ 0 OH sessions`
- **Location:** Nav bar right side

### `{{OH_SESSIONS_COUNT}}`
- **Format:** Plain number or "no sessions"
- **Example:** `3 sessions` or `0 sessions`
- **Location:** Nav bar right + OH section header count badge

### `{{ANSWER_LETTER}}`
- **Value:** Single letter: A, B, C, or D
- **Example:** `C`
- **Location:** Nav bar right + Answer tag + footer

---

## Problem Section Placeholders

### `{{PROBLEM_STATEMENT}}`
- **Content:** The full problem statement exactly as given in the practice book
- **Format:** Plain text (HTML entities for special characters if needed)
- **Example:** "A 10hp pump with 90% efficiency transports water to an elevation of 200ft above the pump. What volume of water is transported in a 1 hour period?"
- **Location:** Left sidebar, inside `.problem-statement` div (already has background styling)

### `{{ANSWER_CHOICES_HTML}}`
- **Content:** Four answer choice divs (A, B, C, D)
- **Format:** Exact HTML structure:
  ```html
  <div class="choice"><span class="choice-letter">A.</span><span>Choice text here</span></div>
  <div class="choice"><span class="choice-letter">B.</span><span>Choice text here</span></div>
  <div class="choice correct"><span class="choice-letter">C.</span><span>Choice text here ✓</span></div>
  <div class="choice"><span class="choice-letter">D.</span><span>Choice text here</span></div>
  ```
- **Rules:**
  - Must have exactly 4 choices (A, B, C, D)
  - Add `class="correct"` to the correct answer only
  - Add ` ✓` (checkmark) after the correct answer text
  - Keep choice text concise (1-3 lines max)
- **Example:** See above
- **Location:** Left sidebar, after "Answer Choices" section header

---

## Solution Section Placeholders

### `{{QUICK_OVERVIEW}}`
- **Content:** 4-6 numbered solution steps
- **Format:** Plain narrative, no formulas, one step per line
- **Example:**
  ```
  1. Identify given information: 10 hp pump, 90% efficiency, water pumped to 200 ft elevation, find volume in 1 hour.
  2. Account for pump efficiency: Ẇ_water = 10 hp × 0.90 = 9 hp.
  3. Convert power to consistent units: 9 hp × 550 ft·lbf/s per hp = 4,950 ft·lbf/s.
  4. Apply work-energy principle: Power = Work / Time, so Ẇ = ṁ·g·h.
  5. Solve for mass flow rate: ṁ = 4,950 / 200 = 24.75 lbm/s.
  6. Calculate total volume: m = 24.75 × 3,600 = 89,100 lbm → V ≈ 10,700 gallons.
  ```
- **Rules:**
  - Plain text only, no formulas
  - Each step 1-2 sentences max
  - Mirrors the "recipe" of the solution
- **Location:** Top of `.solution-box`, inside `<pre>` tags

### `{{FULL_SOLUTION}}`
- **Content:** Direct copy from the HVAC Practice Book solution
- **Format:** Preserve all formatting from source (paragraphs, line breaks, etc.)
- **Rules:**
  - NO AI rewriting, paraphrasing, or additions
  - Include all formulas, units, and calculations as in the book
  - Do NOT add "why wrong answers are wrong" section
  - Keep to 150-250 words
- **Location:** Below Quick Overview in `.solution-box`

---

## Right Sidebar Placeholders

### `{{VIDEO_SYNTHESIS}}`
- **Content:** 4-6 bullet points from the solution video transcript
- **Format:** HTML with line breaks, bullet points if applicable
- **Example:**
  ```
  • Key insight: Always account for efficiency when calculating useful power output
  • Unit conversion: Imperial units (ft/s, lbf/s) require careful factor handling
  • Common mistake: Using volumetric flow rate without converting to mass flow
  • Takeaway: The energy approach (power = work/time) is universal across pump types
  • Strategy tip: For PE exams, draw a quick energy balance to validate your approach
  ```
- **Rules:**
  - Focus on: common misconceptions, unit traps, textbook shortcuts
  - 1-2 sentences per bullet max
  - Plain language, no jargon
- **Location:** Right sidebar, inside `.video-box`

### `{{KEY_TAKEAWAYS}}`
- **Content:** 3-5 key conceptual points (one sentence each)
- **Format:** Plain bullet list or numbered (your choice, but be consistent)
- **Example:**
  ```
  • Efficiency reduces the actual power delivered to the working fluid
  • Power is energy per unit time — use this to convert between W, Q, and ṁ
  • Mass flow rate (lbm/s) and volumetric flow rate (gal/s) are related by density
  • Always use absolute pressure/temperature in Carnot or thermodynamic relations
  ```
- **Rules:**
  - NO exam strategy tips, NO formulas
  - Just core physics/concept
  - 3-5 points exactly
  - One sentence per point
- **Location:** Right sidebar, inside `.takeaway-box`

### `{{OH_QA_CONTENT}}`
- **Content:** Either Q&A blocks (if coverage exists) OR placeholder message (if none)

#### **If Office Hours Coverage Exists:**
```html
<div class="qa-group">
  <div class="qa-session">OH 115 · March 2, 2026 — Newest</div>
  <div class="qa-question"><strong>Q:</strong> When does it make sense to use hfg from the steam tables vs. using mCpΔT?</div>
  <div class="qa-answer"><strong>A:</strong> Use hfg whenever a phase change is involved. mCpΔT only works within a single phase and completely misses the energy of phase transition.</div>
</div>

<div class="qa-group">
  <div class="qa-session">OH 88 · September 17, 2024</div>
  <div class="qa-question"><strong>Q:</strong> Is it better to memorize one solution method or learn multiple approaches?</div>
  <div class="qa-answer"><strong>A:</strong> Learn multiple solution approaches during study time so you can adapt on exam day. Use the fastest shortcut on the actual exam — but only if you understand why it works.</div>
</div>
```

**Rules for Q&A blocks:**
- One `<div class="qa-group">` per Q&A pair
- Session header: `OH XXX · [Date] — [Recency: "Newest" for most recent, omit for older]`
- Q and A are both 1-2 sentences max
- Wrap Q in `<strong>Q:</strong>` and A in `<strong>A:</strong>`
- Sort by recency (newest OH first, oldest last)

#### **If NO Office Hours Coverage:**
```html
<div class="oh-placeholder">
  <strong style="display:block;margin-bottom:6px;color:#6b7280;">No Office Hours coverage yet</strong>
  Dan plans to cover this in an upcoming session. Check back after the next OH recording is processed.
</div>
```

**Rules for placeholder:**
- Use ONLY if no OH sessions exist in the lookup
- Keep the exact text as shown above
- Do NOT skip this section or leave it empty

---

## Template Validation Checklist

Before returning the HTML, verify:

- [ ] All `{{PLACEHOLDERS}}` are filled with actual content (no curly braces remain)
- [ ] Problem statement is in the `.problem-statement` div
- [ ] Exactly 4 answer choices (A, B, C, D)
- [ ] One choice has `class="correct"` and the ✓ checkmark
- [ ] Quick Overview has 4-6 numbered steps
- [ ] Full Solution is copied directly from the book (no AI additions)
- [ ] Video Synthesis has 4-6 bullet points
- [ ] Key Takeaways has exactly 3-5 points (one sentence each)
- [ ] OH Q&A has either Q&A blocks or the placeholder div (never empty)
- [ ] No CSS or HTML structure has been modified
- [ ] Navigation bar is complete with all metadata
- [ ] Footer has program, chapter, and problem number
- [ ] JavaScript toggle function is present and correct

---

## Common Mistakes to Avoid

❌ **Don't:** Add formulas to Quick Overview
✅ **Do:** Use plain narrative steps only

❌ **Don't:** Rewrite or paraphrase the Full Solution from the practice book
✅ **Do:** Copy it exactly as written

❌ **Don't:** Add exam strategy tips to Key Takeaways
✅ **Do:** Include only core physics concepts

❌ **Don't:** Change the HTML structure or class names
✅ **Do:** Keep the template exactly as provided

❌ **Don't:** Leave `{{PLACEHOLDERS}}` unfilled
✅ **Do:** Replace every placeholder with actual content

❌ **Don't:** Add multiple Q&A sessions without sorting by recency
✅ **Do:** Sort all Q&A groups newest-first

---

## Example: Complete Filled Section

**Input placeholder:**
```html
{{ANSWER_CHOICES_HTML}}
```

**Correct output:**
```html
<div class="choice"><span class="choice-letter">A.</span><span>300 gallons</span></div>
<div class="choice"><span class="choice-letter">B.</span><span>1,400 gallons</span></div>
<div class="choice correct"><span class="choice-letter">C.</span><span>10,700 gallons ✓</span></div>
<div class="choice"><span class="choice-letter">D.</span><span>11,900 gallons</span></div>
```

---

**Questions?** Refer to the benchmark problems (HVAC_Thermodynamics_1 through 5) for examples of properly filled templates.
