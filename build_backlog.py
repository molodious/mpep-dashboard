#!/usr/bin/env python3
"""Build backlog.html — deferred work log dashboard."""

import json
import os
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, "data", "backlog.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "backlog.html")

with open(DATA_PATH) as f:
    data = json.load(f)
items = data["items"]

BUILD_TIME = datetime.now().strftime("%B %d, %Y at %I:%M %p")
ITEMS_JSON = json.dumps(items, indent=2)

# ── Derived stats ──
open_count = len([i for i in items if i["status"] == "open"])
ip_count = len([i for i in items if i["status"] == "in_progress"])
done_count = len([i for i in items if i["status"] == "done"])
wontdo_count = len([i for i in items if i["status"] == "wont_do"])
someday_count = len([i for i in items if i["status"] == "someday"])
area_options = sorted({i["area"] for i in items if i.get("area")})

CSS = r""":root{--bg:#f5f7fa;--surface:#fff;--text:#333;--muted:#666;--border:#e5e7eb;--blue:#2563eb;--red:#e74c3c;--amber:#f39c12;--gray:#95a5a6;--light-gray:#f3f4f6;--green:#16a34a}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;background:#f5f7fa;color:#333;min-height:100vh}
.container{max-width:1200px;margin:0 auto;padding:20px}
header{background:#fff;padding:24px 28px;border-radius:10px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
h1{font-size:26px;margin-bottom:12px}
.header-info{display:flex;gap:28px;font-size:14px;color:#666;flex-wrap:wrap;align-items:center}
.header-actions{display:flex;gap:8px;margin-left:auto}
.summary-count{font-weight:700;color:#2c3e50}
.btn{padding:7px 16px;border:1px solid #dde1e7;border-radius:5px;background:#fff;cursor:pointer;font-size:13px;font-weight:500;transition:all .15s}
.btn:hover{background:#f0f2f5}
.btn-primary{background:#2563eb;color:#fff;border-color:#2563eb}
.btn-primary:hover{background:#1d4ed8}
.btn-success{background:#16a34a;color:#fff;border-color:#16a34a}
.btn-success:hover{background:#15803d}
.controls{background:#fff;padding:16px 20px;border-radius:10px;margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,.08);display:flex;gap:16px;flex-wrap:wrap;align-items:center}
.view-tabs{display:flex;gap:6px}
.view-tab{padding:7px 14px;background:#f0f2f5;border:1px solid #dde1e7;border-radius:5px;cursor:pointer;font-size:13px;font-weight:500;transition:all .15s}
.view-tab:hover{background:#e5e7eb}
.view-tab.active{background:#2563eb;color:#fff;border-color:#2563eb}
.sort-control{display:flex;align-items:center;gap:6px;font-size:13px;color:#666}
.sort-control select{padding:6px 10px;border:1px solid #dde1e7;border-radius:5px;background:#fff;font-size:13px}
.search-box{flex:1;min-width:180px}
.search-box input{width:100%;padding:7px 12px;border:1px solid #dde1e7;border-radius:5px;font-size:13px;outline:none;transition:border-color .15s}
.search-box input:focus{border-color:#2563eb}
.archive-bar{padding:6px 0 0 0;margin-left:20px;margin-right:20px}
.archive-link{font-size:13px;color:#666;cursor:pointer;padding:4px 8px;border-radius:4px;user-select:none}
.archive-link:hover{color:#2563eb;background:#dbeafe}
.archive-link.active{color:#2563eb;background:#dbeafe}
.backlog-list{background:#fff;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.08);overflow:hidden}
.backlog-item{border-bottom:1px solid #f0f0f0;cursor:pointer;transition:background .1s}
.backlog-item:last-child{border-bottom:none}
.backlog-item:hover{background:#fafbfc}
.item-header{padding:14px 20px;display:flex;align-items:center;gap:10px}
.item-header.unsaved::before{content:"\2022";color:#f59e0b;font-size:20px;font-weight:700;margin-right:2px;line-height:1}
.priority-badge{padding:3px 8px;border-radius:4px;font-size:11px;font-weight:700;min-width:32px;text-align:center;flex-shrink:0}
.priority-p1{background:#e74c3c;color:#fff}
.priority-p2{background:#f39c12;color:#fff}
.priority-p3{background:#95a5a6;color:#fff}
.priority-none{background:#e0e0e0;color:#999}
.ref-badge{padding:3px 7px;border-radius:4px;font-size:11px;font-weight:700;background:#eef2ff;color:#3730a3;border:1px solid #c7d2fe;min-width:54px;text-align:center;flex-shrink:0}
.item-title{flex:1;font-size:14px;font-weight:500;line-height:1.4}
.item-title.strikethrough{text-decoration:line-through;color:#999}
.area-badge{padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;background:#f0f2f5;color:#666;flex-shrink:0}
.status-badge{padding:3px 8px;border-radius:4px;font-size:11px;font-weight:600;flex-shrink:0}
.status-open{background:#dbeafe;color:#1e40af}
.status-in_progress{background:#d1fae5;color:#065f46}
.status-done{background:#f3f4f6;color:#6b7280;text-decoration:line-through;opacity:.7}
.status-wont_do{background:#f3f4f6;color:#9ca3af}
.status-someday{background:#fef3c7;color:#92400e}
.item-date{font-size:11px;color:#999;min-width:85px;text-align:right;flex-shrink:0}
.item-expand{font-size:11px;color:#bbb;flex-shrink:0;transition:transform .2s;user-select:none}
.item-expand.expanded{transform:rotate(180deg)}
.item-details{display:none;padding:0 20px 16px 62px;border-top:1px solid #f5f5f5}
.item-details.expanded{display:block!important}
.item-editors{display:flex;gap:12px;margin-bottom:14px;flex-wrap:wrap;align-items:flex-end}
.editor-group{display:flex;flex-direction:column;gap:3px}
.editor-group label{font-size:10px;font-weight:600;color:#999;text-transform:uppercase;letter-spacing:.3px}
.editor-group select{padding:5px 8px;border:1px solid #dde1e7;border-radius:4px;background:#fff;font-size:12px;min-width:90px;cursor:pointer}
.editor-group select:focus{outline:none;border-color:#2563eb}
.detail-label{font-size:10px;font-weight:600;text-transform:uppercase;color:#999;letter-spacing:.3px;margin-bottom:3px}
.detail-value{font-size:13px;color:#555;line-height:1.5;margin-bottom:12px;white-space:pre-wrap}
.empty-state{padding:60px 20px;text-align:center;color:#999;font-size:15px}
.area-group-heading{background:#f8f9fa;padding:10px 20px;font-size:12px;font-weight:600;text-transform:uppercase;color:#888;letter-spacing:.5px}
.footer{text-align:right;font-size:11px;color:#bbb;margin-top:16px;padding-bottom:10px}
/* new item form */
.new-item-form{display:none;background:#fff;padding:24px 28px;border-radius:10px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.08);border:2px dashed #dde1e7}
.new-item-form.expanded{display:block}
.new-item-form h3{margin-bottom:16px;font-size:16px;font-weight:600}
.new-item-form .form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px}
.new-item-form .form-group{display:flex;flex-direction:column}
.new-item-form .form-group label{font-size:11px;font-weight:600;color:#666;margin-bottom:4px}
.new-item-form .form-group input,.new-item-form .form-group select,.new-item-form .form-group textarea{padding:7px 10px;border:1px solid #dde1e7;border-radius:4px;font-size:13px;font-family:inherit;outline:none;transition:border-color .15s}
.new-item-form .form-group input:focus,.new-item-form .form-group select:focus,.new-item-form .form-group textarea:focus{border-color:#2563eb}
.new-item-form .form-group textarea{resize:vertical;min-height:50px}
.new-item-form .full-width{grid-column:1/-1}
.new-item-form .form-actions{display:flex;gap:10px;justify-content:flex-end;margin-top:14px}
/* archive view collapsed */
.archive-collapsed .item-header{padding:10px 20px}
.archive-collapsed .item-details{display:none!important}
.archive-collapsed:hover{background:#f8f9fa}
"""

