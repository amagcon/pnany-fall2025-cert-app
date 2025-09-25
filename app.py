import streamlit as st

st.set_page_config(page_title="PNANY Fall 2025 — Sanity Check", page_icon="🎓")
st.title("🎓 PNANY Fall 2025 — Streamlit is LIVE")

with st.form("smoke"):
    name = st.text_input("Full Name")
    email = st.text_input("Email")
    submitted = st.form_submit_button("Submit")
    if submitted:
        if not name or not email:
            st.error("Please enter both name and email.")
        else:
            st.success(f"Thanks, {name}! Your app is working.")
