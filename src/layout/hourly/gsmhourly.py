from utils.dbcon import DatabaseHandler
import pandas as pd
import streamlit as st
from streamlit_dynamic_filters import DynamicFilters
from typing import Optional, List, Dict
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from config.colors import ColorPalette

st.set_page_config(layout="wide")


class GSMDHourlyAnalyzer:
    def __init__(self):
        self.data = self.get_filtered_gsm_data()
        self.color_map = None
        if self.data is not None:
            self.transform_data()
            self.color_map = self.generate_color_map()

    # @st.cache_resource(experimental_allow_widgets=True)
    def get_filtered_gsm_data(_self) -> Optional[pd.DataFrame]:
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
        self.data["CELL_HEADER"] = self.data["GERANCELL"].apply(lambda x: x[:-1])

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

    def generate_color_map(self) -> Dict[str, Dict[int, str]]:
        unique_headers = sorted(self.data["CELL_HEADER"].unique())
        color_map = {1: {}, 2: {}, 3: {}}
        for i, header in enumerate(unique_headers):
            for sector in [1, 2, 3]:
                color_map[sector][header] = ColorPalette.get_color(i)
        return color_map

    def plot_chart(self, y_column: str, yaxis_range: List[float]):
        if self.data is None:
            st.error("No data available for plotting.")
            return

        col1, col2, col3 = st.columns(3)
        cont1 = col1.container(border=True)
        cont2 = col2.container(border=True)
        cont3 = col3.container(border=True)

        # cols = st.columns(3)
        for sector, col in zip([1, 2, 3], [cont1, cont2, cont3]):
            with col:
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

        for header in sector_data["CELL_HEADER"].unique():
            header_data = sector_data[sector_data["CELL_HEADER"] == header]
            fig.add_trace(
                go.Scatter(
                    x=header_data["DATE_ID"],
                    y=header_data[y_column],
                    mode="lines+markers",
                    name=f"{header}{sector}",
                    line=dict(color=self.color_map[sector][header]),
                ),
                secondary_y=False,
            )

        fig.update_layout(
            title_text=f"SECTOR {sector}",
            margin_r=30,
            margin_t=50,
            margin_b=30,
            template="plotly_white",
            yaxis=dict(range=yaxis_range),
            xaxis=dict(tickformat="%m/%d/%y", tickangle=-45),
            autosize=True,
            showlegend=True,
            width=600,
            height=300,
        )

        st.plotly_chart(fig, use_container_width=True)

    def create_legend(self):
        if self.color_map is None:
            self.color_map = self.generate_color_map()

        col1, col2, col3 = st.columns(3)
        containers = [
            col1.container(border=True),
            col2.container(border=True),
            col3.container(border=True),
        ]

        for sector, container in zip([1, 2, 3], containers):
            sector_data = self.data[self.data["SECTOR"] == sector]
            unique_headers = sorted(sector_data["CELL_HEADER"].unique())

            for header in unique_headers:
                container.markdown(
                    f'<p style="color:{self.color_map[sector][header]};">● {header}{sector}</p>',
                    unsafe_allow_html=True,
                )


def gsm_hourly_page():
    analyzer = GSMDHourlyAnalyzer()
    if analyzer.data is not None:
        yaxis_ranges = [[0, 100], [-105, -145], [0, 20]]

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

        # Create legend after all charts
        # analyzer.create_legend()


if __name__ == "__main__":
    gsm_hourly_page()
