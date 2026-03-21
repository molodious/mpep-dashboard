#!/usr/bin/env python3
"""
Apply auth protection to unprotected dashboard pages.
Wraps content with auth overlay + main-content divs and adds auth.js script.
"""

import re
from pathlib import Path

DASHBOARD_DIR = Path(__file__).parent
FILES_TO_PROTECT = [
    'cron.html',
    'oh-prep.html',
]

AUTH_OVERLAY_HTML = '''<!-- ── Auth overlay ── -->
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

'''

AUTH_STYLES = '''
    /* ── Auth overlay ── */
    #auth-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: var(--bg);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
    }

    .auth-box {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 32px;
      width: 100%;
      max-width: 280px;
      text-align: center;
    }

    .auth-logo { font-size: 36px; margin-bottom: 12px; }
    .auth-title { font-size: 20px; font-weight: 700; color: var(--text); margin-bottom: 4px; }
    .auth-sub   { font-size: 13px; color: var(--muted); margin-bottom: 28px; }

    .auth-box input {
      width: 100%;
      padding: 8px 12px;
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 4px;
      color: var(--text);
      font-size: 13px;
      margin-bottom: 8px;
    }

    .auth-box input:focus { border-color: var(--blue); outline: none; }

    .auth-box button {
      width: 100%;
      padding: 8px 12px;
      background: var(--blue);
      color: var(--bg);
      border: none;
      border-radius: 4px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
    }

    .auth-box button:hover  { opacity: 0.88; }
    .auth-box button:disabled { opacity: 0.55; cursor: default; }

    #pwd-error {
      display: none;
      color: var(--red);
      font-size: 11px;
      margin-bottom: 8px;
    }

    #main-content { display: none; }

'''

def has_auth_protection(html_content):
    """Check if HTML already has auth protection."""
    return 'auth-overlay' in html_content or 'auth.js' in html_content

def add_auth_styles(html_content):
    """Add auth CSS to <style> block if not already present."""
    if '/* ── Auth overlay ──' in html_content:
        return html_content
    
    # Find the closing </style> tag
    match = re.search(r'</style>', html_content, re.IGNORECASE)
    if not match:
        print("Warning: No <style> tag found, skipping CSS injection")
        return html_content
    
    # Insert auth styles before closing </style>
    pos = match.start()
    new_html = html_content[:pos] + AUTH_STYLES + html_content[pos:]
    return new_html

def add_auth_overlay_and_wrapper(html_content):
    """
    Add auth overlay before <body> content.
    Wrap main content with <div id="main-content">.
    """
    # Find <body> tag
    body_match = re.search(r'<body[^>]*>', html_content, re.IGNORECASE)
    if not body_match:
        print("Warning: No <body> tag found")
        return html_content
    
    # Insert auth overlay right after opening <body> tag
    body_end = body_match.end()
    new_html = html_content[:body_end] + '\n\n' + AUTH_OVERLAY_HTML + '<div id="main-content">' + html_content[body_end:]
    
    # Wrap closing </body> with closing </div> for main-content
    new_html = re.sub(
        r'(</body>)',
        r'</div><!-- end main-content -->\n\1',
        new_html,
        count=1,
        flags=re.IGNORECASE
    )
    
    return new_html

def add_auth_script(html_content):
    """Add auth.js script reference before </body>."""
    if '<script src="auth.js"></script>' in html_content:
        return html_content
    
    # Find closing </body> tag and add script before it
    script_tag = '<script src="auth.js"></script>'
    new_html = re.sub(
        r'(</body>)',
        script_tag + '\n\1',
        html_content,
        count=1,
        flags=re.IGNORECASE
    )
    
    return new_html

def protect_file(file_path):
    """Apply auth protection to a single file."""
    print(f"\n🔒 Protecting {file_path.name}...", end=" ")
    
    with open(file_path, 'r') as f:
        html = f.read()
    
    # Check if already protected
    if has_auth_protection(html):
        print("✅ Already protected")
        return True
    
    # Apply protections in order
    html = add_auth_styles(html)
    html = add_auth_overlay_and_wrapper(html)
    html = add_auth_script(html)
    
    # Write back
    try:
        with open(file_path, 'w') as f:
            f.write(html)
        print("✅ Protected")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🔐 APPLYING PASSWORD PROTECTION TO DASHBOARD PAGES")
    print("=" * 70)
    
    protected = 0
    failed = 0
    
    for filename in FILES_TO_PROTECT:
        file_path = DASHBOARD_DIR / filename
        if not file_path.exists():
            print(f"\n⚠️  {filename} not found, skipping")
            continue
        
        if protect_file(file_path):
            protected += 1
        else:
            failed += 1
    
    print(f"\n{'=' * 70}")
    print(f"✅ COMPLETE")
    print(f"{'=' * 70}")
    print(f"Protected: {protected} pages")
    print(f"Failed:    {failed} pages")
    print(f"\nAll pages now share the same localStorage session (mpep_auth_v1).")
    print(f"Single password unlock grants access to all dashboard pages.")
    print(f"\nNext: git add -A && git commit -m 'Apply password protection to all dashboard pages' && git push")

if __name__ == '__main__':
    main()
