# app.py
eval_payload = {
"name": name,
"email": email,
"license": license_no,
"session_ratings": ratings,
"comments": comments,
"quiz_score": score,
"passed": passed,
"course_title": COURSE_TITLE,
"course_date": COURSE_DATE,
"credit_hours": CREDIT_HOURS,
}


try:
insert_row("evaluations", eval_payload)
except Exception as e:
st.error(f"Could not save evaluation to Supabase: {e}")
st.stop()


st.success(f"Thanks, {name}! Your score: {score}% — {'PASS' if passed else 'NOT PASSING'} (required: {PASSING_SCORE}%).")


if not passed:
st.info("You can review materials and resubmit to meet the passing score.")
st.stop()


# Passed: generate certificate
cert_id = uuid.uuid4()
pdf_bytes = make_certificate_pdf(
name=name,
course_title=COURSE_TITLE,
course_date=COURSE_DATE,
credit_hours=CREDIT_HOURS,
issuer=CERT_ISSUER,
sign_name=SIGN_NAME,
sign_title=SIGN_TITLE,
org_name=ORG_NAME,
)


# Insert certificate row
cert_row = {
"cert_id": str(cert_id),
"name": name,
"email": email,
"course_title": COURSE_TITLE,
"course_date": COURSE_DATE,
"credit_hours": CREDIT_HOURS,
"issuer": CERT_ISSUER,
"signature_name": SIGN_NAME,
"signature_title": SIGN_TITLE,
}


storage_url = None
if USE_STORAGE:
year = datetime.utcnow().strftime("%Y")
path = f"CERTS/{year}/{cert_id}.pdf"
try:
storage_url = upload_to_storage(pdf_bytes, path)
cert_row["storage_path"] = path
except Exception as e:
st.warning(f"Saved locally; could not upload to storage: {e}")


try:
insert_row("certificates", cert_row)
except Exception as e:
st.warning(f"Certificate recorded locally only (DB insert issue): {e}")


# Offer download and/or link
st.download_button(
label="⬇️ Download Your Certificate (PDF)",
data=pdf_bytes,
file_name=f"certificate-{cert_id}.pdf",
mime="application/pdf",
)


if storage_url:
st.link_button("Open Certificate Link", storage_url)
