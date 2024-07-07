import os
import tempfile
from datetime import timedelta

import altair as alt
import folium
import pandas as pd
import streamlit as st
import toml
from branca.element import MacroElement, Template
from colors import ColorPalette
from omegaconf import DictConfig, OmegaConf
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from streamlit_extras.mandatory_date_range import date_range_picker
from streamlit_extras.stylable_container import stylable_container
from styles import styling

# MARK: - Config OK
# BUG: - Need run query if not select neid - DONE
# TODO: - Need to append target to ltedaily data - create another query chart to display target data with datums DONE
# TODO: - Need create chart area for payload parameter - DONE
# TODO: - Need to create chart PRB and Active User - DONE
# TODO:  CQI Overlay - DONE | Geo Plotting


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

    def get_ltehourly_data(self, selected_sites, end_date):
        like_conditions = " OR ".join(
            [f'"EUtranCellFDD" LIKE :site_{i}' for i in range(len(selected_sites))]
        )
        start_date = end_date - timedelta(days=15)
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

    # def get_ltemdt_data(self, enodebid, ci):
    def get_ltemdt_data(self, selected_sites):
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
        return self.fetch_data(query, params=params)

    # def get_ltemdt_data(self, enodebid):
    #     query = text(
    #         """
    #     SELECT *
    #     FROM ltemdt
    #     WHERE enodebid = :enodebid
    #     """
    #     )
    #     return self.fetch_data(query, {"enodebid": enodebid})

    def get_ltetastate_data(self, enodebid, ci):
        query = text(
            """
        SELECT *
        FROM ltetastate
        WHERE enodebid = :enodebid AND ci = :ci
        """
        )
        return self.fetch_data(query, {"enodebid": enodebid, "ci": ci})

    def get_vswr_data(self, selected_sites, end_date):
        like_conditions = " OR ".join(
            [f'"NE_NAME" LIKE :site_{i}' for i in range(len(selected_sites))]
        )

        # Calculate start_date as one day before end_date
        start_date = end_date - timedelta(days=1)

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

    # TAG: - Create Charts  Line
    def create_charts(
        self, df, param, site, x_param, y_param, sector_param, yaxis_range=None
    ):
        sectors = sorted(df[sector_param].apply(self.determine_sector).unique())
        # sorted_sectors = sorted(df[sector_param].unique())
        # color_mapping = {
        #     cell: color
        #     for cell, color in zip(
        #         sorted_sectors,
        #         self.get_colors(len(sorted_sectors)),
        #     )
        # }
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

    # TAG: - Create Charts Line with Datums
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
                        # scale=alt.Scale(domain=yaxis_range),
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
                    .mark_rule(color="red", strokeDash=[10, 5], size=3, opacity=0.1)
                    .encode(y=alt.Y(y2_avg, type="quantitative", title="with Baseline"))
                )
                sector_chart = alt.layer(y2_avg_line, sector_chart)

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

    # TAG: - Create Charts Stacked Area
    def create_charts_area(
        self, df, param, site, x_param, y_param, sector_param, yaxis_range=None
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

            # Determine y-axis range
            if yaxis_range:
                y_scale = alt.Scale(domain=yaxis_range)
            else:
                y_scale = alt.Scale()

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

    # TAG: - Create Charts based on Frequency
    # APPLY
    def create_charts_neid(
        self, df, param, site, x_param, y_param, neid, yaxis_range=None
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

        chart = (
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
            .properties(
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
                # strokeColor="#9A9A9A",
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

    # TAG: - Create Charts for VSWR
    def create_charts_vswr(self, df, x1_param, x2_param, y_param, nename):
        # Define color mapping
        color_mapping = {
            cell: color
            for cell, color in zip(
                df[x2_param].unique(),
                self.get_colors(len(df[x2_param].unique())),
            )
        }

        # Create baseline rule
        baseline_value = 1.3
        baseline = (
            alt.Chart(pd.DataFrame({"baseline": [baseline_value]}))
            .mark_rule(color="red", strokeDash=[8, 4], strokeWidth=5)
            .encode(y="baseline:Q")
        )

        # Create main chart
        bars = (
            alt.Chart(df)
            .mark_bar(size=10)  # Adjust bar width
            .encode(
                x=alt.X(
                    x1_param,
                    type="ordinal",
                    axis=alt.Axis(title="", labels=False),  # Hide x-axis labels
                    scale=alt.Scale(type="point", padding=0.1),
                ),  # Adjust padding between bars
                y=alt.Y(
                    y_param,
                    type="quantitative",
                    axis=alt.Axis(title=y_param),
                    stack="zero",
                ),
                color=alt.Color(
                    x2_param,
                    scale=alt.Scale(
                        domain=list(color_mapping.keys()),
                        range=list(color_mapping.values()),
                    ),
                ),
                tooltip=[x1_param, x2_param, y_param],
            )
        )

        # Create highlight chart for values above the baseline
        highlight = bars.mark_bar(color="#e45755").transform_filter(
            alt.datum[y_param] > baseline_value
        )

        # Combine charts and add facet for NE_NAME
        chart = (
            (bars + highlight + baseline)
            .facet(
                column=alt.Facet(nename, type="nominal", title=""),
                spacing=0,  # Remove spacing between facets
            )
            # .properties(
            #     title="",
            # )
            .resolve_scale(x="shared")  # Share x-axis scale across facets
            .configure(background="#F5F5F5")
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
            .configure_view(strokeWidth=0)
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
            col1, _ = st.columns([1.5, 1])
            con1 = col1.container()
            with con1:
                st.altair_chart(chart, use_container_width=True)


class TempDataManager:
    def __init__(self):
        self.temp_file = None

    def save_data(self, df, filename):
        if self.temp_file is None:
            self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        df.to_csv(self.temp_file.name, index=False)
        st.session_state[filename] = self.temp_file.name

    def load_data(self, filename):
        if filename in st.session_state:
            return pd.read_csv(st.session_state[filename])
        return None

    def cleanup(self):
        if self.temp_file:
            try:
                os.remove(self.temp_file.name)
            except OSError:
                pass


class GeoApp:
    def __init__(self, geocell_file, driveless_file):
        self.geocell_data = self.load_data(geocell_file)
        self.driveless_data = self.load_data(driveless_file)
        self.unique_cis = self.get_unique_cis()
        self.map_center = self.calculate_map_center()
        self.tile_options = self.define_tile_options()
        self.map = None

    @staticmethod
    def load_data(file_path):
        """Load data from a CSV file."""
        return pd.read_csv(file_path)

    def get_unique_cis(self):
        """Extract and sort unique Cell IDs."""
        return sorted(self.geocell_data["cellId"].unique())

    def calculate_map_center(self):
        """Calculate the geographic center of the map."""
        return [
            self.geocell_data["Latitude"].mean(),
            self.geocell_data["Longitude"].mean(),
        ]

    @staticmethod
    def define_tile_options():
        """Define map tile options."""
        return {
            "Openstreetmap": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            "Google Hybrid": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        }

    def initialize_map(self):
        """Initialize the map with a selected tile provider."""
        tile_provider = st.selectbox(
            "Select Map", list(self.tile_options.keys()), index=1
        )
        self.map = folium.Map(
            location=self.map_center,
            zoom_start=15,
            tiles=self.tile_options[tile_provider],
            attr=tile_provider,
        )

    def get_ci_color(self, ci):
        """Get color based on Cell ID index."""
        ci_index = self.unique_cis.index(ci)
        return ColorPalette.get_color(ci_index)

    def get_rsrp_color(self, rsrp):
        """
        Determines the color representation based on the RSRP value.

        :param rsrp: The RSRP value to evaluate.
        :return: A string representing the color associated with the RSRP range.
        """
        ranges = [(-85, "blue"), (-95, "green"), (-105, "yellow"), (-115, "orange")]
        for limit, color in ranges:
            if rsrp >= limit:
                return color
        return "red"

    def create_sector_polygon(self, lat, lon, azimuth, beamwidth, radius):
        from math import asin, atan2, cos, degrees, radians, sin

        lat_rad = radians(lat)
        lon_rad = radians(lon)
        azimuth_rad = radians(azimuth)
        beamwidth_rad = radians(beamwidth)
        num_points = 50
        angle_step = beamwidth_rad / (num_points - 1)
        start_angle = azimuth_rad - beamwidth_rad / 2
        points = []

        for i in range(num_points):
            angle = start_angle + i * angle_step
            lat_new = asin(
                sin(lat_rad) * cos(radius / 6371)
                + cos(lat_rad) * sin(radius / 6371) * cos(angle)
            )
            lon_new = lon_rad + atan2(
                sin(angle) * sin(radius / 6371) * cos(lat_rad),
                cos(radius / 6371) - sin(lat_rad) * sin(lat_new),
            )
            points.append([degrees(lat_new), degrees(lon_new)])

        points.append([lat, lon])  # Return to the starting point for a complete polygon
        return points

    def add_geocell_layer(self):
        geocell_layer = folium.FeatureGroup(name="Geocell Sites")

        for _, row in self.geocell_data.iterrows():
            color = self.get_ci_color(row["cellId"])
            self.add_circle_marker(row, color, geocell_layer)
            self.add_custom_marker(row, geocell_layer)
            self.add_sector_polygon(row, color, geocell_layer)

        geocell_layer.add_to(self.map)

    def create_popup_content(self, row):
        return f"""
        <div style="font-family: Arial; font-size: 12px;">
            <b>Site:</b> {row['Site_ID']}<br>
            <b>Cell:</b> {row['Cell_Name']}<br>
            <b>CI:</b> {row['cellId']}
        </div>
        """

    def add_circle_marker(self, row, color, layer):
        popup_content = self.create_popup_content(row)
        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=6,
            popup=folium.Popup(popup_content, max_width=250),
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=1.0,
        ).add_to(layer)

    def add_custom_marker(self, row, layer):
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=row["Site_ID"],
            icon=folium.DivIcon(
                html=f'<div style="font-size: 24pt; color: white">{row["Site_ID"]}</div>'
            ),
        ).add_to(layer)

    def add_sector_polygon(self, row, color, layer):
        sector_polygon = self.create_sector_polygon(
            row["Latitude"],
            row["Longitude"],
            row["Dir"],
            row["Ant_BW"],
            row["Ant_Size"],
        )
        folium.Polygon(
            locations=sector_polygon,
            color="black",
            fill=True,
            fill_color=color,
            fill_opacity=1.0,
        ).add_to(layer)

    def add_driveless_layer(self, color_by_ci=True):
        driveless_layer = folium.FeatureGroup(name="Driveless Data")

        for _, row in self.driveless_data.iterrows():
            if color_by_ci:
                color = self.get_ci_color(row["ci"])
            else:
                color = self.get_rsrp_color(row["rsrp_mean"])
            folium.CircleMarker(
                location=[row["lat_grid"], row["long_grid"]],
                radius=4,
                popup=f"CI: {row['ci']} RSRP: {row['rsrp_mean']} dBm",
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=1,
            ).add_to(driveless_layer)

        driveless_layer.add_to(self.map)

    def add_spider_graph(self):
        for _, row in self.driveless_data.iterrows():
            geocell_match = self.geocell_data[
                (self.geocell_data["cellId"] == row["ci"])
                & (self.geocell_data["eNBId"] == row["enodebid"])
            ]
            if not geocell_match.empty:
                geocell_lat = geocell_match["Latitude"].values[0]
                geocell_lon = geocell_match["Longitude"].values[0]
                color = self.get_ci_color(row["ci"])
                folium.PolyLine(
                    locations=[
                        [row["lat_grid"], row["long_grid"]],
                        [geocell_lat, geocell_lon],
                    ],
                    color=color,
                    weight=1,
                    opacity=0.5,
                ).add_to(self.map)

    def display_map(self):
        folium.LayerControl().add_to(self.map)
        self.add_legend()
        st.components.v1.html(self.map._repr_html_(), height=800)

    def display_legend(self):
        st.subheader("Legend")
        for index, ci in enumerate(self.unique_cis):
            color = ColorPalette.get_color(index)
            st.markdown(
                f'<span style="color:{color};">{ci}: {color}</span>',
                unsafe_allow_html=True,
            )

    def add_legend(self):
        # Combined Legend
        combined_legend_template = """
        {% macro html(this, kwargs) %}
        <div id='maplegend' class='maplegend'
            style='position: absolute; z-index:9999; background-color: rgba(255, 255, 255, 0.5);
            border-radius: 6px; padding: 10px; font-size: 12px; right: 12px; top: 70px;'>
        <div class='legend-scale'>
          <ul class='legend-labels'>
            <li><strong>RSRP</strong></li>
            <li><span style='background: blue; opacity: 0.75;'></span>RSRP >= -85</li>
            <li><span style='background: green; opacity: 0.75;'></span>-95 <= RSRP < -85</li>
            <li><span style='background: yellow; opacity: 0.75;'></span>-105 <= RSRP < -95</li>
            <li><span style='background: orange; opacity: 0.75;'></span>-115 <= RSRP < -105</li>
            <li><span style='background: red; opacity: 0.75;'></span>RSRP < -115</li>
          </ul>
          <ul class='legend-labels'>
            <li><strong>CELL IDENTITY</strong></li>
        """
        for index, ci in enumerate(self.unique_cis):
            color = ColorPalette.get_color(index)
            combined_legend_template += f"<li><span style='background: {color}; opacity: 0.75;'></span>CI {ci}</li>"

        combined_legend_template += """
          </ul>
        </div>
        </div>
        <style type='text/css'>
          .maplegend .legend-scale ul {margin: 0; padding: 0; color: #0f0f0f;}
          .maplegend .legend-scale ul li {list-style: none; line-height: 18px; margin-bottom: 1.5px;}
          .maplegend ul.legend-labels li span {float: left; height: 16px; width: 16px; margin-right: 4.5px;}
        </style>
        {% endmacro %}
        """
        combined_macro = MacroElement()
        combined_macro._template = Template(combined_legend_template)
        self.map.get_root().add_child(combined_macro)

    def run(self):
        col1, col2, _, _ = st.columns([1, 1, 2, 2])

        with col1:
            self.initialize_map()

        with col2:
            category = st.selectbox(
                "Category",
                ["CellId", "RSRP", "CellId with Spidergraph", "RSRP with Spidergraph"],
            )

        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            self.add_geocell_layer()
            color_by_ci = "CellId" in category
            self.add_driveless_layer(color_by_ci=color_by_ci)

            if "Spidergraph" in category:
                self.add_spider_graph()

            self.display_map()

        with col2:
            st.markdown("---")

        with col3:
            st.markdown("---")


# if __name__ == "__main__":
#     st.set_page_config(layout="wide")
#     script_dir = os.path.dirname(__file__)
#     sitelist_mcom = os.path.join(script_dir, "test_geocell.csv")
#     sitelist_driveless = os.path.join(script_dir, "test_driveless.csv")

#     app = GeoApp(sitelist_mcom, sitelist_driveless)
#     app.run()


class App:
    def __init__(self):
        self.config = Config().load()
        self.database_session = DatabaseSession(self.config)
        self.query_manager = None
        self.dataframe_manager = DataFrameManager()
        self.streamlit_interface = StreamlitInterface()
        self.chart_generator = ChartGenerator()
        self.temp_data_manager = TempDataManager()

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
                # combined_ltemdt_data = []
                combined_ltetastate_data = []
                combined_ltedaily_data = []

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
                            row["KABUPATEN"],
                            row["MC_class"],
                            row["LTE"],
                            # row["KABUPATEN"],
                            # row["LTE"],
                        )
                        target_data["EutranCell"] = row["Cell_Name"]
                        combined_target_data.append(target_data)

                        # Get and append ltemdt data
                        # ltemdt_data = self.query_manager.get_ltemdt_data(
                        #     row["eNBId"], row["cellId"]
                        # )
                        # ltemdt_data = self.query_manager.get_ltemdt_data(row["eNBId"])
                        # ltemdt_data["EutranCell"] = row["Cell_Name"]
                        # combined_ltemdt_data.append(ltemdt_data)

                        # Get and append ltetastate data
                        ltetastate_data = self.query_manager.get_ltetastate_data(
                            row["eNBId"], row["cellId"]
                        )
                        ltetastate_data["EutranCell"] = row["Cell_Name"]
                        combined_ltetastate_data.append(ltetastate_data)

                    # Fetch LTE daily data for each site
                    ltedaily_data = self.query_manager.get_ltedaily_data(
                        siteid, selected_neids, start_date, end_date
                    )
                    combined_ltedaily_data.append(ltedaily_data)
                    self.dataframe_manager.add_dataframe(
                        f"ltedaily_data_{siteid}", ltedaily_data
                    )
                    # self.dataframe_manager.display_dataframe(
                    #     f"ltedaily_data_{siteid}", f"LTE Daily Data for Site: {siteid}"
                    # )

                # Combine target data and display
                if combined_target_data:
                    combined_target_df = pd.concat(
                        combined_target_data, ignore_index=True
                    )
                    self.dataframe_manager.add_dataframe(
                        "combined_target_data", combined_target_df
                    )
                    # self.dataframe_manager.display_dataframe(
                    #     "combined_target_data", "Combined Target Data"
                    # )

                # TAG: - Combine LTE MDT Data
                # if combined_ltemdt_data:
                #     combined_ltemdt_df = pd.concat(
                #         combined_ltemdt_data, ignore_index=True
                #     )
                #     self.dataframe_manager.add_dataframe(
                #         "combined_ltemdt_data", combined_ltemdt_df
                #     )
                #     self.dataframe_manager.display_dataframe(
                #         "combined_ltemdt_data", "Combined LTE MDT Data"
                #     )
                #     self.temp_data_manager.save_data(
                #         combined_ltemdt_df, "ltemdt_data_saved"
                #     )

                # Combine ltetastate data and display
                if combined_ltetastate_data:
                    combined_ltetastate_df = pd.concat(
                        combined_ltetastate_data, ignore_index=True
                    )
                    self.dataframe_manager.add_dataframe(
                        "combined_ltetastate_data", combined_ltetastate_df
                    )
                    # self.dataframe_manager.display_dataframe(
                    #     "combined_ltetastate_data", "Combined LTE TA State Data"
                    # )

                # Combine ltedaily data and display
                if combined_ltedaily_data:
                    combined_ltedaily_df = pd.concat(
                        combined_ltedaily_data, ignore_index=True
                    )
                    self.dataframe_manager.add_dataframe(
                        "combined_ltedaily_data", combined_ltedaily_df
                    )
                    # self.dataframe_manager.display_dataframe(
                    #     "combined_ltedaily_data", "LTE Daily Data"
                    # )

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
                    # self.dataframe_manager.display_dataframe(
                    #     "combined_target_ltedaily_data",
                    #     "LTE Daily Data & Datum",
                    # )

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
                        # yaxis_range=yaxis_ranges[4],
                        yaxis_range=None,
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
                    )

                payload_data = self.query_manager.get_ltedaily_payload(
                    selected_sites, start_date, end_date
                )
                self.dataframe_manager.add_dataframe("payload_data", payload_data)

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
                        )

                st.markdown(
                    *styling(
                        f"📶 CQI Comparison across Frequencies for Site {siteid}",
                        font_size=24,
                        text_align="left",
                        tag="h6",
                    )
                )

                self.chart_generator.create_charts(
                    df=payload_data,
                    param="CQI Overlay",
                    site="Combined Sites",
                    x_param="DATE_ID",
                    y_param="CQI Bh",
                    sector_param="EutranCell",
                    yaxis_range=None,
                )

                ltehourly_data = self.query_manager.get_ltehourly_data(
                    selected_sites, end_date
                )

                ltehourly_data["datetime"] = pd.to_datetime(
                    ltehourly_data["DATE_ID"].astype(str)
                    + " "
                    + ltehourly_data["hour_id"].astype(str).str.zfill(2),
                    format="%Y-%m-%d %H",
                )

                self.dataframe_manager.add_dataframe("ltehourly_data", ltehourly_data)
                # self.dataframe_manager.display_dataframe(
                #     "ltehourly_data", "LTE Hourly Data"
                # )

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
                vswr_data = self.query_manager.get_vswr_data(selected_sites, end_date)
                self.dataframe_manager.add_dataframe("vswr_data", vswr_data)
                # self.dataframe_manager.display_dataframe("vswr_data", "VSWR Data")
                # TAG: - VSWR

                st.markdown(
                    *styling(
                        f"📶 VSWR Analysis for Site {siteid} (dBm)",
                        font_size=24,
                        text_align="left",
                        tag="h6",
                    )
                )
                self.chart_generator.create_charts_vswr(
                    df=vswr_data,
                    x1_param="DATE_ID",
                    x2_param="RRU",
                    y_param="VSWR",
                    nename="RRU",
                )
                # Close session

                ltemdtdata = self.query_manager.get_ltemdt_data(selected_sites)
                self.dataframe_manager.add_dataframe("ltemdtdata", ltemdtdata)
                self.dataframe_manager.display_dataframe("ltemdtdata", "LTE MDT Data")
                self.temp_data_manager.cleanup()
                session.close()
            else:
                st.warning("Please select site IDs and date range to load data.")


if __name__ == "__main__":
    app = App()
    app.run()
