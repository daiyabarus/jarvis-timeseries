import csv
import math
import multiprocessing
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from multiprocessing import Pool
from pathlib import Path
from typing import List, Tuple, Optional


# Domain Models
@dataclass
class CellData:
    """Domain model representing a cell tower."""
    ne_id: str
    cellname: str
    latitude: float
    longitude: float
    azimuth: float
    horizontal_beam: float = 60.0  # Default beam width


@dataclass
class CellRelationship:
    """Domain model representing a relationship between two cells."""
    source: CellData
    target: CellData
    distance: float
    bearing_from_source: float
    bearing_from_target: float
    remark_from_source: str
    remark_from_target: str
    head_to_head_remark: str
    max_beam_source: float
    min_beam_source: float
    max_beam_target: float
    min_beam_target: float


# Interfaces (Ports)
class ICsvReader(ABC):
    """Interface for reading CSV files."""

    @abstractmethod
    def read_cells(self, file_path: str) -> List[CellData]:
        pass


class ICsvWriter(ABC):
    """Interface for writing CSV files."""

    @abstractmethod
    def write_relationships(self, relationships: List[CellRelationship], output_file: str) -> None:
        pass


class IGeographicCalculator(ABC):
    """Interface for geographic calculations."""

    @abstractmethod
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        pass

    @abstractmethod
    def calculate_bearing_excel_formula(self, source_lat: float, source_lon: float,
                                        target_lat: float, target_lon: float) -> float:
        pass


class IRelationshipProcessor(ABC):
    """Interface for processing cell relationships."""

    @abstractmethod
    def process_relationships(self, source_cells: List[CellData], target_cells: List[CellData],
                              max_distance: float) -> List[CellRelationship]:
        pass


