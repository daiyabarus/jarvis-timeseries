# app.py
import streamlit as st
from config.navbar import navbar
from config.page_config import page_config
from layout.upload import upload_page
from layout.sidebar import sidebar
from layout.gsmdaily import gsm_daily_page  # Adjusted import statement
import pandas as pd


def init_session_state():
    if "selected_functionality" not in st.session_state:
        st.session_state["selected_functionality"] = None


def run_app():
    page_config()
    page = navbar()
    init_session_state()

    selected_table, df = None, None

    if page not in ["Upload", "Jarvis", "Github", "About"]:
        sidebar_options = sidebar(page)
        selected_table = sidebar_options.get("selected_table")
        df = sidebar_options.get("dataframe")

    get_page_content(page, df)


def get_page_content(page: str, df: pd.DataFrame):
    if page == "Upload":
        upload_page()
    elif page == "LTE":
        st.write("Running LTE page...")
        # Add your logic for the LTE page
    elif page == "NR":
        st.write("Running NR page...")
        # Add your logic for the NR page
    elif page == "GSM":
        gsm_daily_page(
            df
        )  # Call the gsm_daily_page function with the filtered dataframe
