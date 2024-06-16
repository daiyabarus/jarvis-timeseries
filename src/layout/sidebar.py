import streamlit as st
from utils.db_process import DatabaseUtils
from streamlit_dynamic_filters import DynamicFilters


def sidebar():
    # Connect to the database
    db_utils = DatabaseUtils()
    db_utils.connect_to_database()
    selected_table = db_utils.select_table()
    df = db_utils.get_table_dataframe()

    if df is not None:
        filter = DynamicFilters(df, filters=["siteid", "neid", "Band Type"])
        with st.sidebar:
            filter.display_filters()
        filter.display_df()
    db_utils.disconnect_from_database()
