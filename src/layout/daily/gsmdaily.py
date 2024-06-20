# gsmdaily.py
import streamlit as st
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go


class GsmDaily:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def transform_data(self):
        self.data["SECTOR"] = self.data["GERANCELL"].apply(self.calculate_sector)

    def gerancell_header(self):
        unique_gerancells = self.data["GERANCELL"].unique()
        if len(unique_gerancells) > 1:
            gerancell_header = " ".join(unique_gerancells)
        else:
            gerancell_header = unique_gerancells[0]
        return gerancell_header

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

    def plot_chart(self, y_column: str, yaxis_range):
        if self.data is not None:
            self.transform_data()

            # Create three columns for each sector
            col1, col2, col3 = st.columns(3)
            cont1 = col1.container(border=True)
            cont2 = col2.container(border=True)
            cont3 = col3.container(border=True)

            # Filter by SECTOR and plot charts in each column
            for sector, col in zip([1, 2, 3], [cont1, cont2, cont3]):
                with col:
                    st.markdown('<div class="chart-box">', unsafe_allow_html=True)
                    sector_data = self.data[self.data["SECTOR"] == sector]

                    fig = make_subplots(specs=[[{"secondary_y": True}]])
                    fig.add_trace(
                        go.Scatter(
                            x=sector_data["DATE_ID"],
                            y=sector_data[y_column],
                            mode="lines+markers",
                            name=y_column,
                            line=dict(color="#E60000"),
                            showlegend=False,
                        ),
                        secondary_y=True,
                    )

                    fig.update_layout(
                        title_text=f"SECTOR {sector}",
                        title_x=0.5,
                        template="plotly_white",
                        yaxis=dict(range=yaxis_range),
                        xaxis=dict(tickformat="%m/%d/%y", tickangle=-45),
                        autosize=True,
                        showlegend=False,
                        legend=dict(
                            orientation="v",
                            yanchor="top",
                            y=0.99,
                            xanchor="left",
                            x=0.01,
                        ),
                        width=600,
                        height=350,
                    )
                    fig.update_yaxes(range=[0, 100], secondary_y=True)
                    fig.update_yaxes(range=[0, 100], secondary_y=True)

                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)


def gsm_daily_page(df: pd.DataFrame):
    yaxis_ranges = [[0, 100], [-105, -145]]

    # TAG: Edit on markdown line to change the title of the chart
    gsm_daily = GsmDaily(df)
    st.markdown(
        "<h3 style='text-align: left; color: grey;'>Availability</h3>",
        unsafe_allow_html=True,
    )
    gsm_daily.plot_chart("Availability", yaxis_ranges[0])
    st.markdown(
        "<h3 style='text-align: left; color: grey;'>Interference</h3>",
        unsafe_allow_html=True,
    )
    gsm_daily.plot_chart("Interference_UL_ICM_Band4_Band5", yaxis_ranges[0])
    st.markdown(
        "<h3 style='text-align: left; color: grey;'>Call Setup Success Rate</h3>",
        unsafe_allow_html=True,
    )
    gsm_daily.plot_chart("Call_Setup_Success_Rate", yaxis_ranges[0])