# ── Build HTML ──
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Backlog - Mechanical PE Exam Prep</title>
<style>{CSS}</style>
</head>
<body>
<div id="auth-overlay"><div class="auth-box"><div class="auth-logo">♠️</div><div class="auth-title">MPEP Dashboard</div><div class="auth-sub">Internal use only</div><form id="auth-form"><input type="password" id="pwd-input" placeholder="Password"><div id="pwd-error"></div><button type="submit" id="pwd-btn">Unlock</button></form></div></div>
<div id="main-content">
<div class="container">
<header>
<h1>📋 Backlog — Deferred Work Log</h1>
<div class="header-info">
<span><strong class="summary-count" id="count-open">{open_count}</strong> open</span>
<span><strong class="summary-count" id="count-in-progress">{ip_count}</strong> in progress</span>
<span><strong class="summary-count" id="count-done">{done_count}</strong> completed</span>
<span><strong class="summary-count" id="count-wont-do">{wontdo_count}</strong> will not do</span>
<span><strong class="summary-count" id="count-someday">{someday_count}</strong> someday</span>
<div class="header-actions">
<button class="btn btn-primary" id="btn-add-item">+ Add Item</button>
<button class="btn btn-success" id="btn-export">📥 Export Changes</button>
</div>
</div>
</header>

