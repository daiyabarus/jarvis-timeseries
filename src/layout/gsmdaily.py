# gsmdaily.py
import streamlit as st
import pandas as pd
import plotly.express as px


class GsmDaily:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def transform_data(self):
        self.data["SECTOR"] = self.data["GERANCELL"].apply(
            lambda x: self.calculate_sector(x)
        )

    @staticmethod
    def calculate_sector(gerancell: str) -> int:
        sector_mapping = {
            "0": 1,
            "1": 1,
            "2": 2,
            "3": 3,
            "4": 1,
            "5": 2,
            "6": 3,
            "7": 1,
            "8": 2,
            "9": 3,
            "A": 1,
            "B": 2,
            "C": 3,
        }
        last_char = gerancell[-1].upper()
        return sector_mapping.get(last_char, 0)

    def plot_chart(self):
        if self.data is not None:
            self.transform_data()

            # Filter by SECTOR and plot charts
            for sector in [1, 2, 3]:
                sector_data = self.data[self.data["SECTOR"] == sector]
                fig = px.line(
                    sector_data,
                    x="DATE_ID",
                    y="Availability",
                    color="GERANCELL",
                    title=f"Sector {sector}",
                    labels={"DATE_ID": "Date", "Availability": "Availability"},
                    template="plotly_white",
                )
                fig.update_layout(
                    xaxis_title=None,
                    yaxis_title=None,
                    legend_title_text="GERANCELL",
                    xaxis=dict(tickformat="%m/%d/%y"),
                    legend=dict(
                        orientation="v",
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=0.01,
                    ),
                    autosize=True,
                )
                st.plotly_chart(fig, use_container_width=True)


def gsm_daily_page(df: pd.DataFrame):
    gsm_daily = GsmDaily(df)
    gsm_daily.plot_chart()
