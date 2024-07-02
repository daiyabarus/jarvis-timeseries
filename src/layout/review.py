import os

import pandas as pd
import streamlit as st
import toml
from omegaconf import DictConfig, OmegaConf
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from streamlit_extras.mandatory_date_range import date_range_picker


# Configuration and database session functions
def load_config():
    with open(".streamlit/secrets.toml") as f:
        cfg = OmegaConf.create(toml.loads(f.read()))
    return cfg


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


# Streamlit interface functions
def load_sitelist(filepath):
    with open(filepath) as file:
        return [line.strip() for line in file]


def site_selection(sitelist):
    return st.multiselect("SITEID", sitelist)


def select_date_range():
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


# Query functions
def fetch_data(engine, query, params=None):
    try:
        df = pd.read_sql(query, engine, params=params)
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()


def get_mcom_data(engine, siteid):
    query = text(
        """
    SELECT "Site_ID", "NODE_ID", "NE_ID", "Cell_Name", "Longitude", "Latitude", "Dir", "Ant_BW",
           "Ant_Size", "cellId", "eNBId", "MC_class", "KABUPATEN", "LTE"
    FROM mcom
    WHERE "Site_ID" LIKE :siteid
    """
    )
    return fetch_data(engine, query, {"siteid": siteid})


def get_ltedaily_data(engine, siteid, start_date, end_date):
    query = text(
        """
    SELECT *
    FROM ltedaily
    WHERE "SITEID" LIKE :siteid
      AND "DATE_ID" BETWEEN :start_date AND :end_date
    """
    )
    return fetch_data(
        engine,
        query,
        {"siteid": siteid, "start_date": start_date, "end_date": end_date},
    )


def get_ltehourly_data(engine, selected_sites, start_date, end_date):
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

    return fetch_data(engine, query, params=params)


def get_target_data(engine, city, mc_class, band):
    query = text(
        """
    SELECT *
    FROM target
    WHERE "City" = :city AND "MC Class" = :mc_class AND "Band" = :band
    """
    )
    return fetch_data(engine, query, {"city": city, "mc_class": mc_class, "band": band})


def get_ltemdt_data(engine, enodebid, ci):
    query = text(
        """
    SELECT *
    FROM ltemdt
    WHERE enodebid = :enodebid AND ci = :ci
    """
    )
    return fetch_data(engine, query, {"enodebid": enodebid, "ci": ci})


def get_ltetastate_data(engine, enodebid, ci):
    query = text(
        """
    SELECT *
    FROM ltetastate
    WHERE enodebid = :enodebid AND ci = :ci
    """
    )
    return fetch_data(engine, query, {"enodebid": enodebid, "ci": ci})


def get_vswr_data(engine, selected_sites, start_date, end_date):
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

    return fetch_data(engine, query, params=params)


def main():
    st.title("Site Data Analysis")

    # Load configuration
    cfg = load_config()

    # Create database session
    session, engine = create_session(cfg)
    if session is None:
        return

    # Load sitelist
    script_dir = os.path.dirname(__file__)
    sitelist_path = os.path.join(script_dir, "test_sitelist.txt")
    sitelist = load_sitelist(sitelist_path)

    # Site selection
    selected_sites = site_selection(sitelist)
    if not selected_sites:
        st.warning("Please select at least one site.")
        return

    # Date range selection
    date_range = select_date_range()

    # DataFrames to store results
    combined_target_data = []
    combined_ltemdt_data = []
    combined_ltetastate_data = []

    # Fetch data for each selected site
    if st.button("Run Query"):
        if selected_sites and date_range:
            start_date, end_date = date_range

            st.header("MCOM Data")
            for siteid in selected_sites:
                mcom_data = get_mcom_data(engine, siteid)
                st.subheader(f"MCOM Data for Site: {siteid}")
                st.write(mcom_data)

                # Fetch additional data based on mcom results
                for _, row in mcom_data.iterrows():
                    # Get and append target data
                    target_data = get_target_data(
                        engine, row["KABUPATEN"], row["MC_class"], row["LTE"]
                    )
                    target_data["EUtranCell"] = row["Cell_Name"]
                    combined_target_data.append(target_data)

                    # Get and append ltemdt data
                    ltemdt_data = get_ltemdt_data(engine, row["eNBId"], row["cellId"])
                    ltemdt_data["EUtranCell"] = row["Cell_Name"]
                    combined_ltemdt_data.append(ltemdt_data)

                    # Get and append ltetastate data
                    ltetastate_data = get_ltetastate_data(
                        engine, row["eNBId"], row["cellId"]
                    )
                    ltetastate_data["EUtranCell"] = row["Cell_Name"]
                    combined_ltetastate_data.append(ltetastate_data)

            # Combine dataframes
            if combined_target_data:
                combined_target_df = pd.concat(combined_target_data, ignore_index=True)
                st.header("Combined Target Data")
                st.write(combined_target_df)

            if combined_ltemdt_data:
                combined_ltemdt_df = pd.concat(combined_ltemdt_data, ignore_index=True)
                st.header("Combined LTE MDT Data")
                st.write(combined_ltemdt_df)

            if combined_ltetastate_data:
                combined_ltetastate_df = pd.concat(
                    combined_ltetastate_data, ignore_index=True
                )
                st.header("Combined LTE TA State Data")
                st.write(combined_ltetastate_df)

            st.header("LTE Daily Data")
            for siteid in selected_sites:
                ltedaily_data = get_ltedaily_data(engine, siteid, start_date, end_date)
                st.subheader(f"LTE Daily Data for Site: {siteid}")
                st.write(ltedaily_data)

            st.header("LTE Hourly Data")
            ltehourly_data = get_ltehourly_data(
                engine, selected_sites, start_date, end_date
            )
            st.write(ltehourly_data)

            st.header("VSWR")
            vswr_data = get_vswr_data(engine, selected_sites, start_date, end_date)
            st.write(vswr_data)

            # Close session
            session.close()
        else:
            st.warning("Please select site IDs and date range to load data.")


if __name__ == "__main__":
    main()
