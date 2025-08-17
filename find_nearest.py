import csv
import math
import multiprocessing
import sys
from datetime import datetime
from functools import partial
from multiprocessing import Pool

# python main.py find.csv raw.csv


def calculate_distance(lat1, lon1, lat2, lon2):
    # Calculate the distance between two points using the Haversine formula
    R = 6371  # Radius of the Earth in kilometers

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance


def calculate_azimuth(lat1, lon1, lat2, lon2):
    # Calculate the azimuth (bearing) between two points
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlon = lon2_rad - lon1_rad

    y = math.sin(dlon) * math.cos(lat2_rad)
    x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(
        lat2_rad
    ) * math.cos(dlon)
    azimuth_rad = math.atan2(y, x)

    azimuth_deg = math.degrees(azimuth_rad)
    azimuth_deg = (azimuth_deg + 360) % 360  # Convert negative azimuth to positive

    return azimuth_deg


def process_row(row, target_rows, beamwidth):
    if len(row) < 5:
        return []  # Skip rows with insufficient columns

    rnc, utrancell, lat, lon, azimuth = row

    distances = []
    for target_row in target_rows:
        if len(target_row) < 5:
            continue  # Skip target rows with insufficient columns

        _, _, target_lat, target_lon, _ = target_row

        distance = calculate_distance(
            float(lat), float(lon), float(target_lat), float(target_lon)
        )

        target_azimuth = calculate_azimuth(
            float(lat), float(lon), float(target_lat), float(target_lon)
        )

        azimuth_diff = abs(target_azimuth - float(azimuth))
        azimuth_diff = min(
            azimuth_diff, 360 - azimuth_diff
        )  # Consider circular difference

        if azimuth_diff <= beamwidth / 2:
            distances.append((distance, target_row))

    nearest_relationships = sorted(distances)[:31]  # Get the 30 nearest relationships
    result = []
    for distance, target_row in nearest_relationships:
        result.append(
            [
                rnc,
                utrancell,
                lat,
                lon,
                target_row[0],
                target_row[1],
                target_row[2],
                target_row[3],
                f"{distance:.2f}",
            ]
        )

    return result


if __name__ == "__main__":
    source_file = sys.argv[1]
    target_file = sys.argv[2]
    beamwidth = 120  # Specify the beamwidth value

    with open(source_file, encoding="utf-8", errors="ignore") as source_csvfile:
        source_reader = csv.reader(line.replace("\0", "") for line in source_csvfile)
        next(source_reader)  # Skip the header row
        source_rows = list(source_reader)

    with open(target_file, encoding="utf-8", errors="ignore") as target_csvfile:
        target_reader = csv.reader(line.replace("\0", "") for line in target_csvfile)
        next(target_reader)  # Skip the header row
        target_rows = list(target_reader)

    # Use multiprocessing to process rows in parallel
    pool = Pool(processes=multiprocessing.cpu_count() // 2)
    process_func = partial(process_row, target_rows=target_rows, beamwidth=beamwidth)
    results = pool.map(process_func, source_rows)
    pool.close()
    pool.join()

    # Flatten the list of results
    flattened_results = [item for sublist in results for item in sublist]

    # Write the results to a CSV file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"results_{timestamp}.csv"
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            [
                "Source",
                "Cells",
                "latitude_Cells",
                "longitude_Cells",
                "Target",
                "Target_Cells",
                "latitude_target",
                "longitude_target",
                "Distance",
            ]
        )
        writer.writerows(flattened_results)
