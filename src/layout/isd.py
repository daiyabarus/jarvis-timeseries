from math import atan2, cos, radians, sin, sqrt

import pandas as pd


class InterSiteDistance:
    def __init__(self, neid, data):
        self.neid = neid
        self.data = data
        self.beamwidth = 90
        self.earth_radius = 6371  # in kilometers

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return self.earth_radius * c

    def find_nearest_neighbors(self, cell_name):
        site_data = self.data[self.data["Cell_Name"] == cell_name]
        lat1, lon1, dir1 = site_data.iloc[0][["Latitude", "Longitude", "Dir"]]

        neighbors = []
        for _, row in self.data.iterrows():
            if row["Cell_Name"] != cell_name:
                lat2, lon2, dir2 = row[["Latitude", "Longitude", "Dir"]]
                distance = self.calculate_distance(lat1, lon1, lat2, lon2)
                if distance == 0:  # Exclude zero distances
                    continue
                beam_diff1 = abs(dir1 - dir2)
                beam_diff2 = 360 - beam_diff1 if beam_diff1 > 180 else beam_diff1
                if beam_diff1 <= self.beamwidth and beam_diff2 <= self.beamwidth:
                    neighbors.append((distance, row["Cell_Name"]))

        neighbors.sort()
        return neighbors[:3]

    def calculate_isd(self, cell_name):
        neighbors = self.find_nearest_neighbors(cell_name)
        if len(neighbors) < 3:
            return None

        dist1, dist2, dist3 = (dist for dist, _ in neighbors)
        if dist3 > 2 * dist1:
            return round((dist1 + dist2) / 2)
        else:
            return round((dist1 + dist2 + dist3) / 2)

    def calculate_all_isd(self):
        isd_data = []
        for cell_name in self.data["Cell_Name"].unique():
            isd = self.calculate_isd(cell_name)
            if isd is not None:
                isd_data.append({"Cell_Name": cell_name, "ISD": isd})
        return pd.DataFrame(isd_data)
