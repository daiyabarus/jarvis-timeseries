from utils.dbcon import DatabaseHandler
import pandas as pd
import streamlit as st
from streamlit_dynamic_filters import DynamicFilters
from typing import Optional, List
from plotly.subplots import make_subplots
import plotly.graph_objects as go


class GSMDailyAnalyzer:
    def __init__(self):
        self.data = self.get_filtered_gsm_data()
        if self.data is not None:
            self.transform_data()

    def get_filtered_gsm_data(self) -> Optional[pd.DataFrame]:
        db_handler = None
        try:
            db_path = "database/database.db"
            db_handler = DatabaseHandler(db_path)
            db_handler.connect()

            db_data = db_handler.get_table_data("eri_gsm")
            df = pd.DataFrame(db_data)

            df_filter = DynamicFilters(
                df, filters=["BSC", "GERANCELL"], filters_name="gsm_filter"
            )
            df_filter.display_filters(location="columns", num_columns=2, gap="small")
            return df_filter.filter_df()
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            return None
        finally:
            if db_handler and db_handler.connection:
                db_handler.close()

    def transform_data(self):
        self.data["SECTOR"] = self.data["GERANCELL"].apply(self.calculate_sector)

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

    @staticmethod
    def gerancell_header(gerancell: pd.Series) -> str:
        unique_gerancells = gerancell.unique()
        return (
            " ".join(unique_gerancells)
            if len(unique_gerancells) > 1
            else unique_gerancells[0]
        )

    def plot_chart(self, y_column: str, yaxis_range: List[float]):
        if self.data is None:
            st.error("No data available for plotting.")
            return

        cols = st.columns(3)
        for sector, col in zip([1, 2, 3], cols):
            with col.container(border=True):
                sector_data = self.data[self.data["SECTOR"] == sector]
                self._create_sector_plot(sector_data, y_column, yaxis_range, sector)

    def _create_sector_plot(
        self,
        sector_data: pd.DataFrame,
        y_column: str,
        yaxis_range: List[float],
        sector: int,
    ):
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Scatter(
                x=sector_data["DATE_ID"],
                y=sector_data[y_column],
                mode="lines",
                name=f"Sector {sector}",
                line=dict(color="#E60000"),
            ),
            secondary_y=False,
        )

        fig.update_layout(
            title_text=f"SECTOR {sector}",
            template="plotly_white",
            yaxis=dict(range=yaxis_range),
            yaxis2=dict(range=yaxis_range),
            xaxis=dict(tickformat="%m/%d/%y", tickangle=-45),
            autosize=True,
            legend=dict(
                orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5
            ),
            width=600,
            height=350,
        )

        st.plotly_chart(fig, use_container_width=True)


def gsm_daily_page():
    analyzer = GSMDailyAnalyzer()
    if analyzer.data is not None:
        yaxis_ranges = [[0, 100], [-105, -145], [0, 50]]

        charts = [
            ("Availability", "Availability", yaxis_ranges[0]),
            ("Interference", "Interference_UL_ICM_Band4_Band5", yaxis_ranges[2]),
            ("Call Setup Success Rate", "Call_Setup_Success_Rate", yaxis_ranges[0]),
        ]

        for title, column, range in charts:
            st.markdown(
                f"<h3 style='text-align: left; color: grey;'>{title}</h3>",
                unsafe_allow_html=True,
            )
            analyzer.plot_chart(column, range)


if __name__ == "__main__":
    gsm_daily_page()
