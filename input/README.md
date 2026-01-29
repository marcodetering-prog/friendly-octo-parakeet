# Input Data Folder

Place your CSV files here for analysis.

## Required Files

### 1. properties.csv
Contains property addresses to analyze.

**Column requirements:**
- Address column (e.g., `Strasse`, `Street`, `Address`)
- Optional: House number column (`Hausnummer`, `Number`)
- Optional: Postal code column (`PLZ`, `Postal Code`)

**Example:**
```
Street,Number,PostalCode
Main Street,101,10001
Main Street,102,10001
Oak Avenue,20,10002
```

### 2. craftsman.csv (or craftsmen.csv)
Contains craftsman data with specializations and service areas.

**Column requirements:**
- Name column (e.g., `Firmenname`, `Name`)
- Service area column (e.g., `Einsatzgebiet`, `Service Areas`)
- Category columns with TRUE/FALSE/X/✓ values

**Example:**
```
Name,Plumbing,Electrical,ServiceAreas
Smith Plumbing,TRUE,FALSE,"Main Street 101, 102"
Jones Electric,FALSE,TRUE,"Oak Avenue 20"
```

## Notes

- The analyzer auto-detects columns by keywords
- Supports both simple and complex Google Sheets exports
- Properties are automatically deduplicated by address
- Service areas from multiple rows are accumulated per craftsman
