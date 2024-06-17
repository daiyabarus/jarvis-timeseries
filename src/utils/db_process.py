import streamlit as st
import pandas as pd
from utils.db_con import DatabaseConnector

# TAG: Process the database "DatabaseUtils" is a class that processes the database.


class DatabaseUtils:
    def __init__(self):
        self.db_connector = DatabaseConnector()
        self.conn = None
        self.selected_table = None

    def connect_to_database(self):
        self.conn = self.db_connector.connect()

    def disconnect_from_database(self):
        self.db_connector.disconnect()

    def get_tables_list(self):
        if self.conn:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
            tables = [table[0] for table in cursor.fetchall()]
            cursor.close()
            return tables
        else:
            st.error("Not connected to the database.")
            return []

    def select_table(self):
        tables = self.get_tables_list()
        selected_table = st.sidebar.selectbox(
            "Select a table", tables, key="db_process_select_table"
        )
        self.selected_table = selected_table
        return selected_table

    def get_table_dataframe(self):
        if self.conn and self.selected_table:
            try:
                df = pd.read_sql_query(
                    f"SELECT * FROM {self.selected_table}", self.conn
                )
                return df
            except Exception as e:
                st.error(f"Error fetching table data: {e}")
                return None
        else:
            st.error("Not connected to the database or no table selected.")
            return None
