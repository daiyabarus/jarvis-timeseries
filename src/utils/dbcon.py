import streamlit as st
import sqlite3
import pandas as pd


class DatabaseHandler:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        self.connection = sqlite3.connect(self.db_path)

    @st.cache_data(ttl=600)
    def get_tables(_self):
        if _self.connection:
            query = "SELECT name FROM sqlite_master WHERE type='table';"
            tables = pd.read_sql_query(query, _self.connection)["name"].tolist()
            return tables

    @st.cache_data(ttl=600)
    def get_table_data(_self, table_name: str):
        if _self.connection:
            query = f"SELECT * FROM {table_name};"
            data = pd.read_sql_query(query, _self.connection)
            return data

    def close(self):
        if self.connection:
            self.connection.close()
