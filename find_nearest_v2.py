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
    def calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        pass


class IRelationshipProcessor(ABC):
    """Interface for processing cell relationships."""

    @abstractmethod
    def process_relationships(self, source_cells: List[CellData], target_cells: List[CellData],
                              beamwidth: float) -> List[CellRelationship]:
        pass


# Domain Services
class GeographicCalculator(IGeographicCalculator):
    """Service for geographic calculations using Haversine formula."""

    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula."""
        R = 6371  # Earth radius in kilometers

        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate bearing from point 1 to point 2."""
        if self.calculate_distance(lat1, lon1, lat2, lon2) == 0:
            return 0

        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        y = (math.cos(lat1_rad) * math.sin(lat2_rad) -
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(lon2_rad - lon1_rad))
        x = math.sin(lon2_rad - lon1_rad) * math.cos(lat2_rad)

        bearing_rad = math.atan2(x, y)
        bearing_deg = (math.degrees(bearing_rad) % 360)

        return bearing_deg


class BeamCalculator:
    """Service for beam-related calculations."""

    @staticmethod
    def calculate_max_beam(azimuth: float, horizontal_beam: float) -> float:
        """Calculate maximum beam angle."""
        result = azimuth + horizontal_beam
        return result % 360 if result >= 360 else result

    @staticmethod
    def calculate_min_beam(azimuth: float, horizontal_beam: float) -> float:
        """Calculate minimum beam angle."""
        result = azimuth - horizontal_beam
        return result % 360 if result < 0 else result

    @staticmethod
    def is_in_direction(bearing: float, min_beam: float, max_beam: float) -> bool:
        """Check if bearing is within beam direction."""
        # Handle wrap-around cases
        if min_beam > max_beam:  # Beam crosses 0 degrees
            return bearing >= min_beam or bearing <= max_beam
        else:
            return min_beam <= bearing <= max_beam


class RelationshipAnalyzer:
    """Service for analyzing cell relationships."""

    def __init__(self, geo_calculator: IGeographicCalculator):
        self.geo_calculator = geo_calculator
        self.beam_calculator = BeamCalculator()

    def analyze_relationship(self, source: CellData, target: CellData) -> Optional[CellRelationship]:
        """Analyze relationship between source and target cells."""
        distance = self.geo_calculator.calculate_distance(
            source.latitude, source.longitude, target.latitude, target.longitude
        )

        # Calculate bearings using Excel formula logic
        bearing_from_source = self.geo_calculator.calculate_bearing(
            source.latitude, source.longitude, target.latitude, target.longitude
        )
        bearing_from_target = (bearing_from_source +
                               180) % 360 if distance > 0 else 0

        # Calculate beam boundaries
        max_beam_source = self.beam_calculator.calculate_max_beam(
            source.azimuth, source.horizontal_beam)
        min_beam_source = self.beam_calculator.calculate_min_beam(
            source.azimuth, source.horizontal_beam)
        max_beam_target = self.beam_calculator.calculate_max_beam(
            target.azimuth, target.horizontal_beam)
        min_beam_target = self.beam_calculator.calculate_min_beam(
            target.azimuth, target.horizontal_beam)

        # Determine remarks
        if distance == 0:
            remark_from_source = "Colocated"
            remark_from_target = "Colocated"
        else:
            remark_from_source = ("Indirection" if
                                  self.beam_calculator.is_in_direction(
                                      bearing_from_source, min_beam_source, max_beam_source)
                                  else "NotIndirection")
            remark_from_target = ("Indirection" if
                                  self.beam_calculator.is_in_direction(
                                      bearing_from_target, min_beam_target, max_beam_target)
                                  else "NotIndirection")

        # Head to Head remark
        if remark_from_source == "Colocated" or remark_from_target == "Colocated":
            head_to_head_remark = "Colocated"
        elif remark_from_source == "Indirection" and remark_from_target == "Indirection":
            head_to_head_remark = "Head to Head"
        else:
            head_to_head_remark = "Not Head to Head"

        # Only return Head to Head relationships
        if head_to_head_remark != "Head to Head":
            return None

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
class RelationshipProcessor(IRelationshipProcessor):
    """Application service for processing cell relationships."""

    def __init__(self, geo_calculator: IGeographicCalculator):
        self.analyzer = RelationshipAnalyzer(geo_calculator)

    def process_relationships(self, source_cells: List[CellData], target_cells: List[CellData],
                              beamwidth: float) -> List[CellRelationship]:
        """Process relationships between source and target cells."""
        with Pool(processes=multiprocessing.cpu_count() // 2) as pool:
            process_func = partial(self._process_source_cell,
                                   target_cells=target_cells, beamwidth=beamwidth)
            results = pool.map(process_func, source_cells)

        # Flatten and filter results
        return [rel for sublist in results for rel in sublist if rel is not None]

    def _process_source_cell(self, source: CellData, target_cells: List[CellData],
                             beamwidth: float) -> List[Optional[CellRelationship]]:
        """Process a single source cell against all target cells."""
        relationships = []

        for target in target_cells:
            relationship = self.analyzer.analyze_relationship(source, target)
            if relationship:
                relationships.append(relationship)

        # Sort by distance and return top 31
        relationships.sort(key=lambda x: x.distance)
        return relationships[:31]


# Infrastructure Adapters
class CsvReader(ICsvReader):
    """Adapter for reading CSV files."""

    def read_cells(self, file_path: str) -> List[CellData]:
        """Read cells from CSV file."""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as csvfile:
                reader = csv.reader(line.replace("\0", "") for line in csvfile)
                next(reader)  # Skip header

                cells = []
                for row in reader:
                    if len(row) >= 5:
                        try:
                            cell = CellData(
                                ne_id=row[0],
                                cellname=row[1],
                                latitude=float(row[2]),
                                longitude=float(row[3]),
                                azimuth=float(row[4]),
                                horizontal_beam=float(row[5]) if len(
                                    row) > 5 and row[5] else 60.0
                            )
                            cells.append(cell)
                        except (ValueError, TypeError):
                            print(f"Skipping invalid row: {row}")
                            continue

                return cells
        except FileNotFoundError:
            print(f"Error: File '{file_path}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file '{file_path}': {e}")
            sys.exit(1)


class CsvWriter(ICsvWriter):
    """Adapter for writing CSV files."""

    def write_relationships(self, relationships: List[CellRelationship], output_file: str) -> None:
        """Write relationships to CSV file."""
        try:
            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)

                # Write header
                writer.writerow([
                    "NE_ID_Source", "Cellname_Source", "Long_Source", "Lat_Source", "Azimuth_Source",
                    "Horizontal Beam Source", "NE_ID_Target", "Cellname_Target", "Long_Target",
                    "Lat_Target", "Azimuth_Target", "Horizontal Beam Target",
                    "Distance (KM)", "Bearing From Source", "Bearing From Target",
                    "Remark from Source", "Remark from Target", "Head to Head Remark",
                    "max beam source", "min beam source", "max beam target", "min beam target"
                ])

                # Write data
                for rel in relationships:
                    writer.writerow([
                        rel.source.ne_id,
                        rel.source.cellname,
                        rel.source.longitude,
                        rel.source.latitude,
                        rel.source.azimuth,
                        rel.source.horizontal_beam,
                        rel.target.ne_id,
                        rel.target.cellname,
                        rel.target.longitude,
                        rel.target.latitude,
                        rel.target.azimuth,
                        rel.target.horizontal_beam,
                        f"{rel.distance:.9f}",
                        rel.bearing_from_source,
                        rel.bearing_from_target,
                        rel.remark_from_source,
                        rel.remark_from_target,
                        rel.head_to_head_remark,
                        rel.max_beam_source,
                        rel.min_beam_source,
                        rel.max_beam_target,
                        rel.min_beam_target
                    ])

            print(f"Output written to {output_file}")
        except Exception as e:
            print(f"Error writing to output file '{output_file}': {e}")
            sys.exit(1)


