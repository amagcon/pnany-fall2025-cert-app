# test_supabase.py
import os
from supabase import create_client
import json

SUPABASE_URL = os.environ.get("SUPABASE_URL") or "https://YOUR-PROJECT.supabase.co"
SUPABASE_ANON = os.environ.get("SUPABASE_ANON") or "YOUR_ANON_PUBLIC_KEY"

sb = create_client(SUPABASE_URL, SUPABASE_ANON)

probe = {
    "name": "Health Check",
    "email": "healthcheck@example.com",
    "license": None,
    "session_ratings": {"ping": True},
    "comments": "debug insert",
    "quiz_score": 0,
    "passed": False,
    "course_title": "HealthCheck",
    "course_date": "N/A",
    "credit_hours": 0
}

try:
    res = sb.table("evaluations").insert(probe).execute()
    print("Insert response:", res.data)
except Exception as e:
    print("Insert FAILED:", e)
