# Address Matching Formats

This document explains how the analyzer matches properties to craftsman service areas and how it handles different formats.

## Current Supported Formats

The analyzer currently handles these service area formats automatically:

### Format 1: Multi-street with slash-separated numbers
```
"Zürcherstr. 65 / 67 / 69 / 71"
→ Matches: Zürcherstr. 65, 67, 69, 71
```

### Format 2: Multi-street with slash-separated addresses
```
"Baslerstr. 127/129/131/133 / Calandastr. 16/18"
→ Matches: Baslerstr. 127, 129, 131, 133 + Calandastr. 16, 18
```

### Format 3: Adjacent street and number (no space)
```
"Badenerstr.717/Im Struppen 8, 8048 Zürich"
→ Matches: Badenerstr. 717, Im Struppen 8
```

### Format 4: Comma-separated numbers
```
"Im Struppen 11, 12, 13, 14, 15, 16, 17, 19, 21, 8048 Zürich"
→ Matches: Im Struppen 11, 12, 13, 14, 15, 16, 17, 19, 21
```

## How Matching Works

**Priority 1: Exact Address Match**
- Property: "Street 123"
- Service Area: "Street 123" or "Street 123, other"
- Result: MATCH ✓

**Priority 2: Same Street + Number in Range**
- Property: "Street 71"
- Service Area: "Street 65 / 67 / 69 / 71"
- Process:
  1. Extract street: "Street"
  2. Extract property number: "71"
  3. Extract all numbers from service area: [65, 67, 69, 71]
  4. Check if 71 in [65, 67, 69, 71]: YES → MATCH ✓

**Priority 3: Abbreviated Street Names**
- Property: "Calandastrasse 16"
- Service Area: "Calandastr. 16"
- Process:
  1. Normalize both: "calandastr" == "calandastr"
  2. Match numbers: 16 == 16 → MATCH ✓

## Adding Support for New Formats

If you encounter a new format that doesn't match, follow these steps:

### 1. Identify the Pattern

First, find where the mismatch occurs:

```bash
# Look in output/ folder or console output for unmatched properties
# Check the "UNMATCHED CRAFTSMAN SERVICE AREAS" section
```

### 2. Add to the Matching Logic

The matching happens in `find_craftsmen_for_property_and_category()` method around lines 920-950.

Current logic:
```python
# Split by " / " separator
service_segments = [s.strip() for s in service_area.split(" / ")]

for segment in service_segments:
    # Extract street name (without numbers)
    service_street_part = segment.split("/")[0].split(",")[0].strip()
    service_street_only = re.sub(r'[\s.]*\d+.*$', '', service_street_part).strip()

    # Match numbers
    service_numbers = self.extract_apartment_numbers(segment)
    if any(pn in service_numbers for pn in property_numbers):
        serves_property = True
```

### 3. Test Your Fix

Create a test script:

```python
import sys
from google_sheets_analyzer import CraftsmanCoverageAnalyzer

# Test your new format
analyzer = CraftsmanCoverageAnalyzer([], [], {})

# Property to find
prop = "Mystreet 42 8048"

# Service area format
service_area = "Your new format here"

# Check if it extracts correctly
print(f"Street: {analyzer.extract_street_name(prop)}")
print(f"Numbers: {analyzer.extract_apartment_numbers(prop)}")
```

### 4. Common Parsing Issues

**Issue: Postal codes treated as property numbers**
- Solution: Filter out 4-5 digit postal codes in `extract_apartment_numbers()`
- Current code excludes PLZ codes (4-5 digits)

**Issue: Numbers-only segments don't have street name**
- Solution: Track `last_street_name` across segments
- Used for: "Zürcherstr. 65 / 67 / 69 / 71" format

**Issue: Abbreviated vs full street names**
- Solution: Normalize both using `normalize_street_name()`
- Converts "Calandastrasse" and "Calandastr." both to "calandastr"

### 5. Key Methods to Understand

- `extract_street_name()` - Removes postal code from address
- `extract_apartment_numbers()` - Finds all apartment/house numbers
- `normalize_street_name()` - Handles abbreviations and spacing
- `find_craftsmen_for_property_and_category()` - Main matching logic

## Testing New Formats

Run the analyzer with your new data:

```bash
# Place CSV files in input/
python3 google_sheets_analyzer.py

# Check output/ for coverage analysis
# If any properties show 0% coverage but craftsmen exist,
# those are the unmatched formats
```

## Extending the Analyzer

Rather than changing the matching logic, you might:

1. **Normalize the input data** - Clean up CSV files before analysis
2. **Add preprocessing** - Fix formatting in the CSV parser
3. **Use aliases** - Define street name variants (e.g., "Str." = "Strasse")

## Questions?

If a format consistently doesn't work:
1. Note the property address and service area
2. Check if it follows one of the 4 supported formats
3. Add a new matching rule following the pattern above
4. Test with your data
5. Submit as an issue on GitHub

## Future Improvements

Potential enhancements for format handling:

- Machine learning to detect new patterns
- Configuration file for custom delimiters
- Address fuzzy matching for typos
- Coordinate-based matching (GPS) for complex cases
