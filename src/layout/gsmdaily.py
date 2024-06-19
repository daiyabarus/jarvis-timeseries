# gsmdaily.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
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
        return sector_mapping.get(last_char, 0)  # Default to 0 if not found

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
                # name="Availability",
                line=dict(color="#E60000"),
            ),
            secondary_y=False,
        )

        fig.update_layout(
            title_text=f"Sector {sector}",
            template="plotly_white",
            yaxis=dict(range=yaxis_range),
            # xaxis=dict(tickformat="%m/%d/%y", title="Date", tickangle=-45),
            xaxis=dict(tickformat="%m/%d/%y", tickangle=-45),
            autosize=True,
            showlegend=False,
            legend=dict(orientation="v", yanchor="top", y=0.99, xanchor="left", x=0.01),
            width=800,
            height=350,
        )
        # fig.update_yaxes(title_text="Availability", secondary_y=False)
        fig.update_yaxes(secondary_y=False)

        st.plotly_chart(fig, use_container_width=True)


def gsm_daily_page(df: pd.DataFrame):
    # st.title("GSM Daily Metrics")
    gsm_daily = GsmDaily(df)
    gsm_daily.plot_chart()


# gsmdaily.py
# import streamlit as st
# import pandas as pd
# import plotly.express as px


# class GsmDaily:
#     def __init__(self, data: pd.DataFrame):
#         self.data = data

#     def transform_data(self):
#         self.data["SECTOR"] = self.data["GERANCELL"].apply(
#             lambda x: self.calculate_sector(x)
#         )

#     @staticmethod
#     def calculate_sector(gerancell: str) -> int:
#         sector_mapping = {
#             "0": 1,
#             "1": 1,
#             "2": 2,
#             "3": 3,
#             "4": 1,
#             "5": 2,
#             "6": 3,
#             "7": 1,
#             "8": 2,
#             "9": 3,
#             "A": 1,
#             "B": 2,
#             "C": 3,
#         }
#         last_char = gerancell[-1].upper()
#         return sector_mapping.get(last_char, 0)

#     def plot_chart_avail(self):
#         if self.data is not None:
#             self.transform_data()

#             # Create three columns for each sector
#             col1, col2, col3 = st.columns(3)

#             # Filter by SECTOR and plot charts in each column
#             for sector, col in zip([1, 2, 3], [col1, col2, col3]):
#                 sector_data = self.data[self.data["SECTOR"] == sector]
#                 fig = px.line(
#                     sector_data,
#                     x="DATE_ID",
#                     y="Availability",
#                     color="GERANCELL",
#                     labels={"DATE_ID ": "Date", "Availability ": "Availability"},
#                     template="plotly_white",
#                     width=600,
#                     height=400,
#                 )
#                 fig.update_layout(
#                     xaxis_title=None,
#                     yaxis_title=None,
#                     xaxis=dict(tickformat="%d/%m/%y", tickangle=-45),
#                     showlegend=False,
#                     autosize=True,
#                 )
#                 col.plotly_chart(fig, use_container_width=True)

#     def plot_chart_icmband(self):
#         if self.data is not None:
#             self.transform_data()

#             # Create three columns for each sector
#             col1, col2, col3 = st.columns(3)

#             # Filter by SECTOR and plot charts in each column
#             for sector, col in zip([1, 2, 3], [col1, col2, col3]):
#                 sector_data = self.data[self.data["SECTOR"] == sector]
#                 fig = px.line(
#                     sector_data,
#                     x="DATE_ID",
#                     y="Interference_UL_ICM_Band4_Band5",
#                     color="GERANCELL",
#                     labels={
#                         "DATE_ID ": "Date",
#                         "Interference_UL_ICM_Band4_Band5 ": "Interference_UL_ICM_Band4_Band5",
#                     },
#                     template="plotly_white",
#                     width=600,
#                     height=400,
#                 )
#                 fig.update_layout(
#                     xaxis_title=None,
#                     yaxis_title=None,
#                     xaxis=dict(tickformat="%d/%m/%y", tickangle=-45),
#                     showlegend=False,
#                     autosize=True,
#                 )
#                 col.plotly_chart(fig, use_container_width=True)

#     def plot_chart_cssr(self):
#         if self.data is not None:
#             self.transform_data()

#             # Create three columns for each sector
#             col1, col2, col3 = st.columns(3)

#             # Filter by SECTOR and plot charts in each column
#             for sector, col in zip([1, 2, 3], [col1, col2, col3]):
#                 sector_data = self.data[self.data["SECTOR"] == sector]
#                 fig = px.line(
#                     sector_data,
#                     x="DATE_ID",
#                     y="Call_Setup_Success_Rate",
#                     color="GERANCELL",
#                     labels={
#                         "DATE_ID ": "Date",
#                         "Call_Setup_Success_Rate ": "Call_Setup_Success_Rate",
#                     },
#                     template="plotly_white",
#                     width=600,
#                     height=400,
#                 )
#                 fig.update_layout(
#                     xaxis_title=None,
#                     yaxis_title=None,
#                     xaxis=dict(tickformat="%d/%m/%y", tickangle=-45),
#                     showlegend=False,
#                     autosize=True,
#                 )
#                 col.plotly_chart(fig, use_container_width=True)


# def gsm_daily_page(df: pd.DataFrame):
#     gsm_daily = GsmDaily(df)
#     gsm_daily.plot_chart_avail()
#     gsm_daily.plot_chart_icmband()
#     gsm_daily.plot_chart_cssr()
