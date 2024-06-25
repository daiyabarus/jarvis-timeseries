# dbcon.py
import sqlite3

import pandas as pd
import streamlit as st


class DatabaseHandler:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        try:
            self.connection = sqlite3.connect(self.db_path)
        except Exception as e:
            st.error(f"Error connecting to database: {e}")

    @st.cache_data(ttl=600)
    def get_tables(_self):
        if _self.connection:
            query = "SELECT name FROM sqlite_master WHERE type='table';"
            try:
                tables = pd.read_sql_query(query, _self.connection)["name"].tolist()
                return tables
            except Exception as e:
                st.error(f"Error fetching tables: {e}")
                return []

    @st.cache_data(ttl=600)
    def get_min_date(_self, table: str, date_column: str):
        if _self.connection:
            # trunk-ignore(bandit/B608)
            query = f"SELECT MIN({date_column}) FROM {table};"
            try:
                min_date = pd.read_sql_query(query, _self.connection).iloc[0, 0]
                min_date_month = pd.to_datetime(min_date).strftime("%Y-%m")
                return min_date_month
            except Exception as e:
                st.error(f"Error fetching minimum date: {e}")
                return None

    @st.cache_data(ttl=600)
    def get_max_date(_self, table: str, date_column: str):
        if _self.connection:
            # trunk-ignore(bandit/B608)
            query = f"SELECT MAX({date_column}) FROM {table};"
            try:
                max_date = pd.read_sql_query(query, _self.connection).iloc[0, 0]
                max_date_month = pd.to_datetime(max_date).strftime("%Y-%m")
                return max_date_month
            except Exception as e:
                st.error(f"Error fetching maximum date: {e}")
                return None

    @st.cache_data(ttl=600)
    def get_erbs(_self, table: str, erbs_column: str):
        if _self.connection:
            # trunk-ignore(bandit/B608)
            query = f"SELECT DISTINCT {erbs_column} FROM {table};"
            try:
                erbs_values = pd.read_sql_query(query, _self.connection)[
                    erbs_column
                ].tolist()
                return erbs_values
            except Exception as e:
                st.error(f"Error fetching ERBS values: {e}")
                return []

    @st.cache_data(ttl=600)
    def get_cell(_self, table: str, cell_column: str):
        if _self.connection:
            # trunk-ignore(bandit/B608)
            query = f"SELECT DISTINCT {cell_column} FROM {table};"
            try:
                cell_values = pd.read_sql_query(query, _self.connection)[
                    cell_column
                ].tolist()
                return cell_values
            except Exception as e:
                st.error(f"Error fetching cell values: {e}")
                return []

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
            conditions = [f"{date_column} BETWEEN '{start_date}' AND '{end_date}'"]
            params = []

            if erbs:
                erbs_list = erbs.split(",")
                conditions.append(
                    f"{erbs_column} IN ({','.join(['?']*len(erbs_list))})"
                )
                params.extend(erbs_list)

            if cell:
                cell_list = cell.split(",")
                conditions.append(
                    f"{cell_column} IN ({','.join(['?']*len(cell_list))})"
                )
                params.extend(cell_list)

            where_clause = " AND ".join(conditions)
            # trunk-ignore(bandit/B608)
            query = f"SELECT * FROM {table} WHERE {where_clause};"

            try:
                result = pd.read_sql_query(query, self.connection, params=params)
                return result
            except Exception as e:
                st.error(f"Error executing query: {e}")
                return pd.DataFrame()

    @st.cache_data(ttl=600)
    def get_table_data(_self, table_name: str):
        if _self.connection:
            # trunk-ignore(bandit/B608)
            query = f"SELECT * FROM {table_name};"
            try:
                data = pd.read_sql_query(query, _self.connection)
                return data
            except Exception as e:
                st.error(f"Error fetching table data: {e}")
                return pd.DataFrame()

    def close(self):
        if self.connection:
            self.connection.close()
