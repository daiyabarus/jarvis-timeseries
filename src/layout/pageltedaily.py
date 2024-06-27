import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit_antd_components as sac
from enumclass.enumdailylte import LTEDailyGut
from plotly.subplots import make_subplots
from streamlit_extras.mandatory_date_range import date_range_picker
from streamlit_extras.stylable_container import stylable_container
from utils.dbcon import DatabaseHandler

st.set_page_config(layout="wide")


class LTEDataFilterApp:
    def __init__(self, db_path):
        self.db = DatabaseHandler(db_path)
        self.data = None
        self.initialize_app()

    def initialize_app(self):
        self.marginpage()
        self.db.connect()
        self.initialize_session_state()

    def initialize_session_state(self):
        if "selected_erbs" not in st.session_state:
            st.session_state["selected_erbs"] = []
        if "selected_neid" not in st.session_state:
            st.session_state["selected_neid"] = []
        if "selected_cells" not in st.session_state:
            st.session_state["selected_cells"] = []
        if "data_range" not in st.session_state:
            st.session_state["data_range"] = None

    def marginpage(self):
        st.markdown(
            """
            <style>
            [data-testid="collapsedControl"] {
                    display: none;
                }
            #MainMenu, header, footer {visibility: hidden;}
            .appview-container .main .block-container {
                padding-top: 1px;
                padding-left: 1rem;
                padding-right: 1rem;
                padding-bottom: 1rem;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    def keep(self, key):
        st.session_state[key] = st.session_state["_" + key]

    def unkeep(self, key):
        st.session_state["_" + key] = st.session_state[key]

    def run(self):
        self.display_filters()
        self.display_filter_button()
        self.process_filter()

    def display_filter_button(self):
        css_styles = """
            <style>
                .custom-button {
                    background-color: transparent;
                    border: none;
                    position: absolute;
                    top: 15px;
                    right: 0px;
                    padding: 0;
                }
                .custom-button img {
                    width: 40px;
                    height: 40px;
                }
            </style>
        """
        st.markdown(css_styles, unsafe_allow_html=True)
        button_html = """
        <button class="custom-button" onclick="location.href='home'">
            <img src="https://img.icons8.com/?size=100&id=80319&format=png&color=000000" width="25" height="25">
        </button>
        """
        col1, col5 = st.columns([1, 1])[0], st.columns([1, 1])[1]
        col1.container().markdown(button_html, unsafe_allow_html=True)

        with col5.container():
            with stylable_container(
                key="filter1",
                css_styles="""
                button {
                    background-color: #E04F5F;
                    border-radius: 10px;
                    color: white;
                    border: 2px solid indianred;
                    position:relative;
                    top: 0px;
                }
                """,
            ):
                self.filter_button = st.button("FILTER", key="filter1")

    def display_filters(self):
        selected_table = LTEDailyGut.TABLE.value
        min_date = self.db.get_min_date(selected_table, LTEDailyGut.DATEID.value)
        max_date = self.db.get_max_date(selected_table, LTEDailyGut.DATEID.value)
        erbs_options = self.db.get_erbs(selected_table, LTEDailyGut.ERBS.value)
        neid_options = self.db.get_erbs(selected_table, LTEDailyGut.NEID.value)
        cell_options = self.db.get_cell(selected_table, LTEDailyGut.CELL.value)

        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        self.display_date_range_picker(col1, min_date, max_date)
        self.display_selector(col2, "SITEID", erbs_options, "selected_erbs")
        self.display_selector(col3, "NEID", neid_options, "selected_neid")
        self.display_selector(col4, "CELL", cell_options, "selected_cells")

    def display_date_range_picker(self, container, min_date, max_date):
        with container:
            with stylable_container(
                "datepicker",
                """
                input {
                    color: #666667;
                    background-color: #FFFFFF !important;
                    font-size: 12px;
                    position: relative;
                    padding: 10px 15px;
                }
                div[role="presentation"] div {
                    color: #666667;
                    background-color: #FFFFFF !important;
                    font-size: 12px !important;
                    border-radius: 6px;
                    text-decoration: none;
                }
                div[class="st-b3 st-d0"] button {
                    color: #666667;
                    background-color: #FFFFFF !important;
                    border: 1px solid #1E90FF;
                    border-radius: 4px;
                    padding: 5px 10px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                }
                """,
            ):
                min_value = pd.to_datetime(min_date)
                max_value = pd.to_datetime(max_date)
                if st.session_state["data_range"] is None:
                    st.session_state["data_range"] = (min_value, max_value)
                st.session_state["data_range"] = date_range_picker(
                    "DATE RANGE",
                    default_start=st.session_state["data_range"][0],
                    default_end=st.session_state["data_range"][1],
                )

    def display_selector(self, container, label, options, key):
        with container:
            with stylable_container(
                key=key,
                css_styles="""
                div[data-baseweb="select"] > div {
                    background-color: transparent !important;
                    font-size: 12px !important;
                    border-radius: 6px;
                    text-decoration: none;
                }
                li>span {
                    color: white !important;
                    font-size: 12px;
                    background-color: blue !important;
                }
                li {
                    background-color: transparent !important;
                }
                .stSelectbox label {
                    color: #A195FD !important;
                    font-size: 12px !important;
                    font-weight: bold !important;
                    margin-bottom: 5px !important;
                }
                .stSelectbox label span {
                    color: #FF0000 !important;
                }
                .stSelectbox {
                    background-color: rgba(255, 255, 255, 0.1) !important;
                    padding: 5px !important;
                    border-radius: 5px !important;
                }
                """,
            ):
                self.unkeep(key)
                st.multiselect(
                    label,
                    options=options,
                    key="_" + key,
                    on_change=self.keep,
                    args=[key],
                )

    def process_filter(self):
        if self.filter_button:
            query_conditions = ["1=1"]
            if st.session_state["data_range"]:
                start_date, end_date = st.session_state["data_range"]
                query_conditions.append(
                    f"{LTEDailyGut.DATEID.value} BETWEEN '{self.format_date(start_date)}' AND '{self.format_date(end_date)}'"
                )
            if st.session_state["selected_erbs"]:
                query_conditions.append(
                    self.build_condition(
                        LTEDailyGut.ERBS.value, st.session_state["selected_erbs"]
                    )
                )
            if st.session_state["selected_neid"]:
                query_conditions.append(
                    self.build_condition(
                        LTEDailyGut.NEID.value, st.session_state["selected_neid"]
                    )
                )
            if st.session_state["selected_cells"]:
                query_conditions.append(
                    self.build_condition(
                        LTEDailyGut.CELL.value, st.session_state["selected_cells"]
                    )
                )

            where_clause = " AND ".join(query_conditions)
            query = f"SELECT * FROM {LTEDailyGut.TABLE.value} WHERE {where_clause};"
            filtered_data = pd.read_sql_query(query, self.db.connection)
            filtered_data["SECTOR"] = filtered_data[LTEDailyGut.CELL.value].apply(
                self.determine_sector
            )
            self.data = pd.DataFrame(filtered_data)
            self.lte_daily_page(self.data)
        else:
            sac.result(
                label="Alert",
                description="Please select filter options and click Filter to run the query.",
            )

    @staticmethod
    def format_date(date):
        return date.strftime("%m/%d/%Y")

    @staticmethod
    def build_condition(column, values):
        formatted_values = [f'"{value}"' for value in values]
        return f"{column} IN ({', '.join(formatted_values)})"

    @staticmethod
    def determine_sector(cell: str) -> int:
        sector_mapping = {"1": 1, "2": 2, "3": 3, "4": 1, "5": 2, "6": 3}
        last_char = cell[-1].upper()
        return sector_mapping.get(last_char, 0)

    @staticmethod
    def get_header(cell):
        result = []
        for input_string in cell:
            last_char = input_string[-1]
            formatted_string = f"Sector {last_char}"
            if formatted_string not in result:
                result.append(formatted_string)
        result.sort()
        final_result = ", ".join(result)
        return final_result

    def sector(self, dataframe):
        sectors = dataframe["SECTOR"].unique()
        sector_data = [dataframe[dataframe["SECTOR"] == sector] for sector in sectors]
        return sector_data

    def colors(self):
        return ["#E60000", "#0000FF", "#00FF00", "#FF00FF", "#00FFFF", "#FF8000"]

    def lte_daily_page(self, df):
        yaxis_ranges = [[0, 100], [-10, 105], [-105, -145], [0, 20]]
        charts = [
            ("Availability", "Availability", yaxis_ranges[0]),
            ("RRC Success Rate", "RRC_SR", yaxis_ranges[0]),
            ("ERAB Success Rate", "ERAB_SR", yaxis_ranges[0]),
            ("Session Setup Success Rate", "SSSR", yaxis_ranges[0]),
            ("Signalling Abnormal Release", "SAR", yaxis_ranges[3]),
        ]

        for title, column, yaxis_range in charts:
            st.markdown(
                f"<h3 style='text-align: left; color: #4682B4;'>{title}</h3>",
                unsafe_allow_html=True,
            )
            col1, col2, col3 = st.columns(3)
            con1 = col1.container(border=True)
            con2 = col2.container(border=True)
            con3 = col3.container(border=True)
            for sector, con in zip(self.sector(df), [con1, con2, con3]):
                with con:
                    cells = sector[LTEDailyGut.CELL.value].unique()
                    fig = self.create_chart(sector, cells, title, column, yaxis_range)
                    st.plotly_chart(fig, use_container_width=True)

    def create_chart(self, data, cells, title, column, yaxis_range):
        fig = make_subplots(specs=[[{"secondary_y": False}]])
        colors = self.colors()
        title = self.get_header(cells)
        for i, cell in enumerate(cells):
            cell_data = data[data[LTEDailyGut.CELL.value] == cell]
            fig.add_trace(
                go.Scatter(
                    x=cell_data["DATE_ID"],
                    y=cell_data[column],
                    mode="lines+markers",
                    name=cell,
                    line=dict(color=colors[i % len(colors)]),
                ),
                secondary_y=False,
            )
        fig.update_layout(
            title_text=f"{title}",
            title_x=0,
            template="plotly_white",
            yaxis=dict(range=yaxis_range),
            xaxis=dict(tickformat="%m/%d/%y", tickangle=-45),
            autosize=True,
            showlegend=True,
            legend=dict(
                orientation="h", yanchor="top", y=-0.6, xanchor="center", x=0.5
            ),
            width=600,
            height=350,
        )
        fig.update_yaxes(secondary_y=False)
        return fig


if __name__ == "__main__":
    app = LTEDataFilterApp(LTEDailyGut.DB_PATH.value)
    app.run()
