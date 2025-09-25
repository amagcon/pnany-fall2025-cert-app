
import streamlit as st

st.title("PNANY Fall 2025 Conference Evaluation & Certificate App")
st.write("This is a placeholder for the full Streamlit app.")

name = st.text_input("Full Name")
email = st.text_input("Email")
if st.button("Submit"):
    st.success(f"Thank you {name}, certificate will be generated here.")
