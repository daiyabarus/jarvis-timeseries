# pageltedaily.py
import pandas as pd
import streamlit as st
from dbcon import DatabaseHandler
from enumdaily.enumdailylte import HeaderLTEDaily
from streamlit_extras.mandatory_date_range import date_range_picker
from streamlit_extras.stylable_container import stylable_container

st.set_page_config(layout="wide")


class LTEDataFilterApp:
    def __init__(self, db_path):
        self.db = DatabaseHandler(db_path)
        self.db.connect()

    def run(self):
        selected_table = HeaderLTEDaily.TABLE.value

        min_date = self.db.get_min_date(selected_table, HeaderLTEDaily.DATEID.value)
        max_date = self.db.get_max_date(selected_table, HeaderLTEDaily.DATEID.value)
        erbs_options = self.db.get_erbs(selected_table, HeaderLTEDaily.ERBS.value)
        cell_options = self.db.get_cell(selected_table, HeaderLTEDaily.CELL.value)

        # Layout columns
        col1, col2, col3, col4 = st.columns([0.6, 0.6, 0.6, 0.6])
        con1 = col1.container()
        con2 = col2.container()
        con3 = col3.container()
        con4 = col4.container()

        with con1:
            with stylable_container(
                "datepicker",
                """
                input {
                    color: #D3D3D3;
                    background-color: #FFFFFF !important;
                }
                div[role="presentation"] div {
                    color: #D3D3D3;
                    background-color: #FFFFFF !important;
                    font-size: 8px !important;
                    border-radius: 6px;
                    text-decoration: none;
                }
                div[class="st-b3 st-d0"] button {
                    color: #FFFFFF;
                    background-color: #FFFFFF !important;
                    border: 1px solid #1E90FF;
                    border-radius: 4px;
                    padding: 5px 10px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                }
                div[class="st-b3 st-d0"] button:hover {
                    background-color: rgba(30, 144, 255, 0.1) !important;
                }
                .stDateInput {
                    position: relative;
                    top: 0px;
                }
                /* Make the date range picker background transparent */
                div[data-baseweb="input"] {
                    background-color: #FFFFFF !important;
                }
                /* Ensure the arrow remains visible */
                div[data-baseweb="input"]::after {
                    content: "";
                    position: absolute;
                    font-size: 8px;
                    right: 10px;
                    top: 50%;
                    transform: translateY(-50%);
                    width: 0;
                    height: 0;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 5px solid #1E90FF;
                    pointer-events: none;
                }
                """,
            ):
                min_value = pd.to_datetime(min_date)
                max_value = pd.to_datetime(max_date)
                data_range = date_range_picker(
                    "DATE RANGE",
                    default_start=min_value,
                    default_end=max_value,
                )

        with con2:
            with stylable_container(
                key="selected_erbs",
                css_styles="""
                /* Style for the multiselect container */
                div[data-baseweb="select"] > div {
                    background-color: transparent !important;
                    font-size: 12px !important;
                    border-radius: 6px;
                    text-decoration: none;
                }

                /* Style for the selected items */
                li>span {
                    color: white !important;
                    font-size: 12px;
                    background-color: blue !important;
                }

                /* Style for the dropdown items */
                li {
                    background-color: transparent !important;
                }

                /* Style for the label */
                .stSelectbox label {
                    color: #A195FD !important;
                    font-size: 12px !important;
                    font-weight: bold !important;
                    margin-bottom: 5px !important;
                }

                /* Style for the label icon (if any) */
                .stSelectbox label span {
                    color: #FF0000 !important;
                }

                /* Ensure the label is visible against transparent background */
                .stSelectbox {
                    background-color: rgba(255, 255, 255, 0.1) !important;
                    padding: 5px !important;
                    border-radius: 5px !important;
                }
                """,
            ):
                selected_erbs = st.multiselect(
                    "ERBS",
                    options=erbs_options,
                    key="erbs",
                )

        with con3:
            with stylable_container(
                key="selected_cell",
                css_styles="""
                div[data-baseweb="select"] > div {
                    background-color: transparent !important;
                    font-size: 12px !important;
                    border-radius: 6px;
                    text-decoration: none;
                    }

                li>span {
                    color: transparent !important;
                    font-size: 12px;
                    background-color: blue !important;
                    }


                li {
                    background-color: transparent !important;
                }
                    """,
            ):
                selected_cells = st.multiselect(
                    "CELL",
                    options=cell_options,
                    key="cells",
                )

        with con4:
            with stylable_container(
                key="filter1",
                css_styles="""
                button {
                    background-color: #556B2F;
                    border-radius: 10px;
                    color: white;
                    border: 2px solid indianred;
                    position:relative;
                    top: 28px;
                }
                """,
            ):
                filter_button = st.button("FILTER", key="filter1")

        def format_date(date):
            return f"{date.month}/{date.day}/{date.year}"

        if filter_button:
            query_conditions = ["1=1"]

            if data_range:
                start_date, end_date = data_range
                query_conditions.append(
                    f"{HeaderLTEDaily.DATEID.value} BETWEEN '{format_date(start_date)}' AND '{format_date(end_date)}'"
                )

            if selected_erbs:
                erbs_condition = f"{HeaderLTEDaily.ERBS.value} IN ({', '.join([f'\"{erbs}\"' for erbs in selected_erbs])})"
                query_conditions.append(erbs_condition)

            if selected_cells:
                cells_condition = f"{HeaderLTEDaily.CELL.value} IN ({', '.join([f'\"{cell}\"' for cell in selected_cells])})"
                query_conditions.append(cells_condition)

            where_clause = " AND ".join(query_conditions)
            query = f"SELECT * FROM {selected_table} WHERE {where_clause};"
            # st.write(query)

            filtered_data = pd.read_sql_query(query, self.db.connection)

            st.write(filtered_data)
        else:
            st.warning(
                "Please select filter options and click Filter to run the query."
            )


if __name__ == "__main__":
    app = LTEDataFilterApp(HeaderLTEDaily.DB_PATH.value)
    app.run()
