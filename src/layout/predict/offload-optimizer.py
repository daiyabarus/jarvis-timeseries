import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
import logging
import plotly as plt
# Initialize logging
logging.basicConfig(level=logging.INFO)

class NetworkOptimizer:
    def __init__(self):
        self.data = {}
        self.sector_utilization = {}
        self.user_distribution = {}
        self.signal_quality = {}
        self.timing_advance = {}
        self.current_parameters = {}
        self.optimized_parameters = {}
        self.cell_mapping = {}
        self.sticky_areas = {}
        self.sticky_area_rsrp = {}

    def load_data(self):
        # Load all CSV files
        csv_files = [
            "kpi.csv",
            "mdt.csv",
            "ta.csv",
            "ReportConfigA5.csv",
            "ReportConfigEUtraInterFreqLb.csv",
            "ReportConfigSearch.csv",
            "EUtranFreqRelation.csv",
            "gain.csv",
            "geocell.csv",
        ]
        for file in csv_files:
            key = file.split(".")[0].lower()
            try:
                self.data[key] = pd.read_csv(file)
                logging.info(f"Successfully loaded {file}")
            except FileNotFoundError:
                logging.error(f"Error: {file} not found")
            except Exception as e:
                logging.error(f"Error loading {file}: {str(e)}")

    def preprocess_data(self):
        logging.info("\nPreprocessing data...")

        # Print column names for each DataFrame
        for key, df in self.data.items():
            logging.info(f"Columns in {key}: {df.columns.tolist()}")

        # Create a mapping between Cell_Name and ci
        if "geocell" in self.data:
            if "Cell_Name" in self.data["geocell"].columns and "cellId" in self.data["geocell"].columns:
                self.cell_mapping = dict(zip(self.data["geocell"]["Cell_Name"], self.data["geocell"]["cellId"]))
                logging.info("Cell mapping created successfully")
            else:
                logging.error("Error: 'Cell_Name' or 'cellId' not found in geocell data")
                return
        else:
            logging.error("Error: geocell data not loaded")
            return

        # Map ci to Cell_Name in mdt and ta data
        if "mdt" in self.data:
            if "ci" in self.data["mdt"].columns:
                self.data["mdt"]["Cell_Name"] = self.data["mdt"]["ci"].map({v: k for k, v in self.cell_mapping.items()})
                logging.info("Cell_Name added to mdt data")
            else:
                logging.error("Error: 'ci' not found in mdt data")
                return
        else:
            logging.error("Error: mdt data not loaded")
            return

        if "ta" in self.data:
            if "ci" in self.data["ta"].columns:
                self.data["ta"]["Cell_Name"] = self.data["ta"]["ci"].map({v: k for k, v in self.cell_mapping.items()})
                logging.info("Cell_Name added to ta data")
            else:
                logging.error("Error: 'ci' not found in ta data")
                return
        else:
            logging.error("Error: ta data not loaded")
            return

        # Merge relevant DataFrames based on Cell_Name
        try:
            logging.info("Starting merge operations...")
            if "kpi" in self.data and "geocell" in self.data:
                self.data["merged"] = pd.merge(self.data["kpi"], self.data["geocell"], on="Cell_Name", how="inner")
                logging.info("First merge completed")
            else:
                logging.error("Error: kpi or geocell data missing")
                return

            if "mdt" in self.data:
                self.data["merged"] = pd.merge(
                    self.data["merged"],
                    self.data["mdt"].groupby("Cell_Name").mean().reset_index(),
                    on="Cell_Name",
                    how="inner",
                )
                logging.info("Second merge completed")
            else:
                logging.error("Error: mdt data missing")

            if "ta" in self.data:
                self.data["merged"] = pd.merge(self.data["merged"], self.data["ta"], on "Cell_Name", how="inner")
                logging.info("Third merge completed")
            else:
                logging.error("Error: ta data missing")

            logging.info("All merge operations completed")
            logging.info(f"Columns in merged DataFrame: {self.data['merged'].columns.tolist()}")
        except KeyError as e:
            logging.error(f"Error during merge: {e}")
        except Exception as e:
            logging.error(f"Unexpected error during merge: {str(e)}")

        logging.info("Preprocessing completed")

    def run_optimization(self):
        self.load_data()
        self.preprocess_data()
        self.analyze_sector_utilization()
        self.analyze_sticky_areas()
        self.analyze_user_distribution()
        self.analyze_signal_quality()
        self.analyze_timing_advance()
        self.analyze_parameters()
        self.load_balancing_algorithm()
        self.optimize_parameters()
        return self.generate_recommendations()

    def analyze_sector_utilization(self):
        # Implement K-means clustering for sector utilization
        utilization_data = self.data.get("merged")
        if utilization_data is None:
            raise KeyError(
                "'merged' key not found in data. Ensure preprocessing is successful."
            )

        utilization_data = utilization_data[
            ["Cell_Name", "DL_Resource_Block_Utilizing_Rate"]
        ]
        kmeans = KMeans(n_clusters=3, random_state=42)
        utilization_data["Cluster"] = kmeans.fit_predict(
            utilization_data[["DL_Resource_Block_Utilizing_Rate"]]
        )
        self.sector_utilization = utilization_data

    def analyze_sticky_areas(self):
        # Define sticky areas as those where a significant percentage of users are at larger distances
        distance_columns = [
            "perc_1500",
            "perc_2000",
            "perc_3000",
            "perc_5000",
            "perc_10000",
            "perc_15000",
            "perc_30000",
        ]
        sticky_threshold = 20  # 20% of users at distances > 1500m

        for _, row in self.data["ta"].iterrows():
            cell_name = row["Cell_Name"]
            sticky_percentage = row[distance_columns].sum()
            if sticky_percentage > sticky_threshold:
                self.sticky_areas[cell_name] = sticky_percentage

        # Calculate average RSRP for sticky areas
        for cell_name in self.sticky_areas.keys():
            cell_mdt = self.data["mdt"][self.data["mdt"]["Cell_Name"] == cell_name]
            self.sticky_area_rsrp[cell_name] = cell_mdt["rsrp_mean"].mean()

    def analyze_user_distribution(self):
        # Implement KDE for user distribution, grouped by Cell_Name
        self.user_distribution = (
            self.data["mdt"]
            .groupby("Cell_Name")
            .apply(lambda x: stats.gaussian_kde(x[["long_grid", "lat_grid"]].values.T))
        )

    def analyze_signal_quality(self):
        # Analyze RSRP distribution by Cell_Name
        self.signal_quality = (
            self.data["mdt"].groupby("Cell_Name")["rsrp_mean"].describe()
        )

    def analyze_timing_advance(self):
        # Implement CDF analysis for timing advance data by Cell_Name
        ta_columns = [col for col in self.data["ta"].columns if col.startswith("perc_")]
        self.timing_advance = self.data["ta"].groupby("Cell_Name")[ta_columns].cumsum()

    def analyze_parameters(self):
        # Implement Random Forest for parameter analysis
        X = self.data["report_config_a5"][["a5Threshold1Rsrp", "a5Threshold2Rsrp"]]
        y = self.data["kpi"]["DL_Resource_Block_Utilizing_Rate"]
        rf = RandomForestRegressor(n_estimators=100, random_state=42)
        rf.fit(X, y)
        self.current_parameters["importance"] = dict(
            zip(X.columns, rf.feature_importances_)
        )

    def load_balancing_algorithm(self):
        # Implement a simple greedy approach for load balancing
        high_util = self.sector_utilization[self.sector_utilization["Cluster"] == 2]
        low_util = self.sector_utilization[self.sector_utilization["Cluster"] == 0]

        for _, high_sector in high_util.iterrows():
            nearest_low = min(
                low_util.iterrows(),
                key=lambda x: np.linalg.norm(
                    np.array(
                        [
                            self.data["merged"][
                                self.data["merged"]["Cell_Name"]
                                == high_sector["Cell_Name"]
                            ]["Longitude"].values[0],
                            self.data["merged"][
                                self.data["merged"]["Cell_Name"]
                                == high_sector["Cell_Name"]
                            ]["Latitude"].values[0],
                        ]
                    )
                    - np.array(
                        [
                            self.data["merged"][
                                self.data["merged"]["Cell_Name"] == x[1]["Cell_Name"]
                            ]["Longitude"].values[0],
                            self.data["merged"][
                                self.data["merged"]["Cell_Name"] == x[1]["Cell_Name"]
                            ]["Latitude"].values[0],
                        ]
                    )
                ),
            )
            print(
                f"Consider offloading from {high_sector['Cell_Name']} to {nearest_low[1]['Cell_Name']}"
            )

    def optimize_parameters(self):
        # Implement a simple optimization strategy
        current_thresh = self.data["report_config_a5"]["a5Threshold1Rsrp"].mean()
        step = 1
        best_utilization = self.data["kpi"]["DL_Resource_Block_Utilizing_Rate"].std()

        for _ in range(10):  # 10 iterations of optimization
            new_thresh = current_thresh + step
            # Simulate new utilization (in reality, this would require more complex modeling)
            new_utilization = (
                self.data["kpi"]["DL_Resource_Block_Utilizing_Rate"].std() * 0.95
            )

            if new_utilization < best_utilization:
                best_utilization = new_utilization
                current_thresh = new_thresh
            else:
                step = -step / 2

        self.optimized_parameters["a5Threshold1Rsrp"] = current_thresh

    def generate_recommendations(self):
        recommendations = []
        recommendations.append(
            f"Optimize a5Threshold1Rsrp to {self.optimized_parameters['a5Threshold1Rsrp']}"
        )

        high_util = self.sector_utilization[self.sector_utilization["Cluster"] == 2]
        for _, sector in high_util.iterrows():
            recommendations.append(
                f"Consider expanding capacity for sector {sector['Cell_Name']}"
            )

        for cell_name, sticky_percentage in self.sticky_areas.items():
            rsrp = self.sticky_area_rsrp[cell_name]
            recommendations.append(
                f"Sticky area detected in {cell_name} ({sticky_percentage:.2f}% users at distance >1500m). Average RSRP: {rsrp:.2f}"
            )
            if (
                rsrp is not None
            ) and rsrp < -100:  # Assuming -100 dBm as a threshold for poor RSRP
                recommendations.append(
                    f"  - Consider optimizing coverage for {cell_name}"
                )

        return recommendations


# Usage
optimizer = NetworkOptimizer()
recommendations = optimizer.run_optimization()
for rec in recommendations:
    print(rec)

# Visualization example for sticky areas
plt.figure(figsize=(12, 8))
for cell_name, sticky_percentage in optimizer.sticky_areas.items():
    cell_data = optimizer.data["mdt"][optimizer.data["mdt"]["Cell_Name"] == cell_name]
    plt.scatter(
        cell_data["long_grid"],
        cell_data["lat_grid"],
        label=f"{cell_name} ({sticky_percentage:.2f}%)",
        alpha=0.6,
    )
plt.title("User Distribution in Sticky Areas")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.legend()
plt.show()
