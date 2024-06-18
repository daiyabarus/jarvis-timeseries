# sidebar.py
import streamlit as st
import sqlite3
import pandas as pd
from typing import Any, Dict


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


def sidebar(page: str) -> Dict[str, Any]:
    db_handler = None
    options = {"selected_table": None, "dataframe": None}

    with st.sidebar:
        st.title("Database Browser")

        # Select or input database file
        db_path = st.text_input("Database Path", value="example.db")
        if st.button("Connect to Database"):
            db_handler = DatabaseHandler(db_path)
            db_handler.connect()

        if db_handler:
            # Select table
            tables = db_handler.get_tables()
            selected_table = st.selectbox("Select Table", tables)

            if selected_table:
                # Query table
                data = db_handler.get_table_data(selected_table)
                st.dataframe(data)

                options["selected_table"] = selected_table
                options["dataframe"] = data

                # Store headers
                if page == "NR":
                    options["DATE_ID"] = st.select_slider(
                        "DATE_ID", options=data["DATE_ID"].unique().tolist()
                    )
                    options["ERBS"] = st.multiselect(
                        "ERBS", options=data["ERBS"].unique().tolist()
                    )
                    options["NRCELL_ID"] = st.multiselect(
                        "NRCELL_ID", options=data["NRCELL_ID"].unique().tolist()
                    )
                elif page == "LTE":
                    options["DATE_ID"] = st.select_slider(
                        "DATE_ID", options=data["DATE_ID"].unique().tolist()
                    )
                    options["ERBS"] = st.multiselect(
                        "ERBS", options=data["ERBS"].unique().tolist()
                    )
                    options["EUTRANCELL"] = st.multiselect(
                        "EUTRANCELL", options=data["EUTRANCELL"].unique().tolist()
                    )
                elif page == "GSM":
                    options["DATE_ID"] = st.select_slider(
                        "DATE_ID", options=data["DATE_ID"].unique().tolist()
                    )
                    options["BSC"] = st.multiselect(
                        "BSC", options=data["BSC"].unique().tolist()
                    )
                    options["GERANCELL"] = st.multiselect(
                        "GERANCELL", options=data["GERANCELL"].unique().tolist()
                    )

                # Run query button
                if st.button("Run Query"):
                    query = f"SELECT * FROM {selected_table} WHERE 1=1"
                    if "DATE_ID" in options:
                        query += f" AND DATE_ID='{options['DATE_ID']}'"
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

