import streamlit as st
from config import navbar, page_config


def init_session_state():
    if "selected_functionality" not in st.session_state:
        st.session_state["selected_functionality"] = None


def run_app():
    page_config()
    page = navbar()
    init_session_state()

    if page != "Upload":
        options = sidebar(page)
    else:
        options = None
    get_page_content(page, options)


def get_page_content(page):
    if page == "Upload":
        from layout import (
            DatabaseManager,
            UploadButton,
        )  # Move the import statements here

        db_mng = DatabaseManager()
        db_mng.connect_to_database()
        selected_table = db_mng.select_table()
        uploadbttn = UploadButton()
        uploadbttn.connect_to_database()
        uploadbttn.upload_button(selected_table)
