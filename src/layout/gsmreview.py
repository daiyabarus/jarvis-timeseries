import os

# import numpy as np
import pandas as pd

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# import streamlit_antd_components as sac
import toml

from colors import ColorPalette
from omegaconf import DictConfig, OmegaConf

# from plotly.subplots import make_subplots
# from review.geoapp import GeoApp
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from streamlit_extras.mandatory_date_range import date_range_picker

from streamlit_extras.stylable_container import stylable_container

# from layout.styles import styling

from styles import styling


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

    # def site_selection(self, sitelist):
    #     column0_data = [row[0] for row in sitelist]
    #     return st.multiselect("SITEID", column0_data)

    def neid_selection(self, sitelist):
        column1_data = {row[1] for row in sitelist}
        return st.multiselect("NEID", column1_data)

    def select_date_range(self):
        if "date_range" not in st.session_state:
            st.session_state["date_range"] = (
                pd.Timestamp.today() - pd.DateOffset(months=3),
                pd.Timestamp.today(),
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
        st.session_state["xrule_date"] = xrule_date
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

    def get_mcom_siteid(self, siteid):
        query = text(
            """
        SELECT "Site ID", "NE_ID", "Cell", "KABUPATEN"
        FROM gsmmcom
        WHERE "Site ID" LIKE :siteid
        """
        )
        return self.fetch_data(query, {"siteid": siteid})

    def get_mcom_neid(self, neid):
        query = text(
            """
        SELECT "Site ID", "NE_ID", "Cell", "Cell_Type", "KABUPATEN"
        FROM gsmmcom
        WHERE "NE_ID" LIKE :neid
        """
        )
        return self.fetch_data(query, {"neid": neid})

    def get_gsmdaily(self, cells, start_date, end_date):
        like_conditions = " OR ".join(
            [f'"MOID" LIKE :cell_{i}' for i in range(len(cells))]
        )
        query = text(
            f"""
            SELECT *
            FROM gsmdaily
            WHERE ({like_conditions})
            AND "DATE_ID" BETWEEN :start_date AND :end_date
            """
        )
        params = {f"cell_{i}": f"%{cell}%" for i, cell in enumerate(cells)}
        params.update({"start_date": start_date, "end_date": end_date})

        return self.fetch_data(query, params=params)

    def get_target_data(self, city, band):
        query = text(
            """
            SELECT *
            FROM gsmtarget
            WHERE "City" = :city AND "Band" = :band
            """
        )
        return self.fetch_data(query, {"city": city, "band": band})

    def get_gsm_paytraf(self, siteid, start_date, end_date):
        like_conditions = " OR ".join(
            [f'"NE_ID" LIKE :neid_{i}' for i in range(len(siteid))]
        )
        query = text(
            f"""
            SELECT
            "DATE_ID",
            "NE_ID",
            "MOID",
            "TCH_Traffic",
            "DATA_PAYLOAD"
            FROM gsmdaily
            WHERE ({like_conditions})
            AND "DATE_ID" BETWEEN :start_date AND :end_date
            """
        )
        params = {f"neid_{i}": f"%{cell}%" for i, cell in enumerate(siteid)}
        params.update({"start_date": start_date, "end_date": end_date})

        return self.fetch_data(query, params=params)


class ChartGenerator:
    def __init__(self):
        self.color_palette = ColorPalette()

    def get_colors(self, num_colors):
        return [self.color_palette.get_color(i) for i in range(num_colors)]

    def determine_sector(self, cell: str) -> int:
        sector_mapping = {
            "E": 1,
            "F": 2,
            "G": 3,
            "A": 1,
            "B": 2,
            "C": 3,
            "S": 1,
            "T": 2,
            "U": 3,
            "P": 1,
            "Q": 2,
            "R": 3,
        }
        last_char = cell[-1].upper()
        return sector_mapping.get(last_char, 0)

    def create_charts_for_daily(
        self, df, cell_name, x_param, y_param, xrule=False, yline=None
    ):
        df = df.sort_values(by=x_param)
        df[y_param] = df[y_param].astype(float)
        df["sector"] = df[cell_name].apply(self.determine_sector)

        color_mapping = {
            cell: color
            for cell, color in zip(
                sorted(df[cell_name].unique()),
                self.get_colors(len(df[cell_name].unique())),
            )
        }

        sector_count = df["sector"].nunique()
        cols = max(min(sector_count, 3), 1)
        columns = st.columns(cols)

        for idx, sector in enumerate(sorted(df["sector"].unique())):
            sector_data = df[df["sector"] == sector]
            y_min = sector_data[sector_data[y_param] > 0][y_param].min()
            y_max_value = sector_data[y_param].max()
            y_max = (
                100
                if 95 < y_max_value <= 100
                else y_max_value if y_max_value > 100 else y_max_value
            )

            with columns[idx % cols]:
                with stylable_container(
                    key=f"container_with_border_{sector}",
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

                        fig = go.Figure()

                        for cell in sector_data[cell_name].unique():
                            cell_data = sector_data[sector_data[cell_name] == cell]
                            color = color_mapping[cell]

                            fig.add_trace(
                                go.Scatter(
                                    x=cell_data[x_param],
                                    y=cell_data[y_param],
                                    mode="lines",
                                    name=cell,
                                    line=dict(color=color, width=3),
                                    hovertemplate=(
                                        f"<b>{cell}</b><br>"
                                        f"<b>{y_param}:</b> %{{y}}<br>"
                                        "<extra></extra>"
                                    ),
                                )
                            )

                        if yline:
                            yline_value = sector_data[yline].mean()
                            fig.add_hline(
                                y=yline_value,
                                line_dash="dashdot",
                                line_color="#F70000",
                                line_width=2,
                            )
                            if yline_value > y_max:
                                y_max = yline_value
                            elif yline_value < y_min:
                                y_min = yline_value

                        if xrule:
                            fig.add_vline(
                                x=st.session_state["xrule"],
                                line_width=2,
                                line_dash="dash",
                                line_color="#808080",
                            )

                        adjusted_y_min = y_min if y_min > 0 else 0.01
                        yaxis_range = [adjusted_y_min, y_max]

                        fig.update_layout(
                            margin=dict(t=20, l=20, r=20, b=20),
                            title_text=f"SECTOR {sector}",
                            title_x=0.5,
                            template="plotly_white",
                            hoverlabel=dict(font_size=14, font_family="Vodafone"),
                            hovermode="x unified",
                            legend=dict(
                                orientation="h",
                                yanchor="top",
                                y=-0.4,
                                xanchor="center",
                                x=0.5,
                                itemclick="toggleothers",
                                itemdoubleclick="toggle",
                                itemsizing="constant",
                                font=dict(size=14),
                            ),
                            paper_bgcolor="#F5F5F5",
                            plot_bgcolor="#F5F5F5",
                            width=600,
                            height=350,
                            showlegend=True,
                            yaxis=dict(
                                range=yaxis_range,
                                tickfont=dict(
                                    size=14,
                                    color="#000000",
                                ),
                            ),
                            xaxis=dict(
                                tickfont=dict(
                                    size=14,
                                    color="#000000",
                                ),
                            ),
                        )

                        st.plotly_chart(fig, use_container_width=True)

    def create_charts_for_stacked_area(
        self, df, cell_name, x_param, y_param, xrule=False, yline=None
    ):
        df = df.sort_values(by=x_param)
        df[y_param] = df[y_param].astype(float)
        df["sector"] = df[cell_name].apply(self.determine_sector)
        color_mapping = {
            cell: color
            for cell, color in zip(
                df[cell_name].unique(),
                self.get_colors(len(df[cell_name].unique())),
            )
        }

        sector_count = df["sector"].nunique()
        cols = max(min(sector_count, 3), 1)
        columns = st.columns(cols)

        for idx, sector in enumerate(sorted(df["sector"].unique())):
            sector_data = df[df["sector"] == sector]

            with columns[idx % cols]:
                with stylable_container(
                    key=f"container_with_border_{sector}",
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

                        fig = px.area(
                            sector_data,
                            x=x_param,
                            y=y_param,
                            color=cell_name,
                            color_discrete_map=color_mapping,
                            hover_data={
                                cell_name: True,
                                y_param: True,
                            },
                        )
                        fig.update_traces(
                            hovertemplate=f"<b>{cell_name}:</b> %{{customdata[0]}}<br><b>{y_param}:</b> %{{y}}<extra></extra>"
                        )
                        if yline:
                            yline_value = sector_data[yline].mean()
                            fig.add_hline(
                                y=yline_value,
                                line_dash="dot",
                                line_color="#F70000",
                                line_width=2,
                            )

                        if xrule:
                            fig.add_vline(
                                x=st.session_state["xrule"],
                                line_width=2,
                                line_dash="dash",
                                line_color="#808080",
                            )

                        fig.update_layout(
                            margin=dict(t=20, l=20, r=20, b=20),
                            title_text=f"SECTOR {sector}",
                            title_x=0.5,
                            template="plotly_white",
                            hoverlabel=dict(font_size=16, font_family="Vodafone"),
                            hovermode="x unified",
                            legend=dict(
                                orientation="h",
                                yanchor="top",
                                y=-0.5,
                                xanchor="center",
                                x=0.5,
                                itemclick="toggleothers",
                                itemdoubleclick="toggle",
                                itemsizing="constant",
                                font=dict(size=16),
                                title=None,
                            ),
                            yaxis=dict(
                                tickfont=dict(
                                    size=14,  # Updated size for y-axis tick labels
                                    color="#000000",
                                ),
                            ),
                            xaxis=dict(
                                tickfont=dict(
                                    size=14,  # Updated size for x-axis tick labels
                                    color="#000000",
                                ),
                            ),
                            paper_bgcolor="#F5F5F5",
                            plot_bgcolor="#F5F5F5",
                            width=600,
                            height=350,
                            showlegend=True,
                        )

                        st.plotly_chart(fig, use_container_width=True)

    def create_charts_for_stacked_area_neid(
        self, df, neid, x_param, y_param, xrule=False
    ):
        df[y_param] = df[y_param].astype(float)
        df_agg = df.groupby([x_param, neid], as_index=False)[y_param].sum()

        df_agg = df_agg.sort_values(by=x_param)

        color_mapping = {
            cell: color
            for cell, color in zip(
                df_agg[neid].unique(),
                self.get_colors(len(df_agg[neid].unique())),
            )
        }

        container = st.container()
        with container:
            fig = px.area(
                df_agg,
                x=x_param,
                y=y_param,
                color=neid,
                color_discrete_map=color_mapping,
                hover_data={neid: True, y_param: True},
            )

            fig.update_traces(
                hovertemplate=f"<b>{neid}:</b> %{{customdata[0]}}<br><b>{y_param}:</b> %{{y}}<extra></extra>"
            )

            fig.update_layout(
                xaxis_title=None,
                yaxis_title=None,
                margin=dict(t=20, l=20, r=20, b=20),
                template="plotly_white",
                hoverlabel=dict(font_size=16, font_family="Vodafone"),
                hovermode="x unified",
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.2,
                    xanchor="center",
                    x=0.5,
                    itemclick="toggleothers",
                    itemdoubleclick="toggle",
                    itemsizing="constant",
                    font=dict(size=16),
                    title=None,
                ),
                yaxis=dict(
                    tickfont=dict(
                        size=14,  # Updated size for y-axis tick labels
                        color="#000000",
                    ),
                ),
                xaxis=dict(
                    tickfont=dict(
                        size=14,  # Updated size for x-axis tick labels
                        color="#000000",
                    ),
                ),
                paper_bgcolor="#F5F5F5",
                plot_bgcolor="#F5F5F5",
                width=600,
                height=350,
                showlegend=True,
            )

            if xrule:
                fig.add_vline(
                    x=st.session_state["xrule"],
                    line_width=2,
                    line_dash="dash",
                    line_color="#808080",
                )

            with stylable_container(
                key=f"container_with_border_{neid}",
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

    def create_charts_for_blocking(
        self, df, cell_name, x_param, y_param, xrule=False, yline=None
    ):
        df = df.sort_values(by=x_param)
        df[y_param] = df[y_param].astype(float)
        df["sector"] = df[cell_name].apply(self.determine_sector)

        color_mapping = {
            cell: color
            for cell, color in zip(
                sorted(df[cell_name].unique()),
                self.get_colors(len(df[cell_name].unique())),
            )
        }

        sector_count = df["sector"].nunique()
        cols = max(min(sector_count, 3), 1)
        columns = st.columns(cols)

        for idx, sector in enumerate(sorted(df["sector"].unique())):
            sector_data = df[df["sector"] == sector]

            with columns[idx % cols]:
                with stylable_container(
                    key=f"container_with_border_{sector}",
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

                        fig = go.Figure()

                        for cell in sector_data[cell_name].unique():
                            cell_data = sector_data[sector_data[cell_name] == cell]
                            color = color_mapping[cell]

                            fig.add_trace(
                                go.Scatter(
                                    x=cell_data[x_param],
                                    y=cell_data[y_param],
                                    mode="lines",
                                    name=cell,
                                    line=dict(color=color, width=3),
                                    hovertemplate=(
                                        f"<b>{cell}</b><br>"
                                        f"<b>{y_param}:</b> %{{y}}<br>"
                                        "<extra></extra>"
                                    ),
                                )
                            )

                        if yline:
                            yline_value = sector_data[yline].mean()
                            fig.add_hline(
                                y=yline_value,
                                line_dash="dashdot",
                                line_color="#F70000",
                                line_width=2,
                            )
                            if yline_value > y_max:
                                y_max = yline_value
                            elif yline_value < y_min:
                                y_min = yline_value

                        if xrule:
                            fig.add_vline(
                                x=st.session_state["xrule"],
                                line_width=2,
                                line_dash="dash",
                                line_color="#808080",
                            )

                        fig.update_layout(
                            margin=dict(t=20, l=20, r=20, b=20),
                            title_text=f"SECTOR {sector}",
                            title_x=0.5,
                            template="plotly_white",
                            hoverlabel=dict(font_size=14, font_family="Vodafone"),
                            hovermode="x unified",
                            legend=dict(
                                orientation="h",
                                yanchor="top",
                                y=-0.4,
                                xanchor="center",
                                x=0.5,
                                itemclick="toggleothers",
                                itemdoubleclick="toggle",
                                itemsizing="constant",
                                font=dict(size=14),
                            ),
                            paper_bgcolor="#F5F5F5",
                            plot_bgcolor="#F5F5F5",
                            width=600,
                            height=350,
                            showlegend=True,
                            yaxis=dict(
                                tickfont=dict(
                                    size=14,
                                    color="#000000",
                                ),
                            ),
                            xaxis=dict(
                                tickfont=dict(
                                    size=14,
                                    color="#000000",
                                ),
                            ),
                        )

                        st.plotly_chart(fig, use_container_width=True)


class App:
    def __init__(self):
        self.config = Config().load()
        self.database_session = DatabaseSession(self.config)
        self.query_manager = None
        self.dataframe_manager = DataFrameManager()
        self.streamlit_interface = StreamlitInterface()
        self.chart_generator = ChartGenerator()

    def process_neid(self, neid, start_date, end_date):
        band = "GSM" if neid.endswith("MG") else "DCS"
        mcom_data = self.query_manager.get_mcom_neid(neid)
        cells = mcom_data["Cell"].tolist()
        siteid = set(mcom_data["Site ID"].tolist())
        # st.write(siteid)
        cities = sorted(set(mcom_data["KABUPATEN"].tolist()))
        if not cities:
            return None, None

        city = cities[0]
        gsmdailydata = self.query_manager.get_gsmdaily(cells, start_date, end_date)
        target_data = self.query_manager.get_target_data(city, band)
        paytraf_data = self.query_manager.get_gsm_paytraf(siteid, start_date, end_date)
        # st.write(paytraf_data)
        merged_gsmdaily = pd.merge(
            gsmdailydata, mcom_data, left_on="MOID", right_on="Cell", how="inner"
        )
        merged_all = pd.merge(
            merged_gsmdaily,
            target_data,
            left_on="KABUPATEN",
            right_on="City",
            how="inner",
        )

        return merged_all, paytraf_data

    def run_gsmdaily_query(self, selected_neids, date_range):
        if selected_neids and date_range:
            start_date, end_date = date_range
            combined_gsmdaily = []

            for neid in selected_neids:
                merged_all, _ = self.process_neid(neid, start_date, end_date)
                if merged_all is not None:
                    combined_gsmdaily.append(merged_all)

            if combined_gsmdaily:
                final_combined_gsmdaily = pd.concat(
                    combined_gsmdaily, ignore_index=True
                )
                self.dataframe_manager.add_dataframe(
                    "final_combined_gsmdaily", final_combined_gsmdaily
                )
                # self.dataframe_manager.display_dataframe(
                #     "final_combined_gsmdaily", "Final Combined GSM Daily Data"
                # )
                return final_combined_gsmdaily
        return None

    def run_paytraf_query(self, selected_neids, date_range):
        if selected_neids and date_range:
            start_date, end_date = date_range
            combined_paytraf = []

            for neid in selected_neids:
                _, paytraf_data = self.process_neid(neid, start_date, end_date)
                if paytraf_data is not None:
                    combined_paytraf.append(paytraf_data)

            if combined_paytraf:
                final_combined_paytraf = pd.concat(combined_paytraf, ignore_index=True)
                self.dataframe_manager.add_dataframe(
                    "final_combined_paytraf", final_combined_paytraf
                )
                # self.dataframe_manager.display_dataframe(
                #     "final_combined_paytraf", "Final Combined Paytraf Data"
                # )
                return final_combined_paytraf
        return None

    def display_charts(self, gsmdaily_df, paytraf_df, selected_neids):
        st.markdown(
            *styling(
                f"📶 T_AVAIL",
                font_size=24,
                text_align="left",
                tag="h6",
            )
        )
        self.chart_generator.create_charts_for_daily(
            df=gsmdaily_df,
            cell_name="MOID",
            x_param="DATE_ID",
            y_param="T_AVAIL",
            xrule=True,
        )
        st.markdown(
            *styling(
                f"📶 SDSR",
                font_size=24,
                text_align="left",
                tag="h6",
            )
        )
        self.chart_generator.create_charts_for_daily(
            df=gsmdaily_df,
            cell_name="MOID",
            x_param="DATE_ID",
            y_param="SDCCH_Success_Rate",
            xrule=True,
            yline="SDSR",
        )
        st.markdown(
            *styling(
                f"📶 TDR",
                font_size=24,
                text_align="left",
                tag="h6",
            )
        )
        self.chart_generator.create_charts_for_daily(
            df=gsmdaily_df,
            cell_name="MOID",
            x_param="DATE_ID",
            y_param="NEW_TDR",
            xrule=True,
            yline="TCH Drop Rate",
        )
        st.markdown(
            *styling(
                f"📶 HOSR",
                font_size=24,
                text_align="left",
                tag="h6",
            )
        )
        self.chart_generator.create_charts_for_daily(
            df=gsmdaily_df,
            cell_name="MOID",
            x_param="DATE_ID",
            y_param="HO_SUC",
            xrule=True,
            yline="HOSR",
        )
        st.markdown(
            *styling(
                f"📶 TBF Completion Rate",
                font_size=24,
                text_align="left",
                tag="h6",
            )
        )
        self.chart_generator.create_charts_for_daily(
            df=gsmdaily_df,
            cell_name="MOID",
            x_param="DATE_ID",
            y_param="TBF_Completion_Rate",
            xrule=True,
            yline="TBF Comp",
        )

        st.markdown(
            *styling(
                f"📶 TCH Blocking",
                font_size=24,
                text_align="left",
                tag="h6",
            )
        )
        self.chart_generator.create_charts_for_blocking(
            df=gsmdaily_df,
            cell_name="MOID",
            x_param="DATE_ID",
            y_param="TCH_BLOCKING",
            xrule=True,
        )
        st.markdown(
            *styling(
                f"📶 SD Blocking",
                font_size=24,
                text_align="left",
                tag="h6",
            )
        )
        self.chart_generator.create_charts_for_blocking(
            df=gsmdaily_df,
            cell_name="MOID",
            x_param="DATE_ID",
            y_param="S_CONG",
            xrule=True,
        )
        st.markdown(
            *styling(
                f"📶 TCH Traffic",
                font_size=24,
                text_align="left",
                tag="h6",
            )
        )
        self.chart_generator.create_charts_for_stacked_area(
            df=gsmdaily_df,
            cell_name="MOID",
            x_param="DATE_ID",
            y_param="TCH_Traffic",
            xrule=True,
        )
        st.markdown(
            *styling(
                f"📶 Payload",
                font_size=24,
                text_align="left",
                tag="h6",
            )
        )
        self.chart_generator.create_charts_for_stacked_area(
            df=gsmdaily_df,
            cell_name="MOID",
            x_param="DATE_ID",
            y_param="DATA_PAYLOAD",
            xrule=True,
        )
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                *styling(
                    f"📶 TCH Traffic by Site",
                    font_size=24,
                    text_align="left",
                    tag="h6",
                )
            )
            self.chart_generator.create_charts_for_stacked_area_neid(
                df=paytraf_df,
                neid="NE_ID",
                x_param="DATE_ID",
                y_param="TCH_Traffic",
                xrule=True,
            )
        with col2:
            st.markdown(
                *styling(
                    f"📶 Payload by Site",
                    font_size=24,
                    text_align="left",
                    tag="h6",
                )
            )
            self.chart_generator.create_charts_for_stacked_area_neid(
                df=paytraf_df,
                neid="NE_ID",
                x_param="DATE_ID",
                y_param="DATA_PAYLOAD",
                xrule=True,
            )

    def run(self):
        session, engine = self.database_session.create_session()
        if session is None:
            return

        self.query_manager = QueryManager(engine)
        script_dir = os.path.dirname(__file__)
        sitelist_path = os.path.join(script_dir, "gsm_list.csv")
        sitelist = self.streamlit_interface.load_sitelist(sitelist_path)

        col1, col2, col3, _, _ = st.columns([1, 1, 1, 1, 3])
        with col1:
            date_range = self.streamlit_interface.select_date_range()
            st.session_state["date_range"] = date_range

        with col2:
            selected_neids = self.streamlit_interface.neid_selection(sitelist)
            st.session_state.selected_neids = selected_neids

        with col3:
            xrule = self.streamlit_interface.select_xrule_date()
            st.session_state["xrule"] = xrule

        if st.button("Run Query"):
            final_combined_gsmdaily = self.run_gsmdaily_query(
                selected_neids, date_range
            )
            final_combined_paytraf = self.run_paytraf_query(selected_neids, date_range)
            self.display_charts(
                final_combined_gsmdaily, final_combined_paytraf, selected_neids
            )


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
