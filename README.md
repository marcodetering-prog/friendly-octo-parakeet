# Craftsman Coverage Analyzer

Analyzes which craftsmen/trades can serve each property based on their specializations and service areas.

## Quick Start

```bash
python3 google_sheets_analyzer.py
```

Generates:
- `craftsman_coverage_report.json` - Detailed analysis
- `craftsman_coverage_report.csv` - Coverage gaps
- Console summary with statistics

## Data Input

### Option 1: CSV Files (Recommended - No Setup)

Place two CSV files in the `input/` folder:

**input/properties.csv** - Property addresses
```
Street,Number,PostalCode
Main Street,101,10001
Main Street,102,10001
Oak Avenue,20,10002
```

**input/craftsman.csv** - Craftsmen data
```
Name,Plumbing,Electrical,ServiceAreas
Smith Plumbing,TRUE,FALSE,"Main Street 101, 102"
Jones Electric,FALSE,TRUE,"Oak Avenue 20"
```

The analyzer automatically:
- Detects address, house number, and postal code columns
- Combines them into full addresses
- Deduplicates properties (apartments at same address = 1 property)
- Identifies categories by TRUE/FALSE values
- Accumulates all service areas for each craftsman

### Option 2: Google Sheets (Requires Setup)

1. Create `credentials.json` from Google Cloud Console
2. Set sheet IDs in script:
```python
SHEET_ID = "your-sheet-id"
PROPERTY_GID = 123456789
CRAFTSMAN_GID = 987654321
```
3. Share sheet with service account email

## How It Works

1. **Loads data** from CSV or Google Sheets
2. **Groups properties** by unique address (deduplicates apartments)
3. **For each property**, checks which craftsmen can serve it
4. **Matches** by:
   - Craftsman specializes in category (TRUE marked)
   - Craftsman's service area includes property
5. **Reports** coverage percentage and gaps per property

## Reports

**Summary Statistics**
- Total properties analyzed
- Properties with full coverage
- Average coverage percentage
- Categories with lowest coverage

**Per-Property Details**
- Coverage percentage (covered categories / total categories)
- Missing categories
- List of gaps

## Key Features

✅ Auto-detects columns from full Google Sheets exports
✅ Handles multi-line headers and descriptions
✅ Deduplicates properties (automatic apartment deduplication)
✅ Accumulates service areas for craftsmen with multiple rows
✅ Smart address matching (bidirectional substring matching)
✅ Filters metadata columns automatically
✅ Works with CSV or Google Sheets
✅ No manual formatting needed

## CSV Format Requirements

**Properties CSV**
- Must have address column (Strasse, Street, Address, etc.)
- Optional: house number, postal code columns
- One row per apartment/unit (auto-deduplicated)

**Craftsmen CSV**
- Must have name column (Firmenname, Name, etc.)
- Category columns with TRUE/FALSE/X/✓ values
- Service areas column (Einsatzgebiet, PLZ, etc.)
- One row per service area (auto-accumulated)

## Troubleshooting

**No properties found**
- Check that address column exists (Strasse, Street, Address)
- Verify CSV not empty after headers

**No craftsmen found**
- Ensure name column exists (Firmenname, Name)
- Check category columns have TRUE/FALSE values

**Wrong address matching**
- Properties are combined from Street + Number + PLZ columns
- Service areas support substring matching

**Duplicate entries**
- Properties are automatically deduplicated by address
- Craftsmen service areas are automatically accumulated

## Data Structure

```
Input:
- Multiple property entries (apartments and units)
- Craftsmen with multiple service area rows

Processing:
- Properties deduplicated → unique addresses only
- Craftsmen accumulated → all service areas per craftsman

Output:
- Coverage analysis per unique property address
- Summary statistics (total coverage, gaps, categories)
- Gap identification for properties needing service
```

## Command Reference

```bash
# Run analysis
python3 google_sheets_analyzer.py

# Output files
craftsman_coverage_report.json    # Machine-readable report
craftsman_coverage_report.csv     # Spreadsheet-friendly gaps
```

---

**Status**: Production ready