# Domain Services
class RobustGeographicCalculator(IGeographicCalculator):
    """Robust geographic calculator implementing exact Excel formulas."""

    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance using high-precision Haversine formula."""
        if lat1 == lat2 and lon1 == lon2:
            return 0.0

        R = 6371.0  # Earth radius in kilometers

        # Convert to radians with high precision
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Haversine formula with improved precision
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = (math.sin(dlat / 2.0) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2.0) ** 2)

        # Avoid numerical errors for very small distances
        if a > 1.0:
            a = 1.0
        elif a < 0.0:
            a = 0.0

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def calculate_bearing_excel_formula(self, source_lat: float, source_lon: float,
                                        target_lat: float, target_lon: float) -> float:
        """
        Implement the exact Excel bearing formula:
        =IF(K3=0,0,MOD(ATAN2((COS(C3*PI()/180)*SIN(H3*PI()/180))-(SIN(C3*PI()/180)*COS(H3*PI()/180)*COS(G3*PI()/180-B3*PI()/180)), 
        SIN(G3*PI()/180-B3*PI()/180)*COS(H3*PI()/180)),2*PI())*180/PI())

        Where:
        - C3 = source_lat, B3 = source_lon
        - H3 = target_lat, G3 = target_lon
        - K3 = distance
        """
        distance = self.calculate_distance(
            source_lat, source_lon, target_lat, target_lon)

        if distance == 0:
            return 0.0

        # Convert to radians
        source_lat_rad = math.radians(source_lat)
        source_lon_rad = math.radians(source_lon)
        target_lat_rad = math.radians(target_lat)
        target_lon_rad = math.radians(target_lon)

        # Excel formula components
        dlon = target_lon_rad - source_lon_rad

        # Y component: (COS(source_lat)*SIN(target_lat))-(SIN(source_lat)*COS(target_lat)*COS(dlon))
        y = (math.cos(source_lat_rad) * math.sin(target_lat_rad) -
             math.sin(source_lat_rad) * math.cos(target_lat_rad) * math.cos(dlon))

        # X component: SIN(dlon)*COS(target_lat)
        x = math.sin(dlon) * math.cos(target_lat_rad)

        # Calculate bearing using ATAN2
        bearing_rad = math.atan2(x, y)

        # Convert to degrees and normalize to 0-360
        bearing_deg = math.degrees(bearing_rad)
        bearing_normalized = bearing_deg % 360.0

        return bearing_normalized


class RobustBeamCalculator:
    """Robust beam calculations with proper boundary handling."""

    @staticmethod
    def calculate_max_beam(azimuth: float, horizontal_beam: float) -> float:
        """Calculate maximum beam angle with proper normalization."""
        max_beam = azimuth + horizontal_beam
        return max_beam % 360.0 if max_beam >= 360.0 else max_beam

    @staticmethod
    def calculate_min_beam(azimuth: float, horizontal_beam: float) -> float:
        """Calculate minimum beam angle with proper normalization."""
        min_beam = azimuth - horizontal_beam
        return (min_beam + 360.0) % 360.0 if min_beam < 0.0 else min_beam

    @staticmethod
    def is_bearing_in_beam(bearing: float, azimuth: float, horizontal_beam: float) -> bool:
        """
        Check if bearing is within beam sector using robust angular arithmetic.
        Handles all edge cases including 0/360 degree crossover.
        """
        # Normalize all angles to [0, 360)
        bearing = bearing % 360.0
        azimuth = azimuth % 360.0

        # Calculate beam boundaries
        min_beam = RobustBeamCalculator.calculate_min_beam(
            azimuth, horizontal_beam)
        max_beam = RobustBeamCalculator.calculate_max_beam(
            azimuth, horizontal_beam)

        # Handle wraparound case (beam crosses 0/360 degrees)
        if min_beam > max_beam:
            # Beam spans across 0 degrees (e.g., 350° to 10°)
            return bearing >= min_beam or bearing <= max_beam
        else:
            # Normal case (e.g., 30° to 90°)
            return min_beam <= bearing <= max_beam

    @staticmethod
    def calculate_angular_difference(angle1: float, angle2: float) -> float:
        """Calculate the smallest angular difference between two angles."""
        diff = abs(angle1 - angle2) % 360.0
        return min(diff, 360.0 - diff)


class RobustRelationshipAnalyzer:
    """Robust analyzer implementing exact Excel logic."""

    def __init__(self, geo_calculator: IGeographicCalculator):
        self.geo_calculator = geo_calculator
        self.beam_calculator = RobustBeamCalculator()

    def analyze_relationship(self, source: CellData, target: CellData) -> Optional[CellRelationship]:
        """Analyze relationship using exact Excel formulas."""

        # Calculate distance with high precision
        distance = self.geo_calculator.calculate_distance(
            source.latitude, source.longitude, target.latitude, target.longitude
        )

        # Calculate bearings using exact Excel formulas
        bearing_from_source = self.geo_calculator.calculate_bearing_excel_formula(
            source.latitude, source.longitude, target.latitude, target.longitude
        )

        # Bearing from target is 180° opposite (Excel: MOD(bearing-180,360))
        bearing_from_target = (bearing_from_source +
                               180.0) % 360.0 if distance > 0 else 0.0

        # Calculate beam boundaries
        max_beam_source = self.beam_calculator.calculate_max_beam(
            source.azimuth, source.horizontal_beam)
        min_beam_source = self.beam_calculator.calculate_min_beam(
            source.azimuth, source.horizontal_beam)
        max_beam_target = self.beam_calculator.calculate_max_beam(
            target.azimuth, target.horizontal_beam)
        min_beam_target = self.beam_calculator.calculate_min_beam(
            target.azimuth, target.horizontal_beam)

        # Determine direction remarks using robust beam checking
        if distance == 0:
            remark_from_source = "Colocated"
            remark_from_target = "Colocated"
        else:
            # Check if target is within source beam (source pointing toward target)
            source_pointing_to_target = self.beam_calculator.is_bearing_in_beam(
                bearing_from_source, source.azimuth, source.horizontal_beam
            )

            # Check if source is within target beam (target pointing toward source)
            target_pointing_to_source = self.beam_calculator.is_bearing_in_beam(
                bearing_from_target, target.azimuth, target.horizontal_beam
            )

            remark_from_source = "Indirection" if source_pointing_to_target else "NotIndirection"
            remark_from_target = "Indirection" if target_pointing_to_source else "NotIndirection"

        # Head to Head determination (exact Excel logic)
        if remark_from_source == "Colocated" or remark_from_target == "Colocated":
            head_to_head_remark = "Colocated"
        elif remark_from_source == "Indirection" and remark_from_target == "Indirection":
            head_to_head_remark = "Head to Head"
        else:
            head_to_head_remark = "Not Head to Head"

        return CellRelationship(
            source=source,
            target=target,
            distance=distance,
            bearing_from_source=bearing_from_source,
            bearing_from_target=bearing_from_target,
            remark_from_source=remark_from_source,
            remark_from_target=remark_from_target,
            head_to_head_remark=head_to_head_remark,
            max_beam_source=max_beam_source,
            min_beam_source=min_beam_source,
            max_beam_target=max_beam_target,
            min_beam_target=min_beam_target
        )


# Application Services
class RobustRelationshipProcessor(IRelationshipProcessor):
    """Robust processor with distance filtering and validation."""

    def __init__(self, geo_calculator: IGeographicCalculator):
        self.analyzer = RobustRelationshipAnalyzer(geo_calculator)

    def process_relationships(self, source_cells: List[CellData], target_cells: List[CellData],
                              max_distance: float = 50.0) -> List[CellRelationship]:
        """Process relationships with distance filtering and robust validation."""

        print(
            f"Processing {len(source_cells)} source cells against {len(target_cells)} target cells")
        print(f"Maximum distance filter: {max_distance} km")

        # Use multiprocessing for performance
        with Pool(processes=min(multiprocessing.cpu_count(), 8)) as pool:
            process_func = partial(
                self._process_source_cell_robust,
                target_cells=target_cells,
                max_distance=max_distance
            )
            results = pool.map(process_func, source_cells)

        # Flatten results and filter for Head to Head only
        all_relationships = [
            rel for sublist in results for rel in sublist if rel is not None]
        head_to_head_relationships = [rel for rel in all_relationships
                                      if rel.head_to_head_remark == "Head to Head"]

        print(f"Found {len(all_relationships)} total relationships")
        print(
            f"Found {len(head_to_head_relationships)} Head to Head relationships")

        return head_to_head_relationships

    def _process_source_cell_robust(self, source: CellData, target_cells: List[CellData],
                                    max_distance: float) -> List[Optional[CellRelationship]]:
        """Process a single source cell with robust validation."""

        valid_relationships = []

        for target in target_cells:
            # Skip same cell
            if source.ne_id == target.ne_id and source.cellname == target.cellname:
                continue

            try:
                relationship = self.analyzer.analyze_relationship(
                    source, target)

                if relationship and relationship.distance <= max_distance:
                    valid_relationships.append(relationship)

            except Exception as e:
                print(
                    f"Error processing {source.cellname} -> {target.cellname}: {e}")
                continue

        # Sort by distance and return nearest relationships
        valid_relationships.sort(key=lambda x: x.distance)
        return valid_relationships[:50]  # Return top 50 nearest


# Infrastructure Adapters
class RobustCsvReader(ICsvReader):
    """Robust CSV reader with comprehensive validation."""

    def read_cells(self, file_path: str) -> List[CellData]:
        """Read cells with comprehensive validation and error handling."""

        print(f"Reading cells from: {file_path}")

        try:
            with open(file_path, encoding="utf-8", errors="ignore") as csvfile:
                # Clean the file content
                clean_lines = []
                for line in csvfile:
                    # Remove null bytes and other problematic characters
                    clean_line = line.replace("\0", "").strip()
                    if clean_line:
                        clean_lines.append(clean_line)

                # Parse CSV
                reader = csv.reader(clean_lines)
                header = next(reader, None)

                if not header:
                    raise ValueError("Empty CSV file or missing header")

                print(f"CSV Header: {header}")

                cells = []
                invalid_count = 0

                # Start from row 2 (after header)
                for row_num, row in enumerate(reader, start=2):
                    if len(row) < 5:
                        invalid_count += 1
                        continue

                    try:
                        # Validate and parse data
                        ne_id = str(row[0]).strip()
                        cellname = str(row[1]).strip()
                        latitude = float(row[2])
                        longitude = float(row[3])
                        azimuth = float(row[4])

                        # Validate ranges
                        if not (-90 <= latitude <= 90):
                            print(
                                f"Row {row_num}: Invalid latitude {latitude}")
                            invalid_count += 1
                            continue

                        if not (-180 <= longitude <= 180):
                            print(
                                f"Row {row_num}: Invalid longitude {longitude}")
                            invalid_count += 1
                            continue

                        if not (0 <= azimuth < 360):
                            print(
                                f"Row {row_num}: Invalid azimuth {azimuth}, normalizing...")
                            azimuth = azimuth % 360

                        # Get horizontal beam (default 60°)
                        horizontal_beam = 60.0
                        if len(row) > 5 and row[5]:
                            try:
                                horizontal_beam = float(row[5])
                                if not (0 < horizontal_beam <= 180):
                                    print(
                                        f"Row {row_num}: Invalid beam width {horizontal_beam}, using default 60°")
                                    horizontal_beam = 60.0
                            except ValueError:
                                pass

                        cell = CellData(
                            ne_id=ne_id,
                            cellname=cellname,
                            latitude=latitude,
                            longitude=longitude,
                            azimuth=azimuth,
                            horizontal_beam=horizontal_beam
                        )
                        cells.append(cell)

                    except (ValueError, TypeError, IndexError) as e:
                        print(f"Row {row_num}: Skipping invalid data - {e}")
                        invalid_count += 1
                        continue

                print(f"Successfully loaded {len(cells)} cells")
                if invalid_count > 0:
                    print(f"Skipped {invalid_count} invalid rows")

                return cells

        except FileNotFoundError:
            print(f"Error: File '{file_path}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file '{file_path}': {e}")
            sys.exit(1)


class RobustCsvWriter(ICsvWriter):
    """Robust CSV writer with validation and formatting."""

    def write_relationships(self, relationships: List[CellRelationship], output_file: str) -> None:
        """Write relationships with proper formatting and validation."""

        if not relationships:
            print("No relationships to write!")
            return

        try:
            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)

                # Write comprehensive header
                writer.writerow([
                    "NE_ID_Source", "Cellname_Source", "Long_Source", "Lat_Source",
                    "Azimuth_Source", "Horizontal Beam Source",
                    "NE_ID_Target", "Cellname_Target", "Long_Target", "Lat_Target",
                    "Azimuth_Target", "Horizontal Beam Target",
                    "Distance (KM)", "Bearing From Source", "Bearing From Target",
                    "Remark from Source", "Remark from Target", "Head to Head Remark",
                    "max beam source", "min beam source", "max beam target", "min beam target"
                ])

                # Write data with proper formatting
                for rel in relationships:
                    writer.writerow([
                        rel.source.ne_id,
                        rel.source.cellname,
                        f"{rel.source.longitude:.9f}",
                        f"{rel.source.latitude:.9f}",
                        f"{rel.source.azimuth:.0f}",
                        f"{rel.source.horizontal_beam:.0f}",
                        rel.target.ne_id,
                        rel.target.cellname,
                        f"{rel.target.longitude:.9f}",
                        f"{rel.target.latitude:.9f}",
                        f"{rel.target.azimuth:.0f}",
                        f"{rel.target.horizontal_beam:.0f}",
                        f"{rel.distance:.9f}",
                        f"{rel.bearing_from_source:.9f}",
                        f"{rel.bearing_from_target:.9f}",
                        rel.remark_from_source,
                        rel.remark_from_target,
                        rel.head_to_head_remark,
                        f"{rel.max_beam_source:.0f}",
                        f"{rel.min_beam_source:.0f}",
                        f"{rel.max_beam_target:.0f}",
                        f"{rel.min_beam_target:.0f}"
                    ])

            print(
                f"Successfully wrote {len(relationships)} relationships to {output_file}")

        except Exception as e:
            print(f"Error writing to output file '{output_file}': {e}")
            sys.exit(1)


# Application Controller
class RobustCellAnalysisController:
    """Robust main controller with comprehensive validation."""

    def __init__(self, csv_reader: ICsvReader, csv_writer: ICsvWriter,
                 relationship_processor: IRelationshipProcessor):
        self.csv_reader = csv_reader
        self.csv_writer = csv_writer
        self.relationship_processor = relationship_processor

    def analyze_cell_relationships(self, source_file: str, target_file: str,
                                   max_distance: float = 50.0) -> None:
        """Main analysis method with robust error handling."""

        print("=" * 80)
        print("ROBUST CELL RELATIONSHIP ANALYZER")
        print("=" * 80)

        # Validate input files
        for file_path in [source_file, target_file]:
            if not Path(file_path).is_file():
                print(f"Error: File '{file_path}' does not exist.")
                sys.exit(1)
            print(f"✓ File exists: {file_path}")

        try:
            # Read source and target cells
            print("\n1. Reading source cells...")
            source_cells = self.csv_reader.read_cells(source_file)
            if not source_cells:
                print("Error: No valid source cells found!")
                sys.exit(1)

            print("\n2. Reading target cells...")
            target_cells = self.csv_reader.read_cells(target_file)
            if not target_cells:
                print("Error: No valid target cells found!")
                sys.exit(1)

            # Process relationships
            print(
                f"\n3. Processing relationships (max distance: {max_distance} km)...")
            relationships = self.relationship_processor.process_relationships(
                source_cells, target_cells, max_distance
            )

            if not relationships:
                print("No Head to Head relationships found!")
                return

            # Write results
            print("\n4. Writing results...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"robust_head_to_head_results_{timestamp}.csv"
            self.csv_writer.write_relationships(relationships, output_file)

            # Summary statistics
            print("\n" + "=" * 80)
            print("ANALYSIS COMPLETE - SUMMARY:")
            print("=" * 80)
            print(f"Source cells processed: {len(source_cells)}")
            print(f"Target cells processed: {len(target_cells)}")
            print(f"Head to Head relationships found: {len(relationships)}")
            print(
                f"Average distance: {sum(r.distance for r in relationships) / len(relationships):.3f} km")
            print(f"Results saved to: {output_file}")

        except Exception as e:
            print(f"Fatal error during analysis: {e}")
            sys.exit(1)


def main():
    """Main function with robust argument handling."""

    if len(sys.argv) < 3:
        print(
            "Usage: python robust_cell_analyzer.py <source_file> <target_file> [max_distance_km]")
        print("Example: python robust_cell_analyzer.py source.csv target.csv 25.0")
        sys.exit(1)

    source_file = sys.argv[1]
    target_file = sys.argv[2]
    max_distance = float(sys.argv[3]) if len(sys.argv) > 3 else 50.0

    # Dependency injection with robust implementations
    geo_calculator = RobustGeographicCalculator()
    csv_reader = RobustCsvReader()
    csv_writer = RobustCsvWriter()
    relationship_processor = RobustRelationshipProcessor(geo_calculator)

    controller = RobustCellAnalysisController(
        csv_reader, csv_writer, relationship_processor)
    controller.analyze_cell_relationships(
        source_file, target_file, max_distance)


if __name__ == "__main__":
    main()
