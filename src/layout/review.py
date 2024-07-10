import os

import altair as alt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit_antd_components as sac
import toml
from colors import ColorPalette
from geoapp import GeoApp
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
# TODO: - Geo Plotting - DONE


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

    def get_mcom_neid(self):
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

    def get_ltehourly_data(self, selected_sites, end_date):
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

    # TAG: - create_charts_vswr
    # def create_charts_vswr(self, df, x1_param, x2_param, y_param, nename):
    #     # Define color mapping
    #     color_mapping = {
    #         cell: color
    #         for cell, color in zip(
    #             df[x2_param].unique(),
    #             self.get_colors(len(df[x2_param].unique())),
    #         )
    #     }

    #     # Create baseline rule
    #     baseline_value = 1.3
    #     baseline = (
    #         alt.Chart(pd.DataFrame({"baseline": [baseline_value]}))
    #         .mark_rule(color="#F74B00", strokeDash=[8, 4], strokeWidth=4)
    #         .encode(y="baseline:Q")
    #     )

    #     # Create main chart
    #     bars = (
    #         alt.Chart(df)
    #         .mark_bar(size=10)  # Increased bar width
    #         .encode(
    #             x=alt.X(
    #                 x1_param,
    #                 type="ordinal",
    #                 axis=alt.Axis(title="", labels=False),  # Show x-axis labels
    #                 sort=alt.SortField(
    #                     field=x1_param, order="ascending"
    #                 ),  # Sort bars from left to right
    #                 scale=alt.Scale(
    #                     type="point", padding=0.1
    #                 ),  # Adjust padding between bars
    #             ),
    #             y=alt.Y(
    #                 y_param,
    #                 type="quantitative",
    #                 axis=alt.Axis(title=y_param),
    #                 stack=None,  # Remove stacking to create unstacked bars
    #             ),
    #             color=alt.Color(
    #                 x2_param,
    #                 scale=alt.Scale(
    #                     domain=list(color_mapping.keys()),
    #                     range=list(color_mapping.values()),
    #                 ),
    #                 legend=alt.Legend(title=x2_param),
    #             ),
    #             tooltip=[x1_param, x2_param, y_param],
    #         )
    #         .properties(width=300, height=150)
    #     )

    #     # Create highlight chart for values above the baseline
    #     highlight = bars.mark_bar(color="#e45755").transform_filter(
    #         alt.datum[y_param] > baseline_value
    #     )

    #     # Combine charts and add facet for NE_NAME
    #     base_chart = bars + highlight + baseline

    #     # Configure facet, scale, and view
    #     chart_with_facet_and_scale = (
    #         base_chart.facet(
    #             column=alt.Facet(nename, type="nominal", title=""),
    #             spacing=0,  # Remove spacing between facets
    #         )
    #         .resolve_scale(
    #             x="independent"
    #         )  # Use independent x-axis scale for each facet
    #         .configure_view(strokeWidth=0)
    #     )

    #     # Configure chart appearance
    #     configured_chart = (
    #         chart_with_facet_and_scale.configure(background="#F5F5F5")
    #         .configure_title(
    #             fontSize=18, anchor="middle", font="Vodafone", color="#717577"
    #         )
    #         .configure_legend(
    #             orient="bottom",
    #             titleFontSize=16,
    #             labelFontSize=14,
    #             labelFont="Vodafone",
    #             titleColor="#5F6264",
    #             padding=10,
    #             titlePadding=10,
    #             cornerRadius=10,
    #             columns=6,
    #             titleAnchor="start",
    #             direction="vertical",
    #             gradientLength=400,
    #             labelLimit=0,
    #             symbolSize=30,
    #             symbolType="square",
    #         )
    #     )

    #     container = st.container()
    #     with container:
    #         st.altair_chart(configured_chart, use_container_width=True)
    def create_charts_vswr(self, df, x1_param, x2_param, y_param, nename):
        unique_values = df[x2_param].unique()
        colors = self.get_colors(len(unique_values))
        color_mapping = {cell: color for cell, color in zip(unique_values, colors)}

        fig = go.Figure()

        for value in unique_values:
            filtered_df = df[df[x2_param] == value]
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
            xaxis_title=x1_param,
            yaxis_title=y_param,
            plot_bgcolor="#F5F5F5",
            paper_bgcolor="#F5F5F5",
            font=dict(family="Vodafone", size=18, color="#717577"),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
                bgcolor="#F5F5F5",
                bordercolor="#FFFFFF",
                borderwidth=2,
                itemclick="toggleothers",
                itemdoubleclick="toggle",
            ),
            margin=dict(l=20, r=20, t=40, b=20),
        )

        container = st.container()
        with container:
            st.plotly_chart(fig, use_container_width=True)


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
                for siteid in selected_sites:
                    folder = os.path.join(project_root, "sites", siteid)
                    # tier_path = os.path.join(folder, "tier.csv")
                    # tier_data = pd.read_csv(tier_path)
                    # isd_path = os.path.join(folder, "isd.csv")
                    # isd_data = pd.read_csv(isd_path)
                    # st.write(tier_data)
                    # st.write(isd_data)

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

                    # TAG: NAURA and ALARM
                    def display_image_or_message(
                        column, folder_path, image_name, message_prefix
                    ):
                        image_path = os.path.join(folder_path, image_name)
                        if os.path.exists(image_path):
                            column.image(
                                image_path, caption=None, use_column_width=True
                            )
                        else:
                            column.write(f"{message_prefix}: {image_path}")

                    # Define columns first
                    col1, col2 = st.columns([2, 1])

                    # Use the defined function to display styled markdowns
                    styling_args = {"font_size": 24, "text_align": "left", "tag": "h6"}
                    col1.markdown(*styling(f"📝 Naura Site {siteid}", **styling_args))
                    col2.markdown(*styling(f"⚠️ Alarm Site {siteid}", **styling_args))

                    # Create containers with borders
                    con1 = col1.container(border=True)
                    con2 = col2.container(border=True)

                    # Display images or messages using the helper function
                    if os.path.exists(folder):
                        display_image_or_message(
                            con1, folder, "naura.jpg", "Please upload the image"
                        )
                        display_image_or_message(
                            con2, folder, "alarm.jpg", "Please upload the image"
                        )
                    else:
                        st.write(f"Path does not exist: {folder}")

                    mcom_data = self.query_manager.get_mcom_data(siteid)
                    self.dataframe_manager.add_dataframe(
                        f"mcom_data_{siteid}", mcom_data
                    )

                    for _, row in mcom_data.iterrows():
                        target_data = self.query_manager.get_target_data(
                            row["KABUPATEN"],
                            row["MC_class"],
                            row["LTE"],
                            # row["KABUPATEN"],
                            # row["LTE"],
                        )
                        target_data["EutranCell"] = row["Cell_Name"]
                        combined_target_data.append(target_data)

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

                # Combine target data and display
                if combined_target_data:
                    combined_target_df = pd.concat(
                        combined_target_data, ignore_index=True
                    )
                    self.dataframe_manager.add_dataframe(
                        "combined_target_data", combined_target_df
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
                            f"📶 Service Availability for Site {siteid}", **styling_args
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
                            f"📶 RRC Success Rate for Site {siteid}", **styling_args
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
                            **styling_args,
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
                            **styling_args,
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
                            **styling_args,
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
                            **styling_args,
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
                            **styling_args,
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
                            **styling_args,
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
                            **styling_args,
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
                            **styling_args,
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
                            **styling_args,
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
                            **styling_args,
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

                self.dataframe_manager.add_dataframe("ltehourly_data", ltehourly_data)

                vswr_data = self.query_manager.get_vswr_data(selected_sites, end_date)
                self.dataframe_manager.add_dataframe("vswr_data", vswr_data)

                # MARK: - GeoApp MDT Data
                st.session_state.mcom_data = mcom_data
                st.session_state.combined_target_data = combined_target_data

                # MARK: - GeoApp MDT Data
                ltemdtdata = self.query_manager.get_ltemdt_data(selected_sites)
                self.dataframe_manager.add_dataframe("ltemdtdata", ltemdtdata)

                col1, col2 = st.columns([1, 1])
                with col1:
                    st.markdown(
                        *styling(
                            f"📶 Payload Distribution by Frequency for Site  {siteid} (Gpbs)",
                            **styling_args,
                        )
                    )

                with col2:
                    st.markdown(
                        *styling(
                            f"📶 Total Site Payload Overview for Site {siteid} (Gpbs)",
                            **styling_args,
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
                        f"📶 CQI Comparison across Frequencies for Site {siteid}",
                        **styling_args,
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

                # TAG: - PRB & Active User
                st.markdown(
                    *styling(
                        f"📶 PRB Utilization Sectoral for Site {siteid}",
                        **styling_args,
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
                        **styling_args,
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
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(
                        *styling(
                            f"📶 VSWR Analysis for Site {siteid} (dBm)",
                            **styling_args,
                        )
                    )

                with col2:
                    st.markdown(
                        *styling(
                            f"📶 RET After {siteid}",
                            **styling_args,
                        )
                    )

                col1, col2 = st.columns([2, 1])
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
                            width: 80%;
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
                        if os.path.exists(folder):
                            ret = os.path.join(folder, "ret.jpg")
                            if os.path.exists(ret):
                                st.image(ret, caption=None)
                            else:
                                st.write(f"Please upload the image: {ret}")
                        else:
                            st.write(f"Path does not exist: {folder}")

                st.session_state.ltemdtdata = ltemdtdata
                st.markdown(
                    *styling(
                        f"☢️ MDT and TA Summary for Site {siteid}",
                        **styling_args,
                    )
                )
                self.geodata = GeoApp(mcom_data, ltemdtdata)
                self.geodata.run_geo_app()

                # MARK: - MCOM ISD Data
                session.close()
        else:
            # If not running the query, reload the data from session state
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
