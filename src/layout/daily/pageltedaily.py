# pageltedaily.py
import streamlit as st
import pandas as pd
from dbcon import DatabaseHandler
from enumdaily.enumdailylte import HeaderLTEDaily

st.set_page_config(layout="wide")


class LTEDataFilterApp:
    def __init__(self, db_path):
        self.db = DatabaseHandler(db_path)
        self.db.connect()

    def run(self):
        selected_table = HeaderLTEDaily.TABLE.value

        # Fetch filter options
        min_date = self.db.get_min_date(selected_table, HeaderLTEDaily.DATEID.value)
        max_date = self.db.get_max_date(selected_table, HeaderLTEDaily.DATEID.value)
        erbs_options = self.db.get_erbs(selected_table, HeaderLTEDaily.ERBS.value)
        cell_options = self.db.get_cell(selected_table, HeaderLTEDaily.CELL.value)

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            selected_min_date = st.date_input(
                "Start Date",
                value=pd.to_datetime(min_date),
                min_value=pd.to_datetime(min_date),
                max_value=pd.to_datetime(max_date),
                key="min_date",
            )

        with col2:
            selected_max_date = st.date_input(
                "End Date",
                value=pd.to_datetime(max_date),
                min_value=pd.to_datetime(min_date),
                max_value=pd.to_datetime(max_date),
                key="max_date",
            )

        with col3:
            selected_erbs = st.multiselect(
                "ERBS",
                options=erbs_options,
                key="erbs",
            )

        with col4:
            selected_cells = st.multiselect(
                "Cell",
                options=cell_options,
                key="cells",
            )

        with col5:
            filter_button = st.button("Filter")

        # Query and display data based on filter selections
        def format_date(date):
            return f"{date.month}/{date.day}/{date.year}"

        if filter_button:
            query_conditions = ["1=1"]

            if selected_min_date and selected_max_date:
                query_conditions.append(
                    f"{HeaderLTEDaily.DATEID.value} BETWEEN '{format_date(selected_min_date)}' AND '{format_date(selected_max_date)}'"
                )

            if selected_erbs:
                erbs_condition = f"{HeaderLTEDaily.ERBS.value} IN ({', '.join([f'\"{erbs}\"' for erbs in selected_erbs])})"
                query_conditions.append(erbs_condition)

            if selected_cells:
                cells_condition = f"{HeaderLTEDaily.CELL.value} IN ({', '.join([f'\"{cell}\"' for cell in selected_cells])})"
                query_conditions.append(cells_condition)

            where_clause = " AND ".join(query_conditions)
            query = f"SELECT * FROM {selected_table} WHERE {where_clause};"

            # Debug print query
            # st.write(f"Debug Query: {query}")

            filtered_data = pd.read_sql_query(query, self.db.connection)

            st.write(filtered_data)
        else:
            st.warning(
                "Please select filter options and click Filter to run the query."
            )


# Run the Application
if __name__ == "__main__":
    app = LTEDataFilterApp(HeaderLTEDaily.DB_PATH.value)
    app.run()
