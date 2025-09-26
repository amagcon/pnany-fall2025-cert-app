# supabase_client.py
import streamlit as st
from supabase import create_client, Client

@st.cache_resource(show_spinner=False)
def get_supabase() -> Client:
    """Return a cached Supabase client using credentials from secrets.toml"""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)
