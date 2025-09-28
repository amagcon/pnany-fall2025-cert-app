# app.py
import os, io, csv, json, uuid
from datetime import datetime

import streamlit as st
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors

# ====== Google Sheets deps ======
import gspread
from google.oauth2.service_account import Credentials

# =========================
# Streamlit Config
# =========================

st.image("https://drive.google.com/file/d/1bNQ52mcvyWl06nUp2QDjnx5q_aYTKxeh/view?usp=drive_link", width=250)
st.set_page_config(
    page_title="PNANY Fall Conference 2025 — Evaluation, Post-test, & Certificate",
    page_icon="🎓",
    layout="centered",
)

# =========================
# Settings (from secrets)
# =========================
COURSE = st.secrets.get("course", {})
ORG_NAME     = COURSE.get("org_name", "The Philippine Nurses Association of New York, Inc.")
COURSE_TITLE = COURSE.get("course_title", "Lead to INSPIRE Fall Conference 2025 — Gabay at Galing: Empowering the New Generation of Nurse Leaders")
COURSE_DATE  = COURSE.get("course_date", "October 18, 2025")
CREDIT_HOURS = float(COURSE.get("credit_hours", 4.75))
PASSING_SCORE= int(COURSE.get("passing_score", 75))

SHEETS = st.secrets.get("sheets", {})
SHEET_ID = SHEETS.get("sheet_id", "")
EVAL_TAB = SHEETS.get("eval_tab", "EvalandPT")
CERT_TAB = SHEETS.get("cert_tab", "Certificates")

# Local CSV backup folder
SAVE_DIR = "data"
os.makedirs(SAVE_DIR, exist_ok=True)

# =========================
# Load quiz (JSON-driven)
# =========================
with open("questions.json", "r", encoding="utf-8") as f:
    QUIZ = json.load(f)

# =========================
# Google Sheets helpers
# =========================
SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
GS_CREDS = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SHEETS_SCOPES,
)
GSPREAD_CLIENT = gspread.authorize(GS_CREDS)

def sheets_append_dict(sheet_id: str, tab_name: str, row_dict: dict):
    """
    Append a dict to a worksheet by matching column names.
    - Creates the worksheet if missing.
    - Adds any new columns found in row_dict (appended at the end).
    - Preserves existing header order and aligns values by header name.
    """
    sh = GSPREAD_CLIENT.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        header = list(row_dict.keys())
        ws = sh.add_worksheet(title=tab_name, rows=1000, cols=max(len(header), 1))
        ws.append_row(header, value_input_option="USER_ENTERED")

    # Current header
    header = ws.row_values(1) or []
    header_set = set(h.strip() for h in header)

    # Add new columns (found in row_dict but missing in header)
    new_cols = [k for k in row_dict.keys() if k not in header_set]
    if new_cols:
        header_extended = header + new_cols
        ws.resize(rows=ws.row_count, cols=len(header_extended))
        ws.update('1:1', [header_extended])
        header = header_extended

    # Align row values to header order
    row_vals = [row_dict.get(col, "") for col in header]
    ws.append_row(row_vals, value_input_option="USER_ENTERED")

def save_eval_to_sheets(row_enriched: dict):
    # Normalize multi-line text and keep a payload snapshot
    row_enriched = dict(row_enriched)
    row_enriched["topics_interest"] = (row_enriched.get("topics_interest") or "").replace("\n", " ")
    row_enriched["comments"]        = (row_enriched.get("comments") or "").replace("\n", " ")
    row_enriched["payload_json"]    = json.dumps(row_enriched, ensure_ascii=False)
    sheets_append_dict(SHEET_ID, EVAL_TAB, row_enriched)

def save_cert_to_sheets(cert_row: dict):
    cert_row = dict(cert_row)
    cert_row.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
    sheets_append_dict(SHEET_ID, CERT_TAB, cert_row)