<div class="new-item-form" id="new-item-form">
<h3>Add New Item</h3>
<div class="form-grid">
<div class="form-group full-width">
<label>Title *</label>
<input type="text" id="new-title" placeholder="Item title">
</div>
<div class="form-group">
<label>Area</label>
<select id="new-area"><option value="">-- Select Area --</option></select>
</div>
<div class="form-group">
<label>Priority</label>
<select id="new-priority"><option value="">--</option><option value="P1">P1</option><option value="P2">P2</option><option value="P3">P3</option></select>
</div>
<div class="form-group">
<label>Status</label>
<select id="new-status"><option value="open" selected>open</option><option value="in_progress">in_progress</option><option value="done">done</option><option value="wont_do">wont_do</option><option value="someday">someday</option></select>
</div>
<div class="form-group full-width">
<label>Context</label>
<textarea id="new-context" placeholder="Optional context..."></textarea>
</div>
<div class="form-group full-width">
<label>Notes</label>
<textarea id="new-notes" placeholder="Optional notes..."></textarea>
</div>
</div>
<div class="form-actions">
<button class="btn" id="btn-cancel-new">Cancel</button>
<button class="btn btn-primary" id="btn-submit-new">Add Item</button>
</div>
</div>

<div class="controls">
<div class="view-tabs">
<button class="view-tab active" data-view="all">All</button>
<button class="view-tab" data-view="p1">P1</button>
<button class="view-tab" data-view="area">By Area</button>
<button class="view-tab" data-view="someday">Someday</button>
</div>
<div class="sort-control">
<label>Sort:</label>
<select id="sort-select"><option value="priority">Priority</option><option value="date">Date</option><option value="area">Area</option></select>
</div>
<div class="search-box">
<input type="text" id="search-input" placeholder="Search ref, title, ID, or context...">
</div>
</div>

<div class="archive-bar">
<span class="archive-link" id="archive-toggle">📦 View Archive ({done_count + wontdo_count} items)</span>
</div>

<div class="backlog-list" id="backlog-list">
<div class="empty-state">Loading...</div>
</div>

<div class="footer">Last updated: {BUILD_TIME}</div>
</div>
</div>
<script src="auth.js"></script>
<script>
const BACKLOG_ITEMS = {ITEMS_JSON};

// ── State ──
let items = JSON.parse(JSON.stringify(BACKLOG_ITEMS));
let currentView = "all";
let currentSort = "priority";
let searchQuery = "";
let showArchive = false;
let unsavedSet = new Set();

const AREAS = [...new Set(items.map(i => i.area).filter(Boolean))].sort();
const PRIORITY_ORDER = {{ P1: 1, P2: 2, P3: 3 }};

