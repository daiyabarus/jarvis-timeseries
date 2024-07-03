import os

import altair as alt
import pandas as pd
import streamlit as st
import toml
from colors import ColorPalette
from omegaconf import DictConfig, OmegaConf
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from streamlit_extras.mandatory_date_range import date_range_picker

# MARK: - Config OK
# DONE: - Need run query if not select neid


class Config:
    def load(self):
        with open(".streamlit/secrets.toml") as f:
            cfg = OmegaConf.create(toml.loads(f.read()))
        return cfg


class DatabaseSession:
    def __init__(self, cfg: DictConfig):
        self.cfg = cfg

    def create_session(self):
        try:
            db_cfg = self.cfg.connections.postgresql
            engine = create_engine(
                f"{db_cfg.dialect}://{db_cfg.username}:{db_cfg.password}@{db_cfg.host}:{db_cfg.port}/{db_cfg.database}"
            )
            Session = sessionmaker(bind=engine)
            return Session(), engine
        except Exception as e:
            st.error(f"Error creating database session: {e}")
            return None, None


class DataFrameManager:
    def __init__(self):
        self.dataframes = {}

    def add_dataframe(self, name, dataframe):
        self.dataframes[name] = dataframe

    def get_dataframe(self, name):
        return self.dataframes.get(name)

    def display_dataframe(self, name, header):
        dataframe = self.get_dataframe(name)
        if dataframe is not None:
            st.header(header)
            st.write(dataframe)


class StreamlitInterface:
    def load_sitelist(self, filepath):
        data = []
        with open(filepath) as file:
            for line in file:
                columns = line.strip().split(",")
                data.append(columns)
        return data

    def site_selection(self, sitelist):
        column0_data = [row[0] for row in sitelist]
        return st.multiselect("SITEID", column0_data)

    def neid_selection(self, sitelist):
        column2_data = {row[2] for row in sitelist}
        return st.multiselect("NEID", column2_data)

    def select_date_range(self):
        if "date_range" not in st.session_state:
            st.session_state["date_range"] = (
                pd.Timestamp.today() - pd.Timedelta(days=8),
                pd.Timestamp.today(),
            )

        date_range = date_range_picker(
            "DATE RANGE",
            default_start=st.session_state["date_range"][0],
            default_end=st.session_state["date_range"][1],
        )
        return date_range


class QueryManager:
    def __init__(self, engine):
        self.engine = engine

    def fetch_data(self, query, params=None):
        try:
            df = pd.read_sql(query, self.engine, params=params)
            return df
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            return pd.DataFrame()

    def get_mcom_data(self, siteid):
        query = text(
            """
        SELECT "Site_ID", "NODE_ID", "NE_ID", "Cell_Name", "Longitude", "Latitude", "Dir", "Ant_BW",
               "Ant_Size", "cellId", "eNBId", "MC_class", "KABUPATEN", "LTE"
        FROM mcom
        WHERE "Site_ID" LIKE :siteid
        """
        )
        return self.fetch_data(query, {"siteid": siteid})

    def get_ltedaily_data(self, siteid, neids, start_date, end_date):
        query = text(
            """
            SELECT *
            FROM ltedaily
            WHERE "SITEID" LIKE :siteid
            AND "DATE_ID" BETWEEN :start_date AND :end_date
            """
        )
        params = {"siteid": siteid, "start_date": start_date, "end_date": end_date}

        if neids:
            neid_conditions = " OR ".join(
                [f'"NEID" LIKE :neid_{i}' for i in range(len(neids))]
            )
            query = text(
                f"""
                SELECT *
                FROM ltedaily
                WHERE "SITEID" LIKE :siteid
                AND ({neid_conditions})
                AND "DATE_ID" BETWEEN :start_date AND :end_date
                """
            )
            params.update({f"neid_{i}": neid for i, neid in enumerate(neids)})
        else:
            query = text(
                """
                SELECT *
                FROM ltedaily
                WHERE "SITEID" LIKE :siteid
                AND "DATE_ID" BETWEEN :start_date AND :end_date
                """
            )

        return self.fetch_data(query, params)

    def get_ltehourly_data(self, selected_sites, start_date, end_date):
        like_conditions = " OR ".join(
            [f'"EUtranCellFDD" LIKE :site_{i}' for i in range(len(selected_sites))]
        )
        query = text(
            f"""
        SELECT
            "DATE_ID",
            "EUtranCellFDD",
            hour_id,
            "DL_Resource_Block_Utilizing_Rate",
            "Active User"
        FROM ltehourly
        WHERE ({like_conditions})
        AND "DATE_ID" BETWEEN :start_date AND :end_date
        """
        )
        params = {f"site_{i}": f"%{site}%" for i, site in enumerate(selected_sites)}
        params.update({"start_date": start_date, "end_date": end_date})

        return self.fetch_data(query, params=params)

    def get_target_data(self, city, mc_class, band):
        query = text(
            """
        SELECT *
        FROM target
        WHERE "City" = :city AND "MC Class" = :mc_class AND "Band" = :band
        """
        )
        return self.fetch_data(
            query, {"city": city, "mc_class": mc_class, "band": band}
        )

    def get_ltemdt_data(self, enodebid, ci):
        query = text(
            """
        SELECT *
        FROM ltemdt
        WHERE enodebid = :enodebid AND ci = :ci
        """
        )
        return self.fetch_data(query, {"enodebid": enodebid, "ci": ci})

    def get_ltetastate_data(self, enodebid, ci):
        query = text(
            """
        SELECT *
        FROM ltetastate
        WHERE enodebid = :enodebid AND ci = :ci
        """
        )
        return self.fetch_data(query, {"enodebid": enodebid, "ci": ci})

    def get_vswr_data(self, selected_sites, start_date, end_date):
        like_conditions = " OR ".join(
            [f'"NE_NAME" LIKE :site_{i}' for i in range(len(selected_sites))]
        )
        query = text(
            f"""
        SELECT
            "DATE_ID",
            "NE_NAME",
            "RRU",
            "pmReturnLossAvg",
            "VSWR"
        FROM ltevswr
        WHERE ({like_conditions})
        AND "DATE_ID" BETWEEN :start_date AND :end_date
        AND "RRU" NOT LIKE '%RfPort=R%'
        AND "RRU" NOT LIKE '%RfPort=S%'
        """
        )
        params = {f"site_{i}": f"%{site}%" for i, site in enumerate(selected_sites)}
        params.update({"start_date": start_date, "end_date": end_date})

        return self.fetch_data(query, params=params)


