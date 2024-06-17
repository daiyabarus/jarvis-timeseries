import streamlit as st
import altair as alt
import pandas as pd

from streamlit_dynamic_filters import DynamicFilters


# TODO: Add the necessary imports and dynamicfilters
# TODO: Add the container to display the chart


class LteDaily:
    def __init__(self, db_utils):
        self.db_utils = db_utils

    def run(self, df: pd.DataFrame):
        if not df.empty:
            filter = DynamicFilters(df, filters=["siteid", "sector", "CELL_NAME"])
            filter.display_filters(location="columns", num_columns=3, gap="small")
            new_df = filter.filter_df()
            filter.display_df()
            self.create_line_chart(new_df)
        else:
            st.warning("No data available to create the chart.")

    def create_line_chart(self, new_df):
        st.header("CSSR")
        if not new_df.empty:
            source = new_df
            chart = (
                alt.Chart(source)
                .mark_line()
                .encode(x="DATE_ID", y="Call_Setup_Success_Rate", color="CELL_NAME")
                .properties(width=600, height=200)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.warning("No data available to create the chart.")
