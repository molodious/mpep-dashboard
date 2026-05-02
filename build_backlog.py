#!/usr/bin/env python3
"""
Build the backlog dashboard HTML from data/backlog.json
"""

import json
import os
import subprocess
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, "data", "backlog.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "backlog.html")

def load_backlog():
    with open(DATA_PATH, "r") as f:
        return json.load(f)

def build_dashboard():
    data = load_backlog()
    items = data.get("items", [])
    build_time = datetime.now().strftime("%b %d, %Y at %I:%M %p")

    open_count = sum(1 for i in items if i.get("status") == "open")
    in_progress_count = sum(1 for i in items if i.get("status") == "in_progress")
    done_count = sum(1 for i in items if i.get("status") == "done")
    wont_do_count = sum(1 for i in items if i.get("status") == "wont_do")

    items_js = json.dumps(items)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Backlog - Mechanical PE Exam Prep</title>
    <style>
        :root {{
            --bg: #f5f7fa;
            --surface: #ffffff;
            --surface2: #f0f2f5;
            --border: #dde1e7;
            --text: #333333;
            --muted: #777777;
            --blue: #2563eb;
            --red: #dc2626;
            --green: #27ae60;
        }}
        #auth-overlay {{
          position: fixed; top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(0,0,0,0.6);
          display: flex; align-items: center; justify-content: center;
          z-index: 9999;
        }}
        .auth-box {{
          background: var(--surface); border: 1px solid var(--border);
          border-radius: 8px; padding: 32px; width: 100%; max-width: 280px; text-align: center;
        }}
        .auth-logo {{ font-size: 36px; margin-bottom: 12px; }}
        .auth-title {{ font-size: 20px; font-weight: 700; color: var(--text); margin-bottom: 4px; }}
        .auth-sub   {{ font-size: 13px; color: var(--muted); margin-bottom: 28px; }}
        .auth-box input {{
          width: 100%; padding: 8px 12px; background: var(--surface2);
          border: 1px solid var(--border); border-radius: 4px;
          color: var(--text); font-size: 13px; margin-bottom: 8px;
        }}
        .auth-box input:focus {{ border-color: var(--blue); outline: none; }}
        .auth-box button {{
          width: 100%; padding: 8px 12px; background: var(--blue);
          color: #fff; border: none; border-radius: 4px;
          font-size: 14px; font-weight: 600; cursor: pointer;
        }}
        .auth-box button:hover {{ opacity: 0.88; }}
        .auth-box button:disabled {{ opacity: 0.55; cursor: default; }}
        #pwd-error {{ display: none; color: var(--red); font-size: 11px; margin-bottom: 8px; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f7fa;
            color: #333;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        header {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .header-info {{
            display: flex;
            gap: 30px;
            font-size: 14px;
            color: #666;
            flex-wrap: wrap;
        }}
        .header-info span {{ display: flex; align-items: center; gap: 6px; }}
        .summary-count {{ font-weight: 700; color: #2c3e50; }}
        .controls {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            align-items: center;
        }}
        .view-tabs {{ display: flex; gap: 8px; }}
        .view-tab {{
            padding: 8px 16px;
            background: #f0f2f5;
            border: 1px solid #dde1e7;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            color: #555;
        }}
        .view-tab:hover {{ background: #e8eaed; }}
        .view-tab.active {{ background: #2563eb; color: white; border-color: #2563eb; }}
        .sort-control {{ display: flex; align-items: center; gap: 8px; }}
        .sort-control label {{ font-size: 14px; color: #555; font-weight: 500; }}
        .sort-control select {{
            padding: 8px 12px;
            border: 1px solid #dde1e7;
            border-radius: 4px;
            background: #f5f7fa;
            font-size: 14px;
            cursor: pointer;
        }}
        .search-box {{ flex: 1; min-width: 200px; }}
        .search-box input {{
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #dde1e7;
            border-radius: 4px;
            font-size: 14px;
        }}
        .search-box input:focus {{ outline: none; border-color: #2563eb; }}
        .backlog-list {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .backlog-item {{
            border-bottom: 1px solid #f0f0f0;
            cursor: pointer;
            transition: background 0.15s;
        }}
        .backlog-item:hover {{ background: #fafafa; }}
        .backlog-item:last-child {{ border-bottom: none; }}
        .item-header {{
            padding: 16px 20px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .priority-badge {{
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            min-width: 36px;
            text-align: center;
        }}
        .priority-p1 {{ background: #e74c3c; color: white; }}
        .priority-p2 {{ background: #f39c12; color: white; }}
        .priority-p3 {{ background: #95a5a6; color: white; }}
        .priority-none {{ background: #e0e0e0; color: #999; }}
        .item-title {{
            flex: 1;
            font-size: 15px;
            font-weight: 500;
            color: #333;
        }}
        .item-title.strikethrough {{ text-decoration: line-through; color: #999; }}
        .area-badge {{
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            background: #f0f2f5;
            color: #666;
        }}
        .status-badge {{
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .status-open {{ background: #dbeafe; color: #1e40af; }}
        .status-in_progress {{ background: #d1fae5; color: #065f46; }}
        .status-done {{ background: #f3f4f6; color: #6b7280; }}
        .status-wont_do {{ background: #f3f4f6; color: #9ca3af; }}
        .item-date {{
            font-size: 12px;
            color: #999;
            min-width: 90px;
            text-align: right;
        }}
        .item-expand {{
            font-size: 12px;
            color: #999;
            transition: transform 0.2s;
        }}
        .item-expand.expanded {{ transform: rotate(180deg); }}
        .item-details {{
            display: none;
            padding: 0 20px 20px 68px;
            border-top: 1px solid #f5f5f5;
        }}
        .item-details.expanded {{ display: block; }}
        .detail-section {{ margin-bottom: 12px; }}
        .detail-section:last-child {{ margin-bottom: 0; }}
        .detail-label {{
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            color: #999;
            margin-bottom: 4px;
        }}
        .detail-value {{
            font-size: 14px;
            color: #555;
            line-height: 1.5;
        }}
        .detail-value.context {{ font-style: italic; color: #666; }}
        .empty-state {{
            padding: 60px 20px;
            text-align: center;
            color: #999;
            font-size: 16px;
        }}
        .empty-state-icon {{ font-size: 48px; margin-bottom: 16px; }}
        .footer {{
            text-align: right;
            font-size: 12px;
            color: #999;
            margin-top: 20px;
            padding: 0 10px;
        }}
        .area-group {{
            background: #f8f9fa;
            padding: 12px 20px;
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            color: #666;
            border-bottom: 1px solid #e0e0e0;
        }}
    </style>
</head>
<body>

<div id="auth-overlay">
  <div class="auth-box">
    <div class="auth-logo">♠️</div>
    <div class="auth-title">MPEP Dashboard</div>
    <div class="auth-sub">Internal use only — enter your password to continue</div>
    <form id="auth-form">
      <input type="password" id="pwd-input" placeholder="Password" autocomplete="current-password" />
      <div id="pwd-error"></div>
      <button type="submit" id="pwd-btn">Unlock</button>
    </form>
  </div>
</div>

<div id="main-content">
    <div class="container">
        <header>
            <h1>📋 Backlog — Deferred Work Log</h1>
            <div class="header-info">
                <span><strong class="summary-count">{open_count}</strong> open</span>
                <span><strong class="summary-count">{in_progress_count}</strong> in progress</span>
                <span><strong class="summary-count">{done_count}</strong> completed</span>
                <span><strong class="summary-count">{wont_do_count}</strong> won't do</span>
            </div>
        </header>

        <div class="controls">
            <div class="view-tabs">
                <button class="view-tab active" data-view="all">All</button>
                <button class="view-tab" data-view="p1">P1</button>
                <button class="view-tab" data-view="area">By Area</button>
                <button class="view-tab" data-view="completed">Recently Completed</button>
            </div>
            <div class="sort-control">
                <label>Sort by:</label>
                <select id="sort-select">
                    <option value="priority">Priority</option>
                    <option value="date">Date</option>
                    <option value="area">Area</option>
                </select>
            </div>
            <div class="search-box">
                <input type="text" id="search-input" placeholder="Search title or context...">
            </div>
        </div>

        <div class="backlog-list" id="backlog-list"></div>

        <div class="footer">
            Last updated: {build_time}
        </div>
    </div>
</div>

<script src="auth.js"></script>
<script>
    const BACKLOG_ITEMS = {items_js};

    let currentView = 'all';
    let currentSort = 'priority';
    let searchQuery = '';

    const PRIORITY_ORDER = {{ 'P1': 1, 'P2': 2, 'P3': 3, null: 4 }};

    function getPriorityValue(p) {{ return PRIORITY_ORDER[p] || 4; }}

    function sortItems(items) {{
        const sorted = [...items];
        if (currentSort === 'priority') {{
            sorted.sort((a, b) => {{
                const pa = getPriorityValue(a.priority);
                const pb = getPriorityValue(b.priority);
                if (pa !== pb) return pa - pb;
                return new Date(b.surfaced) - new Date(a.surfaced);
            }});
        }} else if (currentSort === 'date') {{
            sorted.sort((a, b) => new Date(b.surfaced) - new Date(a.surfaced));
        }} else if (currentSort === 'area') {{
            sorted.sort((a, b) => {{
                if (a.area !== b.area) return a.area.localeCompare(b.area);
                return getPriorityValue(a.priority) - getPriorityValue(b.priority);
            }});
        }}
        return sorted;
    }}

    function filterItems(items) {{
        let filtered = items;
        if (currentView === 'p1') {{
            filtered = filtered.filter(i => i.priority === 'P1' && (i.status === 'open' || i.status === 'in_progress'));
        }} else if (currentView === 'area') {{
            filtered = filtered.filter(i => i.status !== 'done' && i.status !== 'wont_do');
        }} else if (currentView === 'completed') {{
            filtered = filtered.filter(i => i.status === 'done' || i.status === 'wont_do');
        }}
        if (searchQuery.trim()) {{
            const q = searchQuery.toLowerCase();
            filtered = filtered.filter(i => 
                i.title.toLowerCase().includes(q) ||
                i.context.toLowerCase().includes(q) ||
                i.area.toLowerCase().includes(q)
            );
        }}
        return filtered;
    }}

    function getPriorityClass(p) {{
        if (p === 'P1') return 'priority-p1';
        if (p === 'P2') return 'priority-p2';
        if (p === 'P3') return 'priority-p3';
        return 'priority-none';
    }}

    function getPriorityLabel(p) {{ return p || '—'; }}

    function getStatusClass(s) {{ return 'status-' + s; }

    function getStatusLabel(s) {
        if (s === 'in_progress') return 'In Progress';
        if (s === 'wont_do') return "Won't Do";
        return s.charAt(0).toUpperCase() + s.slice(1);
    }

    function formatDate(d) {
        return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }

    function toggleExpand(id) {
        const details = document.getElementById('details-' + id);
        const arrow = document.getElementById('arrow-' + id);
        details.classList.toggle('expanded');
        arrow.classList.toggle('expanded');
    }

    function renderItem(item) {
        const isDone = item.status === 'done' || item.status === 'wont_do';
        return `
            <div class="backlog-item" onclick="toggleExpand('${item.id}')">
                <div class="item-header">
                    <span class="priority-badge ${getPriorityClass(item.priority)}">${getPriorityLabel(item.priority)}</span>
                    <span class="item-title ${isDone ? 'strikethrough' : ''}">${item.title}</span>
                    <span class="area-badge">${item.area}</span>
                    <span class="status-badge ${getStatusClass(item.status)}">${getStatusLabel(item.status)}</span>
                    <span class="item-date">${formatDate(item.surfaced)}</span>
                    <span class="item-expand" id="arrow-${item.id}">&#9662;</span>
                </div>
                <div class="item-details" id="details-${item.id}">
                    <div class="detail-section">
                        <div class="detail-label">Context</div>
                        <div class="detail-value context">${item.context}</div>
                    </div>
                    ${item.notes ? `
                    <div class="detail-section">
                        <div class="detail-label">Notes</div>
                        <div class="detail-value">${item.notes}</div>
                    </div>
                    ` : ''}
                    <div class="detail-section">
                        <div class="detail-label">ID</div>
                        <div class="detail-value" style="font-size: 12px; color: #999;">${item.id}</div>
                    </div>
                </div>
            </div>
        `;
    }

    function renderGroupedByArea(items) {
        const areas = [...new Set(items.map(i => i.area))].sort();
        let html = '';
        areas.forEach(area => {
            const areaItems = items.filter(i => i.area === area);
            if (areaItems.length > 0) {
                html += `<div class="area-group">${area}</div>`;
                html += areaItems.map(renderItem).join('');
            }
        });
        return html;
    }

    function render() {
        const filtered = filterItems(BACKLOG_ITEMS);
        const sorted = sortItems(filtered);
        const listEl = document.getElementById('backlog-list');

        if (sorted.length === 0) {
            listEl.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">&#127881;</div>
                    <div>Nothing here yet &mdash; all items have been resolved</div>
                </div>
            `;
            return;
        }

        if (currentView === 'area') {
            listEl.innerHTML = renderGroupedByArea(sorted);
        } else {
            listEl.innerHTML = sorted.map(renderItem).join('');
        }
    }

    document.querySelectorAll('.view-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.view-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentView = tab.dataset.view;
            render();
        });
    });

    document.getElementById('sort-select').addEventListener('change', (e) => {
        currentSort = e.target.value;
        render();
    });

    document.getElementById('search-input').addEventListener('input', (e) => {
        searchQuery = e.target.value;
        render();
    });

    function onAuthenticated() {
        render();
    }
</script>
</body>
</html>
"""

    with open(OUTPUT_PATH, "w") as f:
        f.write(html)
    print(f"Created {OUTPUT_PATH}")

    # Apply auth protection
    auth_script = os.path.join(SCRIPT_DIR, "apply_auth_protection_v2.py")
    if os.path.exists(auth_script):
        subprocess.run([sys.executable, auth_script], check=True)
        print("Applied auth protection")

if __name__ == "__main__":
    build_dashboard()
