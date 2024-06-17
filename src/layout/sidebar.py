import streamlit as st
import pandas as pd
from sqlalchemy import text
from utils.dbutils import get_db_connection


def sidebar():
    # Connect to the database using dbutils
    db_engine = get_db_connection()

    # Create a Connection object from the Engine
    with db_engine.connect() as db_connection:
        # Get the list of table_names from the database
        table_names = get_table_names(db_connection)

        # Display a selectbox to choose a table_name
        selected_table = st.sidebar.selectbox("TABLE", table_names)

        if selected_table:
            # Execute a query to get data from the selected table
            query = text(f"SELECT * FROM {selected_table}")
            df = pd.read_sql(query, db_connection)

            # Display a multiselect to choose siteid
            site_ids = df["siteid"].unique().tolist()
            selected_site_ids = st.sidebar.multiselect("SITEID", site_ids)

            # Submit button to execute the query
            submit_button = st.sidebar.button("Submit")

            # Reset button to reset the query process
            reset_button = st.sidebar.button("Reset")

            if reset_button:
                # Reset selected_site_ids and clear the query result
                selected_site_ids.clear()
                st.experimental_rerun()

            if submit_button and selected_site_ids:
                # Execute the query based on the selected siteid
                if len(selected_site_ids) == 1:
                    query = text(
                        f"SELECT * FROM {selected_table} WHERE siteid LIKE '{selected_site_ids[0]}'"
                    )
                else:
                    conditions = " OR ".join(
                        [f"siteid LIKE '{site_id}'" for site_id in selected_site_ids]
                    )
                    query = text(f"SELECT * FROM {selected_table} WHERE {conditions}")

                df = pd.read_sql(query, db_connection)

                # Return selected_table and df
                return selected_table, df
            else:
                st.warning("Please select at least one Site ID and click Submit.")
        else:
            st.warning("Please select a table.")

    # If no table is selected or no siteid is selected, return None
    return None, None


def get_table_names(db_connection):
    # Execute a query to get the list of table_names from the database
    query = text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    )
    result = db_connection.execute(query)
    table_names = [row[0] for row in result]
    return table_names
