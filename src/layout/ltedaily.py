import streamlit as st
import altair as alt

from streamlit_dynamic_filters import DynamicFilters


# TODO: Add the necessary imports and dynamicfilters
# TODO: Add the container to display the chart



class LteDaily:
    def __init__(self, db_utils):
        self.db_utils = db_utils

    def run(self, df):
        if not df.empty:

        else:
            st.warning("No data available to create the chart.")

    def create_line_chart(self, df):
        st.header("CSSR")
        if not df.empty:
            source = df
            chart = (
                alt.Chart(source)
                .mark_line()
                .encode(x="DATE_ID", y="Call_Setup_Success_Rate", color="CELL_NAME")
                .properties(width=600, height=400)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.warning("No data available to create the chart.")
