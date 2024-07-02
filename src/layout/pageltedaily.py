import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit_antd_components as sac
import toml
from omegaconf import DictConfig, OmegaConf
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from streamlit_extras.mandatory_date_range import date_range_picker
from streamlit_extras.stylable_container import stylable_container


# Load configuration file
def load_config():
    with open(".streamlit/secrets.toml") as f:
        cfg = OmegaConf.create(toml.loads(f.read()))
    return cfg


# Create database session
def create_session(cfg: DictConfig):
    try:
        db_cfg = cfg.connections.postgresql
        engine = create_engine(
            f"{db_cfg.dialect}://{db_cfg.username}:{db_cfg.password}@{db_cfg.host}:{db_cfg.port}/{db_cfg.database}"
        )
        Session = sessionmaker(bind=engine)
        return Session(), engine
    except Exception as e:
        st.error(f"Error creating database session: {e}")
        return None, None


# Page configuration
st.set_page_config(layout="wide")
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


class AppConfig:
    @staticmethod
    def configure_streamlit():
        st.set_page_config(layout="wide")
        st.markdown(
            """
            <style>
            [data-testid="collapsedControl"] { display: none; }
            #MainMenu, header, footer { visibility: hidden; }
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


class LTEDataFilterApp:
    def __init__(self, session, engine):
        self.session = session
        self.engine = engine
        self.data = None
        self.initialize_app()

    def initialize_app(self):
        self.initialize_session_state()

    def initialize_session_state(self):
        if "selected_sites" not in st.session_state:
            st.session_state["selected_sites"] = []
        if "date_range" not in st.session_state:
            st.session_state["date_range"] = (
                pd.Timestamp.today() - pd.Timedelta(days=8),
                pd.Timestamp.today(),
            )

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

    def get_sites(self):
        script_dir = os.path.dirname(__file__)
        sitelist_path = os.path.join(script_dir, "test_sitelist.txt")
        with open(sitelist_path) as file:
            sites = file.read().splitlines()
        return sites

    def display_filters(self):
        sites_options = self.get_sites()
        col1, col2 = st.columns([1, 1])
        self.display_date_range_picker(col1)
        self.display_selector(col2, "SITEID", sites_options, "selected_sites")

    def display_date_range_picker(self, container):
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
                date_range = date_range_picker(
                    "DATE RANGE",
                    default_start=st.session_state["date_range"][0],
                    default_end=st.session_state["date_range"][1],
                )
                st.session_state["date_range"] = date_range

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
                st.multiselect(label, options=options, key=key)

    def process_filter(self):
        if self.filter_button:
            query_conditions = ["1=1"]
            selected_sites = st.session_state["selected_sites"]
            start_date, end_date = st.session_state["date_range"]
            if selected_sites:
                like_conditions = " OR ".join(
                    [f'"SITEID" LIKE :site_{i}' for i, _ in enumerate(selected_sites)]
                )
                query_conditions.append(f"({like_conditions})")
            query_conditions.append('"DATE_ID" BETWEEN :start_date AND :end_date')

            where_clause = " AND ".join(query_conditions)
            query = text(f"SELECT * FROM ltedaily WHERE {where_clause}")
            params = {f"site_{i}": f"%{site}%" for i, site in enumerate(selected_sites)}
            params.update({"start_date": start_date, "end_date": end_date})

            df = pd.read_sql_query(query, self.engine, params=params)
            df["SECTOR"] = df["EutranCell"].apply(self.determine_sector)
            self.data = df
            self.lte_daily_page(self.data)
        else:
            sac.result(
                label="Alert",
                description="Please select filter options and click Filter to run the query.",
            )

    @staticmethod
    def format_date(date):
        return date.strftime("%Y-%m-%d")

    @staticmethod
    def determine_sector(cell: str) -> int:
        sector_mapping = {
            "1": 1,
            "2": 2,
            "3": 3,
            "4": 1,
            "5": 2,
            "6": 3,
            "7": 1,
            "8": 2,
            "9": 3,
        }
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
        return [
            "#B8860B",
            "#9932CC",
            "#E9967A",
            "#8FBC8F",
            "#8B0000",
            "#00CED1",
            "#483D8B",
            "#2F4F4F",
            "#4B0150",
            "#FF8C00",
            "#556B2F",
            "#FF0000",
            "#00A86B",
            "#4B0082",
            "#FFA500",
            "#1E90FF",
            "#8B4513",
            "#FF1493",
            "#00FF00",
            "#800080",
            "#FFD700",
            "#32CD32",
            "#FF00FF",
            "#1E4D2B",
            "#CD853F",
            "#00BFFF",
            "#DC143C",
            "#7CFC00",
            "#FFFF00",
            "#4682B4",
            "#800000",
            "#40E0D0",
            "#FF6347",
            "#6B8E23",
        ]

    def lte_daily_page(self, df):
        yaxis_ranges = [[0, 100], [-10, 105], [-105, -145], [0, 10]]
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
                    cells = sector["EutranCell"].unique()
                    fig = self.create_chart(sector, cells, title, column, yaxis_range)
                    st.plotly_chart(fig, use_container_width=True)

    def create_chart(self, data, cells, title, column, yaxis_range):
        fig = make_subplots(specs=[[{"secondary_y": False}]])
        colors = self.colors()
        title = self.get_header(cells)
        for i, cell in enumerate(cells):
            cell_data = data[data["EutranCell"] == cell]
            fig.add_trace(
                go.Scatter(
                    x=cell_data["DATE_ID"],
                    y=cell_data[column],
                    mode="lines",
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
            xaxis=dict(tickformat="%m/%d/%y", tickangle=-45, nticks=30),
            autosize=True,
            showlegend=True,
            legend=dict(
                orientation="h", yanchor="top", y=-0.6, xanchor="center", x=0.5
            ),
            width=600,
            height=400,
        )
        fig.update_yaxes(secondary_y=False)
        return fig


if __name__ == "__main__":
    config = load_config()
    session, engine = create_session(config)
    if session and engine:
        app = LTEDataFilterApp(session, engine)
        app.run()
