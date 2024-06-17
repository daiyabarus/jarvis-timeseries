import streamlit as st
from utils.db_process import DatabaseUtils
from streamlit_dynamic_filters import DynamicFilters
import streamlit_antd_components as sac
from typing import Any, Dict


def sidebar(page: str) -> Dict[str, Any]:
    side_bar_mods()
    with st.sidebar:
        col1, col2 = st.columns(2)
        col1.image("assets/jarvis.png", width=200)
        col2.markdown("# ")
        col2.markdown("# ")

        st.markdown(
            "<h3 style='text-align: center; color: grey;'>Jarvis Dashboard</h3>",
            unsafe_allow_html=True,
        )
        sac.divider(color="black", key="title")

        options = {}
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


def getlte():
    db_utils = DatabaseUtils()
    selected_table = db_utils.select_table()
    df = db_utils.get_table_dataframe()

    if df is not None:
        filter = DynamicFilters(df, filters=["neid", "CELL_NAME", "sector"])
    else:
        filter = None
        st.warning("No data available for the selected table.")

    return selected_table, df, filter
