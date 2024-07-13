import os

import altair as alt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit_antd_components as sac
import toml
from colors import ColorPalette
from omegaconf import DictConfig, OmegaConf
from plotly.subplots import make_subplots
from review.geoapp import GeoApp
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from streamlit_extras.mandatory_date_range import date_range_picker
from streamlit_extras.stylable_container import stylable_container
from styles import styling

# MARK: - Config OK


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
                pd.Timestamp.today() - pd.DateOffset(months=3),
                pd.Timestamp.today() - pd.Timedelta(days=1),
            )

        date_range = date_range_picker(
            "DATE RANGE",
            default_start=st.session_state["date_range"][0],
            default_end=st.session_state["date_range"][1],
        )
        return date_range

    def select_xrule_date(self):
        if "xrule_date" not in st.session_state:
            st.session_state["xrule_date"] = pd.Timestamp.today()

        xrule_date = st.date_input("OA Date", st.session_state["xrule_date"])
        st.session_state["xrule_date"] = xrule_date  # Ensure session state is updated
        return xrule_date


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

    def get_mcom_neid(
        self,
    ):
        query = text(
            """
            SELECT "NE_ID", "Cell_Name", "Longitude", "Latitude", "Dir"
            FROM mcom
        """
        )
        return self.fetch_data(query)

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

    def get_ltedaily_payload(self, selected_sites, start_date, end_date):
        like_conditions = " OR ".join(
            [f'"SITEID" LIKE :site_{i}' for i in range(len(selected_sites))]
        )
        query = text(
            f"""
            SELECT
            "DATE_ID",
            "SITEID",
            "NEID",
            "EutranCell",
            "Payload_Total(Gb)",
            "CQI Bh"
            FROM ltedaily
            WHERE ({like_conditions})
            AND "DATE_ID" BETWEEN :start_date AND :end_date
            """
        )
        params = {f"site_{i}": f"%{site}%" for i, site in enumerate(selected_sites)}
        params.update({"start_date": start_date, "end_date": end_date})

        return self.fetch_data(query, params=params)

    @st.cache_data(ttl=600)
    def get_ltehourly_data(_self, selected_sites, end_date):
        like_conditions = " OR ".join(
            [f'"EUtranCellFDD" LIKE :site_{i}' for i in range(len(selected_sites))]
        )
        start_date = end_date - pd.Timedelta(days=15)
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

        return _self.fetch_data(query, params=params)

    def get_target_data(self, city, mc_class, band):
        # def get_target_data(self, city, band):
        query = text(
            """
        SELECT *
        FROM target
        WHERE "City" = :city AND "Band" = :band AND "MC Class" = :mc_class
        """
        )
        return self.fetch_data(
            # query, {"city": city, "mc_class": mc_class, "band": band}
            query,
            {"city": city, "mc_class": mc_class, "band": band},
        )

    @st.cache_data(ttl=600)
    def get_ltemdt_data(_self, selected_sites):
        like_conditions = " OR ".join(
            [f'"site" LIKE :site_{i}' for i in range(len(selected_sites))]
        )
        query = text(
            f"""
        SELECT
        site,
        enodebid,
        ci,
        sample,
        rsrp_mean,
        rsrq_mean,
        rank,
        long_grid,
        lat_grid
        FROM ltemdt
        WHERE ({like_conditions})
        """
        )
        params = {f"site_{i}": f"%{site}%" for i, site in enumerate(selected_sites)}
        return _self.fetch_data(query, params=params)

    # TODO: - Create query for ta-state
    @st.cache_data(ttl=600)
    def get_ltetastate_data(_self, siteid):
        like_conditions = " OR ".join(
            [f'"site" LIKE :site_{i}' for i in range(len(siteid))]
        )

        query = text(
            f"""
            SELECT *
            FROM ltetastate
            WHERE ({like_conditions})
            """
        )

        params = {f"site_{i}": f"%{site}%" for i, site in enumerate(siteid)}
        return _self.fetch_data(query, params=params)

    def get_mcom_tastate(self, selected_neids):
        like_conditions = " OR ".join(
            [f'"NE_ID" LIKE :neid_{i}' for i in range(len(selected_neids))]
        )
        query = text(
            f"""
        SELECT
        "Site_ID",
        "NE_ID",
        "Cell_Name",
        "cellId",
        "eNBId"
        FROM mcom
        WHERE ({like_conditions})
        """
        )
        params = {f"neid_{i}": f"%{neid}%" for i, neid in enumerate(selected_neids)}
        return self.fetch_data(query, params=params)

    def get_vswr_data(self, selected_sites, end_date):
        like_conditions = " OR ".join(
            [f'"NE_NAME" LIKE :site_{i}' for i in range(len(selected_sites))]
        )

        start_date = end_date - pd.Timedelta(days=3)

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
        AND "VSWR" != 0
        """
        )
        params = {f"site_{i}": f"%{site}%" for i, site in enumerate(selected_sites)}
        params.update({"start_date": start_date, "end_date": end_date})

        return self.fetch_data(query, params=params)

    def get_busyhour(self, selected_sites, end_date):
        like_conditions = " OR ".join(
            [f'"EUtranCellFDD" LIKE :site_{i}' for i in range(len(selected_sites))]
        )
        start_date = end_date - pd.Timedelta(days=15)
        query = text(
            f"""
        SELECT
            "DATE_ID",
            "EUtranCellFDD",
            "CQI"
        FROM ltebusyhour
        WHERE ({like_conditions})
        AND "DATE_ID" BETWEEN :start_date AND :end_date
        """
        )
        params = {f"site_{i}": f"%{site}%" for i, site in enumerate(selected_sites)}
        params.update({"start_date": start_date, "end_date": end_date})

        return self.fetch_data(query, params=params)

    def get_cqi_cluster(self, eutrancellfdd, start_date, end_date):
        query = text(
            """
            SELECT
                "DATE_ID",
                "EUtranCellFDD",
                "CQI"
            FROM ltebusyhour
            WHERE "EUtranCellFDD" LIKE :eutrancellfdd
            AND "DATE_ID" BETWEEN :start_date AND :end_date
            """
        )
        params = {
            "eutrancellfdd": eutrancellfdd,
            "start_date": start_date,
            "end_date": end_date,
        }
        try:
            return pd.read_sql(query, self.engine, params=params)
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            return pd.DataFrame()


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

    # TAG: - create_charts
    def create_charts(
        self,
        df,
        param,
        site,
        x_param,
        y_param,
        sector_param,
        yaxis_range=None,
        xrule=None,
    ):
        sectors = sorted(df[sector_param].apply(self.determine_sector).unique())
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

            if yaxis_range:
                y_scale = alt.Scale(domain=yaxis_range)
            else:
                y_scale = alt.Scale()

            sector_chart = (
                alt.Chart(sector_df)
                .mark_line()
                .encode(
                    x=alt.X(x_param, type="temporal", axis=alt.Axis(title=None)),
                    y=alt.Y(
                        y_param,
                        type="quantitative",
                        scale=y_scale,
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
                .properties(title=f"Sector {sector}", width=590, height=150)
            )

            # Add xrule to the chart if provided
            if xrule:
                xrule_chart = (
                    alt.Chart(
                        pd.DataFrame({"On Air Date": [st.session_state["xrule_date"]]})
                    )
                    .mark_rule(color="#F7BB00", strokeWidth=4, strokeDash=[10, 5])
                    .encode(x="On Air Date:T")
                )
                sector_chart += xrule_chart

            charts.append(sector_chart)

        combined_chart = (
            alt.hconcat(*charts, autosize="fit", background="#F5F5F5")
            .configure_title(
                fontSize=18,
                anchor="middle",
                font="Vodafone",
                color="#717577",
            )
            .configure_legend(
                orient="bottom",
                titleFontSize=16,
                labelFontSize=14,
                labelFont="Vodafone",
                titleColor="#5F6264",
                padding=10,
                titlePadding=10,
                cornerRadius=10,
                columns=6,
                titleAnchor="start",
                direction="vertical",
                gradientLength=400,
                labelLimit=0,
                symbolSize=30,
                symbolType="square",
            )
        )

        with stylable_container(
            key="container_with_border",
            css_styles="""
                {
                    background-color: #F5F5F5;
                    border: 2px solid rgba(49, 51, 63, 0.2);
                    border-radius: 0.5rem;
                    padding: calc(1em - 1px)
                }
                """,
        ):
            container = st.container()
            with container:
                st.altair_chart(combined_chart, use_container_width=True)

    # TAG: - create_charts_datums
    def create_charts_datums(
        self,
        df,
        param,
        site,
        x_param,
        y_param,
        sector_param,
        y2_avg,
        yaxis_range=None,
        yaxis_reverse=False,
        xrule=None,
    ):
        sectors = sorted(df[sector_param].apply(self.determine_sector).unique())

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

            if yaxis_range and yaxis_reverse:
                y_scale = alt.Scale(zero=False, domain=yaxis_range, reverse=True)
            elif yaxis_range:
                y_scale = alt.Scale(domain=yaxis_range)
            else:
                y_scale = alt.Scale()

            sector_chart = (
                alt.Chart(sector_df)
                .mark_line()
                .encode(
                    x=alt.X(x_param, type="temporal", axis=alt.Axis(title=None)),
                    y=alt.Y(
                        y_param,
                        type="quantitative",
                        scale=y_scale,
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
                .properties(title=f"Sector {sector}", width=600, height=150)
            )

            # Add y2_avg line rule to the chart
            if y2_avg in sector_df.columns:
                y2_avg_line = (
                    alt.Chart(sector_df)
                    .mark_rule(color="#F74B00", strokeDash=[10, 5], size=4, opacity=0.1)
                    .encode(y=alt.Y(y2_avg, type="quantitative", title="with Baseline"))
                )
                sector_chart = alt.layer(y2_avg_line, sector_chart)

            if xrule:
                xrule_chart = (
                    alt.Chart(
                        pd.DataFrame({"On Air Date": [st.session_state["xrule_date"]]})
                    )
                    .mark_rule(color="#F7BB00", strokeWidth=4, strokeDash=[10, 5])
                    .encode(x="On Air Date:T")
                )
                sector_chart += xrule_chart

            charts.append(sector_chart)

        combined_chart = (
            alt.hconcat(*charts, autosize="fit", background="#F5F5F5")
            .configure_title(
                fontSize=18,
                anchor="middle",
                font="Vodafone",
                color="#717577",
            )
            .configure_legend(
                orient="bottom",
                titleFontSize=16,
                labelFontSize=14,
                labelFont="Vodafone",
                titleColor="#5F6264",
                padding=10,
                titlePadding=10,
                cornerRadius=10,
                columns=6,
                titleAnchor="start",
                direction="vertical",
                gradientLength=400,
                labelLimit=0,
                symbolSize=30,
                symbolType="square",
            )
        )

        with stylable_container(
            key="container_with_border",
            css_styles="""
                {
                    background-color: #F5F5F5;
                    border: 2px solid rgba(49, 51, 63, 0.2);
                    border-radius: 0.5rem;
                    padding: calc(1em - 1px)
                }
                """,
        ):
            container = st.container()
            with container:
                st.altair_chart(combined_chart, use_container_width=True)

    # TAG: - create_charts_area
    def create_charts_area(
        self,
        df,
        param,
        site,
        x_param,
        y_param,
        sector_param,
        yaxis_range=None,
        xrule=None,
    ):
        sectors = sorted(df[sector_param].apply(self.determine_sector).unique())
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
            y_scale = alt.Scale(domain=yaxis_range) if yaxis_range else alt.Scale()

            sector_chart = (
                alt.Chart(sector_df)
                .mark_area()
                .encode(
                    x=alt.X(x_param, type="temporal", axis=alt.Axis(title=None)),
                    y=alt.Y(
                        y_param,
                        type="quantitative",
                        scale=y_scale,
                        axis=alt.Axis(title=y_param),
                        stack="zero",
                    ),
                    color=alt.Color(
                        sector_param,
                        scale=alt.Scale(
                            domain=list(color_mapping.keys()),
                            range=list(color_mapping.values()),
                        ),
                    ),
                )
                .properties(title=f"Sector {sector}", width=600, height=150)
            )

            if xrule and "xrule_date" in st.session_state:
                xrule_chart = (
                    alt.Chart(
                        pd.DataFrame({"On Air Date": [st.session_state["xrule_date"]]})
                    )
                    .mark_rule(color="#F7BB00", strokeWidth=4, strokeDash=[10, 5])
                    .encode(x="On Air Date:T")
                )
                sector_chart += xrule_chart

            charts.append(sector_chart)

        combined_chart = (
            alt.hconcat(*charts, autosize="fit", background="#F5F5F5")
            .configure_title(
                fontSize=18,
                anchor="middle",
                font="Vodafone",
                color="#717577",
            )
            .configure_legend(
                orient="bottom",
                titleFontSize=16,
                labelFontSize=14,
                labelFont="Vodafone",
                titleColor="#5F6264",
                padding=10,
                titlePadding=10,
                cornerRadius=10,
                columns=6,
                titleAnchor="start",
                direction="vertical",
                gradientLength=400,
                labelLimit=0,
                symbolSize=30,
                symbolType="square",
            )
        )

        with stylable_container(
            key="container_with_border",
            css_styles="""
                {
                    background-color: #F5F5F5;
                    border: 2px solid rgba(49, 51, 63, 0.2);
                    border-radius: 0.5rem;
                    padding: calc(1em - 1px)
                }
                """,
        ):
            container = st.container()
            with container:
                st.altair_chart(combined_chart, use_container_width=True)

    # TAG: - create_charts_neid
    def create_charts_neid(
        self, df, param, site, x_param, y_param, neid, yaxis_range=None, xrule=None
    ):
        # Group by x_param and sum y_param values for each NEID
        grouped_df = df.groupby([x_param, neid])[y_param].sum().reset_index()

        color_mapping = {
            cell: color
            for cell, color in zip(
                grouped_df[neid].unique(),
                self.get_colors(len(grouped_df[neid].unique())),
            )
        }

        # Determine y-axis range
        if yaxis_range:
            y_scale = alt.Scale(domain=yaxis_range)
        else:
            y_scale = alt.Scale()

        base_chart = (
            alt.Chart(grouped_df)
            .mark_area()
            .encode(
                x=alt.X(x_param, type="temporal", axis=alt.Axis(title=None)),
                y=alt.Y(
                    y_param,
                    type="quantitative",
                    scale=y_scale,
                    axis=alt.Axis(title=""),
                    stack="zero",
                ),
                color=alt.Color(
                    neid,
                    scale=alt.Scale(
                        domain=list(color_mapping.keys()),
                        range=list(color_mapping.values()),
                    ),
                ),
            )
        )

        if xrule:
            xrule_chart = (
                alt.Chart(
                    pd.DataFrame({"On Air Date": [st.session_state["xrule_date"]]})
                )
                .mark_rule(color="#F7BB00", strokeWidth=4, strokeDash=[10, 5])
                .encode(x="On Air Date:T")
            )
            chart = alt.layer(base_chart, xrule_chart)
        else:
            chart = base_chart

        chart = (
            chart.properties(
                title="Payload Gbps",
                height=350,
                background="#F5F5F5",
            )
            .configure_title(
                fontSize=18,
                anchor="middle",
                font="Vodafone",
                color="#717577",
            )
            .configure_legend(
                orient="bottom",
                titleFontSize=16,
                labelFontSize=14,
                labelFont="Vodafone",
                titleColor="#5F6264",
                padding=10,
                titlePadding=10,
                cornerRadius=10,
                columns=6,
                titleAnchor="start",
                direction="vertical",
                gradientLength=400,
                labelLimit=0,
                symbolSize=30,
                symbolType="square",
            )
            .configure_view(strokeWidth=0)
        )

        container = st.container()
        with container:
            st.altair_chart(chart, use_container_width=True)

    # TAG: - Create Charts hourly
    def create_charts_hourly(
        self, df, param, site, x_param, y_param, sector_param, yaxis_range=None
    ):
        sectors = sorted(df[sector_param].apply(self.determine_sector).unique())
        # title = self.get_header(df[sector_param].unique(), param, site)

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

            # Determine y-axis range
            if yaxis_range:
                y_scale = alt.Scale(domain=yaxis_range)
            else:
                y_scale = alt.Scale()

            sector_chart = (
                alt.Chart(sector_df)
                .mark_line(strokeWidth=10)
                .encode(
                    x=alt.X(x_param, type="temporal", axis=alt.Axis(title=None)),
                    y=alt.Y(
                        y_param,
                        type="quantitative",
                        scale=y_scale,
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
                .properties(title=f"Sector {sector}", width=600, height=150)
            )
            charts.append(sector_chart)

        combined_chart = (
            alt.hconcat(*charts, autosize="fit", background="#F5F5F5")
            .configure_title(
                fontSize=18,
                anchor="middle",
                font="Vodafone",
                color="#717577",
            )
            .configure_legend(
                orient="bottom",
                titleFontSize=16,
                labelFontSize=14,
                labelFont="Vodafone",
                titleColor="#5F6264",
                padding=10,
                titlePadding=10,
                cornerRadius=10,
                # strokeColor="#9A9A9A",
                columns=6,
                titleAnchor="start",
                direction="vertical",
                gradientLength=400,
                labelLimit=0,
                symbolSize=30,
                symbolType="square",
            )
        )

        with stylable_container(
            key="container_with_border",
            css_styles="""
                {
                    background-color: #F5F5F5;
                    border: 2px solid rgba(49, 51, 63, 0.2);
                    border-radius: 0.5rem;
                    padding: calc(1em - 1px)
                }
                """,
        ):
            container = st.container()
            with container:
                st.altair_chart(combined_chart, use_container_width=True)

    def create_charts_vswr(self, df, x1_param, x2_param, y_param, nename):
        # Calculate the average y_param for each combination of x1_param and x2_param
        avg_df = df.groupby([x1_param, x2_param])[y_param].mean().reset_index()

        unique_values = avg_df[x2_param].unique()
        colors = self.get_colors(len(unique_values))
        color_mapping = {cell: color for cell, color in zip(unique_values, colors)}

        fig = go.Figure()

        for value in unique_values:
            filtered_df = avg_df[avg_df[x2_param] == value]
            fig.add_trace(
                go.Bar(
                    x=filtered_df[x1_param],
                    y=filtered_df[y_param],
                    name=value,
                    marker_color=color_mapping[value],
                )
            )

            fig.add_hline(
                y=1.3,
                line_color="red",
                line_dash="dot",
                annotation_text="",
                annotation_position="bottom right",
                annotation_font_size=20,
                annotation_font_color="blue",
            )

        fig.update_layout(
            barmode="group",
            # xaxis_title=x1_param,
            yaxis_title=y_param,
            plot_bgcolor="#F5F5F5",
            paper_bgcolor="#F5F5F5",
            height=350,
            font=dict(family="Vodafone", size=18, color="#717577"),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
                bgcolor="#F5F5F5",
                bordercolor="#FFFFFF",
                borderwidth=0,
                itemclick="toggleothers",
                itemdoubleclick="toggle",
            ),
            margin=dict(l=20, r=20, t=40, b=20),
        )

        container = st.container()
        with container:
            st.plotly_chart(fig, use_container_width=True)

    # TAG: - Create chart for CQI Cluster
    def cqiclusterchart(self, df, tier_data, xrule=None):
        # Rename df columns for consistency
        df = df.rename(
            columns={"DATE_ID": "date", "EUtranCellFDD": "cellname", "CQI": "cqi"}
        )

        # Convert date column to datetime format
        df["date"] = pd.to_datetime(df["date"])

        # Get unique cellnames from tier_data
        unique_cellnames = tier_data["cellname"].unique()

        # Get unique adjcellnames from tier_data
        unique_adjcellnames = tier_data["adjcellname"].unique()

        # Combine unique_cellnames and unique_adjcellnames to get all unique names
        all_unique_names = np.unique(
            np.concatenate((unique_cellnames, unique_adjcellnames))
        )

        # Generate colors for all unique names
        colors = self.get_colors(len(all_unique_names))

        # Create color mapping for all unique names
        color_mapping = {name: color for name, color in zip(all_unique_names, colors)}

        # Create subplots
        fig = make_subplots(rows=1, cols=len(unique_cellnames), shared_yaxes=True)

        for i, cellname in enumerate(unique_cellnames):
            # Filter df for the current cellname
            baseline_chart1 = df[df["cellname"] == cellname]

            # Sort baseline_chart1 by date
            baseline_chart1 = baseline_chart1.sort_values("date")
            color = color_mapping.get(
                cellname, "black"
            )  # Default to black if not found

            # Create dashdot line for cellname
            fig.add_trace(
                go.Scatter(
                    x=baseline_chart1["date"],
                    y=baseline_chart1["cqi"],
                    mode="lines+text",
                    line=dict(color=color, dash="dashdot", width=5),
                    name=f"{cellname} - Source",
                    hovertemplate="%{y:.2f}<extra></extra>",
                    hoverlabel=dict(bgcolor="white", font=dict(color="black")),
                    text=[""] * (len(baseline_chart1) - 5) + [f"{cellname}"],
                    textposition="top center",
                    textfont=dict(size=10, color=color),
                ),
                row=1,
                col=i + 1,
            )

            # Get adjcellnames for the current cellname
            adjcellnames = tier_data[tier_data["cellname"] == cellname][
                "adjcellname"
            ].unique()

            for adjcellname in adjcellnames:
                # Filter df for the current adjcellname
                tier_value = df[df["cellname"] == adjcellname]

                # Sort tier_value by date
                tier_value = tier_value.sort_values("date")

                # Get color for the current adjcellname from the color mapping
                color = color_mapping.get(
                    adjcellname, "black"
                )  # Default to black if not found

                # Create line chart for adjcellname
                fig.add_trace(
                    go.Scatter(
                        x=tier_value["date"],
                        y=tier_value["cqi"],
                        mode="lines+text",
                        line=dict(color=color),
                        name=f"{adjcellname} - 1st tier",
                        hovertemplate="%{y:.2f}<extra></extra>",
                        hoverlabel=dict(bgcolor="white", font=dict(color="black")),
                        text=[""] * (len(tier_value) - 5) + [f"{adjcellname}"],
                        textposition="top center",
                        textfont=dict(size=10, color=color),
                    ),
                    row=1,
                    col=i + 1,
                )

            if xrule:
                fig.add_vline(
                    x=xrule,
                    line=dict(color="#F7BB00", width=4, dash="dash"),
                    row=1,
                    col=i + 1,
                )

        # Update layout
        fig.update_layout(
            plot_bgcolor="#F5F5F5",
            paper_bgcolor="#F5F5F5",
            font=dict(family="Vodafone", size=50, color="#717577"),
            margin=dict(l=20, r=20, t=40, b=20),
            height=350,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.4,
                xanchor="center",
                x=0.5,
                bgcolor="#F5F5F5",
                bordercolor="#F5F5F5",
                itemclick="toggleothers",
                itemdoubleclick="toggle",
                font=dict(size=20),
            ),
        )

        with stylable_container(
            key="container_with_border",
            css_styles="""
                {
                    background-color: #F5F5F5;
                    border: 2px solid rgba(49, 51, 63, 0.2);
                    border-radius: 0.5rem;
                    padding: calc(1em - 1px)
                }
                """,
        ):
            # Display the chart in Streamlit
            container = st.container()
            with container:
                st.plotly_chart(fig, use_container_width=True)

    # TODO: - create_charts_tastate
    def create_charts_tastate(self, df):
        # Select the specific headers for plotting
        plot_columns = [
            "perc_300",
            "perc_500",
            "perc_700",
            "perc_1000",
            "perc_1500",
            "perc_2000",
            "perc_3000",
            "perc_5000",
            "perc_10000",
            "perc_15000",
            "perc_30000",
        ]

        if "ci" in df.columns:
            df = df[["ci", "Cell_Name"] + plot_columns]
            color_by = "ci"
        else:
            df = df[["Cell_Name"] + plot_columns]
            color_by = "Cell_Name"

        x_values = plot_columns
        unique_values = df[color_by].unique()
        colors = self.get_colors(len(unique_values))
        color_mapping = {value: color for value, color in zip(unique_values, colors)}

        fig = go.Figure()

        for value in unique_values:
            filtered_df = df[df[color_by] == value]
            cell_name = filtered_df["Cell_Name"].iloc[
                0
            ]  # Get the corresponding Cell_Name
            fig.add_trace(
                go.Bar(
                    x=x_values,
                    y=filtered_df.loc[:, x_values].values[0],
                    name=cell_name,
                    marker_color=color_mapping[value],
                )
            )

        fig.update_layout(
            barmode="group",
            xaxis_title="",
            yaxis_title="TOTAL",
            plot_bgcolor="#F5F5F5",
            paper_bgcolor="#F5F5F5",
            height=500,
            font=dict(family="Vodafone", size=25, color="#717577"),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.3,
                xanchor="center",
                x=0.5,
                bgcolor="#F5F5F5",
                bordercolor="#F5F5F5",
                itemclick="toggleothers",
                itemdoubleclick="toggle",
                font=dict(size=20),
            ),
            margin=dict(l=20, r=20, t=40, b=20),
        )

        with stylable_container(
            key="container_with_border",
            css_styles="""
                {
                    background-color: #F5F5F5;
                    border: 2px solid rgba(49, 51, 63, 0.2);
                    border-radius: 0.5rem;
                    padding: calc(1em - 1px)
                }
                """,
        ):
            container = st.container()
            with container:
                st.plotly_chart(fig, use_container_width=True)

    def create_charts_p_charts(self, )

class App:
    def __init__(self):
        self.config = Config().load()
        self.database_session = DatabaseSession(self.config)
        self.query_manager = None
        self.dataframe_manager = DataFrameManager()
        self.streamlit_interface = StreamlitInterface()
        self.chart_generator = ChartGenerator()
        self.geodata = None

    def run(self):
        # Create database session
        session, engine = self.database_session.create_session()
        if session is None:
            return

        self.query_manager = QueryManager(engine)

        # Load sitelist
        script_dir = os.path.dirname(__file__)

        sitelist_path = os.path.join(script_dir, "test_sitelist.csv")
        sitelist = self.streamlit_interface.load_sitelist(sitelist_path)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        assets_image = os.path.join(project_root, "assets/")

        # Site selection
        (
            col1,
            col2,
            col3,
            col4,
            _,
        ) = st.columns([1, 1, 1, 1, 3])
        with col1:
            date_range = self.streamlit_interface.select_date_range()
            st.session_state["date_range"] = date_range

        with col2:
            selected_sites = self.streamlit_interface.site_selection(sitelist)
            st.session_state.selected_sites = selected_sites

        with col3:
            selected_neids = self.streamlit_interface.neid_selection(sitelist)
            st.session_state.selected_neids = selected_neids

        with col4:
            xrule = self.streamlit_interface.select_xrule_date()
            st.session_state["xrule"] = xrule

        # Fetch data for each selected site
        if st.button("Run Query"):
            if selected_sites and date_range:
                start_date, end_date = date_range
                combined_target_data = []
                combined_ltetastate_data = []
                combined_ltedaily_data = []

                # Fetch MCOM data
                def load_tier_data(tier_path):
                    try:
                        tier_data = pd.read_csv(tier_path)
                        st.write("Successfully loaded tier.csv")
                    except FileNotFoundError:
                        st.error(f"File does not exist: {tier_path}")
                        tier_data = None
                    except pd.errors.EmptyDataError:
                        st.write(f"The file {tier_path} is empty.")
                        tier_data = None
                    except Exception as e:
                        st.write(f"An error occurred while reading {tier_path}: {e!s}")
                        tier_data = None
                    return tier_data

                def load_isd_data(isd_path):
                    try:
                        isd_data = pd.read_csv(isd_path)
                        st.write("Successfully loaded isd.csv")
                    except FileNotFoundError:
                        st.error(f"File does not exist: {isd_path}")
                        isd_data = None
                    except pd.errors.EmptyDataError:
                        st.write(f"The file {isd_path} is empty.")
                        isd_data = None
                    except Exception as e:
                        st.write(f"An error occurred while reading {isd_path}: {e!s}")
                        isd_data = None
                    return isd_data

                def calculate_rf(df_isd_data, df_tastate_data):
                    try:
                        # Perform arithmetic operations
                        df_isd_data["ta_overshoot"] = df_isd_data["isd"] + (
                            0.1 * df_isd_data["isd"]
                        )
                        df_isd_data["ta_undershoot"] = df_isd_data["isd"] / 3
                        df_isd_data["ta_overlap"] = df_isd_data["isd"] / 2 + (
                            0.2 * df_isd_data["isd"]
                        )

                        # Merge the dataframes
                        df_merged = pd.merge(
                            df_isd_data,
                            df_tastate_data,
                            left_on=["ci", "enbid"],
                            right_on=["ci", "enodebid"],
                        )

                        # Apply conditional logic for 'final_ta_status'
                        conditions = [
                            (df_merged["isd"] > 5),
                            (df_merged["perc90_ta_distance_km"] > df_merged["isd"]),
                            (
                                df_merged["perc90_ta_distance_km"]
                                < 0.5 * df_merged["isd"]
                            ),
                            (
                                df_merged["perc90_ta_distance_km"]
                                > 0.5 * df_merged["ta_overlap"]
                            ),
                            (
                                df_merged["perc90_ta_distance_km"]
                                == 0.5 * df_merged["ta_overlap"]
                            ),
                        ]

                        choices = [
                            "📐 Open Area",
                            "📈 TA Overshoot",
                            "📉 TA Undershoot",
                            "❌ TA Overlap",
                            "✔️ TA Proper",
                        ]

                        df_merged["final_ta_status"] = np.select(
                            conditions, choices, default="Open Area"
                        )

                        # Select final columns
                        final_df = df_merged[
                            [
                                "siteid",
                                "neid",
                                "eutrancell",
                                "isd",
                                "ta_overshoot",
                                "ta_undershoot",
                                "ta_overlap",
                                "final_ta_status",
                            ]
                        ]

                        return final_df

                    except Exception as e:
                        print(f"An error occurred: {e}")
                        return None

                # Define a function to display images or messages
                def display_image_or_message(
                    column, folder_path, image_name, message_prefix
                ):
                    image_path = os.path.join(folder_path, image_name)
                    if os.path.exists(image_path):
                        column.image(image_path, caption=None, use_column_width=True)
                    else:
                        column.write(f"{message_prefix}: {image_path}")

                # Define a function to style and display markdown
                def display_styled_markdown(
                    column, text, font_size=24, text_align="left", tag="h6"
                ):
                    styling_args = {
                        "font_size": font_size,
                        "text_align": text_align,
                        "tag": tag,
                    }
                    column.markdown(*styling(text, **styling_args))

                for siteid in selected_sites:
                    folder = os.path.join(project_root, "sites", siteid)
                    tier_path = os.path.join(folder, "tier.csv")
                    isd_path = os.path.join(folder, "isd.csv")

                    if os.path.exists(folder):
                        tier_data = load_tier_data(tier_path)
                    else:
                        st.error(f"Folder does not exist: {folder}")
                        tier_data = None

                    if os.path.exists(folder):
                        isd_data = load_isd_data(isd_path)
                    else:
                        st.error(f"Folder does not exist: {folder}")
                        isd_data = None

                    # st.write(f"ISD data: {isd_data}")

                    if tier_data is not None:
                        unique_eutrancellfdd = sorted(
                            set(tier_data["cellname"].unique()).union(
                                set(tier_data["adjcellname"].unique())
                            )
                        )
                        all_data = pd.concat(
                            [
                                self.query_manager.get_cqi_cluster(
                                    eutrancellfdd, start_date, end_date
                                )
                                for eutrancellfdd in unique_eutrancellfdd
                            ],
                            ignore_index=True,
                        )

                        self.dataframe_manager.add_dataframe(
                            f"cqitier_{siteid}", all_data
                        )

                    sac.divider(color="black", align="center")
                    col1, col2, _ = st.columns([1, 1, 5])

                    with col1.container():
                        with stylable_container(
                            key="erilogo",
                            css_styles="""
                                img {
                                    display: block;
                                    margin-left: auto;
                                    margin-right: auto;
                                    width: 100%;
                                    position: relative;
                                    top: 5px;
                                }
                            """,
                        ):
                            st.image(assets_image + "eri.png")

                    with col2.container():
                        with stylable_container(
                            key="tsellogo",
                            css_styles="""
                                img {
                                    display: block;
                                    margin-left: auto;
                                    margin-right: auto;
                                    width: 100%;
                                    position: relative;
                                    top: 0px;  /* Adjust this value as needed */
                                }
                            """,
                        ):
                            st.image(assets_image + "tsel.png")
                    st.markdown("# ")
                    col1, col2 = st.columns([2, 1])

                    # Display styled markdowns
                    display_styled_markdown(col1, f"📝 Naura Site {siteid}")
                    display_styled_markdown(col2, f"⚠️ Alarm Site {siteid}")

                    # Create containers with borders
                    con1 = col1.container(border=True)
                    con2 = col2.container(border=True)

                    # Display images or messages
                    if os.path.exists(folder):
                        display_image_or_message(
                            con1, folder, "naura.jpg", "Please upload the image"
                        )
                        display_image_or_message(
                            con2, folder, "alarm.jpg", "Please upload the image"
                        )
                    else:
                        st.error(f"Path does not exist: {folder}")

                    mcom_data = self.query_manager.get_mcom_data(siteid)
                    self.dataframe_manager.add_dataframe(
                        f"mcom_data_{siteid}", mcom_data
                    )
                    # st.write(mcom_data)

                    for _, row in mcom_data.iterrows():
                        target_data = self.query_manager.get_target_data(
                            row["KABUPATEN"],
                            row["MC_class"],
                            row["LTE"],
                        )
                        target_data["EutranCell"] = row["Cell_Name"]
                        combined_target_data.append(target_data)

                    # Fetch LTE daily data for each site
                    ltedaily_data = self.query_manager.get_ltedaily_data(
                        siteid, selected_neids, start_date, end_date
                    )
                    combined_ltedaily_data.append(ltedaily_data)
                    self.dataframe_manager.add_dataframe(
                        f"ltedaily_data_{siteid}", ltedaily_data
                    )

                # Combine target data and display
                if combined_target_data:
                    combined_target_df = pd.concat(
                        combined_target_data, ignore_index=True
                    )
                    self.dataframe_manager.add_dataframe(
                        "combined_target_data", combined_target_df
                    )
                    self.dataframe_manager.display_dataframe(
                        "combined_target_df", "target"
                    )

                # Combine ltetastate data and display
                if combined_ltetastate_data:
                    combined_ltetastate_df = pd.concat(
                        combined_ltetastate_data, ignore_index=True
                    )
                    self.dataframe_manager.add_dataframe(
                        "combined_ltetastate_data", combined_ltetastate_df
                    )

                # Combine ltedaily data and display
                if combined_ltedaily_data:
                    combined_ltedaily_df = pd.concat(
                        combined_ltedaily_data, ignore_index=True
                    )
                    self.dataframe_manager.add_dataframe(
                        "combined_ltedaily_data", combined_ltedaily_df
                    )

                    # Combine target data with ltedaily data
                    combined_target_ltedaily_df = pd.merge(
                        combined_target_df,
                        combined_ltedaily_df,
                        on="EutranCell",
                        how="right",
                    )
                    self.dataframe_manager.add_dataframe(
                        "combined_target_ltedaily_data", combined_target_ltedaily_df
                    )

                    yaxis_ranges = [
                        [0, 105],
                        [50, 105],
                        [-130, 0],
                        [0, 5],
                        [0, 20],
                        [-120, -105],
                    ]

                    # TAG: - Availability
                    st.markdown(
                        *styling(
                            f"📶 Service Availability for Site {siteid}",
                            font_size=24,
                            text_align="left",
                            tag="h6",
                        )
                    )
                    self.chart_generator.create_charts(
                        df=combined_ltedaily_df,
                        param="Availability",
                        site="Combined Sites",
                        x_param="DATE_ID",
                        y_param="Availability",
                        sector_param="EutranCell",
                        yaxis_range=yaxis_ranges[0],
                        xrule=True,
                    )

                    # TAG: - RRC Setup Success Rate
                    st.markdown(
                        *styling(
                            f"📶 RRC Success Rate for Site {siteid}",
                            font_size=24,
                            text_align="left",
                            tag="h6",
                        )
                    )
                    self.chart_generator.create_charts_datums(
                        df=combined_target_ltedaily_df,
                        param="RRC Setup Success Rate",
                        site="Combined Sites",
                        x_param="DATE_ID",
                        y_param="RRC_SR",
                        sector_param="EutranCell",
                        y2_avg="CSSR",
                        yaxis_range=yaxis_ranges[0],
                        xrule=True,
                    )

                    # TAG: - ERAB SR
                    st.markdown(
                        *styling(
                            f"📶 E-RAB Setup Success Rate for Site {siteid}",
                            font_size=24,
                            text_align="left",
                            tag="h6",
                        )
                    )

                    self.chart_generator.create_charts_datums(
                        df=combined_target_ltedaily_df,
                        param="RRC Setup Success Rate",
                        site="Combined Sites",
                        x_param="DATE_ID",
                        y_param="ERAB_SR",
                        sector_param="EutranCell",
                        y2_avg="CSSR",
                        yaxis_range=yaxis_ranges[0],
                        xrule=True,
                    )

                    # TAG: - SSSR
                    st.markdown(
                        *styling(
                            f"📶 Session Setup Success Rate for Site {siteid}",
                            font_size=24,
                            text_align="left",
                            tag="h6",
                        )
                    )

                    self.chart_generator.create_charts_datums(
                        df=combined_target_ltedaily_df,
                        param="RRC Setup Success Rate",
                        site="Combined Sites",
                        x_param="DATE_ID",
                        y_param="SSSR",
                        sector_param="EutranCell",
                        y2_avg="CSSR",
                        yaxis_range=yaxis_ranges[0],
                        xrule=True,
                    )

                    # TAG: - CSSR
                    st.markdown(
                        *styling(
                            f"📶 Session Abnormal Release Sectoral for Site {siteid}",
                            font_size=24,
                            text_align="left",
                            tag="h6",
                        )
                    )

                    self.chart_generator.create_charts_datums(
                        df=combined_target_ltedaily_df,
                        param="Session Abnormal Release",
                        site="Combined Sites",
                        x_param="DATE_ID",
                        y_param="SAR",
                        sector_param="EutranCell",
                        y2_avg="Service Drop Rate",
                        yaxis_range=None,
                        xrule=True,
                    )

                    # TAG: - CQI Non HOM
                    st.markdown(
                        *styling(
                            f"📶 CQI Distribution (Non-Homogeneous) Sectoral for Site {siteid}",
                            font_size=24,
                            text_align="left",
                            tag="h6",
                        )
                    )

                    self.chart_generator.create_charts_datums(
                        df=combined_target_ltedaily_df,
                        param="CQI Non HOM",
                        site="Combined Sites",
                        x_param="DATE_ID",
                        y_param="avgcqinonhom",
                        sector_param="EutranCell",
                        y2_avg="CQI",
                        yaxis_range=yaxis_ranges[4],
                        xrule=True,
                    )

                    # TAG: - Spectral Efficiency
                    st.markdown(
                        *styling(
                            f"📶 Spectral Efficiency Analysis Sectoral for Site {siteid}",
                            font_size=24,
                            text_align="left",
                            tag="h6",
                        )
                    )

                    self.chart_generator.create_charts_datums(
                        df=combined_target_ltedaily_df,
                        param="Spectral Efficiency",
                        site="Combined Sites",
                        x_param="DATE_ID",
                        y_param="SE_DAILY",
                        sector_param="EutranCell",
                        y2_avg="SE",
                        yaxis_range=None,
                        xrule=True,
                    )

                    # TAG: - Intra HO SR
                    st.markdown(
                        *styling(
                            f"📶 Intra-Frequency Handover Performance Sectoral for Site {siteid} (%)",
                            font_size=24,
                            text_align="left",
                            tag="h6",
                        )
                    )

                    self.chart_generator.create_charts_datums(
                        df=combined_target_ltedaily_df,
                        param="Intra HO SR",
                        site="Combined Sites",
                        x_param="DATE_ID",
                        y_param="Intra_HO_Exe_SR",
                        sector_param="EutranCell",
                        y2_avg="Intra Freq HOSR",
                        yaxis_range=yaxis_ranges[0],
                        xrule=True,
                    )

                    # TAG: - Inter HO SR
                    st.markdown(
                        *styling(
                            f"📶 Inter-Frequency Handover Performance Sectoral for Site {siteid} (%)",
                            font_size=24,
                            text_align="left",
                            tag="h6",
                        )
                    )

                    self.chart_generator.create_charts_datums(
                        df=combined_target_ltedaily_df,
                        param="Inter HO SR",
                        site="Combined Sites",
                        x_param="DATE_ID",
                        y_param="Inter_HO_Exe_SR",
                        sector_param="EutranCell",
                        y2_avg="Inter Freq HOSR",
                        yaxis_range=yaxis_ranges[0],
                        xrule=True,
                    )

                    # TAG: - UL RSSI
                    st.markdown(
                        *styling(
                            f"📶 Average UL RSSI Sectoral for Site {siteid} (dBm)",
                            font_size=24,
                            text_align="left",
                            tag="h6",
                        )
                    )

                    self.chart_generator.create_charts_datums(
                        df=combined_target_ltedaily_df,
                        param="UL RSSI",
                        site="Combined Sites",
                        x_param="DATE_ID",
                        y_param="UL_INT_PUSCH_y",
                        sector_param="EutranCell",
                        y2_avg="UL_INT_PUSCH_x",
                        yaxis_range=yaxis_ranges[2],
                        yaxis_reverse=True,
                        xrule=True,
                    )

                    # TAG: - Throughput Mpbs
                    st.markdown(
                        *styling(
                            f"📶 Throughput (Mbps) Sectoral for Site {siteid}",
                            font_size=24,
                            text_align="left",
                            tag="h6",
                        )
                    )

                    self.chart_generator.create_charts(
                        df=combined_target_ltedaily_df,
                        param="Throughput Mpbs",
                        site="Combined Sites",
                        x_param="DATE_ID",
                        y_param="CellDownlinkAverageThroughput",
                        sector_param="EutranCell",
                        yaxis_range=None,
                        xrule=True,
                    )

                    # TAG: - Payload Sector
                    st.markdown(
                        *styling(
                            f"📶 Payload Distribution Sectoral for Site {siteid} (Gpbs)",
                            font_size=24,
                            text_align="left",
                            tag="h6",
                        )
                    )

                    self.chart_generator.create_charts_area(
                        df=combined_target_ltedaily_df,
                        param="Payload Sectoral",
                        site="Combined Sites",
                        x_param="DATE_ID",
                        y_param="Payload_Total(Gb)",
                        sector_param="EutranCell",
                        yaxis_range=None,
                        xrule=True,
                    )

                payload_data = self.query_manager.get_ltedaily_payload(
                    selected_sites, start_date, end_date
                )
                self.dataframe_manager.add_dataframe("payload_data", payload_data)

                ltehourly_data = self.query_manager.get_ltehourly_data(
                    selected_sites, end_date
                )

                ltehourly_data["datetime"] = pd.to_datetime(
                    ltehourly_data["DATE_ID"].astype(str)
                    + " "
                    + ltehourly_data["hour_id"].astype(str).str.zfill(2),
                    format="%Y-%m-%d %H",
                )

                ltebusyhour_data = self.query_manager.get_busyhour(
                    selected_sites, end_date
                )
                self.dataframe_manager.add_dataframe(
                    "ltebusyhour_data", ltebusyhour_data
                )

                # TAG: - LTE Hourly Data
                self.dataframe_manager.add_dataframe("ltehourly_data", ltehourly_data)

                vswr_data = self.query_manager.get_vswr_data(selected_sites, end_date)
                self.dataframe_manager.add_dataframe("vswr_data", vswr_data)

                col1, col2 = st.columns([1, 1])
                with col1:
                    st.markdown(
                        *styling(
                            f"📶 Payload Distribution by Frequency for Site  {siteid} (Gpbs)",
                            font_size=24,
                            text_align="left",
                            tag="h6",
                        )
                    )

                with col2:
                    st.markdown(
                        *styling(
                            f"📶 Total Site Payload Overview for Site {siteid} (Gpbs)",
                            font_size=24,
                            text_align="left",
                            tag="h6",
                        )
                    )
                # TAG: - Payload Neid
                col1, col2 = st.columns([1, 1])
                con1 = col1.container()
                con2 = col2.container()
                with con1:
                    with stylable_container(
                        key="container_with_border",
                        css_styles="""
                            {
                                background-color: #F5F5F5;
                                border: 2px solid rgba(49, 51, 63, 0.2);
                                border-radius: 0.5rem;
                                padding: calc(1em - 1px)
                            }
                            """,
                    ):
                        self.chart_generator.create_charts_neid(
                            df=payload_data,
                            param="Payload Frequency",
                            site="Sites",
                            x_param="DATE_ID",
                            y_param="Payload_Total(Gb)",
                            neid="NEID",
                            yaxis_range=None,
                            xrule=True,
                        )

                with con2:
                    with stylable_container(
                        key="container_with_border",
                        css_styles="""
                            {
                                background-color: #F5F5F5;
                                border: 2px solid rgba(49, 51, 63, 0.2);
                                border-radius: 0.5rem;
                                padding: calc(1em - 1px)
                            }
                            """,
                    ):
                        self.chart_generator.create_charts_neid(
                            df=payload_data,
                            param="Payload By Site",
                            site="Sites",
                            x_param="DATE_ID",
                            y_param="Payload_Total(Gb)",
                            neid="SITEID",
                            yaxis_range=None,
                            xrule=True,
                        )

                st.markdown(
                    *styling(
                        f"📶 CQI Comparison Across Frequencies for Site  {siteid}",
                        font_size=24,
                        text_align="left",
                        tag="h6",
                    )
                )

                self.chart_generator.create_charts(
                    df=ltebusyhour_data,
                    param="CQI Overlay",
                    site="Combined Sites",
                    x_param="DATE_ID",
                    y_param="CQI",
                    sector_param="EUtranCellFDD",
                    yaxis_range=None,
                    xrule=True,
                )

                # MARK: CQI 1st tier
                st.markdown(
                    *styling(
                        f"📶 CQI: {siteid} vs. Tier 1",
                        font_size=24,
                        text_align="left",
                        tag="h6",
                    )
                )
                if tier_data is not None:
                    try:
                        self.chart_generator.cqiclusterchart(
                            all_data,
                            tier_data,
                            xrule,
                        )
                    except Exception as e:
                        st.write(f"An error occurred: {e!s}")

                # TAG: - PRB & Active User
                st.markdown(
                    *styling(
                        f"📶 PRB Utilization Sectoral for Site {siteid}",
                        font_size=24,
                        text_align="left",
                        tag="h6",
                    )
                )
                self.chart_generator.create_charts(
                    df=ltehourly_data,
                    param="PRB Utilization",
                    site="Combined Sites",
                    x_param="datetime",
                    y_param="DL_Resource_Block_Utilizing_Rate",
                    sector_param="EUtranCellFDD",
                    yaxis_range=None,
                )

                st.markdown(
                    *styling(
                        f"📶 Active User Sectoral for {siteid}",
                        font_size=24,
                        text_align="left",
                        tag="h6",
                    )
                )
                self.chart_generator.create_charts(
                    df=ltehourly_data,
                    param="Active User",
                    site="Combined Sites",
                    x_param="datetime",
                    y_param="Active User",
                    sector_param="EUtranCellFDD",
                    yaxis_range=None,
                )
                # Fetch VSWR data

                # TAG: - VSWR
                col1, col2 = st.columns([3, 2])

                with col1:
                    st.markdown(
                        *styling(
                            f"📶 VSWR Analysis for Site {siteid} (dBm)",
                            font_size=24,
                            text_align="left",
                            tag="h6",
                        )
                    )

                with col2:
                    st.markdown(
                        *styling(
                            f"📶 RET After {siteid}",
                            font_size=24,
                            text_align="left",
                            tag="h6",
                        )
                    )

                col1, col2 = st.columns([3, 2])
                con1 = col1.container()
                con2 = col2.container()
                with con1:
                    with stylable_container(
                        key="container_with_border",
                        css_styles="""

                        img {
                            display: block;
                            margin-left: auto;
                            margin-right: auto;
                            width: 100%;
                            position: relative;
                            top: 0px;  /* Adjust this value as needed */
                        }
                        container {
                            background-color: #F5F5F5;
                            border: 2px solid rgba(49, 51, 63, 0.2);
                            border-radius: 0.5rem;
                            padding: calc(1em - 1px)
                        }
                        """,
                    ):
                        self.chart_generator.create_charts_vswr(
                            df=vswr_data,
                            x1_param="DATE_ID",
                            x2_param="RRU",
                            y_param="VSWR",
                            nename="RRU",
                        )

                with con2:
                    with stylable_container(
                        key="container_with_border",
                        css_styles="""
                        img {
                            display: block;
                            margin-left: auto;
                            margin-right: auto;
                            width: 100%;
                            max-width: 80%;
                            position: relative;
                            top: 0px;
                        }
                        .custom-container {
                            background-color: #F5F5F5;
                            border: 2px solid rgba(49, 51, 63, 0.2);
                            border-radius: 0.5rem;
                            padding: calc(1em - 1px);
                        }
                        """,
                    ):
                        if os.path.exists(folder):
                            ret = os.path.join(folder, "ret.jpg")
                            if os.path.exists(ret):
                                st.image(ret, caption=None, use_column_width=True)
                            else:
                                st.error(f"Please upload the image: {ret}")
                        else:
                            st.error(f"Path does not exist: {folder}")

                # MARK: - GeoApp MDT Data
                mcom_data1 = self.query_manager.get_mcom_data(siteid)
                st.session_state.mcom_data1 = mcom_data1
                st.session_state.combined_target_data = combined_target_data
                required_columns = [
                    "Site_ID",
                    "NODE_ID",
                    "NE_ID",
                    "Cell_Name",
                    "Longitude",
                    "Latitude",
                    "Dir",
                    "Ant_BW",
                    "Ant_Size",
                    "cellId",
                    "eNBId",
                    "MC_class",
                    "KABUPATEN",
                    "LTE",
                ]
                if not all(column in mcom_data.columns for column in required_columns):
                    raise ValueError(
                        "The dataframe does not contain all required columns"
                    )

                self.dataframe_manager.add_dataframe(f"mcom_data_{siteid}", mcom_data)
                # TODO: mcom_data
                # st.write(mcom_data)

                if isinstance(selected_neids, list):
                    selected_neids = selected_neids[0]

                if isinstance(selected_neids, str):
                    ltemcomdata = mcom_data[mcom_data["NE_ID"] == selected_neids]
                else:
                    raise ValueError(
                        "selected_neid should be a string or a list containing a string"
                    )

                # MARK: - GeoApp MDT Data
                ltemdtdata = self.query_manager.get_ltemdt_data(selected_sites)
                self.dataframe_manager.add_dataframe("ltemdtdata", ltemdtdata)
                ltemcomdata["eNBId"] = ltemcomdata["eNBId"].astype(float)
                ltemcomdata["cellId"] = ltemcomdata["cellId"].astype(float)
                ltemdtdata["enodebid"] = ltemdtdata["enodebid"].astype(float)
                ltemdtdata["ci"] = ltemdtdata["ci"].astype(float)

                filter_set = set(zip(ltemcomdata["eNBId"], ltemcomdata["cellId"]))

                ltemdtdata_final = ltemdtdata[
                    ltemdtdata[["enodebid", "ci"]].apply(tuple, axis=1).isin(filter_set)
                ]

                # TODO: mcom and ta state
                # mcom_ta = self.query_manager.get_mcom_tastate(selected_neids)
                # self.dataframe_manager.add_dataframe("mcom_ta", mcom_data1)
                ltetastate_data = self.query_manager.get_ltetastate_data(selected_sites)
                self.dataframe_manager.add_dataframe("ltetastate_data", ltetastate_data)
                mcom_data["cellId"] = mcom_data["cellId"].astype(float)
                mcom_data["eNBId"] = mcom_data["eNBId"].astype(float)
                ltetastate_data["ci"] = ltetastate_data["ci"].astype(float)
                ltetastate_data["enodebid"] = ltetastate_data["enodebid"].astype(float)

                mcom_ta_renamed = mcom_data.rename(
                    columns={"cellId": "ci", "eNBId": "enodebid"}
                )

                mcom_ta_indexed = mcom_ta_renamed.set_index(["ci", "enodebid"])
                ltetastate_data_indexed = ltetastate_data.set_index(["ci", "enodebid"])
                tastate_data = pd.merge(
                    mcom_ta_indexed,
                    ltetastate_data_indexed,
                    on=["ci", "enodebid"],
                    how="inner",
                )

                # MARK: use this to calculate RF Propagation
                self.dataframe_manager.add_dataframe("tastate_data", tastate_data)
                col1, col2 = st.columns([3, 2])
                con1 = col1.container()
                con2 = col2.container()
                # MARK: - GeoApp MDT Data
                st.session_state.mcom_data = mcom_data
                st.session_state.combined_target_data = combined_target_data

                # MARK: - GeoApp MDT Data
                ltemdtdata = self.query_manager.get_ltemdt_data(selected_sites)
                self.dataframe_manager.add_dataframe("ltemdtdata", ltemdtdata)
                st.session_state.ltemdtdata = ltemdtdata
                st.session_state.ltemdtdata_final = ltemdtdata_final
                st.session_state.ltemcomdata = ltemdtdata_final
                with con1:
                    st.markdown(
                        *styling(
                            f"☢️ MDT for Site {siteid}",
                            font_size=24,
                            text_align="left",
                            tag="h6",
                        )
                    )
                    self.geodata = GeoApp(mcom_data, ltemdtdata)
                    self.geodata.run_geo_app()
                with con2:
                    st.markdown(*styling(" "))
                    st.markdown(
                        *styling(
                            f"📶 TA State for Site {siteid}",
                            font_size=24,
                            text_align="left",
                            tag="h4",
                        )
                    )
                    self.chart_generator.create_charts_tastate(tastate_data)
                    st.markdown(
                        *styling(
                            f"📶 TA Remark for Site {siteid}",
                            font_size=24,
                            text_align="left",
                            tag="h4",
                        )
                    )
                    tafinal = calculate_rf(isd_data, tastate_data)
                    st.table(tafinal)

                with col1:
                    st.markdown(
                        *styling(
                            f"⛐ Drive Test Verification for Site {siteid}",
                            font_size=28,
                            text_align="left",
                            tag="h6",
                        )
                    )

                col1, col2, col3 = st.columns([1, 1, 1])
                con1 = col1.container(border=True)
                con2 = col2.container(border=True)
                con3 = col3.container(border=True)

                with con1:
                    with stylable_container(
                        key="rsrpsinr",
                        css_styles="""
                        img {
                            display: block;
                            margin-left: auto;
                            margin-right: auto;
                            width: 100%;
                            max-width: 100%;
                            position: relative;
                            top: 0px;
                        }
                        .custom-container {
                            background-color: #F5F5F5;
                            border: 2px solid rgba(49, 51, 63, 0.2);
                            border-radius: 0.5rem;
                            padding: calc(1em - 1px);
                        }
                        """,
                    ):
                        st.markdown(
                            *styling(
                                f"RSRP & SINR {siteid}",
                                font_size=24,
                                text_align="center",
                                tag="h6",
                            )
                        )
                        if os.path.exists(folder):
                            idlersrp = os.path.join(folder, "idlersrp.png")
                            sinr = os.path.join(folder, "sinr.png")
                            if os.path.exists(idlersrp) and os.path.exists(sinr):
                                st.markdown(*styling("RSRP IDLE", font_size=15))
                                st.image(idlersrp, caption=None, use_column_width=True)
                                st.markdown(*styling("SINR", font_size=15))
                                st.image(sinr, caption=None, use_column_width=True)
                            else:
                                st.error(
                                    f"Please upload the images: {idlersrp} & {sinr}"
                                )
                        else:
                            st.error(f"Path does not exist: {folder}")

                with con2:
                    with stylable_container(
                        key="pci",
                        css_styles="""
                        img {
                            display: block;
                            margin-left: auto;
                            margin-right: auto;
                            width: 100%;
                            max-width: 100%;
                            position: relative;
                            top: 0px;
                        }
                        .custom-container {
                            background-color: #F5F5F5;
                            border: 2px solid rgba(49, 51, 63, 0.2);
                            border-radius: 0.5rem;
                            padding: calc(1em - 1px);
                        }
                        """,
                    ):
                        st.markdown(
                            *styling(
                                f"PCI {siteid}",
                                font_size=24,
                                text_align="center",
                                tag="h6",
                            )
                        )
                        if os.path.exists(folder):
                            pci = os.path.join(folder, "pci.png")
                            if os.path.exists(pci):
                                st.markdown(*styling("PCI", font_size=15))
                                st.image(pci, caption=None, use_column_width=True)
                            else:
                                st.error(f"Please upload the images: {pci}")
                        else:
                            st.error(f"Path does not exist: {folder}")

                with con3:
                    with stylable_container(
                        key="pci",
                        css_styles="""
                        img {
                            display: block;
                            margin-left: auto;
                            margin-right: auto;
                            width: 100%;
                            max-width: 100%;
                            position: relative;
                            top: 0px;
                        }
                        .custom-container {
                            background-color: #F5F5F5;
                            border: 2px solid rgba(49, 51, 63, 0.2);
                            border-radius: 0.5rem;
                            padding: calc(1em - 1px);
                        }
                        """,
                    ):
                        st.markdown(
                            *styling(
                                f"THROUGHPUT {siteid}",
                                font_size=24,
                                text_align="center",
                                tag="h6",
                            )
                        )
                        if os.path.exists(folder):
                            dlthp = os.path.join(folder, "dlthp.png")
                            ulthp = os.path.join(folder, "ulthp.png")
                            if os.path.exists(dlthp) & os.path.exists(ulthp):
                                st.markdown(
                                    *styling("THROUGHPUT DOWNLOAD", font_size=15)
                                )
                                st.image(dlthp, caption=None, use_column_width=True)
                                st.markdown(*styling("THROUGHPUT UPLOAD", font_size=15))
                                st.image(ulthp, caption=None, use_column_width=True)
                            else:
                                st.error(f"Please upload the images: {dlthp} & {ulthp}")
                        else:
                            st.error(f"Path does not exist: {folder}")

                # TODO : IMAGE STATIC
                with col1:
                    st.markdown(
                        *styling(
                            f"⛐ CET Static Verification for Site {siteid}",
                            font_size=28,
                            text_align="left",
                            tag="h6",
                        )
                    )

                col1, col2, col3 = st.columns([1, 1, 1])
                con1 = col1.container(border=True)
                con2 = col2.container(border=True)
                con3 = col3.container(border=True)

                with con1:
                    with stylable_container(
                        key="sec1",
                        css_styles="""
                        img {
                            display: block;
                            margin-left: auto;
                            margin-right: auto;
                            width: 100%;
                            max-width: 100%;
                            position: relative;
                            top: 0px;
                        }
                        .custom-container {
                            background-color: #F5F5F5;
                            border: 2px solid rgba(49, 51, 63, 0.2);
                            border-radius: 0.5rem;
                            padding: calc(1em - 1px);
                        }
                        """,
                    ):
                        st.markdown(
                            *styling(
                                f"SECTOR 1 {siteid}",
                                font_size=24,
                                text_align="center",
                                tag="h6",
                            )
                        )
                        if os.path.exists(folder):
                            gridsec1 = os.path.join(folder, "gridsec1.jpg")
                            speedtestsec1 = os.path.join(folder, "speedtestsec1.jpg")
                            servicemodesec1 = os.path.join(
                                folder, "servicemodesec1.jpg"
                            )
                            gridservicemodesec1 = os.path.join(
                                folder, "gridservicemodesec1.jpg"
                            )

                            existing_images = [
                                img
                                for img in [
                                    gridsec1,
                                    speedtestsec1,
                                    gridservicemodesec1,
                                    servicemodesec1,
                                ]
                                if os.path.exists(img)
                            ]

                            if existing_images:
                                for img in existing_images:
                                    st.image(img, caption=None, use_column_width=True)
                            else:
                                st.error("No Functionality Test for Sector 1.")
                        else:
                            st.error(f"Path does not exist: {folder}")

                with con2:
                    with stylable_container(
                        key="sec2",
                        css_styles="""
                        img {
                            display: block;
                            margin-left: auto;
                            margin-right: auto;
                            width: 100%;
                            max-width: 100%;
                            position: relative;
                            top: 0px;
                        }
                        .custom-container {
                            background-color: #F5F5F5;
                            border: 2px solid rgba(49, 51, 63, 0.2);
                            border-radius: 0.5rem;
                            padding: calc(1em - 1px);
                        }
                        """,
                    ):
                        st.markdown(
                            *styling(
                                f"SECTOR 2 {siteid}",
                                font_size=24,
                                text_align="center",
                                tag="h6",
                            )
                        )
                        if os.path.exists(folder):
                            gridsec2 = os.path.join(folder, "gridsec2.jpg")
                            speedtestsec2 = os.path.join(folder, "speedtestsec2.jpg")
                            servicemodesec2 = os.path.join(
                                folder, "servicemodesec2.jpg"
                            )
                            gridservicemodesec2 = os.path.join(
                                folder, "gridservicemodesec2.jpg"
                            )

                            existing_images = [
                                img
                                for img in [
                                    gridsec2,
                                    speedtestsec2,
                                    gridservicemodesec2,
                                    servicemodesec2,
                                ]
                                if os.path.exists(img)
                            ]

                            if existing_images:
                                for img in existing_images:
                                    st.image(img, caption=None, use_column_width=True)
                            else:
                                st.error("No Functionality Test for Sector 2.")
                        else:
                            st.error(f"Path does not exist: {folder}")

                with con3:
                    with stylable_container(
                        key="sec3",
                        css_styles="""
                        img {
                            display: block;
                            margin-left: auto;
                            margin-right: auto;
                            width: 100%;
                            max-width: 100%;
                            position: relative;
                            top: 0px;
                        }
                        .custom-container {
                            background-color: #F5F5F5;
                            border: 2px solid rgba(49, 51, 63, 0.2);
                            border-radius: 0.5rem;
                            padding: calc(1em - 1px);
                        }
                        """,
                    ):
                        st.markdown(
                            *styling(
                                f"SECTOR 3 {siteid}",
                                font_size=24,
                                text_align="center",
                                tag="h6",
                            )
                        )
                        if os.path.exists(folder):
                            gridsec3 = os.path.join(folder, "gridsec3.jpg")
                            speedtestsec3 = os.path.join(folder, "speedtestsec3.jpg")
                            servicemodesec3 = os.path.join(
                                folder, "servicemodesec3.jpg"
                            )
                            gridservicemodesec3 = os.path.join(
                                folder, "gridservicemodesec3.jpg"
                            )

                        if os.path.exists(folder):
                            gridsec3 = os.path.join(folder, "gridsec3.jpg")
                            speedtestsec3 = os.path.join(folder, "speedtestsec3.jpg")
                            servicemodesec3 = os.path.join(
                                folder, "servicemodesec3.jpg"
                            )
                            gridservicemodesec2 = os.path.join(
                                folder, "gridservicemodesec3.jpg"
                            )

                            existing_images = [
                                img
                                for img in [
                                    gridsec3,
                                    speedtestsec3,
                                    gridservicemodesec3,
                                    servicemodesec3,
                                ]
                                if os.path.exists(img)
                            ]

                            if existing_images:
                                for img in existing_images:
                                    st.image(img, caption=None, use_column_width=True)
                            else:
                                st.error("No Functionality Test for Sector 3.")
                        else:
                            st.error(f"Path does not exist: {folder}")

                session.close()
        else:
            if "mcom_data" in st.session_state and "ltemdtdata" in st.session_state:
                self.geodata = GeoApp(
                    st.session_state.mcom_data, st.session_state.ltemdtdata
                )
                self.geodata.run_geo_app()


if __name__ == "__main__":
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
    app = App()
    app.run()
