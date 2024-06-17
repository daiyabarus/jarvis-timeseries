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
                st.header('Select table to begin the process', divider='red')
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

        st.header('Process to upload csv to table', divider='red')
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

class DeleteDuplicate:
    def __init__(self):
        self.engine = None
        self.selected_table = None

    def connect_to_database(self):
        try:
            self.engine = get_db_connection()
        except Exception as error:
            st.error(f"Error connecting to the database: {error}")

    def delete_duplicate(self, selected_table):
        if self.engine is None:
            st.error("Not connected to the database.")
            return

        try:
            # Button for running Query 1
            st.header('Process to delete duplicate rows in a table', divider='red')
            if st.button(f"1. Get Headers"):

                query1 = text(f"SELECT * FROM {selected_table} WHERE false;")
                with self.engine.connect() as connection:
                    result1 = connection.execute(query1)
                    column_names = result1.keys()
                    st.session_state[f"{selected_table}_column_names"] = column_names

            # Multiselect for selecting headers
            if f"{selected_table}_column_names" in st.session_state:
                selected_headers = st.multiselect(
                    f"Select minimum 3 header to delete duplicate in {selected_table}",
                    st.session_state[f"{selected_table}_column_names"],
                    key=f"{selected_table}_selected_headers"
                )

            # Button for running Query 2
            if st.button(f"2. Delete"):
                if f"{selected_table}_selected_headers" in st.session_state and st.session_state[f"{selected_table}_selected_headers"]:
                    selected_headers = st.session_state[f"{selected_table}_selected_headers"]
                    query2 = text(
                        f"DELETE FROM {selected_table} "
                        f"WHERE ctid IN ("
                        f"    SELECT ctid"
                        f"    FROM ("
                        f"        SELECT ctid,"
                        f"            ROW_NUMBER() OVER ("
                        f"                PARTITION BY {', '.join(f'"{header}"' for header in selected_headers)}"
                        f"            ) AS rn"
                        f"        FROM {selected_table}"
                        f"    ) t"
                        f"    WHERE rn > 1"
                        f");"
                    )

                    # Print out the appended query 2 result
                    st.code(query2, language="sql")

                    # Use SQL engine function using the code inside the function
                    with self.engine.begin() as connection:
                        connection.execute(query2)
                        st.success("Duplicates deleted successfully!")
                else:
                    st.warning(f"Please run Get Headers for {selected_table} first and select at least 3 headers.")
        except Exception as error:
            st.error(f"Error deleting duplicates: {error}")
