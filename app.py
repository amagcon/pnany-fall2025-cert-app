# app.py
import streamlit as st
from datetime import datetime
import uuid, csv, os, io, json

st.write("Secrets keys loaded:", list(st.secrets.keys()))


# Page config MUST be the first Streamlit command
st.set_page_config(page_title="PNANY Fall 2025 — Evaluation & Certificate", page_icon="🎓", layout="centered")

# =========================
# SETTINGS (edit these)
# =========================
ORG_NAME = "The Philippine Nurses Association of New York, Inc."
COURSE_TITLE = "Lead to INSPIRE Fall Conference 2025 — Gabay at Galing: Empowering the New Generation of Nurse Leaders"
COURSE_DATE = "October 18, 2025"
CREDIT_HOURS = 4.75
PASSING_SCORE = 75  # percent; >= passes
CERT_ISSUER = "PNAA Accredited Provider Unit (P0613)"
CERT_SIGNATURE_NAME = "Ninotchka Brydges, PhD, DNP, MBA, APRN, ACNP-BC, FNAP, FAAN"
CERT_SIGNATURE_TITLE = "PNAA Accredited Provider Program Director"
# Set this when you publish a verify endpoint (e.g., Apps Script URL + '?cert_id=')
CERT_VERIFY_BASE_URL = "https://example.org/verify?cert_id="

SAVE_DIR = "data"
os.makedirs(SAVE_DIR, exist_ok=True)

# Optional quick secrets check (AFTER set_page_config)
if "gcp_service_account" in st.secrets:
    st.caption("✅ Found gcp_service_account in Secrets")
else:
    st.caption("ℹ️ Add [gcp_service_account] to Secrets to enable Google Sheets logging.")

# Optional: show which sheet we’ll log to (non-sensitive)
if "SHEET_ID" in st.secrets:
    st.caption("Using Google Sheet ID (SHEET_ID) from Secrets.")


# =========================
# LOAD QUIZ (questions.json at repo root)
# =========================
with open("questions.json", "r", encoding="utf-8") as f:
    QUIZ = json.load(f)

# =========================
# PDF GENERATION
# =========================
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from PIL import Image  # noqa: F401  (required for qrcode PIL backend)
import qrcode

def make_certificate_pdf(full_name: str, email: str, score_pct: float, cert_id: str) -> bytes:
    buffer = io.BytesIO()
    # Landscape letter
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)  # ~792 x 612 points

    # OPTIONAL: full-page background at assets/cert_bg.png
    bg_path = "assets/cert_bg.png"
    if os.path.exists(bg_path):
        try:
            c.drawImage(ImageReader(bg_path), 0, 0, width=width, height=height,
                        preserveAspectRatio=True, anchor="c")
        except Exception as e:
            st.warning(f"Background image found but could not be drawn: {e}")

    # Title (center)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(width/2, height/2 + 90, "Certificate of Completion")

    # Name (center, below title)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width/2, height/2 + 50, full_name)

    # Body (centered block)
    styles = getSampleStyleSheet()
    body = (
        f"successfully completed the Philippine Nurses Association of New York, Inc. webinar "
        f"{COURSE_TITLE} on {COURSE_DATE}."
        #f"Awarded: {CREDIT_HOURS} contact hour(s)."
    )
    from textwrap import wrap
    c.setFont("Helvetica", 12)
    y = height/2 + 18
    for line in wrap(Paragraph(body, styles["Normal"]).text, 100):
        c.drawCentredString(width/2, y, line)
        y -= 16

    # (Optional) Organization at top – comment out if your background already has this
    # c.setFillColor(colors.HexColor("#0B3D91"))
    # c.setFont("Helvetica-Bold", 18)
    # c.drawCentredString(width/2, height - 40, ORG_NAME)
    c.setFillColor(colors.black)

    # Cert ID & issued date (bottom-right cluster)
    issued_on = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.setFont("Helvetica", 7)
    c.drawRightString(width - 60, 72, f"Certificate ID: {cert_id}")
    c.drawRightString(width - 60, 58, f"Issued on: {issued_on}")

    # QR (bottom-right)
    #verify_url = f"{CERT_VERIFY_BASE_URL}{cert_id}"
    #qr = qrcode.QRCode(box_size=3, border=2)
    #qr.add_data(verify_url)
    #qr.make(fit=True)
    #qimg = qr.make_image(fill_color="black", back_color="white")
    #qbuf = io.BytesIO()
    #qimg.save(qbuf, format="PNG")
    #qbuf.seek(0)
    #qr_size = 90
    #c.drawImage(ImageReader(qbuf), width - 150, 78, qr_size, qr_size)
    #c.setFont("Helvetica-Oblique", 9)
    #c.drawRightString(width - 60, 76, "Scan to verify")

    # (Footer removed by request — nothing extra drawn here)

    c.showPage()
    c.save()
    return buffer.getvalue()



