# app.py
import os, io, csv, json, uuid
from datetime import datetime

import streamlit as st
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors

from supabase_client import get_supabase

# ---------- Streamlit Config ----------
st.set_page_config(
    page_title="PNANY Fall 2025 — Evaluation & Certificate",
    page_icon="🎓",
    layout="centered",
)

# ---------- Settings ----------
COURSE = st.secrets.get("course", {})
ORG_NAME     = COURSE.get("org_name", "The Philippine Nurses Association of New York, Inc.")
COURSE_TITLE = COURSE.get("course_title", "Lead to INSPIRE Fall Conference 2025 — Gabay at Galing: Empowering the New Generation of Nurse Leaders")
COURSE_DATE  = COURSE.get("course_date", "October 18, 2025")
CREDIT_HOURS = float(COURSE.get("credit_hours", 4.75))
PASSING_SCORE= int(COURSE.get("passing_score", 75))

SAVE_DIR = "data"
os.makedirs(SAVE_DIR, exist_ok=True)

STORAGE      = st.secrets.get("storage", {})
USE_STORAGE  = bool(STORAGE.get("bucket"))
BUCKET_NAME  = STORAGE.get("bucket", "certificates")
PUBLIC_URLS  = bool(STORAGE.get("public_urls", True))

# ---------- Load quiz ----------
with open("questions.json", "r", encoding="utf-8") as f:
    QUIZ = json.load(f)

# ---------- PDF generation ----------
def make_certificate_pdf(full_name: str, email: str, score_pct: float, cert_id: str) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)

    # Optional background: assets/cert_bg.png
    bg_path = "assets/cert_bg.png"
    if os.path.exists(bg_path):
        try:
            c.drawImage(ImageReader(bg_path), 0, 0, width=width, height=height, preserveAspectRatio=True, anchor="c")
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
        f"“{COURSE_TITLE}” on {COURSE_DATE} and passed the post-test."
        #f"{round(score_pct)}%. Credits awarded: {CREDIT_HOURS} contact hour(s)."
    )
    import textwrap
    y = height/2 + 18
    for line in textwrap.wrap(body, 100):
        c.drawCentredString(width/2, y, line)
        y -= 16

    issued_on = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.setFont("Helvetica", 9)
    c.drawRightString(width - 60, 72, f"Certificate ID: {cert_id}")
    c.drawRightString(width - 60, 58, f"Issued on: {issued_on}")

    c.showPage()
    c.save()
    return buffer.getvalue()

# ---------- Local CSV backup ----------
def save_row_to_csv(path, row):
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=row.keys())
        if new:
            w.writeheader()
        w.writerow(row)

# ---------- Supabase helpers ----------
def sb_insert(table: str, payload: dict):
    return get_supabase().table(table).insert(payload).execute()

