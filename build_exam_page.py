#!/usr/bin/env python3
"""
Build exam-lookahead data and inject it into exams.html.
Fetches from both Typeform forms (same logic as exam_good_luck_scheduler_final.py).
Run by the weekly cron or on-demand.
"""
import os, json, re, requests
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

TYPEFORM_TOKEN      = open(os.path.expanduser(
    "~/.openclaw/workspace/office-hours-config.json")).read()
TYPEFORM_TOKEN      = json.loads(TYPEFORM_TOKEN).get("typeform_token", "")

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

    # Welcome form
    try:
        items = fetch_typeform(WELCOME_FORM_ID)
        for item in items:
            answers = item.get("answers", [])
            email = get_field(answers, WELCOME_EMAIL_FIELD)
            date  = get_field(answers, WELCOME_DATE_FIELD)
            if not email or not date:
                continue
            date = str(date)[:10]
            try:
                d = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if d < NOW or d > HORIZON:
                continue
            email = email.lower().strip()
            if email not in students or date < students[email]["date"]:
                students[email] = {"email": email, "date": date, "name": None}
        print(f"Welcome form: {len(students)} future entries")
    except Exception as e:
        print(f"Warning: welcome form fetch failed: {e}")

    # Exam date form (overrides if more recent)
    try:
        items = fetch_typeform(EXAM_FORM_ID)
        for item in items:
            answers = item.get("answers", [])
            email = get_field(answers, EXAM_EMAIL_FIELD)
            date  = get_field(answers, EXAM_DATE_FIELD)
            if not email or not date:
                continue
            date = str(date)[:10]
            try:
                d = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if d < NOW or d > HORIZON:
                continue
            email = email.lower().strip()
            students[email] = {"email": email, "date": date, "name": None}
        print(f"After exam date form merge: {len(students)} total")
    except Exception as e:
        print(f"Warning: exam date form fetch failed: {e}")

    # Enrich names from Kit
    for email, s in students.items():
        name = kit_name(email)
        s["name"] = name or email.split("@")[0].replace(".", " ").title()

    result = sorted(students.values(), key=lambda x: x["date"])
    return result


def inject_into_html(students):
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


if __name__ == "__main__":
    print("Fetching student exam dates…")
    students = build_students()
    inject_into_html(students)
    print("Done.")
