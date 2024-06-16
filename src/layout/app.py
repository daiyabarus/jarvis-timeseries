import streamlit as st
from config import navbar, page_config

def init_session_state():
  if "selected_functionality" not in st.session_state:
    st.session_state["selected_functionality"] = None

def run_app():
  page_config()
  page = navbar()
  init_session_state()

  if page == "Upload":