def upload_to_storage(file_bytes: bytes, path: str) -> str:
    sb = get_supabase()
    # idempotent replace
    try:
        sb.storage.from_(BUCKET_NAME).remove([path])
    except Exception:
        pass
    sb.storage.from_(BUCKET_NAME).upload(path=path, file=file_bytes, file_options={"content-type": "application/pdf"})
    if PUBLIC_URLS:
        return sb.storage.from_(BUCKET_NAME).get_public_url(path)
    else:
        signed = sb.storage.from_(BUCKET_NAME).create_signed_url(path, 7 * 24 * 3600)
        return signed.get("signedURL")

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
    role = st.selectbox("Role / Credentials", ["RN", "APRN", "NP", "PA", "Student", "Other"])
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
    likert = ["Strongly agree", "Agree", "Undecided", "Disagree", "Strongly disagree"]
    def L(label): return st.select_slider(label, options=likert, value="Strongly agree")

    ev_org = L("Was well organized")
    ev_ad  = L("Was consistent with flyer advertising event")
    ev_rel = L("Was relevant to learning outcomes of presentation")
    ev_virt= L("Effectively used virtual teaching method")
    ev_obj = L("Enabled me to meet my personal objectives")

    st.markdown("**Overall Satisfaction**")
    overall_prog = st.selectbox("Overall satisfaction of the program", ["Excellent","Good","Undecided","Unlikely","Very Unlikely"], index=0)
    overall_rec  = st.selectbox("Likelihood to recommend to colleagues", ["Excellent","Good","Undecided","Unlikely","Very Unlikely"], index=0)
    overall_zoom = st.selectbox("Satisfaction with method of presentation (ZOOM)", ["Excellent","Good","Undecided","Unlikely","Very Unlikely"], index=0)

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
        speaker_ratings[key] = st.select_slider(label, options=["1","2","3","4","5"], value="5")

    st.markdown("**This activity will assist in improvement of (check all that apply):**")
    imp_knowledge   = st.checkbox("Knowledge")
    imp_skills      = st.checkbox("Skills")
    imp_competence  = st.checkbox("Competence")
    imp_performance = st.checkbox("Performance")
    imp_outcomes    = st.checkbox("Patient Outcomes")

    fair_balanced       = st.radio("Do you feel this content was fair and balanced?", ["Yes","No"], index=0)
    commercial_support  = st.radio("Did this presentation have any commercial support?", ["Yes","No"], index=1)
    commercial_bias     = st.radio("If yes, did the speaker demonstrate any commercial bias?", ["N/A","Yes","No"], index=0)
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
        if any(answers[str(i)] is None for i in range(1, len(QUIZ) + 1)):
            st.error("Please answer all post-test questions.")
            st.stop()

        correct = sum(1 for i, q in enumerate(QUIZ, start=1) if answers[str(i)] == q["answer"])
        total = len(QUIZ)
        score_pct = 100 * correct / total
        passed = score_pct >= PASSING_SCORE
        st.info(f"Your score: **{correct}/{total} ({score_pct:.0f}%)**. Passing score is {PASSING_SCORE}%.")

        cert_id = str(uuid.uuid4())

        # CSV backup row
        row = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "full_name": full_name,
            "email": email,
            "role": role,
            "attendance": "Yes" if attendance else "No",

            "ev_org": ev_org, "ev_ad": ev_ad, "ev_rel": ev_rel, "ev_virt": ev_virt, "ev_obj": ev_obj,
            "overall_prog": overall_prog, "overall_rec": overall_rec, "overall_zoom": overall_zoom,
            "lo_met": lo_met,

            "q4_speaker_yap":       speaker_ratings.get("q4_speaker_yap"),
            "q4_speaker_sagar":     speaker_ratings.get("q4_speaker_sagar"),
            "q4_speaker_velasquez": speaker_ratings.get("q4_speaker_velasquez"),
            "q4_speaker_pastoral":  speaker_ratings.get("q4_speaker_pastoral"),
            "q4_speaker_santarina": speaker_ratings.get("q4_speaker_santarina"),
            "q4_speaker_planillo":  speaker_ratings.get("q4_speaker_planillo"),
            "q4_speaker_florendo":  speaker_ratings.get("q4_speaker_florendo"),
            "q4_speaker_jomoc":     speaker_ratings.get("q4_speaker_jomoc"),
            "q4_speaker_oliverio":  speaker_ratings.get("q4_speaker_oliverio"),
            "q4_speaker_temprosa":  speaker_ratings.get("q4_speaker_temprosa"),
            "q4_speaker_bedona":    speaker_ratings.get("q4_speaker_bedona"),
            "q4_speaker_agcon":     speaker_ratings.get("q4_speaker_agcon"),

            "improve_knowledge": imp_knowledge,
            "improve_skills": imp_skills,
            "improve_competence": imp_competence,
            "improve_performance": imp_performance,
            "improve_outcomes": imp_outcomes,

            "fair_balanced": fair_balanced, "commercial_support": commercial_support,
            "commercial_bias": commercial_bias, "bias_explain": bias_explain,

            "pc_values": pc_values, "pc_joy": pc_joy, "pc_health": pc_health, "pc_other": pc_other,
            "beneficial_topic": beneficial_topic,

            "topics_interest": topics_interest.replace("\n", " "),
            "comments": comments.replace("\n", " "),
            "score_pct": f"{score_pct:.0f}",
            "passed": passed,
            "cert_id": cert_id,
        }
        save_row_to_csv(os.path.join(SAVE_DIR, "submissions.csv"), row)

        # Save to Supabase (evaluations)
        payload = {
            "name": full_name,
            "email": email,
            "license": None,
            "session_ratings": {
                "ev_org": ev_org,
                "ev_ad": ev_ad,
                "ev_rel": ev_rel,
                "ev_virt": ev_virt,
                "ev_obj": ev_obj,
                "overall_prog": overall_prog,
                "overall_rec": overall_rec,
                "overall_zoom": overall_zoom,
                "lo_met": lo_met,
                "speakers": speaker_ratings,
                "improvements": {
                    "knowledge": imp_knowledge,
                    "skills": imp_skills,
                    "competence": imp_competence,
                    "performance": imp_performance,
                    "outcomes": imp_outcomes
                },
                "fair_balanced": fair_balanced,
                "commercial_support": commercial_support,
                "commercial_bias": commercial_bias,
                "bias_explain": bias_explain,
                "practice_change": {
                    "values": pc_values,
                    "joy": pc_joy,
                    "health": pc_health,
                    "other": pc_other
                },
                "beneficial_topic": beneficial_topic,
                "topics_interest": topics_interest,
                "comments": comments
            },
            "quiz_score": float(f"{score_pct:.0f}"),
            "passed": passed,
            "course_title": COURSE_TITLE,
            "course_date": COURSE_DATE,
            "credit_hours": CREDIT_HOURS
        }
        try:
            sb_insert("evaluations", payload)
        except Exception as e:
            st.warning(f"Saved locally; Supabase insert failed: {e}")

        if not passed:
            st.error("You did not reach the passing score. You may review content and retake the post-test.")
            st.stop()

        # Passed → certificate
        pdf_bytes = make_certificate_pdf(full_name, email, score_pct, cert_id)
        storage_url = None
        if USE_STORAGE:
            year = datetime.utcnow().strftime("%Y")
            path = f"CERTS/{year}/{cert_id}.pdf"
            try:
                storage_url = upload_to_storage(pdf_bytes, path)
            except Exception as e:
                st.warning(f"Certificate generated but could not upload to storage: {e}")

        cert_row = {
            "cert_id": cert_id,
            "name": full_name,
            "email": email,
            "course_title": COURSE_TITLE,
            "course_date": COURSE_DATE,
            "credit_hours": CREDIT_HOURS,
            "issuer": COURSE.get("issuer", "PNAA Accredited Provider Unit (P0613)"),
            "signature_name": COURSE.get("signature_name", "Ninotchka Rosete, PhD, RN-BC"),
            "signature_title": COURSE.get("signature_title", "Director, PNAA Accredited Provider Unit"),
            "storage_path": f"CERTS/{datetime.utcnow().strftime('%Y')}/{cert_id}.pdf" if storage_url else None
        }
        try:
            sb_insert("certificates", cert_row)
        except Exception as e:
            st.warning(f"Certificate recorded locally only (DB insert issue): {e}")

        st.success("🎉 Congratulations! You passed and your certificate is ready.")
        st.download_button(
            "⬇️ Download Certificate (PDF)",
            data=pdf_bytes,
            file_name=f"Certificate_{full_name.replace(' ', '_')}.pdf",
            mime="application/pdf",
        )
        if storage_url:
            st.link_button("Open Certificate Link", storage_url)

# ============ OPTIONAL: simple admin view (toggle on when needed) ============
with st.expander("🔐 Admin: View submissions (Supabase)"):
    try:
        res = get_supabase().table("evaluations").select("*").order("created_at", desc=True).execute()
        import pandas as pd
        df = pd.DataFrame(res.data or [])
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.info("Admin view unavailable (check Supabase credentials/policies).")
