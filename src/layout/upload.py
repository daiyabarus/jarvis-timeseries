# upload.py
import streamlit as st
import sqlite3
import pandas as pd
from io import StringIO


class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path

    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

    def close(self):
        self.conn.close()

    def get_tables(self):
        self.connect()
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in self.cursor.fetchall()]
        self.close()
        return tables

    def get_table_header(self, table_name):
        self.connect()
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        header = [info[1] for info in self.cursor.fetchall()]
        self.close()
        return header

    def count_rows(self, table_name):
        self.connect()
        self.cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = self.cursor.fetchone()[0]
        self.close()
        return count

    def insert_csv_to_table(self, table_name, csv_data):
        self.connect()
        df = pd.read_csv(StringIO(csv_data))
        df.to_sql(table_name, self.conn, if_exists="append", index=False)
        self.close()

    def remove_duplicates(self, table_name, selected_columns):
        columns_concat = "||','||".join(selected_columns)
        query = f"""
        DELETE FROM {table_name}
        WHERE rowid IN (
            SELECT rowid
            FROM (
                SELECT rowid,
                    ROW_NUMBER() OVER (
                        PARTITION BY {columns_concat}
                        ORDER BY rowid
                    ) AS rn
                FROM {table_name}
            ) t
            WHERE rn > 1
        );
        """
        self.connect()
        self.cursor.execute(query)
        self.conn.commit()
        self.close()

    def create_table_from_csv(self, create_table_query, csv_data):
        self.connect()
        self.cursor.execute(create_table_query)
        df = pd.read_csv(StringIO(csv_data))
        df.to_sql(
            create_table_query.split(" ")[2],
            self.conn,
            if_exists="append",
            index=False,
        )
        self.close()


def upload_page():
    st.title("SQLite3 Database Manager")

    db_file = st.file_uploader("Upload SQLite Database", type="db")
    if db_file:
        db_path = db_file.name
        with open(db_path, "wb") as f:
            f.write(db_file.getbuffer())

        db_manager = DatabaseManager(db_path)

        tables = db_manager.get_tables()
        selected_table = st.selectbox("Select a table", tables)

        if selected_table:
            st.write(f"Selected Table: {selected_table}")

            row_count = db_manager.count_rows(selected_table)
            st.write(f"Row count: {row_count}")

            table_header = db_manager.get_table_header(selected_table)
            st.write(f"Table Header: {table_header}")

            csv_files = st.file_uploader(
                "Upload CSV files", type="csv", accept_multiple_files=True
            )

            if csv_files:
                for csv_file in csv_files:
                    csv_data = StringIO(csv_file.getvalue().decode("utf-8"))
                    db_manager.insert_csv_to_table(selected_table, csv_data.read())

                st.success("CSV files have been imported successfully.")

            selected_columns = st.multiselect(
                "Select columns to check for duplicates", table_header
            )

            if st.button("Remove Duplicates"):
                if selected_columns:
                    db_manager.remove_duplicates(selected_table, selected_columns)
                    st.success("Duplicates have been removed.")
                else:
                    st.warning("Please select columns to check for duplicates.")

        new_table_csv = st.file_uploader("Upload CSV to Create a New Table", type="csv")
        if new_table_csv:
            csv_data = new_table_csv.getvalue().decode("utf-8")
            df = pd.read_csv(StringIO(csv_data))

            st.write("CSV Header and First Row:")
            combined_columns = [
                f"{col} ({val})" for col, val in zip(df.columns, df.iloc[0])
            ]
            st.write(combined_columns)

            schema = [{"name": col, "type": "TEXT"} for col in df.columns]
            schema_df = pd.DataFrame(
                {
                    "column": combined_columns,
                    "type": ["TEXT"] * len(combined_columns),
                }
            )

            st.write("Edit Schema:")
            edited_schema_df = st.data_editor(schema_df, num_rows="dynamic")

            table_name = st.text_input("Enter name for the new table")

            if table_name:
                # Generate the CREATE TABLE query based on the edited schema
                schema = [
                    {"name": col.split(" ")[0], "type": dtype}
                    for col, dtype in zip(
                        edited_schema_df["column"], edited_schema_df["type"]
                    )
                ]
                columns_with_types = ", ".join(
                    [f"{col['name']} {col['type']}" for col in schema]
                )
                create_table_query = (
                    f"CREATE TABLE {table_name} ({columns_with_types});"
                )

                st.write("Generated CREATE TABLE Query:")
                create_table_query = st.text_area(
                    "Edit the CREATE TABLE query if needed:",
                    value=create_table_query,
                    height=200,
                )

                if st.button("Create Table"):
                    try:
                        db_manager.create_table_from_csv(create_table_query, csv_data)
                        st.success(f"Table {table_name} has been created successfully.")
                    except Exception as e:
                        st.error(f"An error occurred: {e}")
    else:
        st.info("Please upload a SQLite database file.")
