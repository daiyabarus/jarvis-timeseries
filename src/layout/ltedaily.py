import streamlit as st
import altair as alt
import pandas as pd


class LteDaily:
    def __init__(self, db_utils):
        self.db_utils = db_utils

    def create_line_chart(self, df):
        st.header("CSSR")
        if df is not None:
            source = df
            chart = (
                alt.Chart(source)
                .mark_line()
                .encode(x="DATE_ID", y="Call_Setup_Success_Rate", color="sector")
                .properties(width=600, height=200)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.warning("No data available to create the chart.")

    def run(self, selected_table: str, df: pd.DataFrame):
        self.create_line_chart(df)
