#!/usr/bin/env python3
"""
Build exam-lookahead data and inject it into exams.html.
Fetches from both Typeform forms (same logic as exam_good_luck_scheduler_final.py).
Run by the weekly cron or on-demand.
"""
import os, json, re, requests
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

TYPEFORM_TOKEN = os.environ.get("TYPEFORM_TOKEN", "")
if not TYPEFORM_TOKEN:
    try:
        _cfg = json.loads(open(os.path.expanduser(
            "~/.openclaw/workspace/office-hours-config.json")).read())
        TYPEFORM_TOKEN = _cfg.get("typeform_token", "")
    except FileNotFoundError:
        pass

WELCOME_FORM_ID     = "mbKafiOp"
WELCOME_EMAIL_FIELD = "5J91OTPz6NuN"
WELCOME_DATE_FIELD  = "vNIcpfWFkt2R"

EXAM_FORM_ID        = "N3SvmDkt"
EXAM_EMAIL_FIELD    = "194dyAGE163L"
EXAM_DATE_FIELD     = "keHn73gZnyxq"

KIT_API_SECRET = os.environ.get("KIT_API_SECRET", "")

ET = ZoneInfo("America/New_York")
NOW = datetime.now(tz=timezone.utc)
HORIZON = NOW + timedelta(days=180)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def fetch_typeform(form_id, page_size=250):
    headers = {"Authorization": f"Bearer {TYPEFORM_TOKEN}"}
    all_items = []
    page = 1
    while True:
        r = requests.get(
            f"https://api.typeform.com/forms/{form_id}/responses",
            headers=headers,
            params={"page": page, "page_size": page_size},
            timeout=15
        )
        r.raise_for_status()
        data = r.json()
        items = data.get("items", [])
        all_items.extend(items)
        total = data.get("total_items", 0)
        if len(all_items) >= total or not items:
            break
        page += 1
    return all_items


def get_field(answers, field_id):
    for a in answers:
        if a.get("field", {}).get("id") == field_id:
            t = a.get("type")
            if t == "email":   return a.get("email", "")
            if t == "date":    return a.get("date", "")
            if t == "text":    return a.get("text", "")
            if t == "choice":  return a.get("choice", {}).get("label", "")
        # fallback ref match
        if a.get("field", {}).get("ref") == field_id:
            t = a.get("type")
            if t == "email":   return a.get("email", "")
            if t == "date":    return a.get("date", "")
    return None


def kit_name(email):
    if not KIT_API_SECRET or not email:
        return None
    try:
        r = requests.get(
            "https://api.convertkit.com/v3/subscribers",
            params={"api_secret": KIT_API_SECRET, "email_address": email},
            timeout=8
        )
        subs = r.json().get("subscribers", [])
        if subs:
            fn = subs[0].get("first_name", "")
            ln = subs[0].get("fields", {}).get("last_name", "")
            full = f"{fn} {ln}".strip()
            return full if full else None
    except Exception:
        pass
    return None


def build_students():
    students = {}
    skipped = []

    # Welcome form
    try:
        items = fetch_typeform(WELCOME_FORM_ID)
        for i, item in enumerate(items):
            answers = item.get("answers", [])
            email = get_field(answers, WELCOME_EMAIL_FIELD)
            date  = get_field(answers, WELCOME_DATE_FIELD)
            
            if not email:
                skipped.append({"form": "welcome", "reason": "missing email", "index": i})
                continue
            if not date:
                skipped.append({"form": "welcome", "reason": "missing date", "email": email, "index": i})
                continue
            
            date = str(date)[:10]
            try:
                d = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
            except ValueError:
                skipped.append({"form": "welcome", "reason": f"invalid date format: {date}", "email": email, "index": i})
                continue
            
            if d < NOW:
                skipped.append({"form": "welcome", "reason": f"past date: {date}", "email": email, "index": i})
                continue
            if d > HORIZON:
                skipped.append({"form": "welcome", "reason": f"beyond 180-day horizon: {date}", "email": email, "index": i})
                continue
            
            email = email.lower().strip()
            if email not in students or date < students[email]["date"]:
                students[email] = {"email": email, "date": date, "name": None}
        
        print(f"Welcome form: {len(students)} future entries")
        if skipped:
            print(f"  (Skipped {len([s for s in skipped if s['form'] == 'welcome'])} submissions from welcome form)")
    except Exception as e:
        print(f"Warning: welcome form fetch failed: {e}")

    # Exam date form (overrides if more recent)
    try:
        items = fetch_typeform(EXAM_FORM_ID)
        for i, item in enumerate(items):
            answers = item.get("answers", [])
            email = get_field(answers, EXAM_EMAIL_FIELD)
            date  = get_field(answers, EXAM_DATE_FIELD)
            
            if not email:
                skipped.append({"form": "exam", "reason": "missing email", "index": i})
                continue
            if not date:
                skipped.append({"form": "exam", "reason": "missing date", "email": email, "index": i})
                continue
            
            date = str(date)[:10]
            try:
                d = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
            except ValueError:
                skipped.append({"form": "exam", "reason": f"invalid date format: {date}", "email": email, "index": i})
                continue
            
            if d < NOW:
                skipped.append({"form": "exam", "reason": f"past date: {date}", "email": email, "index": i})
                continue
            if d > HORIZON:
                skipped.append({"form": "exam", "reason": f"beyond 180-day horizon: {date}", "email": email, "index": i})
                continue
            
            email = email.lower().strip()
            students[email] = {"email": email, "date": date, "name": None}
        
        print(f"After exam date form merge: {len(students)} total")
        if skipped:
            print(f"  (Skipped {len([s for s in skipped if s['form'] == 'exam'])} submissions from exam form)")
    except Exception as e:
        print(f"Warning: exam date form fetch failed: {e}")
    
    # Report skipped submissions
    if skipped:
        print(f"\n⚠️  SKIPPED SUBMISSIONS ({len(skipped)} total):")
        for s in skipped:
            email_str = f" · {s.get('email', 'N/A')}" if s.get('email') else ""
            print(f"  - {s['form'].upper()}: {s['reason']}{email_str}")
        print()

    # Enrich names from Kit
    for email, s in students.items():
        name = kit_name(email)
        s["name"] = name or email.split("@")[0].replace(".", " ").title()

    result = sorted(students.values(), key=lambda x: x["date"])
    return result, skipped


def inject_into_html(students, skipped):
    template_path = os.path.join(SCRIPT_DIR, "exams-template.html")
    with open(template_path, "r") as f:
        html = f.read()

    generated_time = datetime.now(tz=ET).strftime("%b %d, %Y at %I:%M %p ET")
    data_json = json.dumps(students, indent=2)

    # Replace placeholders
    html = html.replace("PLACEHOLDER_EXAM_JSON", data_json)
    html = html.replace("PLACEHOLDER_GENERATED_TIME", generated_time)

    out_path = os.path.join(SCRIPT_DIR, "exams.html")
    with open(out_path, "w") as f:
        f.write(html)
    print(f"Written: {out_path}")
    print(f"Generated at: {generated_time}")
    print(f"Students: {len(students)}")
    
    # Alert if any submissions were skipped
    if skipped:
        print(f"\n⚠️  ALERT: {len(skipped)} submission(s) skipped during build")
        return False
    return True


if __name__ == "__main__":
    print("Fetching student exam dates…")
    students, skipped = build_students()
    success = inject_into_html(students, skipped)
    if not success:
        exit(1)
    print("Done.")
