import streamlit as st
from utils.dbutils import get_db_connection
import pandas as pd
import io
from sqlalchemy import text


class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.tables = []
        self.selected_table = None

    def connect_to_database(self):
        try:
            self.engine = get_db_connection()
            if self.engine:
                st.success("Connected to the database!")
                self.get_tables()
            else:
                st.error("Failed to connect to the database.")
        except Exception as error:
            st.error(f"Error connecting to the database: {error}")

    def get_tables(self):
        if self.engine is None:
            st.error("Not connected to the database.")
            return

        try:
            query = text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
            with self.engine.connect() as connection:
                result = connection.execute(query)
                self.tables = [table[0] for table in result]
        except Exception as error:
            st.error(f"Error retrieving tables: {error}")

    def print_table(self, table_name):
        if self.engine is None:
            st.error("Not connected to the database.")
            return

        try:
            query = text(f"SELECT * FROM {table_name}")
            with self.engine.connect() as connection:
                result = connection.execute(query)
                st.table(result.fetchall())
        except Exception as error:
            st.error(f"Error printing table: {error}")

    def select_table(self):
        if self.engine is None:
            st.error("Not connected to the database.")
            return None

        selected_table = st.selectbox("Select a table", self.tables)
        if selected_table:
            query = text(f'SELECT MAX("DATE_ID") from {selected_table}')
            with self.engine.connect() as connection:
                result = connection.execute(query)
                st.write(f"Latest date in the **{selected_table}** :")
                st.write(result.fetchone()[0])

        self.selected_table = selected_table
        return selected_table


class UploadButton:
    def __init__(self):
        self.engine = None
        self.selected_table = None

    def connect_to_database(self):
        try:
            self.engine = get_db_connection()
        except Exception as error:
            st.error(f"Error connecting to the database: {error}")

    def run_query(self, query):
        if self.engine is None:
            st.error("Not connected to the database.")
            return

        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(query))
                st.table(result.fetchall())
        except Exception as error:
            st.error(f"Error running the query: {error}")

    def upload_button(self, selected_table):
        if self.engine is None:
            st.error("Not connected to the database.")
            return

        uploaded_files = st.file_uploader(
            "Upload CSV files", type="csv", accept_multiple_files=True
        )
        if uploaded_files is not None:
            try:
                for uploaded_file in uploaded_files:
                    # Process each uploaded file
                    df = pd.read_csv(uploaded_file)

                    # Insert the data into the PostgreSQL database
                    with self.engine.begin() as connection:
                        csv_buffer = io.StringIO()
                        df.to_csv(csv_buffer, index=False, header=False)
                        csv_buffer.seek(0)
                        connection.execute(
                            text(
                                f"COPY {selected_table} FROM STDIN WITH CSV DELIMITER ','"
                            ),
                            csv_buffer,
                        )

                    st.success(
                        f"File '{uploaded_file.name}' uploaded and data inserted into the database!"
                    )
            except Exception as error:
                st.error(f"Error uploading files and inserting data: {error}")
