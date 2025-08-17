import csv
import math
import multiprocessing
import sys
from datetime import datetime
from functools import partial
from multiprocessing import Pool
from pathlib import Path

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two points using the Haversine formula.

    Args:
        lat1 (float): Latitude of the first point in degrees.
        lon1 (float): Longitude of the first point in degrees.
        lat2 (float): Latitude of the second point in degrees.
        lon2 (float): Longitude of the second point in degrees.

    Returns:
        float: Distance between the two points in kilometers.
    """
    R = 6371  # Earth radius in kilometers

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def calculate_azimuth(lat1, lon1, lat2, lon2):
    """
    Calculate the azimuth (bearing) between two points.

    Args:
        lat1 (float): Latitude of the first point in degrees.
        lon1 (float): Longitude of the first point in degrees.
        lat2 (float): Latitude of the second point in degrees.
        lon2 (float): Longitude of the second point in degrees.

    Returns:
        float: Azimuth from the first point to the second point in degrees (0-360).
    """
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlon = lon2_rad - lon1_rad

    y = math.sin(dlon) * math.cos(lat2_rad)
    x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)
    azimuth_rad = math.atan2(y, x)

    azimuth_deg = math.degrees(azimuth_rad)
    return (azimuth_deg + 360) % 360


def process_row(row, target_rows, beamwidth):
    """
    Process a source row to find the nearest target cells within the beamwidth,
    including azimuth (Dir) for both source and target cells.

    Args:
        row (list): Source cell data [Site_ID, Cellname, Latitude, Longitude, Dir].
        target_rows (list): List of target cell data rows, each with [Site_ID, Cellname, Latitude, Longitude, Dir].
        beamwidth (float): Beamwidth angle in degrees to filter target cells.

    Returns:
        list: List of relationships including source and target cell data with azimuths.
    """
    if len(row) < 5:
        return []  # Skip rows with insufficient columns

    try:
        site_id, cellname, lat, lon, azimuth = row
        lat, lon, azimuth = float(lat), float(lon), float(azimuth)
    except (ValueError, TypeError):
        print(f"Skipping invalid source row: {row}")
        return []

    distances = []
    for target_row in target_rows:
        if len(target_row) < 5:
            continue  # Skip target rows with insufficient columns

        try:
            target_site_id, target_cellname, target_lat, target_lon, target_azimuth = target_row
            target_lat, target_lon, target_azimuth = float(target_lat), float(target_lon), float(target_azimuth)
        except (ValueError, TypeError):
            print(f"Skipping invalid target row: {target_row}")
            continue

        distance = calculate_distance(lat, lon, target_lat, target_lon)
        target_calculated_azimuth = calculate_azimuth(lat, lon, target_lat, target_lon)

        azimuth_diff = abs(target_calculated_azimuth - azimuth)
        azimuth_diff = min(azimuth_diff, 360 - azimuth_diff)

        if azimuth_diff <= beamwidth / 2:
            distances.append((distance, target_row))

    nearest_relationships = sorted(distances)[:31]  # Get the 30 nearest relationships
    result = []
    for distance, target_row in nearest_relationships:
        target_site_id, target_cellname, target_lat, target_lon, target_azimuth = target_row
        result.append(
            [
                site_id,
                cellname,
                lon,
                lat,
                azimuth,  # Source azimuth (Dir)
                target_site_id,
                target_cellname,
                target_lon,
                target_lat,
                target_azimuth,  # Target azimuth (Dir)
                f"{distance:.2f}",
            ]
        )

    return result


def read_csv_file(file_path):
    """
    Read a CSV file and return its rows, skipping the header.

    Args:
        file_path (str): Path to the CSV file.

    Returns:
        list: List of rows from the CSV file.
    """
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as csvfile:
            reader = csv.reader(line.replace("\0", "") for line in csvfile)
            next(reader)  # Skip header
            return list(reader)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}")
        sys.exit(1)


def main():
    """
    Main function to process cell relationships using source and target CSV files.
    """
    if len(sys.argv) < 3:
        print("Usage: python script.py <source_file> <target_file> [beamwidth]")
        sys.exit(1)

    source_file = sys.argv[1]
    target_file = sys.argv[2]
    beamwidth = float(sys.argv[3]) if len(sys.argv) > 3 else 120.0

    # Validate file existence
    for file_path in [source_file, target_file]:
        if not Path(file_path).is_file():
            print(f"Error: File '{file_path}' does not exist.")
            sys.exit(1)

    # Read source and target rows
    source_rows = read_csv_file(source_file)
    target_rows = read_csv_file(target_file)

    # Process rows in parallel
    with Pool(processes=multiprocessing.cpu_count() // 2) as pool:
        process_func = partial(process_row, target_rows=target_rows, beamwidth=beamwidth)
        results = pool.map(process_func, source_rows)

    # Flatten results
    flattened_results = [item for sublist in results for item in sublist]

    # Write results to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"results_{timestamp}.csv"
    try:
        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                [
                    "Source",
                    "Cells",
                    "longitude_Cells",
                    "latitude_Cells",
                    "Source_Azimuth",
                    "Target",
                    "Target_Cells",
                    "longitude_target",
                    "latitude_target",
                    "Target_Azimuth",
                    "Distance",
                ]
            )
            writer.writerows(flattened_results)
        print(f"Output written to {output_file}")
    except Exception as e:
        print(f"Error writing to output file '{output_file}': {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()