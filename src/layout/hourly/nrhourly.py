import streamlit as st
import pandas as pd


class NRHourly:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def transform_data(self):
        pass  # Add your transformation logic here

    def plot_chart(self):
        st.write("LTE Data Visualization Coming Soon...")


def nr_hourly_page(df: pd.DataFrame):
    lte_page = NRHourly(df)
    lte_page.transform_data()
    lte_page.plot_chart()
