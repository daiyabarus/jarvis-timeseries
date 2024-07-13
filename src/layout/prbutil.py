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

st.set_page_config(layout="wide")


def load_config():
    try:
        with open(".streamlit/secrets.toml") as f:
            return OmegaConf.create(toml.load(f))
    except Exception as e:
        st.error(f"Error loading configuration: {e}")
        return None


def create_session(cfg: DictConfig):
    if cfg is None:
        return None, None
    try:
        db_cfg = cfg.connections.postgresql
        engine_url = f"{db_cfg.dialect}://{db_cfg.username}:{db_cfg.password}@{db_cfg.host}:{db_cfg.port}/{db_cfg.database}"
        engine = create_engine(engine_url)
        Session = sessionmaker(bind=engine)
        return Session(), engine
    except Exception as e:
        st.error(f"Error creating database session: {e}")
        return None, None


def add_site_id_column(df, eutrancellfdd_col):
    def extract_site_id(cell_id):
        if cell_id.startswith(("E_", "E-", "N_", "N-")):
            cell_id = cell_id[2:]
        return cell_id[:6]

    df["site_id"] = df[eutrancellfdd_col].apply(extract_site_id)
    return df


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


def colors():
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


def create_chart(df, site, parameter):
    def format_x_axis(date_id, hour_id):
        return date_id.astype(str) + " " + hour_id.astype(str).str.zfill(2) + ":00:00"

    def add_cell_trace(fig, x_axis, y_values, cell_name, color):
        fig.add_trace(
            go.Scatter(
                x=x_axis,
                y=y_values,
                mode="lines",
                name=cell_name,
                line=dict(color=color),
                hovertemplate=(
                    f"<b>{cell_name}</b><br>"
                    f"<b>Date:</b> %{{x}}<br>"
                    f"<b>{parameter}:</b> %{{y}}<br>"
                    "<extra></extra>"
                ),
            ),
            secondary_y=False,
        )

    fig = make_subplots(specs=[[{"secondary_y": False}]])
    title = get_header(df["EUtranCellFDD"].unique())
    color_mapping = dict(zip(df["EUtranCellFDD"].unique(), colors()))

    for sector, sector_df in df.groupby("sector"):
        for cell, cell_df in sector_df.groupby("EUtranCellFDD"):
            cell_df = cell_df.sort_values(by=["DATE_ID", "hour_id"])
            x_axis = format_x_axis(cell_df["DATE_ID"], cell_df["hour_id"])
            add_cell_trace(fig, x_axis, cell_df[parameter], cell, color_mapping[cell])

    fig.update_layout(
        title_text=title,
        title_x=0.4,
        template="plotly_white",
        xaxis=dict(
            tickformat="%m/%d/%Y %H:%M",
            tickangle=-90,
            type="category",
            tickmode="auto",
            nticks=15,
        ),
        autosize=True,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.8,
            xanchor="center",
            x=0.5,
        ),
        width=600,
        height=350,
    )
    fig.update_yaxes(title_text=parameter, secondary_y=False)
    return fig


# def get_header(cell, site):
def get_header(cell):
    sectors = {f"Sector {input_string[-1]}" for input_string in cell}
    sorted_sectors = sorted(sectors)
    return ", ".join(sorted_sectors)


def main():
    st.title("PRB Utilization Data Viewer")

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

    cfg = load_config()

    if "db_session" not in st.session_state:
        session, engine = create_session(cfg)
        st.session_state.db_session = session
        st.session_state.engine = engine
    else:
        session = st.session_state.db_session
        engine = st.session_state.engine

    if engine is not None:
        try:
            script_dir = os.path.dirname(__file__)
            sitelist_path = os.path.join(script_dir, "test_sitelist.txt")

            with open(sitelist_path) as f:
                site_list = [line.strip() for line in f]

            selected_sites = st.multiselect("Select Site IDs", options=site_list)

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

            df = None

            if st.button("Run Query"):
                if selected_sites and date_range:
                    start_date, end_date = date_range
                    like_conditions = " OR ".join(
                        [
                            f'"EUtranCellFDD" LIKE :site_{i}'
                            for i in range(len(selected_sites))
                        ]
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
                    params = {
                        f"site_{i}": f"%{site}%"
                        for i, site in enumerate(selected_sites)
                    }
                    params.update({"start_date": start_date, "end_date": end_date})

                    df = pd.read_sql(query, engine, params=params)
                else:
                    st.warning("Please select site IDs and date range to load data.")
                    return
        except FileNotFoundError as e:
            st.error(f"Error loading site list: {e}")
            return
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return

        if df is not None:
            df = add_site_id_column(df, "EUtranCellFDD")

            df["sector"] = df["EUtranCellFDD"].apply(determine_sector)

            for site in selected_sites:
                site_df = df[df["site_id"] == site]

                sac.divider(
                    label=f"{site}",
                    icon="graph-up",
                    align="center",
                    size="sm",
                    color="indigo",
                )

                st.markdown(
                    """ <style> .font {
                    font-size:20px ; text-align: left; font-family: 'Ericsson Hilda Light'; color: #393955;}
                    .icon {
                    font-size: 20px;
                    vertical-align: middle;
                    margin-right: 5px;
                    }
                    </style> """,
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<p class="font"><i class="bi bi-graph-up"></i>PRB Utilization {site}</p>',
                    unsafe_allow_html=True,
                )
                col1, col2, col3 = st.columns(3)
                con1 = col1.container(border=True)
                con2 = col2.container(border=True)
                con3 = col3.container(border=True)

                for sector, con in zip(
                    sorted(site_df["sector"].unique()), [con1, con2, con3]
                ):
                    with con:
                        sector_df = site_df[site_df["sector"] == sector]
                        fig = create_chart(
                            sector_df, site, "DL_Resource_Block_Utilizing_Rate"
                        )
                        st.plotly_chart(fig, use_container_width=True)

                st.markdown(
                    """ <style> .font {
                    font-size:20px ; text-align: left; font-family: 'Ericsson Hilda Light'; color: #393955;}
                    .icon {
                    font-size: 20px;
                    vertical-align: middle;
                    margin-right: 5px;
                    }
                    </style> """,
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<p class="font"><i class="icon bi bi-people"></i>Active User {site}</p>',
                    unsafe_allow_html=True,
                )
                col1, col2, col3 = st.columns(3)
                con1 = col1.container(border=True)
                con2 = col2.container(border=True)
                con3 = col3.container(border=True)

                for sector, con in zip(
                    sorted(site_df["sector"].unique()), [con1, con2, con3]
                ):
                    with con:
                        sector_df = site_df[site_df["sector"] == sector]
                        fig = create_chart(sector_df, site, "Active User")
                        st.plotly_chart(fig, use_container_width=True)

                if df is None:
                    sac.result(
                        label="Alert",
                        description="Data not stored in the database. Please update the data.",
                    )
                else:
                    st.error("Data not stored in the database. Please update the data.")


if __name__ == "__main__":
    main()