# =========================
# PERSIST: CSV (local)
# =========================
def save_row_to_csv(path, row):
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

    # Section 1 — Likert (text scale). Default = "Strongly agree" (you can change to "Agree")
    likert = ["Strongly agree", "Agree", "Undecided", "Disagree", "Strongly disagree"]
    def L(label):
        return st.select_slider(label, options=likert, value="Strongly agree")

    ev_org = L("Was well organized")
    ev_ad = L("Was consistent with flyer advertising event")
    ev_rel = L("Was relevant to learning outcomes of presentation")
    ev_virt = L("Effectively used virtual teaching method")
    ev_obj = L("Enabled me to meet my personal objectives")

    # Section 2 — Overall satisfaction
    st.markdown("**Overall Satisfaction**")
    overall_prog = st.selectbox("Overall satisfaction of the program", ["Excellent","Good","Undecided","Unlikely","Very Unlikely"], index=0)
    overall_rec  = st.selectbox("Likelihood to recommend to colleagues", ["Excellent","Good","Undecided","Unlikely","Very Unlikely"], index=0)
    overall_zoom = st.selectbox("Satisfaction with method of presentation (ZOOM)", ["Excellent","Good","Undecided","Unlikely","Very Unlikely"], index=0)

    # Section 3 — Outcomes met
    lo_met = L("Were Activity Learning Outcomes Met? At least 80% of attendees will pass a post-test with a score of 75% or higher.")

    # Section 4 — Speaker teaching effectiveness (1–5)
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

    # Section 5 — Improvement areas (checkboxes)
    st.markdown("**This activity will assist in improvement of (check all that apply):**")
    imp_knowledge = st.checkbox("Knowledge")
    imp_skills = st.checkbox("Skills")
    imp_competence = st.checkbox("Competence")
    imp_performance = st.checkbox("Performance")
    imp_outcomes = st.checkbox("Patient Outcomes")

    # Section 6/7 — Balance & Commercial
    fair_balanced = st.radio("Do you feel this content was fair and balanced?", ["Yes","No"], index=0)
    commercial_support = st.radio("Did this presentation have any commercial support?", ["Yes","No"], index=1)
    commercial_bias = st.radio("If yes, did the speaker demonstrate any commercial bias?", ["N/A","Yes","No"], index=0)
    bias_explain = st.text_input("If yes, explain", "")

    # Section 8 — Practice change + benefit
    st.markdown("**Practice change**")
    pc_values = st.checkbox("Reflect on and adopt values that elevate nurses to heroes")
    pc_joy = st.checkbox("Employ ways to instill and sustain the joy of practice in nursing and healthcare")
    pc_health = st.checkbox("Utilize ways to address healthcare issues of Filipino Americans in NY")
    pc_other = st.text_input("Other (please specify)", "")
    beneficial_topic = st.text_input("Which program topic was most beneficial to you?")

    # Section 9/10 — Topics & comments
    topics_interest = st.text_area("What topics of interest would you like us to provide?")
    comments = st.text_area("Comments")

    # ---- 3) Post-Test ----
    st.subheader("📝 Post-Test (10 items)")
    answers = {}
    for i, q in enumerate(QUIZ, start=1):
        st.markdown(f"**Q{i}. {q['question']}**")
        answers[str(i)] = st.radio(
            f"Answer Q{i}",
            q["options"],
            index=None,
            key=f"q{i}",
            label_visibility="collapsed"
        )
        st.divider()

    # ---- Submit ----
    if st.button("Submit Evaluation & Generate Certificate"):
        if any(answers[str(i)] is None for i in range(1, len(QUIZ)+1)):
            st.error("Please answer all post-test questions.")
            st.stop()

        correct = sum(1 for i, q in enumerate(QUIZ, start=1) if answers[str(i)] == q["answer"])
        total = len(QUIZ)
        score_pct = 100 * correct / total
        passed = score_pct >= PASSING_SCORE
        st.info(f"Your score: **{correct}/{total} ({score_pct:.0f}%)**. Passing score is {PASSING_SCORE}%.")

        cert_id = str(uuid.uuid4())

        # Build saved row (matches Google Sheet headers)
        row = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "full_name": full_name,
            "email": email,
            "role": role,
            "attendance": "Yes" if attendance else "No",

            # Section 1
            "ev_org": ev_org, "ev_ad": ev_ad, "ev_rel": ev_rel, "ev_virt": ev_virt, "ev_obj": ev_obj,
            # Section 2
            "overall_prog": overall_prog, "overall_rec": overall_rec, "overall_zoom": overall_zoom,
            # Section 3
            "lo_met": lo_met,
            # Section 4 (speakers)
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

            # Section 5
            "improve_knowledge": imp_knowledge, "improve_skills": imp_skills, "improve_competence": imp_competence,
            "improve_performance": imp_performance, "improve_outcomes": imp_outcomes,
            # Section 6/7
            "fair_balanced": fair_balanced, "commercial_support": commercial_support,
            "commercial_bias": commercial_bias, "bias_explain": bias_explain,
            # Section 8
            "pc_values": pc_values, "pc_joy": pc_joy, "pc_health": pc_health, "pc_other": pc_other,
            "beneficial_topic": beneficial_topic,
            # Section 9/10
            "topics_interest": topics_interest.replace("\n"," "),
            "comments": comments.replace("\n"," "),

            # Post-test summary
            "score_pct": f"{score_pct:.0f}",
            "passed": passed,
            "cert_id": cert_id,
        }

        # Save locally
        save_row_to_csv(os.path.join(SAVE_DIR, "submissions.csv"), row)

        #
        # Google Sheets logging (TOML secrets)
        # ---------- Google Sheets logging (by Spreadsheet ID) ----------
        try:
            import gspread
            from oauth2client.service_account import ServiceAccountCredentials
        
            missing = []
            if "gcp_service_account" not in st.secrets:
                missing.append("[gcp_service_account]")
            if "SHEET_ID" not in st.secrets:
                missing.append("SHEET_ID")
            if missing:
                st.caption("Sheets logging not enabled. Missing: " + ", ".join(missing))
            else:
                creds_info = dict(st.secrets["gcp_service_account"])
                scope = ["https://www.googleapis.com/auth/spreadsheets",
                         "https://www.googleapis.com/auth/drive"]
                creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
                client = gspread.authorize(creds)
        
                sh = client.open_by_key(st.secrets["SHEET_ID"])
                ws = sh.worksheet(st.secrets.get("WORKSHEET_TITLE", "Sheet1"))
        
                def yn(v): return "Yes" if v else "No"
                values = [
                    row["timestamp"], row["full_name"], row["email"], row["role"], row["attendance"],
                    row["ev_org"], row["ev_ad"], row["ev_rel"], row["ev_virt"], row["ev_obj"],
                    row["overall_prog"], row["overall_rec"], row["overall_zoom"],
                    row["lo_met"],
                    row["q4_speaker_yap"], row["q4_speaker_sagar"], row["q4_speaker_velasquez"], row["q4_speaker_pastoral"],
                    row["q4_speaker_santarina"], row["q4_speaker_planillo"], row["q4_speaker_florendo"], row["q4_speaker_jomoc"],
                    row["q4_speaker_oliverio"], row["q4_speaker_temprosa"], row["q4_speaker_bedona"], row["q4_speaker_agcon"],
                    yn(row["improve_knowledge"]), yn(row["improve_skills"]), yn(row["improve_competence"]), yn(row["improve_performance"]), yn(row["improve_outcomes"]),
                    row["fair_balanced"], row["commercial_support"], row["commercial_bias"], row["bias_explain"],
                    yn(row["pc_values"]), yn(row["pc_joy"]), yn(row["pc_health"]), row["pc_other"], row["beneficial_topic"],
                    row["topics_interest"], row["comments"],
                    row["score_pct"], yn(row["passed"]), row["cert_id"]
                ]
                ws.append_row(values, value_input_option="USER_ENTERED")
                st.caption("✅ Logged to Google Sheets.")
        except Exception as e:
            st.warning(f"Google Sheets logging failed: {e}")



        # Certificate
        if passed:
            pdf_bytes = make_certificate_pdf(full_name, email, score_pct, cert_id)
            st.success("🎉 Congratulations! You passed and your certificate is ready.")
            st.download_button(
                "⬇️ Download Certificate (PDF)",
                data=pdf_bytes,
                file_name=f"Certificate_{full_name.replace(' ','_')}.pdf",
                mime="application/pdf",
            )
            st.caption("A copy of your submission has been recorded.")
        else:
            st.error("You did not reach the passing score. You may review content and retake the post-test.")
