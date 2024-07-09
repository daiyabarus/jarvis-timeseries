import os
from math import atan2, cos, pi, radians, sin, sqrt

import pandas as pd
import streamlit as st


class InterSiteDistance:
    def __init__(self, data):
        self.data = data
        self.beamwidth = 90
        self.earth_radius = 6371  # in kilometers

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        if lat1 == lat2 and lon1 == lon2:
            return 0
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = self.earth_radius * c
        return round(distance, 2)

    def is_within_beamwidth(self, dir1, dir2):
        beam_diff = abs(dir1 - dir2) % 360
        min_diff = min(beam_diff, 360 - beam_diff)
        return min_diff <= self.beamwidth

    def find_nearest_neighbors(self, cell_name):
        site_data = self.data[self.data["Cell_Name"] == cell_name].iloc[0]
        lat1, lon1, dir1 = (
            site_data["Latitude"],
            site_data["Longitude"],
            site_data["Dir"],
        )

        neighbors = [
            (
                self.calculate_distance(lat1, lon1, row["Latitude"], row["Longitude"]),
                row["Cell_Name"],
            )
            for _, row in self.data.iterrows()
            if row["Cell_Name"] != cell_name
            and self.is_within_beamwidth(dir1, row["Dir"])
        ]
        neighbors = [n for n in neighbors if n[0] > 0]
        return sorted(neighbors)[:3]

    def calculate_isd(self, cell_name):
        neighbors = self.find_nearest_neighbors(cell_name)
        if len(neighbors) < 3:
            return None
        distances = [dist for dist, _ in neighbors[:3]]
        return round(sum(distances) / len(distances), 2)

    def calculate_all_isd(self, site_id):
        filtered_data = self.data[self.data["NE_ID"] == site_id]
        isd_data = []

        for cell_name in filtered_data["Cell_Name"].unique():
            isd_value = self.calculate_isd(cell_name)
            if isd_value is not None:
                site_id_values = filtered_data.loc[
                    filtered_data["Cell_Name"] == cell_name, "Site_ID"
                ].values
                ne_id_values = filtered_data.loc[
                    filtered_data["Cell_Name"] == cell_name, "NE_ID"
                ].values
                enbid_values = (
                    filtered_data.loc[
                        filtered_data["Cell_Name"] == cell_name, "eNBId"
                    ].values
                    if "eNBId" in filtered_data
                    else [None]
                )
                ci_values = (
                    filtered_data.loc[
                        filtered_data["Cell_Name"] == cell_name, "cellId"
                    ].values
                    if "cellId" in filtered_data
                    else [None]
                )

                if (
                    site_id_values.size == 0
                    or ne_id_values.size == 0
                    or enbid_values.size == 0
                    or ci_values.size == 0
                ):
                    continue

                site_id = site_id_values[0]
                ne_id = ne_id_values[0]
                enbid = enbid_values[0]
                ci = ci_values[0]

                isd_data.append(
                    {
                        "siteid": site_id,
                        "neid": ne_id,
                        "eutrancell": cell_name,
                        "isd": isd_value,
                        "enbid": enbid,
                        "ci": ci,
                    }
                )

        return pd.DataFrame(isd_data)


