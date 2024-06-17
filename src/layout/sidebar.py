import streamlit as st
import pandas as pd
from sqlalchemy import text
from utils.dbutils import get_db_connection
from typing import Any, Dict
import streamlit_antd_components as sac


def sidebar(page: str) -> Dict[str, Any]:
    """Generate a sidebar for different pages with specific options.

    Args:
        page: The name of the current page.

    Returns:
        A dictionary containing options based on the provided page.
    """
    side_bar_mods()
    with st.sidebar:
        col1, col2 = st.columns(2)
        col1.image("assets/jarvis.png", width=200)
        col2.markdown("# ")
        col2.markdown("# ")

        st.markdown(
            "<h3 style='text-align: center; color: grey;'>Easy" " Dashboard</h3>",
            unsafe_allow_html=True,
        )
        sac.divider(color="black", key="title")

        options = {}
        if page == "LTE":
            options = querylte()
        elif page == "NR":
            options = querylte()

        return options


def side_bar_mods():
    html_injection = """
    <style>
    div[data-testid="stSidebarUserContent"] {
        padding-top: 3rem;
    }
    </style>
    """
    st.markdown(html_injection, unsafe_allow_html=True)

    html_injection = """
    <style>
    .st-emotion-cache-dvne4q {
        padding-right: 1rem;
        padding-bottom: 3rem;
        padding-left: 1rem;
    }
    </style>
    """
    st.markdown(html_injection, unsafe_allow_html=True)


def querylte():
    # Connect to the database using dbutils
    db_engine = get_db_connection()

    # Create a Connection object from the Engine
    with db_engine.connect() as db_connection:
        # Get the list of table_names from the database
        table_names = get_table_names(db_connection)

        # Display a selectbox to choose a table_name
        selected_table = st.sidebar.selectbox(
            "TABLE", table_names, key="table_selectbox"
        )

        if selected_table:
            # Execute a query to get data from the selected table
            query = text(f"SELECT * FROM {selected_table}")
            df = pd.read_sql(query, db_connection)

            # Display a multiselect to choose siteid
            site_ids = df["siteid"].unique().tolist()
            selected_site_ids = st.sidebar.multiselect(
                "SITEID", site_ids, key="siteid_multiselect"
            )

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
