# app.py
import streamlit as st
from config.navbar import navbar
from config.page_config import page_config
from layout.upload import upload_page
from layout.sidebar import sidebar

# from layout.gsmdaily import gsm_daily_page
from layout.test_gsmdaily import gsm_daily_page
from typing import Any, Dict


def init_session_state():
    if "selected_functionality" not in st.session_state:
        st.session_state["selected_functionality"] = None


def run_app():
    page_config()
    page = navbar()
    init_session_state()

    selected_table, options = None, None

    if page not in ["Upload", "Jarvis", "Github", "About"]:
        options = sidebar(page)
        selected_table = options.get("selected_table")
    else:
        options = None

    get_page_content(page, options)


def get_page_content(page: str, options: Dict[str, Any]):
    if page == "Upload":
        upload_page()
    elif page == "LTE":
        st.write("COMING SOON Running LTE page...")
        # Add your logic for the LTE page
    elif page == "NR":
        st.write("COMING SOON Running NR page...")
        # Add your logic for the NR page
    elif page == "Jarvis":
        st.write("COMING SOON...")
        # Add your logic here
    elif page == "About":
        st.write("COMING SOON...")
        # Add your logic here
    elif page == "GSM":
        filtered_df = options.get("filtered_dataframe")
        gsm_daily_page(filtered_df)
