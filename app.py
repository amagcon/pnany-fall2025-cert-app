import streamlit as st
from datetime import datetime
import uuid, csv, os, io, json

# ====== SETTINGS ======
ORG_NAME = "The Philippine Nurses Association of New York, Inc."
COURSE_TITLE = "Lead to INSPIRE Fall Conference 2025 — Gabay at Galing: Empowering the New Generation of Nurse Leaders"
COURSE_DATE = "October 18, 2025"
CREDIT_HOURS = 4.75
PASSING_SCORE = 75
CERT_ISSUER = "PNAA Accredited Provider Unit (P0613)"
CERT_SIGNATURE_NAME = "Ninotchka Brydges, PhD, DNP, MBA, APRN, ACNP-BC, FNAP, FAAN"
CERT_SIGNATURE_TITLE = "PNAA Accredited Provider Program Director"
CERT_VERIFY_BASE_URL = "https://example.org/verify?cert_id="  # set later
SAVE_DIR = "data"; os.makedirs(SAVE_DIR, exist_ok=True)

# ====== LOAD QUIZ (questions.json in repo root) ======
with open("questions.json", "r", encoding="utf-8") as f:
    QUIZ = json.load(f)

# ====== PDF GEN ======
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from PIL import Image
import qrcode

def make_certificate_pdf(full_name: str, email: str, score_pct: float, cert_id: str) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    bg_path = "assets/cert_bg.png"
    if os.path.exists(bg_path):
        c.drawImage(ImageReader(bg_path), 0, 0, width=width, height=height)

    c.setFillColor(colors.HexColor("#0B3D91")); c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width/2, height - 100, ORG_NAME)

    c.setFillColor(colors.black); c.setFont("Helvetica", 14)
    c.drawCentredString(width/2, height - 130, "Certificate of Completion")

    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width/2, height - 180, full_name)

    styles = getSampleStyleSheet()
    body = (
        f"This certifies that <b>{full_name}</b> ({email}) has attended and successfully completed the webinar "
        f"<b>{COURSE_TITLE}</b> held on <b>{COURSE_DATE}</b>, and passed the post-test with a score of "
        f"<b>{round(score_pct)}%</b>. Credits awarded: <b>{CREDIT_HOURS} contact hour(s)</b>."
    )
    para = Paragraph(body, styles["Normal"])
    import textwrap as tw
    for i, line in enumerate(tw.wrap(para.text, 100)):
        c.setFont("Helvetica", 12)
        c.drawCentredString(width/2, height - 220 - 16*i, line)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(72, 140, CERT_SIGNATURE_NAME)
    c.setFont("Helvetica", 11)
    c.drawString(72, 125, CERT_SIGNATURE_TITLE)
    c.drawString(72, 110, f"Issued by: {CERT_ISSUER}")

    issued_on = datetime.now().strftime("%Y-%m-%d %H:%M %Z")
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 72, 110, f"Certificate ID: {cert_id}")
    c.drawRightString(width - 72, 95, f"Issued on: {issued_on}")

    verify_url = f"{CERT_VERIFY_BASE_URL}{cert_id}"
    qr = qrcode.QRCode(box_size=3, border=2); qr.add_data(verify_url); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    qrb = io.BytesIO(); img.save(qrb, format="PNG"); qrb.seek(0)
    c.drawImage(ImageReader(qrb), width - 162, 130, 90, 90)
    c.setFont("Helvetica-Oblique", 9); c.drawRightString(width - 72, 125, "Scan to verify")

    c.setFont("Helvetica", 9)
    footer = [
        "Philippine Nurses Association of America Provider Unit is accredited as a provider of",
        "nursing continuing professional development by the American Nurses Credentialing Center's",
        "Commission on Accreditation. Provider Number: P0613",
        f"Contact Hours Awarded: {CREDIT_HOURS}",
        "PNAA Address: 1346 How Lane, Suites 109-110, North Brunswick, NJ 08902"
    ]
    y = 70
    for line in footer:
        c.drawCentredString(width/2, y, line); y -= 12

    c.showPage(); c.save()
    return buffer.getvalue()

def save_row_to_csv(path, row):
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=row.keys())
        if new: w.writeheader()
        w.writerow(row)

# ====== UI ======
st.set_page_config(page_title="PNANY Fall 2025 — Evaluation & Certificate", page_icon="🎓", layout="centered")
st.title("🎓 PNANY Fall 2025 — Evaluation & Post-Test")
st.caption("Complete the evaluation and post-test. On passing (≥ 75%), your certificate will be generated.")

# 1) Participant info
with st.form("info"):
    c1, c2 = st.columns(2)
    with c1: full_name = st.text_input("Full Name *")
    with c2: email = st.text_input("Email *")
    role = st.selectbox("Role / Credentials", ["RN", "APRN", "NP", "PA", "Student", "Other"])
    attendance = st.checkbox("I attended the PNANY Fall 2025 Conference")
    cont = st.form_submit_button("Continue ➡️")
if cont:
    if not full_name or not email or not attendance:
        st.error("Please complete name, email, and confirm attendance.")
    else:
        st.session_state["participant_ok"] = True
        st.success("Thanks! Continue below.")

