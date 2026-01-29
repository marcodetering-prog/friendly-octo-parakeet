#!/usr/bin/env python3
"""
Dynamic Craftsman Coverage Analyzer with Google Sheets Integration

This script analyzes which craftsman categories have coverage for each property.
It automatically:
- Reads data directly from Google Sheets (no manual entry needed)
- Detects all properties from the property sheet
- Detects all craftsmen and their specializations
- Extracts service areas and categories dynamically
- Generates detailed coverage reports

The solution is self-adjusting: add/remove properties, craftsmen, or categories
in Google Sheets and the script automatically picks up the changes on next run.

Author: Craftsman Coverage Analysis Tool
Date: 2026-01-29
"""

import json
import csv
import os
import sys
from dataclasses import dataclass, asdict
from typing import List, Dict, Set, Tuple, Optional
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class CoverageCategoryGap:
    """Represents a missing coverage for a specific category."""
    category: str
    responsible_craftsmen: List[str]  # Empty list if no coverage


@dataclass
class PropertyCoverageAnalysis:
    """Represents coverage analysis for a single property."""
    property_name: str
    total_categories: int
    covered_categories: int
    coverage_percentage: float
    gaps: List[CoverageCategoryGap]

    def has_gaps(self) -> bool:
        """Check if property has any coverage gaps."""
        return len(self.gaps) > 0

    def get_gap_count(self) -> int:
        """Get total number of gaps."""
        return len(self.gaps)


@dataclass
class CoverageSummary:
    """Summary statistics for all properties."""
    total_properties: int
    properties_with_gaps: int
    properties_with_full_coverage: int
    total_gaps_across_all_properties: int
    average_coverage_percentage: float
    categories_with_lowest_coverage: Dict[str, int]
    data_source: str


@dataclass
class Craftsman:
    """Represents a craftsman with their specializations and service areas."""
    name: str
    categories: List[str]
    service_areas_plz: List[str]  # List of PLZ codes


# ============================================================================
# DATA SOURCE INTERFACE
# ============================================================================

