# app.py
import streamlit as st
from config.navbar import navbar
from config.page_config import page_config
from layout.upload import upload_page
from layout.sidebar import sidebar
from layout.ltedaily import LteDaily
from utils.db_process import DatabaseUtils
import pandas as pd

def init_session_state():
    if "selected_functionality" not in st.session_state:
        st.session_state["selected_functionality"] = None

def run_app():
    page_config()
    page = navbar()
    init_session_state()

    db_utils = DatabaseUtils()
    db_utils.connect_to_database()

    selected_table, df = None, None

    if page not in ["Upload", "Jarvis", "Github", "About"]:
        sidebar_options = sidebar(page)
        selected_table = sidebar_options.get("selected_table")
        df = sidebar_options.get("dataframe")

    get_page_content(page, db_utils, selected_table, df)

    db_utils.disconnect_from_database()

def get_page_content(
    page: str, db_utils: DatabaseUtils, selected_table: str, df: pd.DataFrame
):
    if page == "Upload":
        upload_page()
    elif page == "LTE":
        if selected_table and df is not None:
            lte_daily = LteDaily(db_utils)
            lte_daily.run(df)
        else:
            st.warning("Please select a table and SITEID from the sidebar.")
    elif page == "NR":
        st.write("Running NR page...")
        # Add your logic for the NR page
    elif page == "GSM":
        st.write("Running GSM page...")
        # Add your logic for the GSM page

if __name__ == "__main__":
