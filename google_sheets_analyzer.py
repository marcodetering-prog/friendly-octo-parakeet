#!/usr/bin/env python3
"""
Craftsman Coverage Analyzer

This script analyzes which craftsman categories have coverage for each property.
It automatically:
- Reads data from CSV files (place in input/ folder)
- Detects all properties from properties.csv
- Detects all craftsmen and their specializations from craftsman.csv
- Extracts service areas and categories dynamically
- Generates detailed coverage reports

Usage:
  1. Place input/properties.csv and input/craftsman.csv in the input/ folder
  2. Run: python3 google_sheets_analyzer.py
  3. Check output/ folder for generated reports

Author: Craftsman Coverage Analysis Tool
Date: 2026-01-29
"""

import json
import csv
import os
import sys
import re
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
        Find the address/street column by keyword matching and data patterns.

        Looks for columns like: address, strasse, street, straße, etc.
        Also analyzes column content for street address patterns.
        """
        # Expanded keywords for multiple languages
        address_keywords = [
            "address", "strasse", "straße", "street", "adresse", "rue",
            "via", "calle", "straßenname", "strassenname", "street name",
            "ort", "location", "lugar", "lieu", "weg", "allee", "gasse"
        ]

        # First try keyword matching
        for header in headers:
            if any(keyword.lower() in header.lower() for keyword in address_keywords):
                return header

        # If no keyword match, try to detect by data patterns
        # Look for columns with street-like data (contains text + numbers)
        # This is implemented in fetch_properties when we analyze the data
        return None

    def _find_number_column(self, headers: List[str]) -> Optional[str]:
        """Find the house number column by keyword or data pattern."""
        number_keywords = [
            "hausnummer", "nummer", "number", "house", "nr.", "nr",
            "numero", "numéro", "n°", "no.", "houseno", "house_number",
            "häusnummer", "huisnummer", "numero_civico"
        ]
        for header in headers:
            if any(keyword.lower() in header.lower() for keyword in number_keywords):
                return header
        return None

    def _find_plz_column(self, headers: List[str]) -> Optional[str]:
        """Find the postal code column by keyword or data pattern."""
        plz_keywords = [
            "plz", "postal", "zip", "postleitzahl", "einsatzgebiet",
            "postcode", "code_postal", "postal_code", "zip_code", "postalcode",
            "ort", "city", "stadt", "gemeinde", "cap", "codice_postale",
            "código_postal", "code_postal", "cp", "cep"
        ]
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

    def _detect_column_by_data(self, filepath: str) -> Dict[str, Optional[str]]:
        """
        Detect address columns by analyzing actual data patterns.

        Returns dict with keys: 'address', 'number', 'plz', 'name'
        """
        import re
        detected = {'address': None, 'number': None, 'plz': None, 'name': None}

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                sample_rows = []

                # Collect first 5-10 data rows
                for i, row in enumerate(reader):
                    if i >= 10:
                        break
                    if row and any(row.values()):
                        sample_rows.append(row)

                if not sample_rows:
                    return detected

                # Analyze each column in sample rows
                for col in reader.fieldnames or []:
                    if not col:
                        continue

                    col_values = [str(row.get(col, "")).strip() for row in sample_rows if row.get(col)]

                    # Skip mostly empty columns
                    if len(col_values) < len(sample_rows) / 2:
                        continue

                    # Detect address column: contains text + street-like words + variety
                    has_letters = any(any(c.isalpha() for c in v) for v in col_values)
                    has_streets = any(
                        keyword in v.lower()
                        for v in col_values
                        for keyword in ["str", "weg", "allee", "gasse", "ring", "strasse", "avenue"]
                    )
                    if has_letters and (has_streets or detected['address'] is None):
                        if detected['address'] is None or has_streets:
                            detected['address'] = col

                    # Detect number column: mostly digits/ranges
                    has_numbers = sum(1 for v in col_values if any(c.isdigit() for c in v)) / len(col_values) > 0.7
                    is_mostly_short = sum(1 for v in col_values if len(v) <= 5) / len(col_values) > 0.8
                    if has_numbers and is_mostly_short and not any(c.isalpha() for v in col_values for c in v):
                        if detected['number'] is None:
                            detected['number'] = col

                    # Detect PLZ column: 4-5 digit postal codes
                    is_plz = sum(1 for v in col_values if re.match(r'^\d{4,5}$', v)) / len(col_values) > 0.8
                    if is_plz:
                        detected['plz'] = col

                    # Detect name column: longer text, no numbers, no special patterns
                    is_long_text = sum(1 for v in col_values if len(v) > 10) / len(col_values) > 0.5
                    no_numbers = sum(1 for v in col_values if not any(c.isdigit() for c in v)) / len(col_values) > 0.7
                    if is_long_text and no_numbers and detected['name'] is None:
                        detected['name'] = col

        except Exception:
            pass

        return detected

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

            # Find columns by keyword matching first
            address_col = self._find_address_column(reader.fieldnames)
            number_col = self._find_number_column(reader.fieldnames)
            plz_col = self._find_plz_column(reader.fieldnames)

            # If keyword matching didn't find columns, try data-driven detection
            if not address_col or not number_col or not plz_col:
                detected = self._detect_column_by_data(str(self.properties_file))
                if not address_col and detected['address']:
                    address_col = detected['address']
                if not number_col and detected['number']:
                    number_col = detected['number']
                if not plz_col and detected['plz']:
                    plz_col = detected['plz']

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
# ADAPTIVE ADDRESS PARSER
# ============================================================================

class FormatLearner:
    """Learns number separators from service areas for format-agnostic extraction."""

    def __init__(self):
        """Initialize with empty separator patterns."""
        self.number_separators = {}

    def learn_from_service_areas(self, service_areas: List[str]) -> None:
        """Learn number separators from all service areas."""
        for area in service_areas:
            # Find sequences of numbers and what separates them
            number_sequences = re.findall(r'(\d+(?:[^\d\w]+\d+)*)', area)
            for seq in number_sequences:
                # Detect separators between numbers
                separators = re.findall(r'\d+([^\d\w]+)(?=\d)', seq)
                for sep in separators:
                    self.number_separators[sep] = self.number_separators.get(sep, 0) + 1

    def extract_numbers(self, text: str) -> List[str]:
        """Extract apartment numbers using learned patterns with fallback."""
        # Try range pattern first (handles 1-13, 1 - 13, 1–13, etc.)
        range_match = re.search(r'(\d+)\s*[-–—]\s*(\d+)', text)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            return [str(n) for n in range(start, end + 1)]

        # PRIORITY: Try '/' first (apartment number separator within an address)
        # e.g., "Holeoholzweg 61/63/65/67" - we want all four numbers
        if '/' in text:
            numbers = []
            for part in re.split(r'/', text):
                # Extract ALL numbers from each part (not just the first one)
                matches = re.findall(r'(\d+)', part)
                for match in matches:
                    if len(match) <= 3:
                        numbers.append(match)
            if numbers:
                return list(set(numbers))

        # Try other learned separators (sorted by frequency)
        for separator, _ in sorted(self.number_separators.items(), key=lambda x: x[1], reverse=True):
            if separator in text and separator != '/':  # Skip '/' since we already tried it
                numbers = []
                for part in re.split(re.escape(separator), text):
                    match = re.search(r'(\d+)', part)
                    if match and len(match.group(1)) <= 3:
                        numbers.append(match.group(1))
                if numbers:
                    return list(set(numbers))

        # Generic fallback: all numbers <= 3 digits
        return list(set(n for n in re.findall(r'(\d+)', text) if len(n) <= 3))


class AdaptiveTokenizer:
    """Breaks service areas into meaningful tokens."""

    def __init__(self, format_learner: Optional['FormatLearner'] = None):
        """Initialize with optional format learner."""
        self.format_learner = format_learner or FormatLearner()

    def tokenize(self, text: str) -> List[Dict]:
        """
        Tokenize a service area string into meaningful tokens.

        Returns list of tokens with their types and values.
        """
        if not text or not text.strip():
            return []

        tokens = []
        parts = []

        # Split by " / " then by comma
        for segment in text.split(" / "):
            for subsegment in segment.split(","):
                subsegment = subsegment.strip()
                if subsegment:
                    parts.append(subsegment)

        for part in parts:
            tokens.extend(self._tokenize_part(part))

        return tokens

    def _tokenize_part(self, part: str) -> List[Dict]:
        """Tokenize a single part (street or numbers)."""
        tokens = []

        # Pure number range like "1/3/5"
        if "/" in part and not any(c.isalpha() for c in part.split("/")[0]):
            for num in part.split("/"):
                if num.strip().isdigit():
                    tokens.append({"type": "NUMBER", "value": num.strip()})
        else:
            # Mixed content: street with numbers or just street
            match = re.match(r'^(.*?)[\s.]*(\d+.*)$', part)
            if match:
                street_part = match.group(1).strip()
                if street_part:
                    tokens.append({"type": "STREET", "value": street_part})
                for num in self.format_learner.extract_numbers(match.group(2)):
                    tokens.append({"type": "NUMBER", "value": num})
            elif part:
                if re.match(r'^\d{4,5}\s+', part):
                    tokens.append({"type": "POSTAL", "value": part})
                elif re.match(r'^[A-Z]', part):
                    tokens.append({"type": "CITY", "value": part})
                else:
                    tokens.append({"type": "STREET", "value": part})

        return tokens


class SegmentParser:
    """Extracts meaning from individual segments."""

    def __init__(self, format_learner: Optional['FormatLearner'] = None):
        """Initialize with optional format learner."""
        self.format_learner = format_learner or FormatLearner()

    def parse_segment(self, segment: str) -> Dict:
        """
        Parse a service area segment.

        Returns dict with classification and confidence.
        """
        segment = segment.strip()
        if not segment:
            return {"type": "UNKNOWN", "value": segment, "confidence": 0.0}

        # Postal code pattern: 4-5 digits + city
        if re.match(r'^\d{4,5}\s+[A-Z]', segment):
            return {"type": "POSTAL_CODE", "value": segment, "confidence": 0.95}

        # Pure number
        if re.match(r'^\d+$', segment):
            return {"type": "NUMBER", "value": int(segment), "confidence": 0.9}

        # Street name (has letters and possibly numbers)
        if any(c.isalpha() for c in segment):
            # Extract street and any attached numbers
            match = re.match(r'^(.*?)[\s.]*(\d+.*)$', segment)
            if match:
                street = match.group(1).strip()
                numbers_part = match.group(2)
                numbers = self._extract_numbers(numbers_part)
                return {
                    "type": "STREET",
                    "street": street,
                    "numbers": numbers,
                    "confidence": 0.85
                }
            else:
                return {
                    "type": "STREET",
                    "street": segment,
                    "numbers": [],
                    "confidence": 0.8
                }

        return {"type": "UNKNOWN", "value": segment, "confidence": 0.0}

    def _extract_numbers(self, part: str) -> List[str]:
        """Extract numbers from a mixed content part using learned patterns."""
        return self.format_learner.extract_numbers(part)


class AdaptiveMatcher:
    """Matches properties to service areas intelligently with learned patterns."""

    def __init__(self, format_learner: Optional['FormatLearner'] = None):
        """Initialize the adaptive matcher."""
        self.format_learner = format_learner or FormatLearner()
        self.tokenizer = AdaptiveTokenizer(self.format_learner)
        self.parser = SegmentParser(self.format_learner)

    def extract_patterns(self, service_areas: List[str]) -> None:
        """Learn separators and patterns from all service areas."""
        self.format_learner.learn_from_service_areas(service_areas)

    def _detect_format(self, area: str) -> str:
        """Detect the format of a service area."""
        if " / " in area and not re.search(r'^\d', area.split(" / ")[0]):
            if all(re.match(r'^\d+', part.strip()) for part in area.split(" / ")[1:]):
                return "multi_property_range"
            else:
                return "multi_street"
        elif "," in area:
            return "comma_separated"
        else:
            return "simple"

    def match_property(self, property_address: str, service_area: str) -> Dict:
        """
        Match property to service area using learned patterns.

        Returns dict with match result and confidence.
        """
        # Extract property info
        prop_tokens = self.tokenizer.tokenize(property_address)
        prop_street = self._extract_street_from_tokens(prop_tokens)
        prop_numbers = self._extract_numbers_from_tokens(prop_tokens)

        # Parse service area
        area_format = self._detect_format(service_area)
        parsed = self._parse_by_format(service_area, area_format)

        # Try matching
        for parsed_segment in parsed:
            if self._streets_match(prop_street, parsed_segment.get("street", "")):
                service_numbers = parsed_segment.get("numbers", [])
                if service_numbers and prop_numbers:
                    if any(pn in service_numbers for pn in prop_numbers):
                        return {
                            "matched": True,
                            "confidence": 0.9,
                            "reason": "street_and_number_match",
                            "matched_by": "adaptive_parser"
                        }

        return {
            "matched": False,
            "confidence": 0.0,
            "reason": "no_match",
            "matched_by": "adaptive_parser"
        }

    def _extract_street_from_tokens(self, tokens: List[Dict]) -> str:
        """Extract street name from tokens."""
        for token in tokens:
            if token.get("type") == "STREET":
                return token.get("value", "")
        return ""

    def _extract_numbers_from_tokens(self, tokens: List[Dict]) -> List[str]:
        """Extract numbers from tokens."""
        numbers = []
        for token in tokens:
            if token.get("type") == "NUMBER":
                numbers.append(str(token.get("value", "")))
        return numbers

    def _parse_by_format(self, area: str, format_type: str) -> List[Dict]:
        """Parse service area according to detected format."""
        parsed = []

        if format_type == "multi_property_range":
            # "Street 65 / 67 / 69 / 71" format
            segments = area.split(" / ")
            last_street = None

            for segment in segments:
                segment = segment.strip()
                parsed_seg = self.parser.parse_segment(segment)

                if parsed_seg["type"] == "STREET":
                    last_street = parsed_seg.get("street", "")
                    numbers = parsed_seg.get("numbers", [])
                elif parsed_seg["type"] == "NUMBER":
                    if last_street:
                        parsed.append({
                            "street": last_street,
                            "numbers": [str(parsed_seg["value"])]
                        })
                    else:
                        parsed.append({
                            "street": "",
                            "numbers": [str(parsed_seg["value"])]
                        })

        elif format_type == "multi_street":
            # "Street1 nums / Street2 nums" format
            segments = area.split(" / ")
            for segment in segments:
                segment = segment.strip()
                parsed_seg = self.parser.parse_segment(segment)
                if parsed_seg["type"] == "STREET":
                    parsed.append({
                        "street": parsed_seg.get("street", ""),
                        "numbers": parsed_seg.get("numbers", [])
                    })

        elif format_type == "comma_separated":
            # Can be either:
            # 1. Single street with multiple numbers: "Street 1, 2, 3, 4, City"
            # 2. Multiple streets: "Street1 nums, Street2 nums, City"
            parts = area.split(",")
            street = None
            numbers = []

            for part in parts:
                part = part.strip()
                parsed_part = self.parser.parse_segment(part)

                if parsed_part["type"] == "STREET":
                    # If we have a previous street with numbers, save it first
                    if street and numbers:
                        parsed.append({"street": street, "numbers": numbers})
                        numbers = []

                    street = parsed_part.get("street", "")
                    # Check if this segment also has numbers
                    segment_numbers = parsed_part.get("numbers", [])
                    if segment_numbers:
                        numbers.extend(segment_numbers)
                elif parsed_part["type"] == "NUMBER":
                    numbers.append(str(parsed_part["value"]))

            # Add final street + numbers if present
            if street and numbers:
                parsed.append({"street": street, "numbers": numbers})

        else:
            # Simple format
            parsed_seg = self.parser.parse_segment(area)
            if parsed_seg["type"] == "STREET":
                parsed.append({
                    "street": parsed_seg.get("street", ""),
                    "numbers": parsed_seg.get("numbers", [])
                })

        return parsed

    def _streets_match(self, street1: str, street2: str) -> bool:
        """Check if two street names match (with normalization)."""
        if not street1 or not street2:
            return False
        # Normalize both using shared utility
        norm1 = self._normalize_street(street1)
        norm2 = self._normalize_street(street2)
        return norm1 == norm2

    @staticmethod
    def _normalize_street(street: str) -> str:
        """Normalize street name: handle abbreviations, spacing, and hyphens."""
        normalized = street.lower().strip()
        normalized = re.sub(r'\.', '', normalized)  # Remove periods
        normalized = re.sub(r'\s+', '', normalized)  # Remove spaces
        normalized = re.sub(r'-', '', normalized)    # Remove hyphens (e.g., "Wille-Str" → "Willestr")
        normalized = re.sub(r'strasse$|straße$', 'str', normalized)
        return normalized


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

        # Initialize format learner and pass to adaptive matcher
        self.format_learner = FormatLearner()
        self.adaptive_matcher = AdaptiveMatcher(self.format_learner)

        # Learn patterns from service areas
        all_service_areas = []
        for craftsman in craftsmen.values():
            all_service_areas.extend(craftsman.service_areas_plz)
        if all_service_areas:
            self.adaptive_matcher.extract_patterns(all_service_areas)

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

        Uses learned patterns from service areas to handle format variations.

        Handles formats like:
        - "Rautihalde 1/3/5" -> ["1", "3", "5"]
        - "Rautihalde 1-13" -> ["1", "2", ..., "13"]
        - "Rautihalde 1 - 5" -> ["1", "2", "3", "4", "5"]
        - "Rautihalde 1" -> ["1"]
        - Any other learned separator format

        Excludes PLZ codes (4-5 digit numbers) to avoid false matches.

        Args:
            address_str: Address string potentially containing apartment numbers

        Returns:
            List of apartment numbers found
        """
        # Use format learner for adaptive number extraction
        return self.format_learner.extract_numbers(address_str)

    def normalize_street_name(self, street: str) -> str:
        """
        Normalize street name to handle abbreviations and spacing.

        Handles: Calandastrasse vs Calandastr., Badenerstr. vs Badenerstr, spaces, etc.

        Args:
            street: Street name to normalize

        Returns:
            Normalized street name
        """
        # Use shared normalization from adaptive matcher
        return AdaptiveMatcher._normalize_street(street)

    def find_craftsmen_for_property_and_category(
        self, property_address: str, category: str
    ) -> List[str]:
        """
        Find all craftsmen that serve this property and category.

        Uses adaptive number extraction that learns from all service areas.
        Street matching logic adapts to handle format variations.

        Matching priorities:
        1. No service area restriction (craftsman serves everywhere)
        2. Exact explicit address match in service area
        3. Same street with matching property number (adaptive number parsing)

        Args:
            property_address: Property address (e.g., "Calandastrasse 16 8048")
            category: Craftsman category

        Returns:
            List of craftsmen names that can serve this property/category
        """
        street_name = self.extract_street_name(property_address)
        property_numbers = self.extract_apartment_numbers(property_address)
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
                # Check each service area
                for service_area in craftsman.service_areas_plz:
                    # Normalize whitespace for multi-line service areas (e.g., from Google Sheets)
                    # Convert tab-newline sequences to " / " to preserve street boundaries
                    service_area = service_area.replace('\t\n', ' / ').replace('\t', ' ').replace('\n', ' ')

                    # PRIORITY 1: Exact explicit address match
                    if street_name in service_area or service_area in street_name:
                        serves_property = True
                        break

                    # PRIORITY 2: Street + learned number matching
                    # Extract just the street name (without any numbers)
                    property_street_only = re.sub(r'\s+\d+.*$', '', street_name).strip()

                    # Handle multi-street formats with adaptive parsing
                    # First split by " / " (space-slash-space for multi-street properties)
                    # Then split by "," (comma for comma-separated properties within a street)
                    service_segments = []
                    for main_segment in service_area.split(" / "):
                        # Further split by comma to handle addresses like "Street1 nums, Street2 nums"
                        for sub_segment in main_segment.split(","):
                            sub_segment = sub_segment.strip()
                            if sub_segment and not re.match(r'^\d{4,5}\s+', sub_segment):  # Skip postal codes
                                service_segments.append(sub_segment)

                    last_street_name = None

                    for segment in service_segments:
                        # Note: segment has already been split by " / " (with spaces)
                        # So "/" without spaces is part of apartment numbers (e.g., "153/155"), not a street separator
                        # Don't split by "/" here - let extract_apartment_numbers() handle it
                        service_street_part = segment.split(",")[0].strip()
                        service_street_only = re.sub(r'[\s.]*\d+.*$', '', service_street_part).strip()

                        if not service_street_only and last_street_name:
                            service_street_only = last_street_name
                        elif service_street_only:
                            last_street_name = service_street_only

                        # Try exact match first
                        street_match = (
                            service_street_only.lower() == property_street_only.lower()
                        ) if service_street_only else False

                        # If no exact match, try normalized match
                        if not street_match and service_street_only:
                            normalized_property = self.normalize_street_name(property_street_only)
                            normalized_service = self.normalize_street_name(service_street_only)
                            street_match = (normalized_property == normalized_service)

                        # Try prefix matching for abbreviations
                        if not street_match and service_street_only:
                            normalized_property = self.normalize_street_name(property_street_only)
                            normalized_service = self.normalize_street_name(service_street_only)
                            if len(normalized_service) >= 4 and len(normalized_property) >= 4:
                                street_match = (normalized_property.startswith(normalized_service) or
                                               normalized_service.startswith(normalized_property))

                        if street_match and property_numbers:
                                # Use adaptive number extraction
                                service_numbers = self.extract_apartment_numbers(segment)
                                if service_numbers and any(pn in service_numbers for pn in property_numbers):
                                    serves_property = True
                                    break

                        if serves_property:
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
    def generate_html_report(
        analyses: List[PropertyCoverageAnalysis],
        summary: CoverageSummary,
    ) -> str:
        """
        Generate HTML report (can be opened in Word).

        Args:
            analyses: List of PropertyCoverageAnalysis objects
            summary: CoverageSummary object

        Returns:
            HTML string
        """
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<meta charset='UTF-8'>",
            "<title>Craftsman Coverage Report</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            "h1 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }",
            "h2 { color: #555; margin-top: 30px; }",
            "table { border-collapse: collapse; width: 100%; margin: 15px 0; }",
            "th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }",
            "th { background-color: #007bff; color: white; }",
            "tr:nth-child(even) { background-color: #f9f9f9; }",
            ".summary-stat { display: inline-block; margin-right: 30px; }",
            ".stat-value { font-size: 24px; font-weight: bold; color: #007bff; }",
            ".stat-label { color: #666; }",
            ".gap-section { margin: 20px 0; padding: 15px; background-color: #fff3cd; border-left: 4px solid #ffc107; }",
            ".full-coverage { color: #28a745; font-weight: bold; }",
            ".no-coverage { color: #dc3545; font-weight: bold; }",
            "</style>",
            "</head>",
            "<body>",
            "<h1>Craftsman Coverage Analysis Report</h1>",
            f"<p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
            "<p><strong>Data Source:</strong> " + summary.data_source + "</p>",
            "<h2>Summary Statistics</h2>",
            "<div class='summary-stat'>",
            "<div class='stat-value'>" + str(summary.total_properties) + "</div>",
            "<div class='stat-label'>Total Properties</div>",
            "</div>",
            "<div class='summary-stat'>",
            "<div class='stat-value full-coverage'>" + str(summary.properties_with_full_coverage) + "</div>",
            "<div class='stat-label'>Full Coverage</div>",
            "</div>",
            "<div class='summary-stat'>",
            "<div class='stat-value no-coverage'>" + str(summary.properties_with_gaps) + "</div>",
            "<div class='stat-label'>With Gaps</div>",
            "</div>",
            "<div class='summary-stat'>",
            "<div class='stat-value'>" + f"{round(summary.average_coverage_percentage, 1)}" + "%</div>",
            "<div class='stat-label'>Average Coverage</div>",
            "</div>",
            "<br><br>",
            "<table>",
            "<tr><th>Metric</th><th>Value</th></tr>",
            "<tr><td>Total Properties</td><td>" + str(summary.total_properties) + "</td></tr>",
            "<tr><td>Properties with Full Coverage</td><td>" + str(summary.properties_with_full_coverage) + " (" + f"{round(summary.properties_with_full_coverage/summary.total_properties*100, 1)}" + "%)</td></tr>",
            "<tr><td>Properties with Gaps</td><td>" + str(summary.properties_with_gaps) + " (" + f"{round(summary.properties_with_gaps/summary.total_properties*100, 1)}" + "%)</td></tr>",
            "<tr><td>Total Gaps</td><td>" + str(summary.total_gaps_across_all_properties) + "</td></tr>",
            "<tr><td>Average Coverage</td><td>" + f"{round(summary.average_coverage_percentage, 2)}" + "%</td></tr>",
            "</table>",
            "<h2>Categories with Lowest Coverage</h2>",
            "<table>",
            "<tr><th>Category</th><th>Properties with Gaps</th></tr>",
        ]

        for category, count in summary.categories_with_lowest_coverage.items():
            html_parts.append(f"<tr><td>{category}</td><td>{count}</td></tr>")

        html_parts.extend([
            "</table>",
            "<h2>Properties with Gaps</h2>",
        ])

        gaps_found = False
        for analysis in sorted(analyses, key=lambda x: x.property_name):
            if analysis.has_gaps():
                gaps_found = True
                html_parts.append(f"<div class='gap-section'>")
                html_parts.append(f"<h3>{analysis.property_name}</h3>")
                html_parts.append(f"<p><strong>Coverage:</strong> {analysis.covered_categories}/{analysis.total_categories} categories ({round(analysis.coverage_percentage, 1)}%)</p>")
                html_parts.append("<ul>")
                for gap in analysis.gaps:
                    html_parts.append(f"<li><strong>{gap.category}</strong></li>")
                html_parts.append("</ul>")
                html_parts.append("</div>")

        if not gaps_found:
            html_parts.append("<p><em>No properties with gaps found!</em></p>")

        html_parts.extend([
            "<h2>Properties with Full Coverage</h2>",
            "<table>",
            "<tr><th>Property</th><th>Coverage</th></tr>",
        ])

        for analysis in sorted(analyses, key=lambda x: x.property_name):
            if not analysis.has_gaps():
                html_parts.append(f"<tr><td>{analysis.property_name}</td><td class='full-coverage'>100%</td></tr>")

        html_parts.extend([
            "</table>",
            "</body>",
            "</html>",
        ])

        return "\n".join(html_parts)

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

    # Try data sources in order
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
        print("To use your own data:")
        print("  1. Create CSV files in the input/ folder:")
        print("     - input/properties.csv")
        print("     - input/craftsman.csv")
        print("  2. Run this script again")
        print("")
        print("Falling back to static sample data.")
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

        # Save HTML report (can be opened in Word)
        html_report = ReportGenerator.generate_html_report(analyses, summary)
        html_path = output_dir / f"craftsman_coverage_report_{timestamp}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_report)
        print(f"HTML report saved to: {html_path}")

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
