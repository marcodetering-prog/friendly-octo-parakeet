#!/usr/bin/env python3
"""
Craftsman Coverage Analyzer

This script analyzes which craftsman categories have coverage for each property.
It identifies gaps where certain categories lack coverage and generates detailed reports.

Author: Craftsman Coverage Analysis Tool
Date: 2026-01-29
"""

import json
import csv
from dataclasses import dataclass, asdict
from typing import List, Dict, Set, Tuple
from pathlib import Path


# ============================================================================
# DATA STRUCTURES
# ============================================================================

CRAFTSMAN_CATEGORIES = [
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

PROPERTIES = [
    "Badenerstr. 727",
    "Badenerstr. 731",
    "Badenerstr. 733",
    "Im Struppen 8",
    "Im Struppen 11",
    "Im Struppen 12",
    "Im Struppen 13",
    "Im Struppen 14",
    "Im Struppen 15",
    "Im Struppen 16",
    "Im Struppen 17",
    "Im Struppen 19",
    "Im Struppen 21",
    "Meierwiesenstr. 52-58",
]


# ============================================================================
# CRAFTSMAN DATABASE
# ============================================================================

CRAFTSMEN_DATA = {
    # All-rounder/Caretaker
    "André Gonçalves": {
        "categories": ["All-rounder/Caretaker"],
        "service_areas": ["Badenerstr.", "Im Struppen"],
    },
    "Fernando Leite": {
        "categories": ["All-rounder/Caretaker"],
        "service_areas": ["Badenerstr.", "Im Struppen"],
    },
    "Luis Soares": {
        "categories": ["All-rounder/Caretaker"],
        "service_areas": ["Badenerstr.", "Im Struppen"],
    },
    "Quirino Passi": {
        "categories": ["All-rounder/Caretaker"],
        "service_areas": ["Badenerstr.", "Im Struppen"],
    },
    # Plumbing & Flooring
    "Sibir AG": {
        "categories": [
            "Sanitärleitungen (Plumbing)",
            "Bodenleger (Flooring)",
        ],
        "service_areas": ["Im Struppen", "Badenerstr."],
    },
    # Household Appliance
    "Longhitano HLKS GmbH": {
        "categories": ["Haushaltsgerätetechnik (Household Appliance)"],
        "service_areas": ["Im Struppen", "Badenerstr."],
    },
    # Locksmith & Heating
    "Peter Halter AG": {
        "categories": [
            "Schlosser (Locksmith)",
            "Heizungstechnik (Heating Technician)",
        ],
        "service_areas": ["Im Struppen", "Badenerstr."],
    },
    # Window Specialists
    "Weiss Security AG": {
        "categories": ["Fensterspezialisten (Window Specialists)"],
        "service_areas": ["Im Struppen", "Badenerstr.", "Meierwiesenstr."],
    },
    # Shutter Specialists
    "Jetzer Storen GmbH": {
        "categories": ["Rollladespezialisten (Shutter Specialists)"],
        "service_areas": ["Im Struppen", "Badenerstr.", "Meierwiesenstr."],
    },
    # Electrician
    "Elektro Müller": {
        "categories": ["Elektriker (Electrician)"],
        "service_areas": ["Im Struppen", "Badenerstr."],
    },
    # Painter
    "Malerei Schmidt": {
        "categories": ["Maler (Painter)"],
        "service_areas": ["Im Struppen", "Badenerstr."],
    },
    # Pest Control
    "Schädlingsbekämpfung Expert": {
        "categories": ["Ungeziefer (Pest Control)"],
        "service_areas": ["Im Struppen", "Badenerstr."],
    },
    # Elevator Technician
    "Ascensor Technik": {
        "categories": ["Aufzugstechnik (Elevator Technician)"],
        "service_areas": ["Im Struppen", "Badenerstr."],
    },
    # Garage Door Technician
    "Garagentor Spezialisten": {
        "categories": ["Garagentortechnik (Garage Door Technician)"],
        "service_areas": ["Im Struppen", "Badenerstr."],
    },
    # Carpenter
    "Schreinerei König": {
        "categories": ["Schreiner (Carpenter)"],
        "service_areas": ["Im Struppen", "Badenerstr."],
    },
    # Drain Cleaner
    "Rohrreinigung Schnell": {
        "categories": ["Kanalreiniger (Drain Cleaner)"],
        "service_areas": ["Im Struppen", "Badenerstr."],
    },
}


# ============================================================================
# DATA CLASSES
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


# ============================================================================
# ANALYSIS ENGINE
# ============================================================================


class CraftsmanCoverageAnalyzer:
    """Analyzes craftsman coverage for properties."""

    def __init__(
        self,
        properties: List[str],
        categories: List[str],
        craftsmen_data: Dict[str, Dict],
    ):
        """
        Initialize the analyzer.

        Args:
            properties: List of property addresses
            categories: List of craftsman categories
            craftsmen_data: Dictionary with craftsmen info
        """
        self.properties = properties
        self.categories = categories
        self.craftsmen_data = craftsmen_data

    def extract_street_name(self, property_name: str) -> str:
        """Extract street name from property address."""
        parts = property_name.rsplit(" ", 1)
        return parts[0] if parts else property_name

    def find_craftsmen_for_property_and_category(
        self, property_name: str, category: str
    ) -> List[str]:
        """
        Find all craftsmen that serve this property and category.

        Args:
            property_name: Property address
            category: Craftsman category

        Returns:
            List of craftsmen names that can serve this property/category
        """
        street_name = self.extract_street_name(property_name)
        matching_craftsmen = []

        for craftsman_name, craftsman_info in self.craftsmen_data.items():
            # Check if craftsman serves this category
            if category not in craftsman_info["categories"]:
                continue

            # Check if craftsman serves this street
            serves_street = any(
                street in street_name
                for street in craftsman_info["service_areas"]
            )

            if serves_street:
                matching_craftsmen.append(craftsman_name)

        return matching_craftsmen

    def analyze_property(self, property_name: str) -> PropertyCoverageAnalysis:
        """
        Analyze coverage for a single property.

        Args:
            property_name: Property address

        Returns:
            PropertyCoverageAnalysis object with coverage details
        """
        gaps = []
        covered_count = 0

        for category in self.categories:
            craftsmen = self.find_craftsmen_for_property_and_category(
                property_name, category
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
            property_name=property_name,
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

    def generate_summary(
        self, analyses: List[PropertyCoverageAnalysis]
    ) -> CoverageSummary:
        """
        Generate summary statistics.

        Args:
            analyses: List of PropertyCoverageAnalysis objects

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
            properties_with_full_coverage=len(analyses)
            - properties_with_gaps,
            total_gaps_across_all_properties=total_gaps,
            average_coverage_percentage=avg_coverage,
            categories_with_lowest_coverage=lowest_coverage,
        )


# ============================================================================
# OUTPUT GENERATORS
# ============================================================================


class ReportGenerator:
    """Generates reports in various formats."""

    @staticmethod
    def generate_json_report(
        analyses: List[PropertyCoverageAnalysis], summary: CoverageSummary
    ) -> str:
        """
        Generate JSON report.

        Args:
            analyses: List of PropertyCoverageAnalysis objects
            summary: CoverageSummary object

        Returns:
            JSON string
        """
        report = {
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
                for analysis in analyses
            ],
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

        for analysis in analyses:
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
        analyses: List[PropertyCoverageAnalysis], summary: CoverageSummary
    ) -> str:
        """
        Generate human-readable text report.

        Args:
            analyses: List of PropertyCoverageAnalysis objects
            summary: CoverageSummary object

        Returns:
            Formatted text report
        """
        lines = []
        lines.append("=" * 80)
        lines.append("CRAFTSMAN COVERAGE ANALYSIS REPORT")
        lines.append("=" * 80)
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

        properties_with_gaps = [a for a in analyses if a.has_gaps()]
        properties_with_full_coverage = [
            a for a in analyses if not a.has_gaps()
        ]

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

        lines.append("=" * 80)

        return "\n".join(lines)


# ============================================================================
# MAIN EXECUTION
# ============================================================================


def main():
    """Main execution function."""
    print("Initializing Craftsman Coverage Analyzer...")
    print("")

    # Create analyzer
    analyzer = CraftsmanCoverageAnalyzer(
        properties=PROPERTIES,
        categories=CRAFTSMAN_CATEGORIES,
        craftsmen_data=CRAFTSMEN_DATA,
    )

    # Perform analysis
    print("Analyzing coverage for all properties...")
    analyses = analyzer.analyze_all_properties()
    summary = analyzer.generate_summary(analyses)
    print("Analysis complete!")
    print("")

    # Generate reports
    print("Generating reports...")

    # Text report
    text_report = ReportGenerator.generate_text_report(analyses, summary)
    print(text_report)

    # Save JSON report
    json_report = ReportGenerator.generate_json_report(analyses, summary)
    json_path = Path("craftsman_coverage_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(json_report)
    print(f"JSON report saved to: {json_path}")

    # Save CSV report
    csv_report = ReportGenerator.generate_csv_report(analyses)
    csv_path = Path("craftsman_coverage_report.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(csv_report)
    print(f"CSV report saved to: {csv_path}")

    print("")
    print("All reports generated successfully!")


if __name__ == "__main__":
    main()