# Application Controller
class CellAnalysisController:
    """Main controller for cell analysis application."""

    def __init__(self, csv_reader: ICsvReader, csv_writer: ICsvWriter,
                 relationship_processor: IRelationshipProcessor):
        self.csv_reader = csv_reader
        self.csv_writer = csv_writer
        self.relationship_processor = relationship_processor

    def analyze_cell_relationships(self, source_file: str, target_file: str,
                                   beamwidth: float = 120.0) -> None:
        """Main method to analyze cell relationships."""
        # Validate files
        for file_path in [source_file, target_file]:
            if not Path(file_path).is_file():
                print(f"Error: File '{file_path}' does not exist.")
                sys.exit(1)

        # Read data
        print("Reading source cells...")
        source_cells = self.csv_reader.read_cells(source_file)
        print(f"Loaded {len(source_cells)} source cells")

        print("Reading target cells...")
        target_cells = self.csv_reader.read_cells(target_file)
        print(f"Loaded {len(target_cells)} target cells")

        # Process relationships
        print("Processing relationships...")
        relationships = self.relationship_processor.process_relationships(
            source_cells, target_cells, beamwidth
        )
        print(f"Found {len(relationships)} Head to Head relationships")

        # Write results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"head_to_head_results_{timestamp}.csv"
        self.csv_writer.write_relationships(relationships, output_file)


def main():
    """Main function with dependency injection."""
    if len(sys.argv) < 3:
        print(
            "Usage: python script.py <source_file> <target_file> [beamwidth]")
        sys.exit(1)

    source_file = sys.argv[1]
    target_file = sys.argv[2]
    beamwidth = float(sys.argv[3]) if len(sys.argv) > 3 else 120.0

    # Dependency injection
    geo_calculator = GeographicCalculator()
    csv_reader = CsvReader()
    csv_writer = CsvWriter()
    relationship_processor = RelationshipProcessor(geo_calculator)

    controller = CellAnalysisController(
        csv_reader, csv_writer, relationship_processor)
    controller.analyze_cell_relationships(source_file, target_file, beamwidth)


if __name__ == "__main__":
    main()
