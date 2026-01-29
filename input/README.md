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
Strasse,Hausnummer,PLZ
Badenerstr.,727,8048
Badenerstr.,731,8048
```

### 2. craftsman.csv (or craftsmen.csv)
Contains craftsman data with specializations and service areas.

**Column requirements:**
- Name column (e.g., `Firmenname`, `Name`)
- Service area column (e.g., `Einsatzgebiet`, `Service Areas`)
- Category columns with TRUE/FALSE/X/✓ values

**Example:**
```
Firmenname,Category1,Category2,Einsatzgebiet
Acme AG,TRUE,FALSE,"Badenerstr. 727, 731, 8048"
```

## Notes

- The analyzer auto-detects columns by keywords
- Supports both simple and complex Google Sheets exports
- Properties are automatically deduplicated by address
- Service areas from multiple rows are accumulated per craftsman
