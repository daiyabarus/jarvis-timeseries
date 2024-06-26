# pageltedaily.py
import pandas as pd
import streamlit as st
import streamlit_antd_components as sac
from dbcon import DatabaseHandler
from enumdaily.enumdailylte import LTEDailyGut
from streamlit_extras.mandatory_date_range import date_range_picker
from streamlit_extras.stylable_container import stylable_container

st.set_page_config(layout="wide")

# sac.buttons([sac.ButtonsItem(icon=sac.BsIcon(name='house-door-fill', size=50, color='gray'))], align='center', variant='text'


class LTEDataFilterApp:
    def __init__(self, db_path):
        self.db = DatabaseHandler(db_path)
        self.marginpage()
        self.db.connect()

    def marginpage(self):
        st.markdown(
            """
            <style>
            [data-testid="collapsedControl"] {
                    display: none
                }
            #MainMenu, header, footer {visibility: hidden;}
            .appview-container .main .block-container
            {
                padding-top: 1px;
                padding-left: 1rem;
                padding-right: 1rem;
                padding-bottom: 1px;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    def run(self):

        selected_table = LTEDailyGut.TABLE.value

        min_date = self.db.get_min_date(selected_table, LTEDailyGut.DATEID.value)
        max_date = self.db.get_max_date(selected_table, LTEDailyGut.DATEID.value)
        erbs_options = self.db.get_erbs(selected_table, LTEDailyGut.ERBS.value)
        cell_options = self.db.get_cell(selected_table, LTEDailyGut.CELL.value)

        # Layout columns
        col1,col2,col3,col4,col5 = st.columns([0.6, 0.6, 0.6, 0.6, 0.1])
        con5 = col5.container()
        con1 = col1.container()
        con2 = col2.container()
        con3 = col3.container()
        con4 = col4.container()

        # MARK : Date range
        with con5:
            choice = sac.buttons([sac.ButtonsItem(icon=sac.BsIcon(name='house-door-fill', size=50, color='gray'))], align='center', variant='text')
                if choice:
                    st.switch_page("home")
                else:
                    None

        with con1:
            with stylable_container(
                "datepicker",
                """
                input {
                    color: #666667;
                    background-color: #FFFFFF !important;
                    font-size: 12px;
                    position: relative;
                    padding: 10px 15px;
                }
                div[role="presentation"] div {
                    color: #666667;
                    background-color: #FFFFFF !important;
                    font-size: 12px !important;
                    border-radius: 6px;
                    text-decoration: none;
                }
                div[class="st-b3 st-d0"] button {
                    color: #666667;
                    background-color: #FFFFFF !important;
                    border: 1px solid #1E90FF;
                    border-radius: 4px;
                    padding: 5px 10px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                }
                                """,
            ):
                min_value=pd.to_datetime(min_date)
                max_value=pd.to_datetime(max_date)
                data_range=date_range_picker(
                    "DATE RANGE",
                    default_start=min_value,
                    default_end=max_value,
                )

        # MARK : SITEID
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
            selected_erbs=st.multiselect(
                    "SITEID",
                    options=erbs_options,
                    key="siteid",
                )

        # MARK : eutrancell
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
                selected_cells=st.multiselect(
                    "CELL",
                    options=cell_options,
                    key="cells",
                )

        # MARK : Run query filter
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
                    top: 27px;
                }
                """,
            ):
                filter_button=st.button("FILTER", key="filter1")

        def format_date(date):
            return date.strftime("%m/%d/%Y")
            # return f"{date.month}/{date.day}/{date.year}" # MARK: for using not leading zero in date

        if filter_button:
            query_conditions=["1=1"]

            if data_range:
                start_date, end_date=data_range
                query_conditions.append(
                    f"{LTEDailyGut.DATEID.value} BETWEEN '{format_date(start_date)}' AND '{format_date(end_date)}'"
                )

            if selected_erbs:
                erbs_condition=f"{LTEDailyGut.ERBS.value} IN ({', '.join([f'\"{erbs}\"' for erbs in selected_erbs])})"
                query_conditions.append(erbs_condition)

            if selected_cells:
                cells_condition=f"{LTEDailyGut.CELL.value} IN ({', '.join([f'\"{cell}\"' for cell in selected_cells])})"
                query_conditions.append(cells_condition)

            where_clause=" AND ".join(query_conditions)
            query=f"SELECT * FROM {selected_table} WHERE {where_clause};"
            # st.write(query)

            filtered_data=pd.read_sql_query(query, self.db.connection)

            st.write(filtered_data)
        else:
            sac.result(
                label="Alert",
                description="Please select filter options and click Filter to run the query.",
            )
            # sac.alert(
            #     label="Alert",
            #     description="Please select filter options and click Filter to run the query.",
            #     banner=True,
            #     icon=True,
            #     closable=True,
            # )
            # st.warning(
            #     "Please select filter options and click Filter to run the query."
            # )


if __name__ == "__main__":
    app=LTEDataFilterApp(LTEDailyGut.DB_PATH.value)
    app.run()
