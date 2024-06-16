import streamlit as st
from streamlit_dynamic_filters import DynamicFilters

# import altair as alt


class LteDaily:
    def __init__(self, db_utils):
        self.db_utils = db_utils
        self.selected_table = None
        self.df = None
        self.filter = None

    def select_table_and_get_dataframe(self):
        self.selected_table = self.db_utils.select_table()
        self.df = self.db_utils.get_table_dataframe()

        if self.df is not None:
            self.filter = DynamicFilters(
                self.df, filters=["siteid", "neid", "Band Type"]
            )
        else:
            st.warning("No data available for the selected table.")

    def display_filters(self):
        if self.filter is not None:
            self.filter.display_filters()

    def display_dataframe(self):
        if self.df is not None:
            st.dataframe(self.df)

    # def create_charts(self):
    #     if self.df is not None:
    #         alt.Chart(data=self.df).mark_line().encode(
    #             x="date",
    #             y="Call Setup Success Rate(%)",
    #         ).properties(width=600, height=400).interactive()

    #     def show_line_chart(chart):
    #         chart.display()
    #         # # Create Line Chart
    #         # @LineChart(
    #         #     self.df, "date", "Cell_DL_Avg_Throughput(Kbps)", color="Band Type"
    #         # )
    #         # def show_line_chart(chart):
    #         #     chart.display()

    #         # # Create Bar Chart
    #         # @BarChart(
    #         #     self.df, "Siteid_Sector", "Total_Traffic_Volume(GB)", color="Band Type"
    #         # )
    #         # def show_bar_chart(chart):
    #         #     chart.display()

    #         # # Create Scatter Chart
    #         # @ScatterChart(
    #         #     self.df,
    #         #     "User_DL_Avg_Throughput(Kbps)",
    #         #     "User_UL_Avg_Throughput(Kbps)",
    #         #     color="Band Type",
    #         #     size="CQI_Average_Ver2(Without 256 qam)",
    #         #     tooltip=[
    #         #         "siteid",
    #         #         "User_DL_Avg_Throughput(Kbps)",
    #         #         "User_UL_Avg_Throughput(Kbps)",
    #         #     ],
    #         # )
    #         # def show_scatter_chart(chart):
    #         #     chart.display()

    #         # # Display charts
    #         show_line_chart()
    #         # show_bar_chart()
    #         # show_scatter_chart()

    def run(self):
        self.select_table_and_get_dataframe()
        self.display_filters()
        self.display_dataframe()
        # self.create_charts()