# 2) Evaluation (matches your template, condensed)
if st.session_state.get("participant_ok"):
    st.subheader("📊 Course Evaluation")
    likert = ["Strongly agree","Agree","Undecided","Disagree","Strongly disagree"]
    def L(label): return st.select_slider(label, options=likert, value="Agree")

    ev_org = L("Was well organized")
    ev_ad = L("Was consistent with flyer advertising event")
    ev_rel = L("Was relevant to learning outcomes of presentation")
    ev_virt = L("Effectively used virtual teaching method")
    ev_obj = L("Enabled me to meet my personal objectives")

    st.markdown("**Overall Satisfaction**")
    overall_prog = st.selectbox("Overall satisfaction of the program", ["Excellent","Good","Undecided","Unlikely","Very Unlikely"])
    overall_rec  = st.selectbox("Likelihood to recommend to colleagues", ["Excellent","Good","Undecided","Unlikely","Very Unlikely"])
    overall_zoom = st.selectbox("Satisfaction with method of presentation (ZOOM)", ["Excellent","Good","Undecided","Unlikely","Very Unlikely"])

    lo_met = L("At least 80% of attendees will pass a post-test with a score of 75% or higher.")

    st.markdown("**This activity will assist in improvement of (check all that apply):**")
    imp_knowledge = st.checkbox("Knowledge")
    imp_skills = st.checkbox("Skills")
    imp_competence = st.checkbox("Competence")
    imp_performance = st.checkbox("Performance")
    imp_outcomes = st.checkbox("Patient Outcomes")

    fair_balanced = st.radio("Do you feel this content was fair and balanced?", ["Yes","No"])
    commercial_support = st.radio("Did this presentation have any commercial support?", ["Yes","No"])
    commercial_bias = st.radio("If yes, did the speaker demonstrate any commercial bias?", ["N/A","Yes","No"])
    bias_explain = st.text_input("If yes, explain", "")

    st.markdown("**Practice change**")
    pc_values = st.checkbox("Reflect on and adopt values that elevate nurses to heroes")
    pc_joy = st.checkbox("Employ ways to instill and sustain the joy of practice in nursing and healthcare")
    pc_health = st.checkbox("Utilize ways to address healthcare issues of Filipino Americans in NY")
    pc_other = st.text_input("Other (please specify)", "")

    beneficial_topic = st.text_input("Which program topic was most beneficial to you?")
    topics_interest = st.text_area("What topics of interest would you like us to provide?")
    comments = st.text_area("Comments")

    st.subheader("📝 Post-Test (10 items)")
    answers = {}
    for i, q in enumerate(QUIZ, start=1):
        st.markdown(f"**Q{i}. {q['question']}**")
        answers[str(i)] = st.radio(
            f"Answer Q{i}", q["options"], index=None, key=f"q{i}", label_visibility="collapsed"
        )

    if st.button("Submit Evaluation & Generate Certificate"):
        if any(answers[str(i)] is None for i in range(1, len(QUIZ)+1)):
            st.error("Please answer all post-test questions.")
            st.stop()

        correct = sum(1 for i, q in enumerate(QUIZ, start=1) if answers[str(i)] == q["answer"])
        total = len(QUIZ); score_pct = 100 * correct / total; passed = score_pct >= PASSING_SCORE
        st.info(f"Your score: **{correct}/{total} ({score_pct:.0f}%)**. Passing score is {PASSING_SCORE}%.")

        cert_id = str(uuid.uuid4())

        row = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "full_name": full_name, "email": email, "role": role,
            "attendance": "Yes" if attendance else "No",
            "ev_org": ev_org, "ev_ad": ev_ad, "ev_rel": ev_rel, "ev_virt": ev_virt, "ev_obj": ev_obj,
            "overall_prog": overall_prog, "overall_rec": overall_rec, "overall_zoom": overall_zoom,
            "lo_met": lo_met,
            "improve_knowledge": imp_knowledge, "improve_skills": imp_skills, "improve_competence": imp_competence,
            "improve_performance": imp_performance, "improve_outcomes": imp_outcomes,
            "fair_balanced": fair_balanced, "commercial_support": commercial_support,
            "commercial_bias": commercial_bias, "bias_explain": bias_explain,
            "pc_values": pc_values, "pc_joy": pc_joy, "pc_health": pc_health, "pc_other": pc_other,
            "beneficial_topic": beneficial_topic, "topics_interest": topics_interest.replace("\n"," "),
            "comments": comments.replace("\n"," "),
            "score_pct": f"{score_pct:.0f}", "passed": passed, "cert_id": cert_id,
        }
        save_row_to_csv(os.path.join(SAVE_DIR, "submissions.csv"), row)

        if passed:
            pdf_bytes = make_certificate_pdf(full_name, email, score_pct, cert_id)
            st.success("🎉 Congratulations! You passed and your certificate is ready.")
            st.download_button("⬇️ Download Certificate (PDF)",
                               data=pdf_bytes,
                               file_name=f"Certificate_{full_name.replace(' ','_')}.pdf",
                               mime="application/pdf")
            st.caption("A copy of your submission has been recorded.")
        else:
            st.error("You did not reach the passing score. You may review content and retake the post-test.")
