import streamlit as st
from config.navbar import navbar
from config.page_config import page_config
from layout.upload import upload_page
from layout.daily.pagenrdaily import nr_daily_page
from layout.daily.pageltedaily import lte_daily_page
from layout.daily.pagegsmdaily import gsm_daily_page
from layout.sidebar import sidebar
from typing import Any, Dict
from layout.wiki import wiki


def init_session_state():
    if "selected_functionality" not in st.session_state:
        st.session_state["selected_functionality"] = None
    if "dashboard_tab" not in st.session_state:
        st.session_state["dashboard_tab"] = "NR"


def dashboard_page():
    page = st.session_state.get("dashboard_tab", "NR")

    if page:
        options = sidebar(page)
        filtered_df = options.get("filtered_dataframe")

        if page == "NR":
            nr_daily_page(filtered_df)
        elif page == "LTE":
            lte_daily_page(filtered_df)
        elif page == "GSM":
            gsm_daily_page(filtered_df)
    else:
        st.write("Error: page is not set properly")


def get_page_content(page: str, options: Dict[str, Any]):
    if page == "Database":
        upload_page()
    elif page == "Wiki":
        wiki()
    elif page == "LTE":
        filtered_df = options.get("filtered_dataframe")
        lte_daily_page(filtered_df)
    elif page == "NR":
        filtered_df = options.get("filtered_dataframe")
        nr_daily_page(filtered_df)
    elif page == "Jarvis":
        st.write("COMING SOON...")
    elif page == "GSM":
        filtered_df = options.get("filtered_dataframe")
        gsm_daily_page(filtered_df)


def run_app():
    page_config()
    page = navbar()
    init_session_state()

    selected_table, options = None, None

    if page == "Dashboard":
        dashboard_page()
    else:
        if page not in ["Database", "Jarvis", "GitHub", "Wiki"]:
            options = sidebar(page)
        else:
            options = None

        get_page_content(page, options)
