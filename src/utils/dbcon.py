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
    def get_tables(self):
        if self.connection:
            query = "SELECT name FROM sqlite_master WHERE type='table';"
            tables = pd.read_sql_query(query, self.connection)["name"].tolist()
            return tables

    @st.cache_data(ttl=600)
    def get_min_date(self, table: str, date_column: str):
        if self.connection:
            query = f"SELECT MIN({date_column}) FROM {table};"
            min_date = pd.read_sql_query(query, self.connection).iloc[0, 0]
            min_date_month = pd.to_datetime(min_date).strftime("%Y-%m")
            return min_date_month

    @st.cache_data(ttl=600)
    def get_max_date(self, table: str, date_column: str):
        if self.connection:
            query = f"SELECT MAX({date_column}) FROM {table};"
            max_date = pd.read_sql_query(query, self.connection).iloc[0, 0]
            max_date_month = pd.to_datetime(max_date).strftime("%Y-%m")
            return max_date_month

    @st.cache_data(ttl=600)
    def get_erbs(self, table: str, erbs_column: str):
        if self.connection:
            query = f"SELECT DISTINCT {erbs_column} FROM {table};"
            erbs_values = pd.read_sql_query(query, self.connection)[
                erbs_column
            ].tolist()
            return erbs_values

    @st.cache_data(ttl=600)
    def get_cell(self, table: str, cell_column: str):
        if self.connection:
            query = f"SELECT DISTINCT {cell_column} FROM {table};"
            cell_values = pd.read_sql_query(query, self.connection)[
                cell_column
            ].tolist()
            return cell_values

    def query_after_select(
        self,
        table: str,
        date_column: str,
        erbs_column: str,
        cell_column: str,
        start_date: str,
        end_date: str,
        erbs: str = None,
        cell: str = None,
    ):
        if self.connection:
            conditions = []
            conditions.append(f"{date_column} BETWEEN '{start_date}' AND '{end_date}'")
            if erbs:
                conditions.append(f"{erbs_column} = '{erbs}'")
            if cell:
                conditions.append(f"{cell_column} = '{cell}'")
            where_clause = " AND ".join(conditions)
            query = f"SELECT * FROM {table} WHERE {where_clause};"
            result = pd.read_sql_query(query, self.connection)
            return result

    @st.cache_data(ttl=600)
    def get_table_data(self, table_name: str):
        if self.connection:
            query = f"SELECT * FROM {table_name};"
            data = pd.read_sql_query(query, self.connection)
            return data

    def close(self):
        if self.connection:
            self.connection.close()


# db_handler = DatabaseHandler('path_to_your_database.db')
# db_handler.connect()
# tables = db_handler.get_tables()
# min_date = db_handler.get_min_date('your_table_name', 'date_column')
# max_date = db_handler.get_max_date('your_table_name', 'date_column')
# erbs_values = db_handler.get_erbs('your_table_name', 'erbs_column')
# cell_values = db_handler.get_cell('your_table_name', 'cell_column')
# result = db_handler.query_after_select('your_table_name', 'date_column', 'erbs_column', 'cell_column', '2022-01-01', '2022-12-31', 'some_erbs_value', 'some_cell_value')
# db_handler.close()