# =========================
# Other helpers
# =========================
def make_certificate_pdf(full_name: str, email: str, score_pct: float, cert_id: str) -> bytes:
    """Generate a landscape Letter certificate PDF and return bytes."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)

    # Optional background image at assets/cert_bg.png
    bg_path = "assets/cert_bg.png"
    if os.path.exists(bg_path):
        try:
            c.drawImage(ImageReader(bg_path), 0, 0, width=width, height=height,
                        preserveAspectRatio=True, anchor="c")
        except Exception as e:
            st.warning(f"Background image found but could not be drawn: {e}")

    # Title
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(width/2, height/2 + 95, "Certificate of Completion")

    # Name
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width/2, height/2 + 55, full_name)

    # Body
    c.setFont("Helvetica", 13)
    body = (
        f"has successfully completed the Philippine Nurses Association of New York, Inc. webinar "
        f"“{COURSE_TITLE}” on {COURSE_DATE} and passed the post-test with a score of "
        f"{round(score_pct)}%. Credits awarded: {CREDIT_HOURS} contact hour(s)."
    )
    import textwrap
    y = height/2 + 18
    for line in textwrap.wrap(body, 100):
        c.drawCentredString(width/2, y, line)
        y -= 16

    # Cert ID & issued date
    issued_on = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.setFont("Helvetica", 9)
    c.drawRightString(width - 60, 72, f"Certificate ID: {cert_id}")
    c.drawRightString(width - 60, 58, f"Issued on: {issued_on}")

    c.showPage()
    c.save()
    return buffer.getvalue()

def save_row_to_csv(path: str, row: dict):
    """Append a row to CSV for local backup."""
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=row.keys())
        if new:
            w.writeheader()
        w.writerow(row)

# =========================
# UI
# =========================
st.title("🎓 PNANY Fall 2025 — Evaluation & Post-Test")
st.caption("Complete the evaluation and post-test. On passing (≥ 75%), your certificate will be generated.")

# ---- 1) Participant info ----
with st.form("info"):
    c1, c2 = st.columns(2)
    with c1:
        full_name = st.text_input("Full Name *")
    with c2:
        email = st.text_input("Email *")

    cA, cB = st.columns(2)
    with cA:
        job_title = st.text_input("Role / Job Title")  # NEW
    with cB:
        institution_name = st.text_input("Institution / Facility Name")  # NEW

    c3, c4, c5 = st.columns(3)
    with c3:
        location_city = st.text_input("City")
    with c4:
        location_state = st.text_input("State/Province")
    with c5:
        location_country = st.text_input("Country")

    c6, c7 = st.columns(2)
    with c6:
        role = st.selectbox("Role / Credentials", ["RN", "APRN", "NP", "PA", "Student", "Other"])
    with c7:
        member_status = st.selectbox("PNANY Member Status", ["Member", "Non-member", "Inactive"])

    contact_opt_in = st.checkbox(
        "I’d like to be contacted about future PNANY professional development, membership, and other activities."
    )

    attendance = st.checkbox(
        "I certify that I attended and completed the Lead to INSPIRE Fall Conference: "
        "Gabay at Galing: Empowering the New Generation of Nurse Leaders, held online on October 18, 2025."
    )
    cont = st.form_submit_button("Continue ➡️")

if cont:
    if not full_name or not email or not attendance:
        st.error("Please complete name, email, and confirm attendance.")
    else:
        st.session_state["participant_ok"] = True
        st.success("Thanks! Continue below.")

# ---- 2) Evaluation ----
if st.session_state.get("participant_ok"):
    st.subheader("📊 Course Evaluation")

    LIKERT = ["Strongly agree", "Agree", "Undecided", "Disagree", "Strongly disagree"]
    LIKERT_MAP = {"Strongly agree":5, "Agree":4, "Undecided":3, "Disagree":2, "Strongly disagree":1}
    BOOL = lambda b: "Yes" if bool(b) else "No"

    def L(label):
        return st.select_slider(label, options=LIKERT, value="Strongly agree")

    ev_org = L("Was well organized")
    ev_ad  = L("Was consistent with flyer advertising event")
    ev_rel = L("Was relevant to learning outcomes of presentation")
    ev_virt= L("Effectively used virtual teaching method")
    ev_obj = L("Enabled me to meet my personal objectives")

    st.markdown("**Overall Satisfaction**")
    overall_prog = st.selectbox(
        "Overall satisfaction of the program",
        ["Excellent", "Good", "Undecided", "Unlikely", "Very Unlikely"], index=0
    )
    overall_rec  = st.selectbox(
        "Likelihood to recommend to colleagues",
        ["Excellent", "Good", "Undecided", "Unlikely", "Very Unlikely"], index=0
    )
    overall_zoom = st.selectbox(
        "Satisfaction with method of presentation (ZOOM)",
        ["Excellent", "Good", "Undecided", "Unlikely", "Very Unlikely"], index=0
    )

    lo_met = L("Were Activity Learning Outcomes Met? At least 80% of attendees will pass a post-test with a score of 75% or higher.")

    st.markdown("**Speaker teaching effectiveness** *(1 = Poor, 5 = Excellent)*")
    speaker_fields = [
        ("q4_speaker_yap",        "Wilfredo Yap Jr., DNP, RN, AMB-BC, CENP, NEA-BC"),
        ("q4_speaker_sagar",      "Priscilla L. Sagar, EdD, RN, ACNS-BC, CTN-A, FNYAM, FTNSS, FAAN"),
        ("q4_speaker_velasquez",  "Joana Velasquez, PhD, RN, CNOR"),
        ("q4_speaker_pastoral",   "Gizelle Pastoral, MS, RN, NI-BC"),
        ("q4_speaker_santarina",  "Maia Santarina, BSN, RN"),
        ("q4_speaker_planillo",   "Jose Mapalad M. Planillo, RN, MSN, MBA, HCM, CCRN, CAPA, CPE"),
        ("q4_speaker_florendo",   "Camille Dolly Marie D. Florendo, BSN, RN"),
        ("q4_speaker_jomoc",      "Cristy Ellen Jomoc, MN, RN, MEDSURG-BC, PCCN"),
        ("q4_speaker_oliverio",   "Ebeneza P. Oliverio, MSN, RN"),
        ("q4_speaker_temprosa",   "Clifford Robin Temprosa Li, KOR, BS"),
        ("q4_speaker_bedona",     "Mariel Joy Bedona, BSN, RN"),
        ("q4_speaker_agcon",      "Aubrey May Agcon, MSN, RN"),
    ]
    speaker_ratings = {}
    for key, label in speaker_fields:
        speaker_ratings[key] = st.select_slider(label, options=["1", "2", "3", "4", "5"], value="5")

    st.markdown("**This activity will assist in improvement of (check all that apply):**")
    imp_knowledge   = st.checkbox("Knowledge")
    imp_skills      = st.checkbox("Skills")
    imp_competence  = st.checkbox("Competence")
    imp_performance = st.checkbox("Performance")
    imp_outcomes    = st.checkbox("Patient Outcomes")

    fair_balanced       = st.radio("Do you feel this content was fair and balanced?", ["Yes", "No"], index=0)
    commercial_support  = st.radio("Did this presentation have any commercial support?", ["Yes", "No"], index=1)
    commercial_bias     = st.radio("If yes, did the speaker demonstrate any commercial bias?", ["N/A", "Yes", "No"], index=0)
    bias_explain        = st.text_input("If yes, explain", "")

    st.markdown("**Practice change**")
    pc_values   = st.checkbox("Reflect on and adopt values that elevate nurses to heroes")
    pc_joy      = st.checkbox("Employ ways to instill and sustain the joy of practice in nursing and healthcare")
    pc_health   = st.checkbox("Utilize ways to address healthcare issues of Filipino Americans in NY")
    pc_other    = st.text_input("Other (please specify)", "")
    beneficial_topic = st.text_input("Which program topic was most beneficial to you?")

    topics_interest = st.text_area("What topics of interest would you like us to provide?")
    comments        = st.text_area("Comments")

    # ---- 3) Post-Test ----
    st.subheader(f"📝 Post-Test ({len(QUIZ)} items)")
    answers = {}
    for i, q in enumerate(QUIZ, start=1):
        st.markdown(f"**Q{i}. {q['question']}**")
        answers[str(i)] = st.radio(
            f"Answer Q{i}", q["options"], index=None, key=f"q{i}", label_visibility="collapsed"
        )
        st.divider()

    # ---- Submit ----
    if st.button("Submit Evaluation & Generate Certificate"):
        # Validate quiz completion
        if any(answers[str(i)] is None for i in range(1, len(QUIZ) + 1)):
            st.error("Please answer all post-test questions.")
            st.stop()

        # Compute score
        correct = sum(1 for i, q in enumerate(QUIZ, start=1) if answers[str(i)] == q["answer"])
        total = len(QUIZ)
        score_pct = 100 * correct / total
        passed = score_pct >= PASSING_SCORE

        # Big pass/fail badge
        if passed:
            st.markdown(
                f"""
                <div style="padding:16px;border-radius:12px;background:#ECFDF5;border:1px solid #34D399;">
                  <div style="font-size:28px;line-height:1.2;margin-bottom:6px;">✅ <strong>{score_pct:.0f}%</strong></div>
                  <div style="font-size:16px;">Your score: <strong>{correct}/{total}</strong> — Passing score is {PASSING_SCORE}%</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div style="padding:16px;border-radius:12px;background:#FEF2F2;border:1px solid #F87171;">
                  <div style="font-size:28px;line-height:1.2;margin-bottom:6px;">❌ <strong>{score_pct:.0f}%</strong></div>
                  <div style="font-size:16px;">Your score: <strong>{correct}/{total}</strong> — Passing score is {PASSING_SCORE}%</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        cert_id = str(uuid.uuid4())

        # Build row for CSV + Sheets (header-aware writer will align)
        row = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "full_name": full_name,
            "email": email,

            # Attendee demographics
            "role": role,                           # credentials (RN/APRN/etc.)
            "job_title": job_title,                 # NEW
            "institution_name": institution_name,   # NEW
            "attendance": "Yes" if attendance else "No",
            "location_city": location_city,
            "location_state": location_state,
            "location_country": location_country,
            "member_status": member_status,
            "contact_opt_in": BOOL(contact_opt_in),

            # Evaluation (Likert - text)
            "ev_org": ev_org,
            "ev_ad": ev_ad,
            "ev_rel": ev_rel,
            "ev_virt": ev_virt,
            "ev_obj": ev_obj,
            "lo_met": lo_met,

            # Evaluation numeric mirrors (for averages)
            "ev_org_num":  LIKERT_MAP.get(ev_org, ""),
            "ev_ad_num":   LIKERT_MAP.get(ev_ad, ""),
            "ev_rel_num":  LIKERT_MAP.get(ev_rel, ""),
            "ev_virt_num": LIKERT_MAP.get(ev_virt, ""),
            "ev_obj_num":  LIKERT_MAP.get(ev_obj, ""),

            # Overall ratings
            "overall_prog": overall_prog,
            "overall_rec":  overall_rec,
            "overall_zoom": overall_zoom,

            # Free text
            "beneficial_topic": beneficial_topic,
            "topics_interest": topics_interest.replace("\n", " "),
            "comments": comments.replace("\n", " "),

            # Quiz summary
            "quiz_score": correct,
            "quiz_total": total,
            "quiz_pct": f"{score_pct:.0f}",
            "quiz_passed": BOOL(passed),

            # Pass/Cert linkage
            "score_pct": f"{score_pct:.0f}",
            "passed": passed,
            "cert_id": cert_id,
        }

        # Speaker ratings (1..5)
        row.update({
            "speaker_yap":        speaker_ratings.get("q4_speaker_yap", ""),
            "speaker_sagar":      speaker_ratings.get("q4_speaker_sagar", ""),
            "speaker_velasquez":  speaker_ratings.get("q4_speaker_velasquez", ""),
            "speaker_pastoral":   speaker_ratings.get("q4_speaker_pastoral", ""),
            "speaker_santarina":  speaker_ratings.get("q4_speaker_santarina", ""),
            "speaker_planillo":   speaker_ratings.get("q4_speaker_planillo", ""),
            "speaker_florendo":   speaker_ratings.get("q4_speaker_florendo", ""),
            "speaker_jomoc":      speaker_ratings.get("q4_speaker_jomoc", ""),
            "speaker_oliverio":   speaker_ratings.get("q4_speaker_oliverio", ""),
            "speaker_temprosa":   speaker_ratings.get("q4_speaker_temprosa", ""),
            "speaker_bedona":     speaker_ratings.get("q4_speaker_bedona", ""),
            "speaker_agcon":      speaker_ratings.get("q4_speaker_agcon", ""),
        })

        # Improvement + bias + practice change
        row.update({
            "improve_knowledge":   BOOL(imp_knowledge),
            "improve_skills":      BOOL(imp_skills),
            "improve_competence":  BOOL(imp_competence),
            "improve_performance": BOOL(imp_performance),
            "improve_outcomes":    BOOL(imp_outcomes),

            "fair_balanced":       fair_balanced,
            "commercial_support":  commercial_support,
            "commercial_bias":     commercial_bias,
            "bias_explain":        bias_explain,

            "pc_values": BOOL(pc_values),
            "pc_joy":    BOOL(pc_joy),
            "pc_health": BOOL(pc_health),
            "pc_other":  pc_other,
        })

        # CSV backup (optional)
        save_row_to_csv(os.path.join(SAVE_DIR, "submissions.csv"), row)

        # Save to Google Sheets (evaluations)
        try:
            save_eval_to_sheets(row)
            st.success("Saved to Google Sheets ✅")
        except Exception as e:
            st.error(f"Could not save to Google Sheets (evaluations): {e}")

        # If not passed, stop here
        if not passed:
            st.error("You did not reach the passing score. You may review content and retake the post-test.")
            st.stop()

        # Passed → certificate
        pdf_bytes = make_certificate_pdf(full_name, email, score_pct, cert_id)

        # Save certificate metadata to Google Sheets
        cert_row = {
            "cert_id": cert_id,
            "name": full_name,
            "email": email,
            "course_title": COURSE_TITLE,
            "course_date": COURSE_DATE,
            "credit_hours": CREDIT_HOURS,
        }
        try:
            save_cert_to_sheets(cert_row)
        except Exception as e:
            st.warning(f"Certificate recorded locally only (Sheets issue): {e}")

        st.success("🎉 Congratulations! You passed and your certificate is ready.")
        st.download_button(
            "⬇️ Download Certificate (PDF)",
            data=pdf_bytes,
            file_name=f"Certificate_{full_name.replace(' ', '_')}.pdf",
            mime="application/pdf",
        )
