# sidebar.py
import streamlit as st
import sqlite3
import pandas as pd
from typing import Any, Dict
import streamlit_antd_components as sac


class DatabaseHandler:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None
        self.tables = []

    def connect(self):
        self.connection = sqlite3.connect(self.db_path)

    def get_tables(self):
        if self.connection:
            query = "SELECT name FROM sqlite_master WHERE type='table';"
            self.tables = pd.read_sql_query(query, self.connection)["name"].tolist()
        return self.tables

    def get_table_data(self, table_name: str):
        if self.connection:
            query = f"SELECT * FROM {table_name};"
            data = pd.read_sql_query(query, self.connection)
            return data

    def close(self):
        if self.connection:
            self.connection.close()


def sidebar(page: str,) -> Dict[str, Any]:
    side_bar_mods()
    db_handler = None
    options = {"selected_table": None, "dataframe": None}
    with st.sidebar:
        # st.title("Database Browser")
        col1, col2 = st.columns(2)
        col1.image("assets/jarvis.png", width=200)
        col2.markdown("# ")
        col2.markdown("# ")
        st.markdown(
            "<h3 style='text-align: center; color: grey;'>Easy Dashboard</h3>",
            unsafe_allow_html=True,
        )
        sac.divider(color="black", key="title")

        db_path = "database/database.db"
        db_handler = DatabaseHandler(db_path)
        db_handler.connect()

        # Select table
        tables = db_handler.get_tables()
        if tables:
            selected_table = st.selectbox("Select Table", tables, key="selected_table")
            if selected_table:
                # Query table
                data = db_handler.get_table_data(selected_table)
                # st.dataframe(data)

                options["selected_table"] = selected_table
                options["dataframe"] = data

                # Store headers
                if page in ["NR", "LTE", "GSM"]:
                    col1, col2 = st.columns(2)
                    min_date = col1.selectbox(
                        "Min DATE_ID",
                        options=data["DATE_ID"].unique().tolist(),
                        key="min_date",
                    )
                    max_date = col2.selectbox(
                        "Max DATE_ID",
                        options=data["DATE_ID"].unique().tolist(),
                        key="max_date",
                    )
                    options["DATE_ID"] = (min_date, max_date)

                    if page == "NR":
                        options["ERBS"] = st.multiselect(
                            "ERBS",
                            options=data["ERBS"].unique().tolist(),
                            key="nr_erbs",
                        )
                        options["NRCELL_ID"] = st.multiselect(
                            "NRCELL_ID",
                            options=data["NRCELL_ID"].unique().tolist(),
                            key="nr_nrcell_id",
                        )
                    elif page == "LTE":
                        options["ERBS"] = st.multiselect(
                            "ERBS",
                            options=data["ERBS"].unique().tolist(),
                            key="lte_erbs",
                        )
                        options["EUTRANCELL"] = st.multiselect(
                            "EUTRANCELL",
                            options=data["EUTRANCELL"].unique().tolist(),
                            key="lte_eutrancell",
                        )
                    elif page == "GSM":
                        options["BSC"] = st.multiselect(
                            "BSC", options=data["BSC"].unique().tolist(), key="gsm_bsc"
                        )
                        options["GERANCELL"] = st.multiselect(
                            "GERANCELL",
                            options=data["GERANCELL"].unique().tolist(),
                            key="gsm_gerancell",
                        )

                # Run query button
                if st.button("Run Query"):
                    query = f"SELECT * FROM {selected_table} WHERE 1=1"
                    if "DATE_ID" in options:
                        query += f" AND DATE_ID BETWEEN '{options['DATE_ID'][0]}' AND '{options['DATE_ID'][1]}'"
                    if "ERBS" in options and options["ERBS"]:
                        query += f" AND ERBS IN ({', '.join([f'\"{x}\"' for x in options['ERBS']])})"
                    if "NRCELL_ID" in options and options["NRCELL_ID"]:
                        query += f" AND NRCELL_ID IN ({', '.join([f'\"{x}\"' for x in options['NRCELL_ID']])})"
                    if "EUTRANCELL" in options and options["EUTRANCELL"]:
                        query += f" AND EUTRANCELL IN ({', '.join([f'\"{x}\"' for x in options['EUTRANCELL']])})"
                    if "BSC" in options and options["BSC"]:
                        query += f" AND BSC IN ({', '.join([f'\"{x}\"' for x in options['BSC']])})"
                    if "GERANCELL" in options and options["GERANCELL"]:
                        query += f" AND GERANCELL IN ({', '.join([f'\"{x}\"' for x in options['GERANCELL']])})"

                    result_data = pd.read_sql_query(query, db_handler.connection)
                    st.dataframe(result_data)

        db_handler.close()

    return options


def side_bar_mods():
    html_injection = """
    <style>
    div[data-testid="stSidebarUserContent"] {
        padding-top: 3rem;
    }
    </style>
    """
    st.markdown(html_injection, unsafe_allow_html=True)

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