class ChartGenerator:
    def __init__(self):
        self.color_palette = ColorPalette()

    def get_colors(self, num_colors):
        return [self.color_palette.get_color(i) for i in range(num_colors)]

    def get_header(self, cell, param, site):
        result = []
        for input_string in cell:
            last_char = input_string[-1]
            sector = self.determine_sector(last_char)
            formatted_string = f"Sector {sector}"
            if formatted_string not in result:
                result.append(formatted_string)
        result.sort()
        return f"{param} {site}"

    def determine_sector(self, cell: str) -> int:
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

    def create_charts(
        self, df, param, site, x_param, y_param, sector_param, yaxis_range
    ):
        sectors = sorted(df[sector_param].apply(self.determine_sector).unique())
        title = self.get_header(df[sector_param].unique(), param, site)

        color_mapping = {
            cell: color
            for cell, color in zip(
                df[sector_param].unique(),
                self.get_colors(len(df[sector_param].unique())),
            )
        }

        charts = []
        for sector in sectors:
            sector_df = df[df[sector_param].apply(self.determine_sector) == sector]
            sector_chart = (
                alt.Chart(sector_df)
                .mark_line()
                .encode(
                    x=alt.X(x_param, type="temporal", axis=alt.Axis(title=None)),
                    y=alt.Y(
                        y_param,
                        type="quantitative",
                        scale=alt.Scale(domain=yaxis_range),
                        axis=alt.Axis(title=y_param),
                    ),
                    color=alt.Color(
                        sector_param,
                        scale=alt.Scale(
                            domain=list(color_mapping.keys()),
                            range=list(color_mapping.values()),
                        ),
                    ),
                )
                .properties(title=f"Sector {sector}", width=450, height=200)
            )
            charts.append(sector_chart)

        combined_chart = (
            alt.hconcat(*charts)
            # .properties(title=title)
            .configure_title(
                fontSize=18,
                anchor="middle",
                font="Ericsson Hilda Light",
                color="#800000",
            )
            .configure_legend(orient="right")
            .configure_legend(titleFontSize=11, labelFontSize=11)
        )

        container = st.container(border=True)
        with container:
            st.altair_chart(combined_chart, use_container_width=True)


