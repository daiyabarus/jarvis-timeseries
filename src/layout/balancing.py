# import os
import pandas as pd
import streamlit as st
import toml
from omegaconf import DictConfig, OmegaConf
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


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
    """
    The StreamlitInterface class is designed to provide a user-friendly interface for interacting with
    the load balancing system. It utilizes Streamlit, a popular open-source app framework, to create
    web applications with minimal effort. This class abstracts the complexity of the load balancing
    operations and presents the user with an intuitive graphical interface.

    Attributes
    ----------
        db_manager (QueryManager): An instance of the QueryManager class that handles database queries
        related to load balancing. This allows the StreamlitInterface to retrieve and display data,
        as well as initiate load balancing operations based on user input.
        config (dict): A configuration dictionary that stores settings and preferences for the
        Streamlit interface. This can include layout preferences, default values, and other UI settings.

    Methods
    -------
        display_dashboard(): Renders the main dashboard view in the Streamlit app. This method organizes
        the layout and calls other methods to display specific pieces of information or interactive elements.
        show_load_info(): Fetches and displays the current load information for all nodes in the system.
        This can include metrics such as CPU usage, memory usage, and network activity.
        initiate_load_balancing(): Provides the user with the option to manually trigger a load balancing
        operation. This method calls the load balancing functionality in the db_manager and updates the
        interface to reflect any changes in the system's load distribution.

    This class serves as the entry point for users to interact with the load balancing system, making it
    accessible to users without technical expertise in load balancing or database management.
    """

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


class QueryManager:
    """
    The QueryManager class is designed to manage and execute database queries related to load balancing.
    It encapsulates the logic for constructing, executing, and processing the results of queries
    to efficiently distribute workloads across different resources or nodes in a system.

    Attributes
    ----------
        connection (DatabaseConnection): An instance of a database connection object. This attribute
        is used to execute queries against the database.
        query_cache (dict): An optional cache for storing the results of frequently executed queries
        to improve performance.

    Methods
    -------
        execute_query(query, params): Executes a given SQL query with the specified parameters and
        returns the result.
        get_load_info(node_id): Retrieves load information for a specific node identified by node_id.
        This method constructs a query to fetch relevant load metrics from the database.
        balance_load(): Analyzes the current load distribution and executes necessary queries to
        redistribute the load more evenly across available resources.

    This class is a core component of the system's load balancing strategy, ensuring that resources
    are utilized efficiently and avoiding overloading of individual nodes.
    """

    def __init__(self, engine):
        self.engine = engine

    def fetch_data(self, query, params=None):
        try:
            df = pd.read_sql(query, self.engine, params=params)
            return df
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            return pd.DataFrame()

    def _get_mcom(self, siteid):
        query = text(
            """
        SELECT "Site_ID", "NODE_ID", "NE_ID", "Cell_Name", "Longitude", "Latitude", "Dir", "Ant_BW",
               "Ant_Size", "cellId", "eNBId", "KABUPATEN", "LTE"
        FROM mcom
        WHERE "Site_ID" LIKE :siteid
        """
        )
        return self.fetch_data(query, {"siteid": siteid})

    def _get_prb(_self, selected_sites):
        like_conditions = " OR ".join(
            [f'"EUtranCellFDD" LIKE :site_{i}' for i in range(len(selected_sites))]
        )
        end_date = pd.to_datetime("today") - pd.Timedelta(days=1)
        start_date = pd.to_datetime("today") - pd.Timedelta(days=4)
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

    def _get_mdt(_self, selected_sites):
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
        long_grid,
        lat_grid
        FROM ltemdt
        WHERE ({like_conditions})
        """
        )
        params = {f"site_{i}": f"%{site}%" for i, site in enumerate(selected_sites)}
        return _self.fetch_data(query, params=params)

    def _get_tastate(_self, siteid):
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


class App:
    def __init__(self) -> None:
        self.config = Config.load()
        self.database_session = DatabaseSession(self.config)
        self.query_manager = None
        self.dataframe_manager = DataFrameManager()
        self.streamlit_interface = StreamlitInterface()


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
