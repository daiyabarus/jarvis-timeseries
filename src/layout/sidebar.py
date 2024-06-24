import streamlit as st
import sqlite3
import pandas as pd
from typing import Any, Dict


class DatabaseHandler:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        self.connection = sqlite3.connect(self.db_path)

    @st.cache_data(ttl=600)
    def get_tables(_self):
        if _self.connection:
            query = "SELECT name FROM sqlite_master WHERE type='table';"
            tables = pd.read_sql_query(query, _self.connection)["name"].tolist()
            return tables

    @st.cache_data(ttl=600)
    def get_table_data(_self, table_name: str):
        if _self.connection:
            query = f"SELECT * FROM {table_name};"
            data = pd.read_sql_query(query, _self.connection)
            return data

    def close(self):
        if self.connection:
            self.connection.close()


def sidebar(page: str) -> Dict[str, Any]:
    side_bar_mods()
    db_handler = None
    options = {"selected_table": None, "dataframe": None}
    with st.sidebar:
        col1, col2 = st.columns(2)
        # col1.image("assets/signaltower.png", width=200)
        col2.markdown("# ")
        st.markdown(
            """
            <style>
            [data-testid="collapsedControl"] {
                    display: none;
                }
            #MainMenu, header, footer {visibility: hidden;}
            .appview-container .main .block-container {
                padding-top: 1px;
                padding-left: 0.5rem;
                padding-right: 0.5rem;
                padding-bottom: 1px;
            }
            .stImage img {
                display: block;
                margin-left: auto;
                margin-right: auto;
            }
            </style>
            <h3 style="text-align: center; color: #000000;">Behind The Signal</h3>
            """,
            unsafe_allow_html=True,
        )
        # st.divider(color="black", key="title")

        db_path = "database/database.db"  # TAG this with the correct path
        db_handler = DatabaseHandler(db_path)
        db_handler.connect()

        col1, col2, col3 = st.columns(3)
        if col1.button("NR"):
            st.session_state["dashboard_tab"] = "NR"
        if col2.button("LTE"):
            st.session_state["dashboard_tab"] = "LTE"
        if col3.button("GSM"):
            st.session_state["dashboard_tab"] = "GSM"

        # Select table
        tables = db_handler.get_tables()
        if tables:
            selected_table = st.selectbox(
                f"Select Table ({page})", tables, key=f"{page}_selected_table"
            )
            if selected_table:
                # Query table
                try:
                    data = db_handler.get_table_data(selected_table)
                    options["selected_table"] = selected_table
                    options["dataframe"] = data

                    # Store headers
                    if page in ["NR", "LTE", "GSM"]:
                        col1, col2 = st.columns(2)
                        min_date = col1.selectbox(
                            f"Min DATE ({page})",
                            options=data["DATE_ID"].unique().tolist(),
                            key=f"{page}_min_date",
                        )
                        max_date = col2.selectbox(
                            f"Max DATE ({page})",
                            options=data["DATE_ID"].unique().tolist(),
                            key=f"{page}_max_date",
                        )
                        options["DATE_ID"] = (min_date, max_date)

                        if page == "NR":
                            options["ERBS"] = st.multiselect(
                                f"ERBS ({page})",
                                options=data["ERBS"].unique().tolist(),
                                key=f"{page}_erbs",
                            )
                            options["NRCELL_ID"] = st.multiselect(
                                f"NRCELL_ID ({page})",
                                options=data["NRCELL_ID"].unique().tolist(),
                                key=f"{page}_nrcell_id",
                            )
                        elif page == "LTE":
                            options["ERBS"] = st.multiselect(
                                f"ERBS ({page})",
                                options=data["ERBS"].unique().tolist(),
                                key=f"{page}_erbs",
                            )
                            options["EUTRANCELL"] = st.multiselect(
                                f"EUTRANCELL ({page})",
                                options=data["EUTRANCELL"].unique().tolist(),
                                key=f"{page}_eutrancell",
                            )
                        elif page == "GSM":
                            options["BSC"] = st.multiselect(
                                f"BSC ({page})",
                                options=data["BSC"].unique().tolist(),
                                key=f"{page}_bsc",
                            )
                            options["GERANCELL"] = st.multiselect(
                                f"GERANCELL ({page})",
                                options=data["GERANCELL"].unique().tolist(),
                                key=f"{page}_gerancell",
                            )

                    # Run query button
                    if st.button(f"Run Query ({page})"):
                        query = f"SELECT * FROM {selected_table} WHERE 1=1"
                        if "DATE_ID" in options:
                            query += f" AND DATE_ID BETWEEN '{options['DATE_ID'][0]}' AND '{options['DATE_ID'][1]}'"
                        if "ERBS" in options and options["ERBS"]:
                            query += f" AND ERBS IN ({', '.join([f'\"{x}\"' for x in options['ERBS']])})"
                        if "NRCELL_ID" in options and options["NRCELL_ID"]:
                            query += f" AND NRCELL_ID IN ({', '.join([f'\"{x}\"' for x in options['NRCELL_ID']])})"
                        if "EUTRANCELL" in options and options["EUTRANCELL"]:
                            query += f" AND EUTRANCELL IN ({', '.join([f'\"{x}\"' for x in options['EUTRANCELL']])})"
                        if "BSC" in options and options["BSC"]:
                            query += f" AND BSC IN ({', '.join([f'\"{x}\"' for x in options['BSC']])})"
                        if "GERANCELL" in options and options["GERANCELL"]:
                            query += f" AND GERANCELL IN ({', '.join([f'\"{x}\"' for x in options['GERANCELL']])})"

                        result_data = pd.read_sql_query(query, db_handler.connection)
                        st.dataframe(result_data)
                        options["filtered_dataframe"] = result_data

                except KeyError as e:
                    st.error(
                        f"Error: Please select another Table. The selected table does not contain the expected column: {str(e)}"
                    )

        db_handler.close()

    return options


def side_bar_mods():
    html_injection = """
    <style>
        /* Custom Sidebar Padding */
        div[data-testid="stSidebarUserContent"] {
            padding-top: 1rem;
        }

        .st-emotion-cache-dvne4q {
            padding-right: 1rem;
            padding-bottom: 1rem;
            padding-left: 1rem;
        }

        /* New CSS Styles */
        :root{
            /* ===== Colors ===== */
            --body-color: #E4E9F7;
            --sidebar-color: #FFF;
            --primary-color: #9932CC;
            --primary-color-light: #F6F5FF;
            --toggle-color: #DDD;
            --text-color: #707070;

            /* ====== Transition ====== */
            --tran-03: all 0.2s ease;
            --tran-03: all 0.3s ease;
            --tran-04: all 0.3s ease;
            --tran-05: all 0.3s ease;
        }

        body{
            min-height: 100vh;
            background-color: var(--body-color);
            transition: var(--tran-05);
        }

        ::selection{
            background-color: var(--primary-color);
            color: #fff;
        }

        body.dark{
            --body-color: #18191a;
            --sidebar-color: #242526;
            --primary-color: #3a3b3c;
            --primary-color-light: #3a3b3c;
            --toggle-color: #fff;
            --text-color: #ccc;
        }
    </style>
    """

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
