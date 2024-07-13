import pandas as pd
import streamlit as st
from sqlalchemy import text


class QueryManager:
    def __init__(self, engine):
        """
        Initialize the QueryManager with a SQLAlchemy engine.

        :param engine: SQLAlchemy engine object for database connection.
        """
        self.engine = engine

    def fetch_data(self, query, params=None):
        """
        Execute a SQL query and fetch data into a pandas DataFrame.

        :param query: SQL query string.
        :param params: Dictionary of parameters for the SQL query.
        :return: DataFrame containing the fetched data or an empty DataFrame on error.
        """
        try:
            df = pd.read_sql(query, self.engine, params=params)
            return df
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            return pd.DataFrame()

    def build_like_conditions(_self, column, values):
        """
        Build SQL LIKE conditions for a list of values.

        :param column: The column name to apply the LIKE conditions.
        :param values: List of values to match using LIKE.
        :return: Tuple of the condition string and dictionary of parameters.
        """
        conditions = " OR ".join(
            [f"{column} LIKE :{column.lower()}_{i}" for i in range(len(values))]
        )
        params = {
            f"{column.lower()}_{i}": f"%{value}%" for i, value in enumerate(values)
        }
        return conditions, params

    @st.cache_data(ttl=3600)
    def get_mcom_data(_self, siteid):
        """
        Get mcom data for a specific site ID.

        :param siteid: The site ID to filter the data.
        :return: DataFrame containing the mcom data.
        """
        query = text(
            """
            SELECT "Site_ID", "NODE_ID", "NE_ID", "Cell_Name", "Longitude", "Latitude", "Dir", "Ant_BW",
                   "Ant_Size", "cellId", "eNBId", "MC_class", "KABUPATEN", "LTE"
            FROM mcom
            WHERE "Site_ID" LIKE :siteid
        """
        )
        return _self.fetch_data(query, {"siteid": siteid})

    @st.cache_data(ttl=3600)
    def get_mcom_neid(_self):
        """
        Get mcom NE ID data.

        :return: DataFrame containing the mcom NE ID data.
        """
        query = text(
            """
            SELECT "NE_ID", "Cell_Name", "Longitude", "Latitude", "Dir"
            FROM mcom
        """
        )
        return _self.fetch_data(query)

    @st.cache_data(ttl=3600)
    def get_ltedaily_data(_self, siteid, neids, start_date, end_date):
        """
        Get LTE daily data for specific site ID, NE IDs, and date range.

        :param siteid: The site ID to filter the data.
        :param neids: List of NE IDs to filter the data.
        :param start_date: Start date of the date range.
        :param end_date: End date of the date range.
        :return: DataFrame containing the LTE daily data.
        """
        base_query = """
            SELECT *
            FROM ltedaily
            WHERE "SITEID" LIKE :siteid
            AND "DATE_ID" BETWEEN :start_date AND :end_date
        """
        params = {"siteid": siteid, "start_date": start_date, "end_date": end_date}
        if neids:
            neid_conditions, neid_params = _self.build_like_conditions("NEID", neids)
            query = text(base_query + " AND (" + neid_conditions + ")")
            params.update(neid_params)
        else:
            query = text(base_query)
        return _self.fetch_data(query, params)

    @st.cache_data(ttl=3600)
    def get_ltedaily_payload(_self, selected_sites, start_date, end_date):
        """
        Get LTE daily payload data for selected sites and date range.

        :param selected_sites: List of selected sites to filter the data.
        :param start_date: Start date of the date range.
        :param end_date: End date of the date range.
        :return: DataFrame containing the LTE daily payload data.
        """
        site_conditions, site_params = _self.build_like_conditions(
            "SITEID", selected_sites
        )
        query = text(
            f"""
            SELECT "DATE_ID", "SITEID", "NEID", "EutranCell", "Payload_Total(Gb)", "CQI Bh"
            FROM ltedaily
            WHERE ({site_conditions})
            AND "DATE_ID" BETWEEN :start_date AND :end_date
        """
        )
        params = {**site_params, "start_date": start_date, "end_date": end_date}
        return _self.fetch_data(query, params)

    @st.cache_data(ttl=3600)
    def get_ltehourly_data(_self, selected_sites, end_date):
        """
        Get LTE hourly data for selected sites and date range.

        :param selected_sites: List of selected sites to filter the data.
        :param end_date: End date for the data range.
        :return: DataFrame containing the LTE hourly data.
        """
        site_conditions, site_params = _self.build_like_conditions(
            "EUtranCellFDD", selected_sites
        )
        start_date = end_date - pd.Timedelta(days=15)
        query = text(
            f"""
            SELECT "DATE_ID", "EUtranCellFDD", hour_id, "DL_Resource_Block_Utilizing_Rate", "Active User"
            FROM ltehourly
            WHERE ({site_conditions})
            AND "DATE_ID" BETWEEN :start_date AND :end_date
        """
        )
        params = {**site_params, "start_date": start_date, "end_date": end_date}
        return _self.fetch_data(query, params)

    @st.cache_data(ttl=3600)
    def get_target_data(_self, city, mc_class, band):
        """
        Get target data for a specific city, MC class, and band.

        :param city: The city to filter the data.
        :param mc_class: The MC class to filter the data.
        :param band: The band to filter the data.
        :return: DataFrame containing the target data.
        """
        query = text(
            """
            SELECT *
            FROM target
            WHERE "City" = :city AND "Band" = :band AND "MC Class" = :mc_class
        """
        )
        return _self.fetch_data(
            query, {"city": city, "mc_class": mc_class, "band": band}
        )

    @st.cache_data(ttl=600)
    def get_ltemdt_data(_self, selected_sites):
        """
        Get LTE MDT data for selected sites.

        :param selected_sites: List of selected sites to filter the data.
        :return: DataFrame containing the LTE MDT data.
        """
        site_conditions, site_params = _self.build_like_conditions(
            "site", selected_sites
        )
        query = text(
            f"""
            SELECT site, enodebid, ci, sample, rsrp_mean, rsrq_mean, rank, long_grid, lat_grid
            FROM ltemdt
            WHERE ({site_conditions})
        """
        )
        return _self.fetch_data(query, site_params)

    @st.cache_data(ttl=600)
    def get_ltetastate_data(_self, siteid):
        """
        Get LTE TA state data for specific site IDs.

        :param siteid: List of site IDs to filter the data.
        :return: DataFrame containing the LTE TA state data.
        """
        site_conditions, site_params = _self.build_like_conditions("site", siteid)
        query = text(
            f"""
            SELECT *
            FROM ltetastate
            WHERE ({site_conditions})
        """
        )
        return _self.fetch_data(query, site_params)

    @st.cache_data(ttl=3600)
    def get_mcom_tastate(_self, selected_neids):
        """
        Get mcom TA state data for selected NE IDs.

        :param selected_neids: List of selected NE IDs to filter the data.
        :return: DataFrame containing the mcom TA state data.
        """
        neid_conditions, neid_params = _self.build_like_conditions(
            "NE_ID", selected_neids
        )
        query = text(
            f"""
            SELECT "Site_ID", "NE_ID", "Cell_Name", "cellId", "eNBId"
            FROM mcom
            WHERE ({neid_conditions})
        """
        )
        return _self.fetch_data(query, neid_params)

    @st.cache_data(ttl=3600)
    def get_vswr_data(_self, selected_sites, end_date):
        """
        Get VSWR data for selected sites and date range.

        :param selected_sites: List of selected sites to filter the data.
        :param end_date: End date for the data range.
        :return: DataFrame containing the VSWR data.
        """
        site_conditions, site_params = _self.build_like_conditions(
            "NE_NAME", selected_sites
        )
        start_date = end_date - pd.Timedelta(days=3)
        query = text(
            f"""
            SELECT "DATE_ID", "NE_NAME", "RRU", "pmReturnLossAvg", "VSWR"
            FROM ltevswr
            WHERE ({site_conditions})
            AND "DATE_ID" BETWEEN :start_date AND :end_date
            AND "RRU" NOT LIKE '%RfPort=R%'
            AND "RRU" NOT LIKE '%RfPort=S%'
            AND "VSWR" IS NOT NULL
        """
        )
        params = {**site_params, "start_date": start_date, "end_date": end_date}
        return _self.fetch_data(query, params)

    @st.cache_data(ttl=3600)
    def get_busyhour(_self, selected_sites, end_date):
        """
        Get busy hour data for selected sites and date range.

        :param selected_sites: List of selected sites to filter the data.
        :param end_date: End date for the data range.
        :return: DataFrame containing the busy hour data.
        """
        site_conditions, site_params = _self.build_like_conditions(
            "EUtranCellFDD", selected_sites
        )
        start_date = end_date - pd.Timedelta(days=15)
        query = text(
            f"""
            SELECT "DATE_ID", "EUtranCellFDD", "CQI"
            FROM ltebusyhour
            WHERE ({site_conditions})
            AND "DATE_ID" BETWEEN :start_date AND :end_date
        """
        )
        params = {**site_params, "start_date": start_date, "end_date": end_date}
        return _self.fetch_data(query, params)

    @st.cache_data(ttl=3600)
    def get_cqi_cluster(_self, eutrancellfdd, start_date, end_date):
        """
        Get CQI cluster data for a specific EUtranCellFDD and date range.

        :param eutrancellfdd: The EUtranCellFDD to filter the data.
        :param start_date: Start date of the date range.
        :param end_date: End date of the date range.
        :return: DataFrame containing the CQI cluster data.
        """
        query = text(
            """
            SELECT "DATE_ID", "EUtranCellFDD", "CQI"
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
            return pd.read_sql(query, _self.engine, params=params)
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            return pd.DataFrame()
