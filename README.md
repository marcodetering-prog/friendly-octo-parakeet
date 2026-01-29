# Craftsman Coverage Analyzer

Analyzes which craftsmen/trades can serve each property based on their specializations and service areas.

## Features

✅ Format-agnostic address matching with adaptive pattern recognition
✅ Zero external dependencies (Python stdlib only)
✅ Auto-detects CSV columns by data analysis
✅ Smart street name normalization (handles abbreviations like "Strasse" vs "Str.")
✅ Multi-property range matching ("Street 65 / 67 / 69 / 71")
✅ Deduplicates properties and accumulates service areas
✅ Pre-built Docker image for one-command usage
✅ Generates detailed JSON and CSV reports

## Quick Start

### Option 1: Local Python (Recommended)

```bash
# 1. Place CSV files in input/ folder:
#    - input/properties.csv
#    - input/craftsman.csv

# 2. Run the analyzer
python3 google_sheets_analyzer.py

# 3. Check output/ folder for reports
```

### Option 2: Docker (Zero Setup)

```bash
# 1. Create input folder with CSV files
mkdir -p input output
# Place properties.csv and craftsman.csv in input/

# 2. Run pre-built Docker image
docker run --rm \
  -v $(pwd)/input:/app/input:ro \
  -v $(pwd)/output:/app/output:rw \
  ghcr.io/marcodetering-prog/friendly-octo-parakeet:latest

# 3. Check output/ folder for reports
```

Or with docker-compose:

```yaml
version: '3.8'
services:
  analyzer:
    image: ghcr.io/marcodetering-prog/friendly-octo-parakeet:latest
    volumes:
      - ./input:/app/input:ro
      - ./output:/app/output:rw
```

## CSV Format Requirements

### Properties CSV

**Required columns** (auto-detected):
- Street/Address name (examples: "Strasse", "Street", "Address")
- House number (examples: "Hausnummer", "Nr.", "Number")
- Postal code (examples: "PLZ", "Postal", "Zip")

**Example:**
```csv
Strasse,Hausnummer,PLZ
Zürcherstr.,71,8104
Im Struppen,11,8048
```

The analyzer automatically combines these into full addresses.

### Craftsmen CSV

**Required columns**:
- Name (examples: "Firmenname", "Name", "Handwerker")
- Categories as TRUE/FALSE/X/✓ columns (one column per trade)
- Service areas (examples: "Einsatzgebiet", "ServiceAreas", "PLZ")

**Example:**
```csv
Firmenname,Sanitärleistungen,Elektriker,Einsatzgebiet
Max Meier,TRUE,FALSE,"Zürcherstr. 65 / 67 / 69 / 71"
```

## Supported Address Formats

The analyzer handles all of these formats automatically:

1. **Multi-property range**: `"Zürcherstr. 65 / 67 / 69 / 71"`
2. **Multi-street addresses**: `"Badenerstr. 127/129/131/133 / Calandastr. 16/18"`
3. **Comma-separated**: `"Im Struppen 11, 12, 13, 14, 15, 16, 17, 19, 21, 8048 Zürich"`
4. **Adjacent numbers**: `"Badenerstr.717/Im Struppen 8, 8048 Zürich"`

The adaptive parser learns from data structure and supports new formats without code changes.

## How It Works

1. **Loads data** from CSV files
2. **Auto-detects columns** by analyzing headers and data patterns
3. **Combines address components** (Street + Number + PLZ)
4. **Deduplicates properties** (same address = 1 property)
5. **For each property**, checks which craftsmen can serve it:
   - Craftsman specializes in category (marked TRUE)
   - Craftsman's service area includes property address
6. **Reports** coverage percentage and gaps per property

### Address Matching Algorithm

**Priority 1: Explicit address match**
- Property: "Street 123"
- Service area contains "Street 123"
- Result: MATCH ✓

**Priority 2: Street + number in range**
- Property: "Street 71"
- Service area: "Street 65 / 67 / 69 / 71"
- Check: 71 in [65, 67, 69, 71] ✓
- Result: MATCH ✓

**Priority 3: Normalized street match with abbreviations**
- Property: "Calandastrasse 16"
- Service area: "Calandastr. 16"
- Normalize: "calandastr" == "calandastr" ✓
- Result: MATCH ✓

**Priority 4: Adaptive pattern matching**
- Uses learned format patterns for edge cases
- Fallback for new/unknown formats
- Enables format-agnostic matching

## Reports

### Console Output
- Summary statistics (total properties, coverage %, categories with gaps)
- List of properties with full coverage
- List of properties with coverage gaps
- Unmatched service areas
- Missing properties (addresses with craftsmen but not in property list)

### JSON Report (`craftsman_coverage_report_*.json`)
Machine-readable report with:
- Metadata (data source, generation date)
- Summary statistics
- Per-property analysis with gap details
- Unmatched service areas
- Missing properties

