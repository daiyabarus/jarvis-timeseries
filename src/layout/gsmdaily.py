# gsmdaily.py
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots


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

            # Define the range for the y-axis
            yaxis_range = [0, 103]  # Adjust according to your needs

            st.markdown(
                """
                <style>
                .column-box {
                    border: 2px solid #d3d3d3;
                    border-radius: 5px;
                    padding: 10px;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

            col1, col2, col3 = st.columns(3)
            con1 = col1.container(border=True)
            con2 = col2.container(border=True)
            con3 = col3.container(border=True)

            with con1:
                # st.markdown('<div class="column-box">', unsafe_allow_html=True)
                self.plot_sector_chart(1, yaxis_range)
                # st.markdown("</div>", unsafe_allow_html=True)
            with con2:
                # st.markdown('<div class="column-box">', unsafe_allow_html=True)
                self.plot_sector_chart(2, yaxis_range)
                # st.markdown("</div>", unsafe_allow_html=True)
            with con3:
                # st.markdown('<div class="column-box">', unsafe_allow_html=True)
                self.plot_sector_chart(3, yaxis_range)
                # st.markdown("</div>", unsafe_allow_html=True)

    def plot_sector_chart(self, sector, yaxis_range):
        sector_data = self.data[self.data["SECTOR"] == sector]

        fig = make_subplots(specs=[[{"secondary_y": False}]])
        fig.add_trace(
            go.Scatter(
                x=sector_data["DATE_ID"],
                y=sector_data["Availability"],
                mode="lines+markers",
                line=dict(color="#E60000"),
                showlegend=False,
            ),
            secondary_y=False,
        )

        fig.update_layout(
            title_text=f"SECTOR {sector}",
            title_x=0.5,
            template="plotly_white",
            yaxis=dict(range=yaxis_range),
            xaxis=dict(tickformat="%m/%d/%y", tickangle=-45),
            autosize=True,
            showlegend=False,
            legend=dict(orientation="v", yanchor="top", y=0.99, xanchor="left", x=0.01),
            width=600,
            height=350,
        )
        fig.update_yaxes(secondary_y=False)

        st.plotly_chart(fig, use_container_width=True)


def gsm_daily_page(df: pd.DataFrame):
    # st.title("GSM Daily Metrics")
    gsm_daily = GsmDaily(df)
    gsm_daily.plot_chart()
