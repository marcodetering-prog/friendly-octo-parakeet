# Output Reports Folder

Generated analysis reports are saved here automatically.

## Report Files

Each run of the analyzer generates timestamped reports:

- `craftsman_coverage_report_YYYYMMDD_HHMMSS.json` - Machine-readable detailed analysis
- `craftsman_coverage_report_YYYYMMDD_HHMMSS.csv` - Coverage gaps in spreadsheet format

## Report Contents

**JSON Report includes:**
- Summary statistics (total properties, coverage percentage, gaps)
- Detailed per-property analysis
- Categories with lowest coverage
- Missing categories per property

**CSV Report includes:**
- One row per property
- Coverage percentage
- Total and covered categories
- Missing categories for properties with gaps

## Usage

Reports are automatically generated when you run:

```bash
python3 google_sheets_analyzer.py
```

Check this folder for the latest report with the most recent timestamp.
