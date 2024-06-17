import streamlit as st
from streamlit_dynamic_filters import DynamicFilters
import altair as alt

filter_data = ["siteid", "CELL_NAME", "sector"]


class LteDaily:
    def __init__(self, db_utils):
        self.db_utils = db_utils
        self.selected_table = None
        self.df = None
        self.filter = None

    def select_table_and_get_dataframe(self):
        self.selected_table = self.db_utils.select_table()
        self.df = self.db_utils.get_table_dataframe()

        if self.df is not None:
            self.filter = DynamicFilters(self.df, filters=filter_data)
            self.filter.display_filters(location="columns", num_columns=3, gap="small")
        else:
            st.warning("No data available for the selected table.")

    def create_line_chart(self):
        st.header("CSSR")
        if self.df is not None:
            source = self.df
            chart = (
                alt.Chart(source)
                .mark_line()
                .encode(x="DATE_ID", y="Call_Setup_Success_Rate", color="sector")
                .properties(width=600, height=200)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.warning("No data available to create the chart.")

    def run(self):
        self.select_table_and_get_dataframe()
        self.create_line_chart()