class NeighborSectors:
    def __init__(self, data):
        self.data = data
        self.beamwidth = 60
        self.max_distance = 5  # in kilometers
        self.min_distance = 0  # minimum distance in kilometers

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = 6371 * c  # Earth radius in kilometers
        return distance

    def calculate_bearing(self, lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        bearing = atan2(
            sin(lon2 - lon1) * cos(lat2),
            cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(lon2 - lon1),
        )
        bearing = (bearing * 180 / pi + 360) % 360
        return bearing

    def calculate_remark(
        self, bearing, dir_source, beam_source, dir_target, beam_target
    ):
        max_beam_source = (dir_source + beam_source) % 360
        min_beam_source = (
            (dir_source - beam_source) % 360
            if (dir_source - beam_source) >= 0
            else (dir_source - beam_source + 360)
        )
        max_beam_target = (dir_target + beam_target) % 360
        min_beam_target = (
            (dir_target - beam_target) % 360
            if (dir_target - beam_target) >= 0
            else (dir_target - beam_target + 360)
        )

        in_direction_source = (
            min_beam_source <= bearing <= max_beam_source
            or (bearing + 360 if bearing < min_beam_source else bearing)
            <= max_beam_source
        )
        in_direction_target = (
            min_beam_target <= bearing <= max_beam_target
            or (bearing + 360 if bearing < min_beam_target else bearing)
            <= max_beam_target
        )

        if in_direction_source and in_direction_target:
            return "Direction Source"
        elif in_direction_source:
            return "Head to Head"
        elif in_direction_target:
            return "Direction Target"
        else:
            return "Indirection"

    def find_neighbor_sectors(self, neid):
        filtered_data = self.data[self.data["NE_ID"] == neid]
        neighbors = []

        seen_pairs = set()  # Keep track of processed pairs to avoid duplicates

        for _, source_row in filtered_data.iterrows():
            source_lat, source_lon, source_dir, source_lte, source_beam = (
                source_row["Latitude"],
                source_row["Longitude"],
                source_row["Dir"],
                source_row["LTE"],
                self.beamwidth,
            )
            lte_filtered_data = self.data[self.data["LTE"] == source_lte]

            for _, target_row in lte_filtered_data.iterrows():
                if source_row["Cell_Name"] == target_row["Cell_Name"]:
                    continue

                target_lat, target_lon, target_dir, target_beam = (
                    target_row["Latitude"],
                    target_row["Longitude"],
                    target_row["Dir"],
                    self.beamwidth,
                )
                distance = self.calculate_distance(
                    source_lat, source_lon, target_lat, target_lon
                )
                if distance <= self.min_distance or distance > self.max_distance:
                    continue

                pair = (source_row["Cell_Name"], target_row["Cell_Name"])
                if pair in seen_pairs:
                    continue

                bearing_from_source = self.calculate_bearing(
                    source_lat, source_lon, target_lat, target_lon
                )
                bearing_from_target = (bearing_from_source - 180 + 360) % 360

                remark = self.calculate_remark(
                    bearing_from_source,
                    source_dir,
                    source_beam,
                    target_dir,
                    target_beam,
                )

                neighbors.append(
                    {
                        "siteid": source_row["Site_ID"],
                        "neid": source_row["NE_ID"],
                        "cellname": source_row["Cell_Name"],
                        "adjneid": target_row["NE_ID"],
                        "adjcellname": target_row["Cell_Name"],
                        "distance": round(distance, 2),
                        "bearing_from_source": round(bearing_from_source, 2),
                        "bearing_from_target": round(bearing_from_target, 2),
                        "remark": remark,
                    }
                )

                seen_pairs.add(pair)

        return pd.DataFrame(neighbors)


def save_results(df, site_id, filename):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    folder = os.path.join(project_root, "sites", site_id)
    if not os.path.exists(folder):
        os.makedirs(folder)
    file_path = os.path.join(folder, filename)
    df.to_csv(file_path, index=False)


def process_uploaded_file(uploaded_file):
    try:
        data = pd.read_csv(uploaded_file)
        return data
    except Exception as e:
        st.error(f"Error reading the file: {e}")
        return None


def rename_columns(data, headers):
    column_mapping = {
        headers[0]: "Site_ID",
        headers[1]: "NE_ID",
        headers[2]: "Cell_Name",
        headers[3]: "Longitude",
        headers[4]: "Latitude",
        headers[5]: "Dir",
    }
    return data.rename(columns=column_mapping)


def main():
    st.title("ISD and Neighbor Sector Calculator")
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file is not None:
        data = process_uploaded_file(uploaded_file)
        if data is None:
            return

        headers = list(data.columns)
        st.subheader("Select Headers")
        site_id_header = st.selectbox("Site_ID", headers, index=0)
        ne_id_header = st.selectbox("NEID", headers, index=1)
        cell_name_header = st.selectbox("CELLNAME", headers, index=2)
        longitude_header = st.selectbox("Longitude", headers, index=3)
        latitude_header = st.selectbox("Latitude", headers, index=4)
        dir_header = st.selectbox("Azimuth", headers, index=5)

        data = rename_columns(
            data,
            [
                site_id_header,
                ne_id_header,
                cell_name_header,
                longitude_header,
                latitude_header,
                dir_header,
            ],
        )

        site_ids = data["NE_ID"].unique()
        selected_site_ids = st.multiselect("Select NE_ID", site_ids)

        if st.button("Calculate ISD"):
            isd_calculator = InterSiteDistance(data)
            isd_dfs = []
            for site_id in selected_site_ids:
                isd_df = isd_calculator.calculate_all_isd(site_id)
                if not isd_df.empty:
                    isd_dfs.append(isd_df)

            if isd_dfs:
                combined_isd_df = pd.concat(isd_dfs)
                st.subheader("ISD Results")
                st.dataframe(combined_isd_df)

                filename = "isd.csv"

                if "siteid" in combined_isd_df.columns:
                    for site_id in combined_isd_df["siteid"].unique():
                        save_results(
                            combined_isd_df[combined_isd_df["siteid"] == site_id],
                            site_id,
                            filename,
                        )
                    st.success(f"Files saved in 'sites/{site_id}/' directories.")
                else:
                    st.error("Column 'siteid' not found in ISD results.")

        if st.button("Find Neighbor Sectors"):
            neighbor_calculator = NeighborSectors(data)
            neighbor_dfs = []
            for site_id in selected_site_ids:
                neighbor_df = neighbor_calculator.find_neighbor_sectors(site_id)
                if not neighbor_df.empty:
                    neighbor_dfs.append(neighbor_df)

            if neighbor_dfs:
                combined_neighbor_df = pd.concat(neighbor_dfs)
                st.subheader("Neighbor Sectors Results")
                st.dataframe(combined_neighbor_df)

                filename = "tier.csv"

                if "siteid" in combined_neighbor_df.columns:
                    for site_id in combined_neighbor_df["siteid"].unique():
                        save_results(
                            combined_neighbor_df[
                                combined_neighbor_df["siteid"] == site_id
                            ],
                            site_id,
                            filename,
                        )
                    st.success("Neighbor sectors saved to 'tier.csv'.")
                else:
                    st.error("Column 'siteid' not found in Neighbor Sectors results.")


if __name__ == "__main__":
    main()
