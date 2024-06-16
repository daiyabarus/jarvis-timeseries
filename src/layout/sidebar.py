import streamlit as st
from utils.db_process import DatabaseUtils
from streamlit_dynamic_filters import DynamicFilters
import streamlit_antd_components as sac
from typing import Any, Dict


def sidebar(page: str) -> Dict[str, Any]:
    """
    Generate a sidebar for different pages with specific options.

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
        # col2.title("Jarvis")

        st.markdown(
            "<h3 style='text-align: center; color: grey;'>Jarvis Dashboard</h3>",
            unsafe_allow_html=True,
        )
        sac.divider(color="black", key="title")

        options = {}
        if page == "LTE":
            options = getlte()
        # elif page == "NR":
        #     options = getnr()
        # elif page == "GSM":
        #     options = getgsm()

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
    db_utils.connect_to_database()
    selected_table = db_utils.select_table()
    df = db_utils.get_table_dataframe()

    if df is not None:
        filter = DynamicFilters(df, filters=["siteid", "neid", "Band Type"])
        with st.sidebar:
            filter.display_filters()
        filter.display_df()
    db_utils.disconnect_from_database()


# def getnr():
#     db_utils = DatabaseUtils()
#     db_utils.connect_to_database()
#     selected_table = db_utils.select_table()
#     df = db_utils.get_table_dataframe()

#     if df is not None:
#         filter = DynamicFilters(df, filters=["LC", "ERBS", "freqband"])
#         with st.sidebar:
#             filter.display_filters()
#         filter.display_df()
#     db_utils.disconnect_from_database()


# def getgsm():
#     db_utils = DatabaseUtils()
#     db_utils.connect_to_database()
#     selected_table = db_utils.select_table()
#     df = db_utils.get_table_dataframe()

#     if df is not None:
#         filter = DynamicFilters(df, filters=["SITEID", "SECTOR"])
#         with st.sidebar:
#             filter.display_filters()
#         filter.display_df()
#     db_utils.disconnect_from_database()
