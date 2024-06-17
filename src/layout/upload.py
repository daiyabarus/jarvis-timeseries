import streamlit as st
from utils.db_con import DatabaseConnector
import pandas as pd
import io


class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.tables = []
        self.selected_table = None

    def connect_to_database(self):
        try:
            db_connector = DatabaseConnector()
            self.conn = db_connector.connect()
            if self.conn:
                st.success("Connected to the database!")
                self.get_tables()
            else:
                st.error("Failed to connect to the database.")
        except Exception as error:
            st.error(f"Error connecting to the database: {error}")

    def get_tables(self):
        if self.conn is None:
            st.error("Not connected to the database.")
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
            self.tables = [table[0] for table in cursor.fetchall()]
        except Exception as error:
            st.error(f"Error retrieving tables: {error}")
        finally:
            cursor.close()

    def print_table(self, table_name):
        if self.conn is None:
            st.error("Not connected to the database.")
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name}")
            result = cursor.fetchall()
            st.table(result)
        except Exception as error:
            st.error(f"Error printing table: {error}")
        finally:
            cursor.close()

    def select_table(self):
        if self.conn is None:
            st.error("Not connected to the database.")
            return None

        selected_table = st.selectbox("Select a table", self.tables)
        if selected_table:
            cursor = self.conn.cursor()
            cursor.execute(f'SELECT MAX("DATE_ID") from {selected_table}')
            result = cursor.fetchall()
            st.write(f"Latest date in the **{selected_table}** :")
            st.write(result[0][0])

        self.selected_table = selected_table
        return selected_table


class UploadButton:
    def __init__(self):
        self.conn = None
        self.selected_table = None

    def connect_to_database(self):
        try:
            db_connector = DatabaseConnector()
            self.conn = db_connector.connect()
        except Exception as error:
            st.error(f"Error connecting to the database: {error}")

    def run_query(self, query):
        if self.conn is None:
            st.error("Not connected to the database.")
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            result = cursor.fetchall()
            st.table(result)
        except Exception as error:
            st.error(f"Error running the query: {error}")
        finally:
            cursor.close()

    def upload_button(self, selected_table):
        if self.conn is None:
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
                    cursor = self.conn.cursor()
                    csv_buffer = io.StringIO()
                    df.to_csv(csv_buffer, index=False, header=False)
                    csv_buffer.seek(0)
                    cursor.copy_expert(
                        f"COPY {selected_table} FROM STDIN WITH CSV DELIMITER ','",
                        csv_buffer,
                    )

                    # Commit the changes
                    self.conn.commit()
                    st.success(
                        f"File '{uploaded_file.name}' uploaded and data inserted into the database!"
                    )
                    cursor.close()
            except Exception as error:
                st.error(f"Error uploading files and inserting data: {error}")
                self.conn.rollback()
                cursor.close()
