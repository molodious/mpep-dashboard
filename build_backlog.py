#!/usr/bin/env python3
import json
import os
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
    
    css = """:root{--bg:#f5f7fa;--surface:#fff;--blue:#2563eb;--red:#dc2626}
#auth-overlay{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:9999}
.auth-box{background:#fff;border:1px solid #ddd;border-radius:8px;padding:32px;width:280px;text-align:center}
.auth-logo{font-size:36px;margin-bottom:12px}
.auth-box input{width:100%;padding:8px 12px;border:1px solid #ddd;border-radius:4px;margin-bottom:8px}
.auth-box button{width:100%;padding:8px 12px;background:#2563eb;color:#fff;border:none;border-radius:4px}
#pwd-error{display:none;color:#dc2626;font-size:11px}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#f5f7fa;color:#333}
.container{max-width:1200px;margin:0 auto;padding:20px}
header,.controls{background:#fff;padding:20px;border-radius:8px;margin-bottom:20px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}
h1{font-size:28px;margin-bottom:10px}
.header-info{display:flex;gap:30px;font-size:14px;color:#666;flex-wrap:wrap}
.summary-count{font-weight:700;color:#2c3e50}
.controls{display:flex;gap:20px;flex-wrap:wrap;align-items:center}
.view-tabs{display:flex;gap:8px}
.view-tab{padding:8px 16px;background:#f0f2f5;border:1px solid #dde1e7;border-radius:4px;cursor:pointer}
.view-tab.active{background:#2563eb;color:#fff}
.search-box{flex:1;min-width:200px}
.search-box input{width:100%;padding:8px 12px;border:1px solid #dde1e7;border-radius:4px}
.backlog-list{background:#fff;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}
.backlog-item{border-bottom:1px solid #f0f0f0;cursor:pointer}
.backlog-item:hover{background:#fafafa}
.item-header{padding:16px 20px;display:flex;align-items:center;gap:12px}
.priority-badge{padding:4px 10px;border-radius:4px;font-size:12px;font-weight:700;min-width:36px}
.priority-p1{background:#e74c3c;color:#fff}
.priority-p2{background:#f39c12;color:#fff}
.priority-p3{background:#95a5a6;color:#fff}
.priority-none{background:#e0e0e0;color:#999}
.item-title{flex:1;font-size:15px;font-weight:500}
.item-title.strikethrough{text-decoration:line-through;color:#999}
.area-badge{padding:4px 10px;border-radius:12px;font-size:11px;font-weight:600;background:#f0f2f5;color:#666}
.status-badge{padding:4px 10px;border-radius:4px;font-size:11px;font-weight:600}
.status-open{background:#dbeafe;color:#1e40af}
.status-in_progress{background:#d1fae5;color:#065f46}
.status-done{background:#f3f4f6;color:#6b7280}
.status-wont_do{background:#f3f4f6;color:#9ca3af}
.item-date{font-size:12px;color:#999;min-width:90px;text-align:right}
.item-expand{font-size:12px;color:#999;transition:transform .2s}
.item-expand.expanded{transform:rotate(180deg)}
.item-details{display:none;padding:0 20px 20px 68px;border-top:1px solid #f5f5f5}
.item-details.expanded{display:block}
.detail-label{font-size:11px;font-weight:600;text-transform:uppercase;color:#999;margin-bottom:4px}
.detail-value{font-size:14px;color:#555;line-height:1.5}
.empty-state{padding:60px;text-align:center;color:#999}
.area-group{background:#f8f9fa;padding:12px 20px;font-size:13px;font-weight:600;text-transform:uppercase}
.footer{text-align:right;font-size:12px;color:#999;margin-top:20px}
"""

    with open(OUTPUT_PATH, "w") as f:
        f.write('<!DOCTYPE html><html lang="en"><head>')
        f.write('<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">')
        f.write('<title>Backlog - Mechanical PE Exam Prep</title>')
        f.write('<style>' + css + '</style>')
        f.write('</head><body>')
        f.write('<div id="auth-overlay"><div class="auth-box">')
        f.write('<div class="auth-logo">♠️</div><div class="auth-title">MPEP Dashboard</div>')
        f.write('<div class="auth-sub">Internal use only</div>')
        f.write('<form id="auth-form"><input type="password" id="pwd-input" placeholder="Password"><div id="pwd-error"></div>')
        f.write('<button type="submit" id="pwd-btn">Unlock</button></form>')
        f.write('</div></div>')
        f.write('<div id="main-content"><div class="container"><header>')
        f.write('<h1>📋 Backlog — Deferred Work Log</h1><div class="header-info">')
        f.write(f'<span><strong class="summary-count">{open_count}</strong> open</span>')
        f.write(f'<span><strong class="summary-count">{in_progress_count}</strong> in progress</span>')
        f.write(f'<span><strong class="summary-count">{done_count}</strong> completed</span>')
        f.write(f'<span><strong class="summary-count">{wont_do_count}</strong> will not do</span>')
        f.write('</div></header>')
        f.write('<div class="controls"><div class="view-tabs">')
        f.write('<button class="view-tab active" data-view="all">All</button>')
        f.write('<button class="view-tab" data-view="p1">P1</button>')
        f.write('<button class="view-tab" data-view="area">By Area</button>')
        f.write('<button class="view-tab" data-view="completed">Completed</button>')
        f.write('</div><div class="sort-control"><label>Sort:</label>')
        f.write('<select id="sort-select"><option value="priority">Priority</option><option value="date">Date</option><option value="area">Area</option></select>')
        f.write('</div><div class="search-box">')
        f.write('<input type="text" id="search-input" placeholder="Search title or context...">')
        f.write('</div></div>')
        f.write('<div class="backlog-list" id="backlog-list"></div>')
        f.write(f'<div class="footer">Last updated: {build_time}</div>')
        f.write('</div></div>')
        f.write('<script src="auth.js"></script>')
        f.write('<script>const BACKLOG_ITEMS=' + items_js + ';')
        
        js = """let currentView='all',currentSort='priority',searchQuery='';
const PRIORITY_ORDER={'P1':1,'P2':2,'P3':3};
function getPriorityValue(p){return PRIORITY_ORDER[p]||4}
function sortItems(items){const sorted=[...items];if(currentSort==='priority'){sorted.sort((a,b)=>{const pa=getPriorityValue(a.priority),pb=getPriorityValue(b.priority);if(pa!==pb)return pa-pb;return new Date(b.surfaced)-new Date(a.surfaced)});}else if(currentSort==='date'){sorted.sort((a,b)=>new Date(b.surfaced)-new Date(a.surfaced));}else if(currentSort==='area'){sorted.sort((a,b)=>{if(a.area!==b.area)return a.area.localeCompare(b.area);return getPriorityValue(a.priority)-getPriorityValue(b.priority)});}return sorted;}
function filterItems(items){let filtered=items;if(currentView==='p1'){filtered=filtered.filter(i=>i.priority==='P1'&&(i.status==='open'||i.status==='in_progress'));}else if(currentView==='area'){filtered=filtered.filter(i=>i.status!=='done'&&i.status!=='wont_do');}else if(currentView==='completed'){filtered=filtered.filter(i=>i.status==='done'||i.status==='wont_do');}if(searchQuery.trim()){const q=searchQuery.toLowerCase();filtered=filtered.filter(i=>i.title.toLowerCase().includes(q)||i.context.toLowerCase().includes(q)||i.area.toLowerCase().includes(q));}return filtered;}
function getPriorityClass(p){if(p==='P1')return'priority-p1';if(p==='P2')return'priority-p2';if(p==='P3')return'priority-p3';return'priority-none';}
function getPriorityLabel(p){return p||'-';}
function getStatusClass(s){return'status-'+s;}
function getStatusLabel(s){if(s==='in_progress')return'In Progress';if(s==='wont_do')return"Won't Do";return s.charAt(0).toUpperCase()+s.slice(1);}
function formatDate(d){return new Date(d).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'});}
function toggleExpand(id){document.getElementById('details-'+id).classList.toggle('expanded');document.getElementById('arrow-'+id).classList.toggle('expanded');}
function renderItem(item){const isDone=item.status==='done'||item.status==='wont_do';return'<div class="backlog-item" onclick="toggleExpand(&#39;'+item.id+'&#39;)"><div class="item-header"><span class="priority-badge '+getPriorityClass(item.priority)+'">'+getPriorityLabel(item.priority)+'</span><span class="item-title '+(isDone?'strikethrough':'')+'">'+item.title+'</span><span class="area-badge">'+item.area+'</span><span class="status-badge '+getStatusClass(item.status)+'">'+getStatusLabel(item.status)+'</span><span class="item-date">'+formatDate(item.surfaced)+'</span><span class="item-expand" id="arrow-'+item.id+'">&#9662;</span></div><div class="item-details" id="details-'+item.id+'"><div class="detail-section"><div class="detail-label">Context</div><div class="detail-value context">'+item.context+'</div></div>'+(item.notes?'<div class="detail-section"><div class="detail-label">Notes</div><div class="detail-value">'+item.notes+'</div></div>':'')+'</div></div>';}
function renderGroupedByArea(items){const areas=[...new Set(items.map(i=>i.area))].sort();let html='';areas.forEach(area=>{const areaItems=items.filter(i=>i.area===area);if(areaItems.length>0){html+='<div class="area-group">'+area+'</div>';html+=areaItems.map(renderItem).join('');}});return html;}
function render(){const filtered=filterItems(BACKLOG_ITEMS);const sorted=sortItems(filtered);const listEl=document.getElementById('backlog-list');if(sorted.length===0){listEl.innerHTML='<div class="empty-state">🎉 Nothing here yet — all items have been resolved</div>';return;}if(currentView==='area'){listEl.innerHTML=renderGroupedByArea(sorted);}else{listEl.innerHTML=sorted.map(renderItem).join('');}}
document.querySelectorAll('.view-tab').forEach(tab=>{tab.addEventListener('click',()=>{document.querySelectorAll('.view-tab').forEach(t=>t.classList.remove('active'));tab.classList.add('active');currentView=tab.dataset.view;render();});});
document.getElementById('sort-select').addEventListener('change',(e)=>{currentSort=e.target.value;render();});
document.getElementById('search-input').addEventListener('input',(e)=>{searchQuery=e.target.value;render();});
function onAuthenticated(){render();}
</script></body></html>"""
        
        f.write(js)
    print(f"Created {OUTPUT_PATH}")

if __name__ == "__main__":
    build_dashboard()