function pv(p) {{ return PRIORITY_ORDER[p] || 4 }}
function esc(s) {{ return s ? String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;") : "" }}
function fmtDate(d) {{ try {{ const dt = new Date(d+"T12:00:00"); return dt.toLocaleDateString("en-US",{{month:"short",day:"numeric",year:"numeric"}}) }} catch(e) {{ return d }} }}
function nextBacklogRef() {{
  const nums = items.map(i => {{
    const m = String(i.ref || "").match(/^BL-(\\d+)$/);
    return m ? parseInt(m[1], 10) : 0;
  }});
  const next = nums.length ? Math.max(...nums) + 1 : 1;
  return "BL-" + String(next).padStart(3, "0");
}}

function updateCounts() {{
  const o=items.filter(i=>i.status==="open").length;
  const ip=items.filter(i=>i.status==="in_progress").length;
  const d=items.filter(i=>i.status==="done").length;
  const w=items.filter(i=>i.status==="wont_do").length;
  const s=items.filter(i=>i.status==="someday").length;
  document.getElementById("count-open").textContent=o;
  document.getElementById("count-in-progress").textContent=ip;
  document.getElementById("count-done").textContent=d;
  document.getElementById("count-wont-do").textContent=w;
  document.getElementById("count-someday").textContent=s;
}}

function markUnsaved(id) {{ unsavedSet.add(id); render(); }}

function getFiltered() {{
  let result = [...items];
  // archive filter
  if (showArchive) {{
    result = result.filter(i => i.status === "done" || i.status === "wont_do");
  }} else if (currentView === "someday") {{
    result = result.filter(i => i.status === "someday");
  }} else {{
    result = result.filter(i => i.status !== "done" && i.status !== "wont_do" && i.status !== "someday");
    if (currentView === "p1") result = result.filter(i => i.priority === "P1");
  }}
  // search
  const q = searchQuery.trim().toLowerCase();
  if (q) {{
    result = result.filter(i =>
      (i.title && i.title.toLowerCase().includes(q)) ||
      (i.ref && i.ref.toLowerCase().includes(q)) ||
      (i.id && i.id.toLowerCase().includes(q)) ||
      (i.context && i.context.toLowerCase().includes(q)) ||
      (i.area && i.area.toLowerCase().includes(q))
    );
  }}
  // sort
  if (currentSort === "priority") {{
    result.sort((a,b) => {{ const d = pv(a.priority) - pv(b.priority); return d !== 0 ? d : new Date(b.surfaced+"T12:00:00") - new Date(a.surfaced+"T12:00:00"); }});
  }} else if (currentSort === "date") {{
    result.sort((a,b) => new Date(b.surfaced+"T12:00:00") - new Date(a.surfaced+"T12:00:00"));
  }} else if (currentSort === "area") {{
    result.sort((a,b) => {{ const d = (a.area||"").localeCompare(b.area||""); return d !== 0 ? d : pv(a.priority) - pv(b.priority); }});
  }}
  return result;
}}

function render() {{
  const list = document.getElementById("backlog-list");
  const filtered = getFiltered();
  // archive link text
  const dCnt = items.filter(i=>i.status==="done").length;
  const wCnt = items.filter(i=>i.status==="wont_do").length;
  document.getElementById("archive-toggle").textContent = showArchive ? "📂 Back to Active Items" : "📦 View Archive ("+(dCnt+wCnt)+" items)";

  if (filtered.length === 0) {{
    list.innerHTML = '<div class="empty-state">🎉 Nothing here yet — all items have been resolved</div>';
    return;
  }}

  let html = "";
  if (currentView === "area" && !showArchive) {{
    // group by area
    const groups = {{}};
    filtered.forEach(i => {{ const a = i.area || "Other"; if (!groups[a]) groups[a] = []; groups[a].push(i); }});
    const sortedAreas = Object.keys(groups).sort();
    sortedAreas.forEach(area => {{
      html += '<div class="area-group-heading">'+esc(area)+'</div>';
      groups[area].forEach(item => {{ html += renderItem(item); }});
    }});
  }} else {{
    filtered.forEach(item => {{ html += renderItem(item); }});
  }}
  list.innerHTML = html;
}}

function renderItem(item) {{
  const isArchive = showArchive || item.status === "done" || item.status === "wont_do";
  const pClass = item.priority ? "priority-"+item.priority.toLowerCase() : "priority-none";
  const pLabel = item.priority || "-";
  const sClass = "status-"+item.status;
  const sLabel = item.status === "in_progress" ? "In Progress" : item.status === "wont_do" ? "Won't Do" : item.status.charAt(0).toUpperCase()+item.status.slice(1);
  const strike = (item.status === "done" || item.status === "wont_do") ? "strikethrough" : "";
  const unsaved = unsavedSet.has(item.id) ? "unsaved" : "";
  return '<div class="backlog-item" data-id="'+esc(item.id)+'">'+
    '<div class="item-header '+unsaved+'">'+
      '<span class="priority-badge '+pClass+'">'+pLabel+'</span>'+
      (item.ref ? '<span class="ref-badge">'+esc(item.ref)+'</span>' : '')+
      '<span class="item-title '+strike+'">'+esc(item.title)+'</span>'+
      (item.area ? '<span class="area-badge">'+esc(item.area)+'</span>' : '')+
      '<span class="status-badge '+sClass+'">'+sLabel+'</span>'+
      '<span class="item-date">'+fmtDate(item.surfaced)+'</span>'+
      '<span class="item-expand">▼</span>'+
    '</div>'+
    '<div class="item-details'+(isArchive?'':'')+'">'+
      '<div class="item-editors">'+
        '<div class="editor-group"><label>Priority</label>'+
        '<select class="ed-priority" data-id="'+esc(item.id)+'">'+
          '<option value="">--</option><option value="P1"'+(item.priority==="P1"?" selected":"")+'>P1</option>'+
          '<option value="P2"'+(item.priority==="P2"?" selected":"")+'>P2</option>'+
          '<option value="P3"'+(item.priority==="P3"?" selected":"")+'>P3</option>'+
        '</select></div>'+
        '<div class="editor-group"><label>Status</label>'+
        '<select class="ed-status" data-id="'+esc(item.id)+'">'+
          '<option value="open"'+(item.status==="open"?" selected":"")+'>open</option>'+
          '<option value="in_progress"'+(item.status==="in_progress"?" selected":"")+'>in_progress</option>'+
          '<option value="done"'+(item.status==="done"?" selected":"")+'>done</option>'+
          '<option value="wont_do"'+(item.status==="wont_do"?" selected":"")+'>wont_do</option>'+
          '<option value="someday"'+(item.status==="someday"?" selected":"")+'>someday</option>'+
        '</select></div>'+
        '<div class="editor-group"><label>Area</label>'+
        '<select class="ed-area" data-id="'+esc(item.id)+'">'+
          '<option value="">--</option>'+AREAS.map(a => '<option value="'+a+'"'+(item.area===a?" selected":"")+'>'+a+'</option>').join("")+
        '</select></div>'+
      '</div>'+
      (item.context ? '<div class="detail-label">Context</div><div class="detail-value">'+esc(item.context)+'</div>' : '')+
      (item.notes ? '<div class="detail-label">Notes</div><div class="detail-value">'+esc(item.notes)+'</div>' : '')+
      '<div class="detail-label">IDs</div><div class="detail-value">'+(item.ref ? esc(item.ref)+' / ' : '')+esc(item.id)+'</div>'+
    '</div></div>';
}}

// ── Event handlers ──
document.addEventListener("DOMContentLoaded", function() {{
  // populate area dropdown in new-item form
  const areaSel = document.getElementById("new-area");
  AREAS.forEach(a => {{
    const opt = document.createElement("option");
    opt.value = a; opt.textContent = a;
    areaSel.appendChild(opt);
  }});

  render();

  // view tabs
  document.querySelectorAll(".view-tab").forEach(tab => {{
    tab.addEventListener("click", function() {{
      document.querySelectorAll(".view-tab").forEach(t => t.classList.remove("active"));
      this.classList.add("active");
      currentView = this.dataset.view;
      render();
    }});
  }});

  // sort
  document.getElementById("sort-select").addEventListener("change", function() {{
    currentSort = this.value;
    render();
  }});

  // search
  let searchTimer;
  document.getElementById("search-input").addEventListener("input", function() {{
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {{ searchQuery = this.value; render(); }}, 200);
  }});

  // archive toggle
  document.getElementById("archive-toggle").addEventListener("click", function() {{
    showArchive = !showArchive;
    this.classList.toggle("active", showArchive);
    render();
  }});

  // expand/collapse
  document.getElementById("backlog-list").addEventListener("click", function(e) {{
    const item = e.target.closest(".backlog-item");
    if (!item) return;
    if (e.target.closest("select")) return; // don't toggle on dropdown clicks
    const details = item.querySelector(".item-details");
    const expand = item.querySelector(".item-expand");
    if (details) {{
      details.classList.toggle("expanded");
      if (expand) expand.classList.toggle("expanded");
    }}
  }});

  // inline edit dropdowns
  document.getElementById("backlog-list").addEventListener("change", function(e) {{
    const sel = e.target.closest("select");
    if (!sel || !sel.dataset.id) return;
    const id = sel.dataset.id;
    const item = items.find(i => i.id === id);
    if (!item) return;
    if (sel.classList.contains("ed-priority")) {{
      item.priority = sel.value || null;
    }} else if (sel.classList.contains("ed-status")) {{
      item.status = sel.value;
    }} else if (sel.classList.contains("ed-area")) {{
      const oldArea = item.area;
      item.area = sel.value || null;
      if (item.area && !AREAS.includes(item.area)) {{
        AREAS.push(item.area);
        AREAS.sort();
        // re-render all area dropdowns
        render();
        return;
      }}
    }}
    markUnsaved(id);
    updateCounts();
  }});

  // Add Item form
  document.getElementById("btn-add-item").addEventListener("click", function() {{
    const form = document.getElementById("new-item-form");
    form.classList.toggle("expanded");
    if (form.classList.contains("expanded")) {{
      document.getElementById("new-title").focus();
    }}
  }});

  document.getElementById("btn-cancel-new").addEventListener("click", function() {{
    document.getElementById("new-item-form").classList.remove("expanded");
  }});

  document.getElementById("btn-submit-new").addEventListener("click", function() {{
    const title = document.getElementById("new-title").value.trim();
    if (!title) {{ alert("Title is required."); return; }}
    const area = document.getElementById("new-area").value;
    const priority = document.getElementById("new-priority").value || null;
    const status = document.getElementById("new-status").value;
    const context = document.getElementById("new-context").value.trim();
    const notes = document.getElementById("new-notes").value.trim();

    const today = new Date().toISOString().split("T")[0];
    const prefix = today+"-";
    const existing = items.filter(i => i.id.startsWith(prefix)).map(i => parseInt(i.id.split("-")[3]) || 0);
    const seq = existing.length > 0 ? Math.max(...existing) + 1 : 1;
    const id = prefix + String(seq).padStart(3, "0");

    const newItem = {{
      id: id, ref: nextBacklogRef(), title: title, priority: priority, area: area || null,
      surfaced: today, context: context, notes: notes, status: status
    }};
    items.push(newItem);
    if (newItem.area && !AREAS.includes(newItem.area)) {{ AREAS.push(newItem.area); AREAS.sort(); }}
    unsavedSet.add(id);
    document.getElementById("new-item-form").classList.remove("expanded");
    document.getElementById("new-title").value = "";
    document.getElementById("new-area").value = "";
    document.getElementById("new-priority").value = "";
    document.getElementById("new-status").value = "open";
    document.getElementById("new-context").value = "";
    document.getElementById("new-notes").value = "";
    updateCounts();
    render();
  }});

  // Export
  document.getElementById("btn-export").addEventListener("click", function() {{
    const exportData = {{ items: items, _exportedAt: new Date().toISOString(), _unsavedIds: [...unsavedSet] }};
    const blob = new Blob([JSON.stringify(exportData, null, 2)], {{ type: "application/json" }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "backlog-export.json";
    a.click();
    URL.revokeObjectURL(url);
    unsavedSet.clear();
  }});

  // unload warning
  window.addEventListener("beforeunload", function(e) {{
    if (unsavedSet.size > 0 || document.getElementById("new-item-form").classList.contains("expanded")) {{
      e.preventDefault();
      e.returnValue = "You have unsaved backlog changes. Export before leaving?";
      return e.returnValue;
    }}
  }});
}});
</script>
</body>
</html>"""

# ── Write output ──
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w") as f:
    f.write(html)

print(f"✅ Backlog dashboard built: {OUTPUT_PATH}")