class App:
    def __init__(self):
        self.config = Config().load()
        self.database_session = DatabaseSession(self.config)
        self.query_manager = None
        self.dataframe_manager = DataFrameManager()
        self.streamlit_interface = StreamlitInterface()
        self.chart_generator = ChartGenerator()

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

    def run(self):
        st.title("Site Data Analysis")

        # Create database session
        session, engine = self.database_session.create_session()
        if session is None:
            return

        self.query_manager = QueryManager(engine)

        # Load sitelist
        script_dir = os.path.dirname(__file__)
        sitelist_path = os.path.join(script_dir, "test_sitelist.csv")
        sitelist = self.streamlit_interface.load_sitelist(sitelist_path)

        # Site selection
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            # Date range selection
            date_range = self.streamlit_interface.select_date_range()

        with col2:
            selected_sites = self.streamlit_interface.site_selection(sitelist)

        with col3:
            selected_neids = self.streamlit_interface.neid_selection(sitelist)

        # Fetch data for each selected site
        if st.button("Run Query"):
            if selected_sites and date_range:
                start_date, end_date = date_range

                combined_target_data = []
                combined_ltemdt_data = []
                combined_ltetastate_data = []

                # Fetch MCOM data
                for siteid in selected_sites:
                    mcom_data = self.query_manager.get_mcom_data(siteid)
                    self.dataframe_manager.add_dataframe(
                        f"mcom_data_{siteid}", mcom_data
                    )
                    self.dataframe_manager.display_dataframe(
                        f"mcom_data_{siteid}", f"MCOM Data for Site: {siteid}"
                    )

                    # Fetch additional data based on mcom results
                    for _, row in mcom_data.iterrows():
                        # Get and append target data
                        target_data = self.query_manager.get_target_data(
                            row["KABUPATEN"], row["MC_class"], row["LTE"]
                        )
                        target_data["EutranCell"] = row["Cell_Name"]
                        combined_target_data.append(target_data)

                        # Get and append ltemdt data
                        ltemdt_data = self.query_manager.get_ltemdt_data(
                            row["eNBId"], row["cellId"]
                        )
                        ltemdt_data["EutranCell"] = row["Cell_Name"]
                        combined_ltemdt_data.append(ltemdt_data)

                        # Get and append ltetastate data
                        ltetastate_data = self.query_manager.get_ltetastate_data(
                            row["eNBId"], row["cellId"]
                        )
                        ltetastate_data["EutranCell"] = row["Cell_Name"]
                        combined_ltetastate_data.append(ltetastate_data)

                # Combine target data and display
                if combined_target_data:
                    combined_target_df = pd.concat(
                        combined_target_data, ignore_index=True
                    )
                    self.dataframe_manager.add_dataframe(
                        "combined_target_data", combined_target_df
                    )
                    self.dataframe_manager.display_dataframe(
                        "combined_target_data", "Combined Target Data"
                    )

                # Combine ltemdt data and display
                if combined_ltemdt_data:
                    combined_ltemdt_df = pd.concat(
                        combined_ltemdt_data, ignore_index=True
                    )
                    self.dataframe_manager.add_dataframe(
                        "combined_ltemdt_data", combined_ltemdt_df
                    )
                    self.dataframe_manager.display_dataframe(
                        "combined_ltemdt_data", "Combined LTE MDT Data"
                    )

                # Combine ltetastate data and display
                if combined_ltetastate_data:
                    combined_ltetastate_df = pd.concat(
                        combined_ltetastate_data, ignore_index=True
                    )
                    self.dataframe_manager.add_dataframe(
                        "combined_ltetastate_data", combined_ltetastate_df
                    )
                    self.dataframe_manager.display_dataframe(
                        "combined_ltetastate_data", "Combined LTE TA State Data"
                    )

                # Fetch LTE daily data
                for siteid in selected_sites:
                    ltedaily_data = self.query_manager.get_ltedaily_data(
                        siteid, selected_neids, start_date, end_date
                    )
                    self.dataframe_manager.add_dataframe(
                        f"ltedaily_data_{siteid}", ltedaily_data
                    )
                    self.dataframe_manager.display_dataframe(
                        f"ltedaily_data_{siteid}", f"LTE Daily Data for Site: {siteid}"
                    )
                    yaxis_ranges = [[0, 105], [50, 105], [-105, -145], [0, 5], [0, 20]]

                    self.chart_generator.create_charts(
                        df=ltedaily_data,
                        param="Availability",
                        site=siteid,
                        x_param="DATE_ID",
                        y_param="Availability",
                        sector_param="EutranCell",
                        yaxis_range=yaxis_ranges[0],
                    )

                    self.chart_generator.create_charts(
                        df=ltedaily_data,
                        param="RRC Setup Success Rate",
                        site=siteid,
                        x_param="DATE_ID",
                        y_param="RRC_SR",
                        sector_param="EutranCell",
                        yaxis_range=yaxis_ranges[0],
                    )

                    self.chart_generator.create_charts(
                        df=ltedaily_data,
                        param="Spectral Efficiency",
                        site=siteid,
                        x_param="DATE_ID",
                        y_param="SE_DAILY",
                        sector_param="EutranCell",
                        yaxis_range=yaxis_ranges[3],
                    )

                    self.chart_generator.create_charts(
                        df=ltedaily_data,
                        param="CQI Non HOM",
                        site=siteid,
                        x_param="DATE_ID",
                        y_param="avgcqinonhom",
                        sector_param="EutranCell",
                        yaxis_range=yaxis_ranges[4],
                    )

                    self.chart_generator.create_charts(
                        df=ltedaily_data,
                        param="Session Abnormal Release",
                        site=siteid,
                        x_param="DATE_ID",
                        y_param="SAR",
                        sector_param="EutranCell",
                        yaxis_range=yaxis_ranges[4],
                    )

                # Fetch LTE hourly data
                ltehourly_data = self.query_manager.get_ltehourly_data(
                    selected_sites, start_date, end_date
                )
                self.dataframe_manager.add_dataframe("ltehourly_data", ltehourly_data)
                self.dataframe_manager.display_dataframe(
                    "ltehourly_data", "LTE Hourly Data"
                )

                # Fetch VSWR data
                vswr_data = self.query_manager.get_vswr_data(
                    selected_sites, start_date, end_date
                )
                self.dataframe_manager.add_dataframe("vswr_data", vswr_data)
                self.dataframe_manager.display_dataframe("vswr_data", "VSWR Data")

                # Close session
                session.close()
            else:
                st.warning("Please select site IDs and date range to load data.")


if __name__ == "__main__":
    app = App()
    app.run()