### CSV Report (`craftsman_coverage_report_*.csv`)
Spreadsheet-friendly format with one row per gap:
```
Property,Coverage %,Total Categories,Covered Categories,Missing Category
"Zürcherstr. 71 8104",100.0,15,15,Full Coverage
"Albisriederstr. 261 8047",0.0,15,0,"Allrounder/Hauswart"
```

## Troubleshooting

### No properties found
- Verify address column exists and contains addresses
- Check CSV is not empty after headers
- Look for column headers like: Strasse, Street, Address

### No craftsmen found
- Ensure name column exists (Firmenname, Name, Handwerker)
- Check category columns have TRUE/FALSE/X/✓ values
- Service areas column should be present

### Wrong address matching
- Properties combine: Street + Number + PLZ columns
- Verify these columns are detected correctly
- Check analyzer output for column detection messages

### Properties show 0% coverage but craftsmen exist
- Check if service area format is supported (see "Supported Address Formats")
- Verify address spelling matches between properties and service areas
- Street abbreviations should be handled automatically
- If issue persists, file a GitHub issue with example data

## Docker Image Tags

All images available on GitHub Container Registry:

| Tag | Availability | Use Case |
|-----|--------------|----------|
| `latest` | On every push to main | Latest stable version |
| `main` | On every push | Current main branch |
| `v1.0.0`, `v1.0`, `v1` | On version tags | Specific releases |
| `sha-abc1234` | On every commit | Specific commit |

Pull latest version:
```bash
docker pull ghcr.io/marcodetering-prog/friendly-octo-parakeet:latest
```

## Data Structure

```
Input:
- Properties CSV: Multiple property entries (deduplicates automatically)
- Craftsmen CSV: Multiple service area rows per craftsman (accumulates automatically)

Processing:
- Properties deduplicated → unique addresses only
- Craftsmen accumulated → all service areas per craftsman
- Address matching with pattern recognition and normalization

Output:
- Coverage analysis per unique property address
- Summary statistics (total coverage, gaps, categories)
- Gap identification for coverage planning
```

## Performance

Typical runtime by dataset size:
- **Small** (< 100 properties): < 5 seconds
- **Medium** (100-1000 properties): 5-30 seconds
- **Large** (> 1000 properties): 30-120 seconds

## Architecture

### Core Components

**CraftsmanCoverageAnalyzer**: Main analysis engine
- Loads and validates data
- Performs address matching
- Generates analysis and reports

**AdaptiveTokenizer**: Intelligent text parser
- Breaks service areas into meaningful tokens
- Handles multiple delimiters
- Preserves context (street name + numbers)

**SegmentParser**: Token classifier
- Classifies tokens by type (street, number, postal code, city)
- Assigns confidence scores
- Extracts structured data

**AdaptiveMatcher**: Pattern-based matcher
- Learns patterns from all service areas
- Detects format types automatically
- Matches properties using learned patterns
- Provides fallback for new formats

### Data Sources

**CSVDataSource**: Reads local CSV files
- Auto-detects file types by content
- Intelligent column detection (keyword + data-driven)
- Handles complex headers
- Supports multiple languages

**StaticDataSource**: Sample data fallback
- Used if CSV files not found
- Useful for testing/examples

## Column Auto-Detection

The analyzer automatically finds columns by:

1. **Keyword matching** (priority 1)
   - English keywords: address, street, number, postal code, name, etc.
   - German keywords: Strasse, Hausnummer, PLZ, Firmenname, etc.
   - Multiple language support

2. **Data pattern analysis** (priority 2, fallback)
   - Detects address columns: contain text + street-like words
   - Detects number columns: mostly digits, short length
   - Detects postal code columns: 4-5 digit format
   - Detects name columns: long text, no numbers

## Extending the Analyzer

### Adding Support for New Formats

The adaptive parser learns from data automatically, but if you need to explicitly handle a new format:

1. Add test cases in your data
2. Run the analyzer
3. Check "Unmatched service areas" in output
4. The adaptive parser will learn the pattern

No code changes needed for new formats!

### Custom Column Detection

If column auto-detection fails, edit `CSVDataSource._detect_column_by_data()`:
- Add keywords to detection lists
- Adjust data pattern thresholds
- Extend pattern recognition logic

## Development

### Code Style
- Python 3.12+
- Type hints for all functions
- Docstrings for public methods
- Minimal external dependencies

### Testing
```bash
python3 google_sheets_analyzer.py
```

Run with your CSV files in `input/` folder.

### Building Docker Image Locally
```bash
docker build -t craftsman-analyzer:local .
docker run --rm -v $(pwd)/input:/app/input:ro -v $(pwd)/output:/app/output:rw craftsman-analyzer:local
```

## Requirements

**Python**: 3.12+

**External Dependencies**: None! Uses Python standard library only:
- json, csv, dataclasses, pathlib, abc, re, datetime

**Docker**: Optional (pre-built images available)

## Status

Production ready. Used for real craftsman coverage analysis.

---

**Get started**: Place your CSVs in `input/` and run `python3 google_sheets_analyzer.py`
