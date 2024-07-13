import pandas as pd
import streamlit as st


def apply_to_dataframe(func):
    def wrapper(self, name, *args, **kwargs):
        dataframe = self.get_dataframe(name)
        if dataframe is not None:
            result = func(dataframe, *args, **kwargs)
            self.add_dataframe(name, result)
        else:
            print(f"DataFrame {name} not found.")

    return wrapper


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

    def combine_dataframes(self, names, new_name):
        combined_df = pd.concat(
            [
                self.get_dataframe(name)
                for name in names
                if self.get_dataframe(name) is not None
            ]
        )
        self.add_dataframe(new_name, combined_df)

    def merge_dataframes(self, name1, name2, new_name, **merge_params):
        df1 = self.get_dataframe(name1)
        df2 = self.get_dataframe(name2)
        if df1 is not None and df2 is not None:
            merged_df = pd.merge(df1, df2, **merge_params)
            self.add_dataframe(new_name, merged_df)

    def concat_dataframes(self, names, new_name, **concat_params):
        dfs = [
            self.get_dataframe(name)
            for name in names
            if self.get_dataframe(name) is not None
        ]
        concatenated_df = pd.concat(dfs, **concat_params)
        self.add_dataframe(new_name, concatenated_df)


# Example usage of the decorator
@apply_to_dataframe
def uppercase_dataframe(dataframe):
    return dataframe.applymap(lambda x: x.upper() if isinstance(x, str) else x)


# Assuming df_manager is an instance of DataFrameManager
# df_manager.uppercase_dataframe('some_dataframe_name')
