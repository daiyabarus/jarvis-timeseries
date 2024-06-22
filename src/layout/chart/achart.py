import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Dict


class ChartPlotter:
    def __init__(
        self,
        data: pd.DataFrame,
        color_map: Dict,
        sector_col: str,
        cell_header_col: str,
        date_id_col: str,
    ):
        self.data = data
        self.color_map = color_map
        self.sector_col = sector_col
        self.cell_header_col = cell_header_col
        self.date_id_col = date_id_col

    def plot_chart(self, y_column: str, yaxis_range: List[float]):
        if self.data is None:
            st.error("No data available for plotting.")
            return

        col1, col2, col3 = st.columns(3)
        cont1 = col1.container()
        cont2 = col2.container()
        cont3 = col3.container()

        unique_sectors = self.data[self.sector_col].unique()
        containers = [cont1, cont2, cont3][: len(unique_sectors)]

        for sector, col in zip(unique_sectors, containers):
            with col:
                sector_data = self.data[self.data[self.sector_col] == sector]
                self._create_sector_plot(sector_data, y_column, yaxis_range, sector)

    def _create_sector_plot(
        self,
        sector_data: pd.DataFrame,
        y_column: str,
        yaxis_range: List[float],
        sector: int,
    ):
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        for header in sector_data[self.cell_header_col].unique():
            header_data = sector_data[sector_data[self.cell_header_col] == header]
            fig.add_trace(
                go.Scatter(
                    x=header_data[self.date_id_col],
                    y=header_data[y_column],
                    mode="lines+markers",
                    name=f"{header}{sector}",
                    line=dict(color=self.color_map[sector][header]),
                ),
                secondary_y=False,
            )

        fig.update_layout(
            title_text=f"SECTOR {sector}",
            margin=dict(r=30, t=50, b=30),
            template="plotly_white",
            yaxis=dict(range=yaxis_range),
            xaxis=dict(tickformat="%m/%d/%y", tickangle=-45),
            autosize=True,
            showlegend=True,
            width=600,
            height=300,
        )

        st.plotly_chart(fig, use_container_width=True)


# plotter = ChartPlotter(data, color_map, sector_col='SECTOR', cell_header_col='CELL_HEADER', date_id_col='DATE_ID')
# plotter.plot_chart(y_column='your_y_column', yaxis_range=[0, 100])
