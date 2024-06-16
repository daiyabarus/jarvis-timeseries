import streamlit as st
from config.navbar import navbar
from config.page_config import page_config
from layout.upload import DatabaseManager, UploadButton
from layout.sidebar import sidebar
from layout.ltedaily import LteDaily
from utils.db_process import DatabaseUtils


def init_session_state():
    if "selected_functionality" not in st.session_state:
        st.session_state["selected_functionality"] = None


def run_app():
    page_config()
    page = navbar()
    init_session_state()

    db_utils = DatabaseUtils()
    db_utils.connect_to_database()

    if page not in ["Upload", "Jarvis", "Github", "About"]:
        options = sidebar(page)
    else:
        options = None
    get_page_content(page, db_utils)

    db_utils.disconnect_from_database()


def get_page_content(page, db_utils):
    if page == "Upload":
        db_mng = DatabaseManager()
        db_mng.connect_to_database()
        selected_table = db_mng.select_table()
        uploadbttn = UploadButton()
        uploadbttn.connect_to_database()
        uploadbttn.upload_button(selected_table)
    elif page == "LTE":
        lte_daily = LteDaily(db_utils)
        lte_daily.run()
