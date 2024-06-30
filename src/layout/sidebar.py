import sqlite3

import pandas as pd
import streamlit as st
import streamlit_antd_components as sac


class DatabaseHandler:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        # self.db_path = "database/database.db"
        self.connection = sqlite3.connect(self.db_path)

    @st.cache_data(ttl=1800)
    def get_tables(_self):
        if _self.connection:
            query = "SELECT name FROM sqlite_master WHERE type='table';"
            tables = pd.read_sql_query(query, _self.connection)["name"].tolist()
            return tables

    @st.cache_data(ttl=1800)
    def get_table_data(_self, table_name: str):
        if _self.connection:
            query = f"SELECT * FROM {table_name};"
            data = pd.read_sql_query(query, _self.connection)
            return data

    def close(self):
        if self.connection:
            self.connection.close()


def sidebar(page: str):
    side_bar_mods()
    db_handler = None
    options = {"selected_table": None, "dataframe": None}
    with st.sidebar:
        col1, col2 = st.columns(2)
        col1.image("assets/signaltower.png", width=200)
        col2.markdown("# ")
        st.markdown(
            "<h3 style='text-align: center; color: #000000;'>Behind The Signal</h3>",
            unsafe_allow_html=True,
        )
        sac.divider(color="black", key="title")

        db_path = "database/database.db"  # TAG this with the correct path
        db_handler = DatabaseHandler(db_path)
        db_handler.connect()

        col1, col2, col3 = st.columns(3)
        if col1.button("NR"):
            st.session_state["dashboard_tab"] = "NR"
            tables = "eri_gut_nr"
        if col2.button("LTE"):
            st.session_state["dashboard_tab"] = "LTE"
            tables = "eri_gut_lte"
        if col3.button("GSM"):
            st.session_state["dashboard_tab"] = "GSM"
            tables = "eri_gut_gsm"

    return options


def side_bar_mods():
    html_injection = """
    <style>
        /* Custom Sidebar Padding */
        div[data-testid="stSidebarUserContent"] {
            padding-top: 1rem;
        }

        .st-emotion-cache-dvne4q {
            padding-right: 1rem;
            padding-bottom: 1rem;
            padding-left: 1rem;
        }
    </style>
    """

    html_injection = """
    <style>
    .st-emotion-cache-dvne4q {
        padding-right: 1rem;
        padding-bottom: 3rem;
        padding-left: 1rem;
    }
    </style>
    """
    st.markdown(html_injection, unsafe_allow_html=True)