class DataSource(ABC):
    """Abstract base class for data sources."""

    @abstractmethod
    def fetch_properties(self) -> List[str]:
        """Fetch list of property addresses from data source."""
        pass

    @abstractmethod
    def fetch_categories(self) -> List[str]:
        """Fetch list of all craftsman categories from data source."""
        pass

    @abstractmethod
    def fetch_craftsmen(self) -> Dict[str, Craftsman]:
        """Fetch craftsmen with their specializations and service areas."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this data source is available/configured."""
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Get human-readable name of this data source."""
        pass


# ============================================================================
# GOOGLE SHEETS DATA SOURCE
# ============================================================================

class GoogleSheetsDataSource(DataSource):
    """Fetches data from Google Sheets using the Google Sheets API."""

    def __init__(self, sheet_id: str, property_gid: int, craftsman_gid: int):
        """
        Initialize Google Sheets data source.

        Args:
            sheet_id: Google Sheets ID
            property_gid: Sheet GID for properties
            craftsman_gid: Sheet GID for craftsmen
        """
        self.sheet_id = sheet_id
        self.property_gid = property_gid
        self.craftsman_gid = craftsman_gid
        self.service = None
        self._initialize_service()

    def _initialize_service(self):
        """Initialize Google Sheets API service."""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.service_account import Credentials
            from google.auth.transport.urllib3 import AuthorizedHttp
            import urllib3
            from googleapiclient.discovery import build
            from googleapiclient.errors import HttpError

            self.build = build
            self.HttpError = HttpError

            # Try to load credentials from file
            creds_file = Path("credentials.json")
            if creds_file.exists():
                try:
                    credentials = Credentials.from_service_account_file(
                        str(creds_file),
                        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
                    )
                    self.service = build("sheets", "v4", credentials=credentials)
                except Exception as e:
                    print(f"Warning: Could not load credentials from file: {e}")
                    self.service = None
        except ImportError:
            self.service = None

    def is_available(self) -> bool:
        """Check if Google Sheets API is configured."""
        return self.service is not None

    def get_source_name(self) -> str:
        """Get human-readable name of this data source."""
        return "Google Sheets"

    def fetch_properties(self) -> List[str]:
        """
        Fetch properties from Google Sheets.

        Sheet structure:
        - Column C: Strasse (addresses)
        - Starts from row 2 (row 1 is header)

        Returns:
            List of property addresses
        """
        if not self.is_available():
            raise RuntimeError("Google Sheets API not configured")

        try:
            # Fetch column C (properties) from property sheet
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=f"gid={self.property_gid}&range=C2:C1000"
            ).execute()

            values = result.get("values", [])
            properties = [row[0] for row in values if row and row[0].strip()]
            return properties
        except Exception as e:
            print(f"Error fetching properties: {e}")
            raise

    def fetch_categories(self) -> List[str]:
        """
        Fetch categories from Google Sheets.

        Detects categories from column headers in craftsman sheet.
        Service-related columns (excluding Name, Service Areas, etc.)

        Returns:
            List of category names
        """
        if not self.is_available():
            raise RuntimeError("Google Sheets API not configured")

        try:
            # Fetch header row to get categories
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=f"gid={self.craftsman_gid}&range=A1:Z1"
            ).execute()

            headers = result.get("values", [[]])[0]

            # Filter out non-service columns
            exclude_columns = ["Name", "Einsatzgebiet PLZ", "Service Areas", ""]
            categories = [
                h for h in headers
                if h and h not in exclude_columns
            ]
            return categories
        except Exception as e:
            print(f"Error fetching categories: {e}")
            raise

    def fetch_craftsmen(self) -> Dict[str, Craftsman]:
        """
        Fetch craftsmen from Google Sheets.

        Sheet structure:
        - Column A: Craftsman name
        - Column G: Einsatzgebiet PLZ (service areas)
        - Other columns: Categories with TRUE/checkmark for specialization

        Returns:
            Dictionary mapping craftsman name to Craftsman object
        """
        if not self.is_available():
            raise RuntimeError("Google Sheets API not configured")

        try:
            # Fetch all data from craftsman sheet
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=f"gid={self.craftsman_gid}&range=A1:Z1000"
            ).execute()

            rows = result.get("values", [])
            if not rows:
                return {}

            # Parse header row to map columns to categories
            headers = rows[0]
            name_col = 0
            plz_col = 6  # Column G is service areas

            craftsmen = {}

            # Process each craftsman row (skip header)
            for row_idx in range(1, len(rows)):
                row = rows[row_idx]
                if not row or not row[0].strip():
                    continue

                name = row[0].strip()

                # Extract service areas
                service_areas = []
                if len(row) > plz_col and row[plz_col]:
                    # Parse service areas, reconstructing full addresses from split pieces
                    service_areas = self._parse_service_areas(row[plz_col])

                # Extract categories (TRUE/checkmark values)
                categories = []
                for col_idx, header in enumerate(headers):
                    if col_idx >= len(row):
                        continue

                    # Skip non-service columns
                    if header in ["Name", "Einsatzgebiet PLZ", ""]:
                        continue

                    # Check if this category is marked for the craftsman
                    cell_value = row[col_idx].strip().upper() if col_idx < len(row) else ""
                    if cell_value in ["TRUE", "1", "X", "✓"]:
                        categories.append(header)

                if categories or service_areas:
                    craftsmen[name] = Craftsman(
                        name=name,
                        categories=categories,
                        service_areas_plz=service_areas
                    )

            return craftsmen
        except Exception as e:
            print(f"Error fetching craftsmen: {e}")
            raise


# ============================================================================
# FALLBACK DATA SOURCE
# ============================================================================

class StaticDataSource(DataSource):
    """Fallback data source with hardcoded sample data."""

    def is_available(self) -> bool:
        """Static data source is always available."""
        return True

    def get_source_name(self) -> str:
        """Get human-readable name of this data source."""
        return "Static Sample Data (Fallback)"

    def fetch_properties(self) -> List[str]:
        """Fetch sample properties."""
        return [
            "Main Street 101 10001",
            "Main Street 102 10001",
            "Main Street 103 10001",
            "Oak Avenue 20 10002",
            "Oak Avenue 21 10002",
            "Oak Avenue 22 10002",
            "Elm Road 5 10003",
            "Elm Road 6 10003",
        ]

    def fetch_categories(self) -> List[str]:
        """Fetch sample categories."""
        return [
            "All-rounder/Caretaker",
            "Sanitärleitungen (Plumbing)",
            "Haushaltsgerätetechnik (Household Appliance)",
            "Bodenleger (Flooring)",
            "Schlosser (Locksmith)",
            "Fensterspezialisten (Window Specialists)",
            "Rollladespezialisten (Shutter Specialists)",
            "Elektriker (Electrician)",
            "Maler (Painter)",
            "Ungeziefer (Pest Control)",
            "Aufzugstechnik (Elevator Technician)",
            "Garagentortechnik (Garage Door Technician)",
            "Schreiner (Carpenter)",
            "Heizungstechnik (Heating Technician)",
            "Kanalreiniger (Drain Cleaner)",
        ]

    def fetch_craftsmen(self) -> Dict[str, Craftsman]:
        """Fetch sample craftsmen."""
        return {
            "André Gonçalves": Craftsman(
                name="André Gonçalves",
                categories=["All-rounder/Caretaker"],
                service_areas_plz=["8049", "8050"]
            ),
            "Fernando Leite": Craftsman(
                name="Fernando Leite",
                categories=["All-rounder/Caretaker"],
                service_areas_plz=["8049", "8050"]
            ),
            "Sibir AG": Craftsman(
                name="Sibir AG",
                categories=["Sanitärleitungen (Plumbing)", "Bodenleger (Flooring)"],
                service_areas_plz=["8049", "8050"]
            ),
            "Weiss Security AG": Craftsman(
                name="Weiss Security AG",
                categories=["Fensterspezialisten (Window Specialists)"],
                service_areas_plz=["8049", "8050", "8051"]
            ),
            "Elektro Müller": Craftsman(
                name="Elektro Müller",
                categories=["Elektriker (Electrician)"],
                service_areas_plz=["8049", "8050"]
            ),
        }


# ============================================================================
# CSV DATA SOURCE
# ============================================================================

class CSVDataSource(DataSource):
    """Reads data from CSV files in the input folder with flexible format detection."""

    def __init__(self, input_dir: str = "input"):
        """
        Initialize CSV data source.

        Supports full Google Sheets exports with automatic column detection.
        Works with both simple and complex CSV formats.
        Auto-detects file types by analyzing column headers.

        Args:
            input_dir: Directory containing CSV files
        """
        self.input_dir = Path(input_dir)
        self.properties_file = None
        self.craftsmen_file = None

        # Auto-detect CSV files by content
        self._auto_detect_csv_files()

    def _auto_detect_csv_files(self):
        """Auto-detect properties and craftsmen CSV files by analyzing column headers."""
        if not self.input_dir.exists():
            return

        csv_files = list(self.input_dir.glob("*.csv"))

        for csv_file in csv_files:
            try:
                file_type = self._detect_file_type(str(csv_file))
                if file_type == "properties":
                    self.properties_file = csv_file
                elif file_type == "craftsmen":
                    self.craftsmen_file = csv_file
            except Exception:
                # Skip files that can't be read
                continue

    def _detect_file_type(self, filepath: str) -> Optional[str]:
        """
        Detect whether a CSV file contains properties or craftsmen data.

        Returns:
            "properties" if file has address/street columns (Liegenschaft, Strasse, Hausnummer, PLZ, Ort)
            "craftsmen" if file has name + service area + category columns
            None if file type can't be determined
        """
        try:
            # Use the same header detection as the rest of the code
            lines = self._find_valid_header_row(filepath)

            import io
            text_stream = io.StringIO("".join(lines))
            reader = csv.DictReader(text_stream)

            if not reader.fieldnames:
                return None

            # Normalize headers to lowercase
            headers_lower = [h.lower() if h else "" for h in reader.fieldnames]
            headers_text = " ".join(headers_lower)

            # Distinctive properties file indicators (Liegenschaft is very specific)
            has_liegenschaft = "liegenschaft" in headers_text
            has_strasse = any(kw in headers_text for kw in ["strasse", "straße", "street"])
            has_plz_ort = any(kw in headers_text for kw in ["plz", "postal", "ort", "city"])

            # Distinctive craftsmen file indicators
            has_firmenname = "firmenname" in headers_text
            has_einsatzgebiet = "einsatzgebiet" in headers_text

            # Count how many TRUE/FALSE category columns exist
            first_rows = []
            for _ in range(min(3, len(lines) - 1)):  # Check first 3 data rows
                row = next(reader, None)
                if row:
                    first_rows.append(row)
                else:
                    break

            true_false_columns = 0
            if first_rows:
                for col_idx in range(len(reader.fieldnames)):
                    for row in first_rows:
                        if col_idx < len(reader.fieldnames):
                            col_name = reader.fieldnames[col_idx]
                            if col_name and col_name in row:
                                val = str(row.get(col_name, "")).strip().upper()
                                if val in ["TRUE", "FALSE", "1", "0", "X", "✓", "WAHR"]:
                                    true_false_columns += 1
                                    break

            # Determine file type based on distinctive indicators
            # Properties file must have Liegenschaft OR (Strasse + PLZ/Ort)
            is_properties = has_liegenschaft or (has_strasse and has_plz_ort)

            # Craftsmen file must have Firmenname AND (Einsatzgebiet OR many TRUE/FALSE columns)
            is_craftsmen = has_firmenname and (has_einsatzgebiet or true_false_columns >= 5)

            if is_properties and not is_craftsmen:
                return "properties"
            elif is_craftsmen and not is_properties:
                return "craftsmen"
            elif is_craftsmen and is_properties:
                # Both match, use Firmenname as tiebreaker
                return "craftsmen" if has_firmenname else "properties"

            return None
        except Exception:
            return None

    def is_available(self) -> bool:
        """Check if CSV files exist."""
        return self.properties_file is not None and self.craftsmen_file is not None

    def get_source_name(self) -> str:
        """Get human-readable name of this data source."""
        return f"CSV Files (input/ folder)"

    def _find_address_column(self, headers: List[str]) -> Optional[str]:
        """
        Find the address/street column by common names.

        Looks for columns like: address, strasse, street, straße, etc.
        """
        address_keywords = ["address", "strasse", "straße", "street", "adresse", "rue"]
        for header in headers:
            if any(keyword.lower() in header.lower() for keyword in address_keywords):
                return header
        return None

    def _find_number_column(self, headers: List[str]) -> Optional[str]:
        """Find the house number column."""
        number_keywords = ["hausnummer", "nummer", "number", "house"]
        for header in headers:
            if any(keyword.lower() in header.lower() for keyword in number_keywords):
                return header
        return None

    def _find_plz_column(self, headers: List[str]) -> Optional[str]:
        """Find the postal code column by common names."""
        plz_keywords = ["plz", "postal", "zip", "postleitzahl", "einsatzgebiet"]
        for header in headers:
            if header and any(keyword.lower() in header.lower() for keyword in plz_keywords):
                return header
        return None

    def _find_name_column(self, headers: List[str]) -> Optional[str]:
        """Find the craftsman/company name column."""
        # Prioritize these keywords in order
        name_keywords = ["firmenname", "name", "handwerker", "craftsman", "betrieb", "company"]
        for keyword in name_keywords:
            for header in headers:
                if header and keyword.lower() in header.lower():
                    return header
        # If no match, use first non-empty column
        for header in headers:
            if header and header.strip():
                return header
        return None

    def _is_metadata_row(self, row: Dict) -> bool:
        """Check if a row is metadata/header info rather than data."""
        # Skip rows that are mostly empty or contain only commas
        non_empty = [v for v in row.values() if v and str(v).strip()]
        return len(non_empty) == 0

    def _find_valid_header_row(self, filepath: str) -> list:
        """
        Find the real header row by reading the CSV properly and locating
        the row with known header keywords (Strasse, Hausnummer, etc).
        """
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row_idx, row in enumerate(reader):
                # Look for header keywords that indicate this is the header row
                row_text = " ".join(str(v).lower() for v in row)
                if any(keyword in row_text for keyword in ["strasse", "hausnummer", "name", "firmenname"]):
                    # Found the header, return from this point
                    with open(filepath, "r", encoding="utf-8") as f2:
                        lines = f2.readlines()
                    return lines[row_idx:]

        # Fallback: return all lines
        with open(filepath, "r", encoding="utf-8") as f:
            return f.readlines()

    def _parse_service_areas(self, service_area_str: str) -> List[str]:
        """
        Parse service areas from a comma-separated string, reconstructing full addresses.

        Handles formats like:
        - "Im Struppen 11,12,13,14,15,16,17,19,21, 8048 Zürich"
        - "Badenerstr.717/Im Struppen 8, 8048 Zürich"

        Returns:
            List of reconstructed full addresses (e.g., ["Im Struppen (various), 8048 Zürich"])
        """
        import re

        if not service_area_str or not service_area_str.strip():
            return []

        pieces = [p.strip() for p in service_area_str.split(",") if p.strip()]
        if not pieces:
            return []

        # Find postal code pieces (format: XXXX City or similar)
        postal_code_pattern = re.compile(r'^\d{4,5}\s+')

        # Group pieces by postal code
        addresses = []
        current_streets = []

        for piece in pieces:
            if postal_code_pattern.match(piece):
                # This is a postal code + city
                if current_streets:
                    # Combine streets with this postal code
                    full_address = ", ".join(current_streets) + ", " + piece
                    addresses.append(full_address)
                    current_streets = []
                else:
                    # Postal code alone (shouldn't happen but handle it)
                    addresses.append(piece)
            else:
                # This is a street/address piece
                current_streets.append(piece)

        # Handle remaining streets without postal code
        if current_streets:
            addresses.append(", ".join(current_streets))

        return addresses if addresses else [service_area_str]

    def fetch_properties(self) -> List[str]:
        """
        Fetch properties from CSV file.

        Automatically detects address, house number, and postal code columns.
        Combines them to create full addresses.
        Works with full Google Sheets exports or simple address lists.
        Handles complex headers with multiple description rows.

        Returns:
            List of property addresses
        """
        if not self.is_available():
            raise RuntimeError("CSV files not found in input folder")

        try:
            properties = []

            # Find valid header row in case of complex structure
            lines = self._find_valid_header_row(str(self.properties_file))

            # Create reader from remaining lines
            import io
            text_stream = io.StringIO("".join(lines))
            reader = csv.DictReader(text_stream)

            if not reader.fieldnames:
                return []

            # Find columns
            address_col = self._find_address_column(reader.fieldnames)
            number_col = self._find_number_column(reader.fieldnames)
            plz_col = self._find_plz_column(reader.fieldnames)

            if not address_col:
                # Fallback: try "address" column
                address_col = next(
                    (col for col in reader.fieldnames if col and "address" in col.lower()),
                    None
                )

            if not address_col:
                raise ValueError(f"Could not find address column. Available: {reader.fieldnames}")

            # Use set to track unique properties and preserve order
            seen_properties = set()

            for row in reader:
                if self._is_metadata_row(row):
                    continue

                address = row.get(address_col, "").strip() if address_col else ""
                if not address:
                    continue

                # Add house number if available
                if number_col:
                    number = row.get(number_col, "").strip()
                    if number:
                        address = f"{address} {number}"

                # Add PLZ if available
                if plz_col:
                    plz = row.get(plz_col, "").strip()
                    if plz:
                        address = f"{address} {plz}"

                # Only add if not already seen (deduplicate)
                if address not in seen_properties:
                    properties.append(address)
                    seen_properties.add(address)

            return properties
        except Exception as e:
            print(f"Error reading properties.csv: {e}")
            raise

    def fetch_categories(self) -> List[str]:
        """
        Fetch categories from craftsmen CSV.

        Automatically detects category columns by finding columns with
        TRUE/FALSE/1/0/X/✓ values. Skips metadata columns.
        Handles complex headers with multiple description rows.

        Returns:
            List of category names
        """
        if not self.is_available():
            raise RuntimeError("CSV files not found in input folder")

        try:
            # Find valid header row in case of complex structure
            lines = self._find_valid_header_row(str(self.craftsmen_file))

            # Create reader from remaining lines
            import io
            text_stream = io.StringIO("".join(lines))
            reader = csv.DictReader(text_stream)

            if not reader.fieldnames:
                return []

            name_col = self._find_name_column(reader.fieldnames)

            # Metadata columns to skip
            skip_columns = [
                "name", "handwerker", "craftsman", "service", "area", "plz",
                "postal", "zip", "einsatzgebiet", "priority", "priorit",
                "notes", "note", "bemerkung", "comment", "kontakt", "email",
                "telefon", "phone", "adresse", "address", "summe", "kompetenz",
                "ansprechperson", "firmenname", "netto", "stundenpauschale",
                "sprache", "auftrag", "pikkett", "versicherung", "priorisierung",
                "mail"  # Catches "E-Mail"
            ]

            categories = []
            for col in reader.fieldnames:
                if not col:  # Skip empty column names
                    continue
                # Skip metadata columns and name column
                if any(skip.lower() in col.lower() for skip in skip_columns):
                    continue
                if col == name_col:
                    continue

                # Add as category
                categories.append(col)

            return categories
        except Exception as e:
            print(f"Error reading craftsmen.csv: {e}")
            raise

    def fetch_craftsmen(self) -> Dict[str, Craftsman]:
        """
        Fetch craftsmen from CSV file.

        Automatically detects:
        - Craftsman name column
        - Category columns (columns with TRUE/FALSE/1/0/X/✓ values)
        - Service area columns (contains PLZ codes or addresses)

        Handles complex headers with multiple description rows.

        Returns:
            Dictionary mapping craftsman name to Craftsman object
        """
        if not self.is_available():
            raise RuntimeError("CSV files not found in input folder")

        try:
            craftsmen = {}

            # Find valid header row in case of complex structure
            lines = self._find_valid_header_row(str(self.craftsmen_file))

            # Create reader from remaining lines
            import io
            text_stream = io.StringIO("".join(lines))
            reader = csv.DictReader(text_stream)

            if not reader.fieldnames:
                return {}

            name_col = self._find_name_column(reader.fieldnames)
            plz_col = self._find_plz_column(reader.fieldnames)

            # Metadata columns to skip
            skip_columns = [
                "name", "handwerker", "craftsman", "priority", "priorit",
                "notes", "note", "bemerkung", "comment", "kontakt",
                "email", "phone", "telefon", "mobile", "adresse", "address",
                "summe", "kompetenz", "sprache", "pikkett", "ansprechperson"
            ]

            for row_idx, row in enumerate(reader):
                if self._is_metadata_row(row):
                    continue

                name = row.get(name_col, "").strip() if name_col else None
                if not name:
                    continue

                # Extract service areas (PLZ or addresses)
                service_areas = []
                if plz_col:
                    plz_value = row.get(plz_col, "").strip()
                    if plz_value:
                        service_areas = self._parse_service_areas(plz_value)

                # Extract categories (columns marked as TRUE/X/✓)
                categories = []
                for col, value in row.items():
                    if not col:  # Skip empty column names
                        continue
                    # Skip metadata and name columns
                    if col == name_col or not value:
                        continue
                    if any(skip.lower() in col.lower() for skip in skip_columns):
                        continue

                    cell_value = str(value).strip().upper()
                    # Check for truthy values
                    if cell_value in ["TRUE", "1", "X", "✓", "WAHR"]:
                        categories.append(col)

                if categories or service_areas:
                    # If craftsman already exists, accumulate service areas
                    if name in craftsmen:
                        # Add new service areas (avoid duplicates)
                        existing_areas = set(craftsmen[name].service_areas_plz)
                        existing_areas.update(service_areas)
                        # Merge categories (avoid duplicates)
                        existing_cats = set(craftsmen[name].categories)
                        existing_cats.update(categories)
                        craftsmen[name] = Craftsman(
                            name=name,
                            categories=list(existing_cats),
                            service_areas_plz=list(existing_areas)
                        )
                    else:
                        craftsmen[name] = Craftsman(
                            name=name,
                            categories=categories,
                            service_areas_plz=service_areas
                        )

            return craftsmen
        except Exception as e:
            print(f"Error reading craftsmen.csv: {e}")
            raise


# ============================================================================
# ANALYSIS ENGINE
# ============================================================================

class CraftsmanCoverageAnalyzer:
    """Analyzes craftsman coverage for properties."""

    def __init__(
        self,
        properties: List[str],
        categories: List[str],
        craftsmen: Dict[str, Craftsman],
    ):
        """
        Initialize the analyzer.

        Args:
            properties: List of property addresses
            categories: List of craftsman categories
            craftsmen: Dictionary mapping craftsman name to Craftsman object
        """
        self.properties = properties
        self.categories = categories
        self.craftsmen = craftsmen

    def extract_plz_from_address(self, property_address: str) -> Optional[str]:
        """
        Extract PLZ from property address.

        Looks for German postal codes (5-digit numbers) in the address.

        Args:
            property_address: Property address string

        Returns:
            PLZ code if found, None otherwise
        """
        # Simple extraction - look for 5-digit number
        import re
        match = re.search(r'\b\d{4}\b|\b\d{5}\b', property_address)
        if match:
            return match.group(0)
        return None

    def extract_street_name(self, property_address: str) -> str:
        """
        Extract street name from property address.

        Args:
            property_address: Property address string

        Returns:
            Street name
        """
        parts = property_address.rsplit(" ", 1)
        return parts[0] if parts else property_address

    def extract_apartment_numbers(self, address_str: str) -> List[str]:
        """
        Extract individual apartment/house numbers from address string.

        Handles formats like:
        - "Rautihalde 1/3/5" -> ["1", "3", "5"]
        - "Rautihalde 1-5" -> ["1", "5"]
        - "Rautihalde 1" -> ["1"]

        Excludes PLZ codes (4-5 digit numbers) to avoid false matches.

        Args:
            address_str: Address string potentially containing apartment numbers

        Returns:
            List of apartment numbers found
        """
        import re
        numbers = []

        # Find all number sequences
        matches = re.findall(r'(\d+(?:/\d+)*)', address_str)
        for match in matches:
            # Split by slash and add all numbers
            parts = match.split('/')
            for num in parts:
                # Skip PLZ codes (4-5 digit numbers that stand alone)
                # Apartment numbers are typically 1-3 digits
                if len(num) <= 3:
                    numbers.append(num)

        return list(set(numbers))  # Remove duplicates

    def normalize_street_name(self, street: str) -> str:
        """
        Normalize street name to handle abbreviations and spacing.

        Handles: Calandastrasse vs Calandastr., Badenerstr. vs Badenerstr, spaces, etc.

        Args:
            street: Street name to normalize

        Returns:
            Normalized street name
        """
        import re
        # Normalize common German street suffixes
        normalized = street.lower().strip()
        # Remove periods and extra spaces
        normalized = re.sub(r'\.', '', normalized)
        normalized = re.sub(r'\s+', '', normalized)  # Remove all spaces
        # Replace full forms with abbreviations
        # "strasse" or "straße" → "str" (even in compound words like calandastrasse)
        normalized = re.sub(r'strasse$|straße$', 'str', normalized)
        return normalized

    def find_craftsmen_for_property_and_category(
        self, property_address: str, category: str
    ) -> List[str]:
        """
        Find all craftsmen that serve this property and category.

        Matches based on:
        1. Full explicit address match (e.g., "Main Street 101" in service area)
        2. Same street with matching property number (e.g., property "71" in "St. 65/67/69/71")
        3. Normalized street match with property number (handles abbreviations)

        Args:
            property_address: Property address (e.g., "Calandastrasse 16 8048")
            category: Craftsman category

        Returns:
            List of craftsmen names that can serve this property/category
        """
        import re

        street_name = self.extract_street_name(property_address)  # "Calandastrasse 16"
        property_numbers = self.extract_apartment_numbers(property_address)  # ["16"]
        matching_craftsmen = []

        for craftsman_name, craftsman in self.craftsmen.items():
            # Check if craftsman specializes in this category
            if category not in craftsman.categories:
                continue

            # Check if craftsman serves this property
            serves_property = False

            if not craftsman.service_areas_plz:
                # No service area restriction - serves everywhere
                serves_property = True
            else:
                # Check service areas
                for service_area in craftsman.service_areas_plz:
                    # PRIORITY 1: Exact explicit address match
                    # E.g., "Calandastrasse 16" exactly in service area
                    if street_name in service_area or service_area in street_name:
                        serves_property = True
                        break

                    # PRIORITY 2: Same street with matching property number
                    # Extract just the street name (without any numbers)
                    property_street_only = re.sub(r'\s+\d+.*$', '', street_name).strip()

                    # Try each street segment in the service area
                    # Handle multi-street formats like "Baslerstr. 127/129/131/133 / Calandastr. 16/18"
                    # Split on " / " first (street separator), not all "/"
                    service_segments = [s.strip() for s in service_area.split(" / ")]

                    for segment in service_segments:
                        service_street_part = segment.split("/")[0].split(",")[0].strip()
                        # Remove trailing numbers (handle "Badenerstr.717" and "Badenerstr. 717")
                        service_street_only = re.sub(r'[\s.]*\d+.*$', '', service_street_part).strip()

                        # Try exact match first
                        street_match = (
                            service_street_only.lower() == property_street_only.lower()
                        )

                        # If no exact match, try normalized match (handles abbreviations)
                        if not street_match:
                            normalized_property = self.normalize_street_name(property_street_only)
                            normalized_service = self.normalize_street_name(service_street_only)
                            street_match = (normalized_property == normalized_service)

                        if street_match and property_numbers:
                            # Extract all property numbers from this segment
                            service_numbers = self.extract_apartment_numbers(segment)
                            # Check if property number is in service area numbers
                            if service_numbers and any(pn in service_numbers for pn in property_numbers):
                                serves_property = True
                                break

                    if serves_property:
                        break

            if serves_property:
                matching_craftsmen.append(craftsman_name)

        return matching_craftsmen

    def analyze_property(self, property_address: str) -> PropertyCoverageAnalysis:
        """
        Analyze coverage for a single property.

        Args:
            property_address: Property address

        Returns:
            PropertyCoverageAnalysis object with coverage details
        """
        gaps = []
        covered_count = 0

        for category in self.categories:
            craftsmen = self.find_craftsmen_for_property_and_category(
                property_address, category
            )

            if not craftsmen:
                gaps.append(
                    CoverageCategoryGap(
                        category=category, responsible_craftsmen=[]
                    )
                )
            else:
                covered_count += 1

        coverage_percentage = (
            covered_count / len(self.categories) * 100
            if self.categories
            else 0
        )

        return PropertyCoverageAnalysis(
            property_name=property_address,
            total_categories=len(self.categories),
            covered_categories=covered_count,
            coverage_percentage=coverage_percentage,
            gaps=gaps,
        )

    def analyze_all_properties(self) -> List[PropertyCoverageAnalysis]:
        """
        Analyze coverage for all properties.

        Returns:
            List of PropertyCoverageAnalysis objects
        """
        return [self.analyze_property(prop) for prop in self.properties]

    def find_missing_properties(self) -> Dict[str, List[str]]:
        """
        Find addresses that craftsmen serve but aren't in the properties list.

        Returns:
            Dictionary mapping address to list of craftsmen that serve it
        """
        missing_by_address = {}

        for craftsman_name, craftsman in self.craftsmen.items():
            if not craftsman.service_areas_plz:
                continue

            for service_area in craftsman.service_areas_plz:
                # Check if this service area matches any property
                area_matches_property = False

                for prop in self.properties:
                    # Try all three matching priorities used in coverage analysis
                    prop_street = self.extract_street_name(prop)

                    # Priority 1: Explicit address match
                    if prop_street in service_area or service_area in prop_street:
                        area_matches_property = True
                        break

                    # Priority 2: Apartment number match
                    if not area_matches_property:
                        prop_numbers = self.extract_apartment_numbers(prop)
                        area_numbers = self.extract_apartment_numbers(service_area)
                        if prop_numbers and area_numbers and any(
                            pn in area_numbers for pn in prop_numbers
                        ):
                            area_matches_property = True
                            break

                    # Priority 3: Full address match
                    if not area_matches_property:
                        if (prop in service_area or prop.strip() in service_area or
                            service_area in prop):
                            area_matches_property = True
                            break

                # If service area is a complete address (not just a PLZ), add to missing
                if not area_matches_property:
                    # Only include if it looks like an address (contains street name or numbers)
                    service_lower = service_area.lower().strip()
                    # Check if it's NOT just a PLZ code
                    is_just_plz = len(service_lower) <= 5 and service_lower.isdigit()

                    if not is_just_plz:
                        # Add this craftsman to the missing address
                        if service_area not in missing_by_address:
                            missing_by_address[service_area] = []
                        missing_by_address[service_area].append(craftsman_name)

        # Sort craftsmen names for each address
        for address in missing_by_address:
            missing_by_address[address] = sorted(missing_by_address[address])

        return missing_by_address

    def find_unmatched_service_areas(self) -> Dict[str, List[str]]:
        """
        Find service areas in craftsmen that don't match any property.

        Returns:
            Dictionary mapping service area to list of craftsmen that serve it
        """
        # First pass: find all unmatched service areas and which craftsmen serve them
        unmatched_by_area = {}

        for craftsman_name, craftsman in self.craftsmen.items():
            if not craftsman.service_areas_plz:
                continue

            for service_area in craftsman.service_areas_plz:
                # Check if this service area matches any property
                area_matches_property = False

                for prop in self.properties:
                    # Try all three matching priorities used in coverage analysis
                    prop_street = self.extract_street_name(prop)

                    # Priority 1: Explicit address match
                    if prop_street in service_area or service_area in prop_street:
                        area_matches_property = True
                        break

                    # Priority 2: Apartment number match
                    if not area_matches_property:
                        prop_numbers = self.extract_apartment_numbers(prop)
                        area_numbers = self.extract_apartment_numbers(service_area)
                        if prop_numbers and area_numbers and any(
                            pn in area_numbers for pn in prop_numbers
                        ):
                            area_matches_property = True
                            break

                    # Priority 3: Full address match
                    if not area_matches_property:
                        if (prop in service_area or prop.strip() in service_area or
                            service_area in prop):
                            area_matches_property = True
                            break

                if not area_matches_property:
                    # Add this craftsman to the unmatched service area
                    if service_area not in unmatched_by_area:
                        unmatched_by_area[service_area] = []
                    unmatched_by_area[service_area].append(craftsman_name)

        # Sort craftsmen names for each service area
        for service_area in unmatched_by_area:
            unmatched_by_area[service_area] = sorted(unmatched_by_area[service_area])

        return unmatched_by_area

    def generate_summary(
        self, analyses: List[PropertyCoverageAnalysis], source_name: str
    ) -> CoverageSummary:
        """
        Generate summary statistics.

        Args:
            analyses: List of PropertyCoverageAnalysis objects
            source_name: Name of the data source

        Returns:
            CoverageSummary object with aggregate statistics
        """
        properties_with_gaps = sum(1 for a in analyses if a.has_gaps())
        total_gaps = sum(a.get_gap_count() for a in analyses)
        avg_coverage = (
            sum(a.coverage_percentage for a in analyses) / len(analyses)
            if analyses
            else 0
        )

        # Find categories with lowest coverage
        category_gap_count = {}
        for analysis in analyses:
            for gap in analysis.gaps:
                category_gap_count[gap.category] = (
                    category_gap_count.get(gap.category, 0) + 1
                )

        lowest_coverage = dict(
            sorted(
                category_gap_count.items(), key=lambda x: x[1], reverse=True
            )[:5]
        )

        return CoverageSummary(
            total_properties=len(analyses),
            properties_with_gaps=properties_with_gaps,
            properties_with_full_coverage=len(analyses) - properties_with_gaps,
            total_gaps_across_all_properties=total_gaps,
            average_coverage_percentage=avg_coverage,
            categories_with_lowest_coverage=lowest_coverage,
            data_source=source_name,
        )


# ============================================================================
# OUTPUT GENERATORS
# ============================================================================

class ReportGenerator:
    """Generates reports in various formats."""

    @staticmethod
    def generate_json_report(
        analyses: List[PropertyCoverageAnalysis],
        summary: CoverageSummary,
        unmatched_areas: Dict[str, List[str]] = None,
        missing_properties: Dict[str, List[str]] = None,
    ) -> str:
        """
        Generate JSON report.

        Args:
            analyses: List of PropertyCoverageAnalysis objects
            summary: CoverageSummary object
            unmatched_areas: Dictionary of unmatched service areas
            missing_properties: Dictionary of addresses craftsmen serve but not in properties list

        Returns:
            JSON string
        """
        report = {
            "metadata": {
                "data_source": summary.data_source,
                "generated_date": __import__('datetime').datetime.now().isoformat(),
            },
            "summary": {
                "total_properties": summary.total_properties,
                "properties_with_gaps": summary.properties_with_gaps,
                "properties_with_full_coverage": (
                    summary.properties_with_full_coverage
                ),
                "total_gaps_across_all_properties": (
                    summary.total_gaps_across_all_properties
                ),
                "average_coverage_percentage": round(
                    summary.average_coverage_percentage, 2
                ),
                "categories_with_lowest_coverage": (
                    summary.categories_with_lowest_coverage
                ),
            },
            "properties": [
                {
                    "property_name": analysis.property_name,
                    "total_categories": analysis.total_categories,
                    "covered_categories": analysis.covered_categories,
                    "coverage_percentage": round(
                        analysis.coverage_percentage, 2
                    ),
                    "has_gaps": analysis.has_gaps(),
                    "gaps": [
                        {
                            "category": gap.category,
                            "responsible_craftsmen": (
                                gap.responsible_craftsmen
                            ),
                        }
                        for gap in analysis.gaps
                    ],
                }
                for analysis in sorted(analyses, key=lambda x: x.property_name)
            ],
            "unmatched_service_areas": unmatched_areas or {},
            "missing_properties": missing_properties or {},
        }
        return json.dumps(report, indent=2, ensure_ascii=False)

    @staticmethod
    def generate_csv_report(
        analyses: List[PropertyCoverageAnalysis],
    ) -> str:
        """
        Generate CSV report with one row per gap.

        Args:
            analyses: List of PropertyCoverageAnalysis objects

        Returns:
            CSV string
        """
        output = []
        output.append(
            "Property,Coverage %,Total Categories,Covered Categories,Missing Category"
        )

        for analysis in sorted(analyses, key=lambda x: x.property_name):
            if analysis.has_gaps():
                for gap in analysis.gaps:
                    output.append(
                        f'"{analysis.property_name}",{round(analysis.coverage_percentage, 2)},{analysis.total_categories},{analysis.covered_categories},"{gap.category}"'
                    )
            else:
                output.append(
                    f'"{analysis.property_name}",{round(analysis.coverage_percentage, 2)},{analysis.total_categories},{analysis.covered_categories},Full Coverage'
                )

        return "\n".join(output)

    @staticmethod
    def generate_text_report(
        analyses: List[PropertyCoverageAnalysis],
        summary: CoverageSummary,
        unmatched_areas: Dict[str, List[str]] = None,
        missing_properties: Dict[str, List[str]] = None,
    ) -> str:
        """
        Generate human-readable text report.

        Args:
            analyses: List of PropertyCoverageAnalysis objects
            summary: CoverageSummary object
            unmatched_areas: Dictionary of unmatched service areas
            missing_properties: Dictionary of addresses craftsmen serve but not in properties list

        Returns:
            Formatted text report
        """
        lines = []
        lines.append("=" * 80)
        lines.append("CRAFTSMAN COVERAGE ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Data source information
        lines.append(f"Data Source: {summary.data_source}")
        lines.append("")

        # Summary section
        lines.append("SUMMARY STATISTICS")
        lines.append("-" * 80)
        lines.append(
            f"Total Properties: {summary.total_properties}"
        )
        lines.append(
            f"Properties with Full Coverage: {summary.properties_with_full_coverage}"
        )
        lines.append(
            f"Properties with Gaps: {summary.properties_with_gaps}"
        )
        lines.append(
            f"Total Gaps Across All Properties: {summary.total_gaps_across_all_properties}"
        )
        lines.append(
            f"Average Coverage: {round(summary.average_coverage_percentage, 2)}%"
        )
        lines.append("")

        if summary.categories_with_lowest_coverage:
            lines.append("Categories with Lowest Coverage:")
            for category, count in (
                summary.categories_with_lowest_coverage.items()
            ):
                lines.append(f"  - {category}: Missing in {count} properties")
            lines.append("")

        # Detailed property analysis
        lines.append("DETAILED PROPERTY ANALYSIS")
        lines.append("-" * 80)

        properties_with_gaps = sorted(
            [a for a in analyses if a.has_gaps()],
            key=lambda x: x.property_name
        )
        properties_with_full_coverage = sorted(
            [a for a in analyses if not a.has_gaps()],
            key=lambda x: x.property_name
        )

        if properties_with_gaps:
            lines.append("\nPROPERTIES WITH COVERAGE GAPS:")
            lines.append("")
            for analysis in properties_with_gaps:
                lines.append(
                    f"Property: {analysis.property_name}"
                )
                lines.append(
                    f"  Coverage: {analysis.covered_categories}/{analysis.total_categories} categories ({round(analysis.coverage_percentage, 2)}%)"
                )
                lines.append(
                    f"  Missing Categories ({len(analysis.gaps)}):"
                )
                for gap in analysis.gaps:
                    lines.append(f"    - {gap.category}")
                lines.append("")

        if properties_with_full_coverage:
            lines.append("\nPROPERTIES WITH FULL COVERAGE:")
            lines.append("")
            for analysis in properties_with_full_coverage:
                lines.append(f"  - {analysis.property_name}")
            lines.append("")

        # Unmatched service areas
        if unmatched_areas:
            lines.append("\nUNMATCHED CRAFTSMAN SERVICE AREAS:")
            lines.append("(Service areas that don't match any property)")
            lines.append("-" * 80)
            for service_area in sorted(unmatched_areas.keys()):
                craftsmen = unmatched_areas[service_area]
                lines.append(f"\nService Area: {service_area}")
                lines.append(f"  Craftsmen serving this area: {len(craftsmen)}")
                for craftsman_name in craftsmen:
                    lines.append(f"    - {craftsman_name}")
            lines.append("")

        # Missing properties (addresses craftsmen serve but not in properties list)
        if missing_properties:
            lines.append("\nMISSING PROPERTIES:")
            lines.append("(Addresses with craftsmen assigned but not in properties list)")
            lines.append("-" * 80)
            for address in sorted(missing_properties.keys()):
                craftsmen = missing_properties[address]
                lines.append(f"\nAddress: {address}")
                lines.append(f"  Craftsmen serving this address: {len(craftsmen)}")
                for craftsman_name in craftsmen:
                    lines.append(f"    - {craftsman_name}")
            lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function."""
    print("=" * 80)
    print("DYNAMIC CRAFTSMAN COVERAGE ANALYZER")
    print("=" * 80)
    print("")

    # Try different data sources in order
    data_source = None

    # 1. Try CSV files first
    print("Checking for CSV files in input/ folder...")
    csv_source = CSVDataSource("input")
    if csv_source.is_available():
        print("Found CSV files!")
        data_source = csv_source
    else:
        print("No CSV files found in input/ folder.")
        print("")

        # 2. Try Google Sheets
        print("Attempting to load data from Google Sheets...")
        SHEET_ID = "10zosC8dEj0qj6waVjRc_Gx1cSpxUlcMZz783SyW3N5s"
        PROPERTY_GID = 1124098260
        CRAFTSMAN_GID = 1542074825

        gs_source = GoogleSheetsDataSource(
            sheet_id=SHEET_ID,
            property_gid=PROPERTY_GID,
            craftsman_gid=CRAFTSMAN_GID,
        )

        if gs_source.is_available():
            print("Connected to Google Sheets!")
            data_source = gs_source
        else:
            print("Warning: Google Sheets API not configured.")
            print("Falling back to static sample data.")
            print("")
            print("To use your own data:")
            print("  Option 1 - CSV files (no setup needed):")
            print("    1. Edit input/properties.csv and input/craftsmen.csv")
            print("    2. Run this script again")
            print("")
            print("  Option 2 - Google Sheets:")
            print("    1. See SETUP_GOOGLE_SHEETS.md for configuration")
            print("    2. Create credentials.json file")
            print("    3. Run this script again")
            print("")
            data_source = StaticDataSource()

    print(f"Data Source: {data_source.get_source_name()}")
    print("")

    try:
        # Fetch data
        print("Fetching properties...")
        properties = data_source.fetch_properties()
        print(f"  Found {len(properties)} properties")

        print("Fetching craftsmen and categories...")
        craftsmen = data_source.fetch_craftsmen()
        categories = data_source.fetch_categories()
        print(f"  Found {len(craftsmen)} craftsmen")
        print(f"  Found {len(categories)} categories")
        print("")

        # Create analyzer
        print("Initializing analyzer...")
        analyzer = CraftsmanCoverageAnalyzer(
            properties=properties,
            categories=categories,
            craftsmen=craftsmen,
        )

        # Perform analysis
        print("Analyzing coverage for all properties...")
        analyses = analyzer.analyze_all_properties()
        summary = analyzer.generate_summary(analyses, data_source.get_source_name())

        # Find unmatched service areas
        unmatched_areas = analyzer.find_unmatched_service_areas()

        # Find missing properties (addresses craftsmen serve but not in properties list)
        missing_properties = analyzer.find_missing_properties()
        print("Analysis complete!")
        print("")

        # Generate reports
        print("Generating reports...")

        # Create output folder if it doesn't exist
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        # Generate timestamp for unique report names
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Text report
        text_report = ReportGenerator.generate_text_report(
            analyses, summary, unmatched_areas, missing_properties
        )
        print(text_report)

        # Save JSON report
        json_report = ReportGenerator.generate_json_report(
            analyses, summary, unmatched_areas, missing_properties
        )
        json_path = output_dir / f"craftsman_coverage_report_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json_report)
        print(f"JSON report saved to: {json_path}")

        # Save CSV report
        csv_report = ReportGenerator.generate_csv_report(analyses)
        csv_path = output_dir / f"craftsman_coverage_report_{timestamp}.csv"
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(csv_report)
        print(f"CSV report saved to: {csv_path}")

        print("")
        print("All reports generated successfully!")

    except Exception as e:
        print(f"Error during analysis: {e}")
        print("")
        print("Make sure:")
        print("  1. You have valid credentials.json file")
        print("  2. Google Sheets API is enabled in your Google Cloud Console")
        print("  3. Sheet ID and GIDs are correct")
        print("")
        print("See SETUP_GOOGLE_SHEETS.md for detailed setup instructions.")
        sys.exit(1)


if __name__ == "__main__":
    main()
