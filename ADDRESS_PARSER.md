# Adaptive Address Parser Architecture

This document describes the intelligent, format-agnostic address parser system for the Craftsman Analyzer.

## Overview

The adaptive parser uses **pattern recognition and heuristics** to intelligently parse service areas without predefined format rules. It learns from the data structure automatically.

## Core Concept: Pattern Analysis

Instead of hard-coding formats, the parser:

1. **Analyzes the raw service area string**
2. **Detects delimiters** (/, comma, space patterns)
3. **Identifies segment types** (street name, number, postal code, city)
4. **Groups related segments** (Street + its numbers)
5. **Reconstructs logical pairings** (Street with all its numbers)

## Implementation Strategy

### Phase 1: Delimiter Detection

```
Input: "Zürcherstr. 65 / 67 / 69 / 71"

Detected delimiters:
- "/" appears 3 times → major delimiter between items
- " " between text and numbers → natural grouping
- Pattern: [Text] [Numbers] / [Numbers] / [Numbers] / [Numbers]
```

### Phase 2: Segment Classification

Classify each segment or token:

```python
def classify_token(token):
    if matches(r'^\d{4,5}$'):
        return "POSTAL_CODE"
    elif matches(r'^[A-Z][a-z]+$'):
        return "CITY"
    elif matches(r'^\d+$'):
        return "NUMBER"
    elif has_street_keywords():
        return "STREET"
    else:
        return "UNKNOWN"
```

### Phase 3: Intelligent Grouping

Group tokens into logical units:

```
Input tokens: [Zürcherstr, 65, /, 67, /, 69, /, 71]

Logical groups:
1. STREET: "Zürcherstr"
2. NUMBERS: [65, 67, 69, 71]

Result: {"street": "Zürcherstr", "numbers": [65, 67, 69, 71]}
```

### Phase 4: Adaptive Matching

For each property-address pair:

```
Property: "Zürcherstr. 71 8048"
Service area: "Zürcherstr. 65 / 67 / 69 / 71"

1. Extract property street: "Zürcherstr"
2. Extract property numbers: [71]
3. Parse service area → {"street": "Zürcherstr", "numbers": [65,67,69,71]}
4. Compare streets (normalize): "zürcherstr" == "zürcherstr" ✓
5. Check numbers: 71 in [65,67,69,71] ✓
6. MATCH!
```

## Algorithm Components

### 1. Smart Tokenizer

```python
class AdaptiveTokenizer:
    """Breaks service areas into meaningful tokens"""

    def tokenize(self, text):
        # Handles: delimiters, abbreviations, numbers
        # Preserves context (e.g., "Str. 127" stays together initially)
        pass

    def detect_delimiters(self, text):
        # Finds common delimiters: / , - &
        # Scores by frequency and consistency
        pass
```

### 2. Segment Parser

```python
class SegmentParser:
    """Extracts meaning from individual segments"""

    def parse_segment(self, segment):
        # Returns: {"type": "street|number|postal|city",
        #           "value": value,
        #           "confidence": 0.0-1.0}
        pass

    def merge_related_tokens(self, tokens):
        # Groups: "Street" + "123/456" → Street with [123,456]
        pass
```

### 3. Adaptive Matcher

```python
class AdaptiveMatcher:
    """Matches properties to service areas intelligently"""

    def extract_patterns(self, service_areas):
        # Learns common patterns from all service areas
        # Builds pattern library dynamically
        pass

    def match_property(self, prop, service_area):
        # Uses learned patterns to make intelligent matches
        # Scores confidence of match
        pass
```

## Pseudo-Code Example

```python
def parse_service_area_intelligent(area):
    """
    Intelligently parse any service area format
    """

    # Step 1: Detect structure
    delimiters = detect_delimiters(area)  # ["/", ",", " "]
    delimiter_score = score_delimiters(delimiters)  # Best: "/"

    # Step 2: Split by best delimiter
    segments = area.split(delimiter_score["primary"])

    # Step 3: Classify each segment
    typed_segments = [classify(s) for s in segments]

    # Step 4: Group logically
    groups = group_segments(typed_segments)

    # Step 5: Extract street-number pairs
    result = []
    for group in groups:
        streets = extract_streets(group)
        numbers = extract_numbers(group)

        for street in streets:
            result.append({
                "street": street,
                "numbers": numbers if numbers else []
            })

    return result


def classify(segment):
    """Auto-detect segment type"""
    s = segment.strip()

    # Postal code: 4-5 digits, possibly with city
    if matches(r'^\d{4,5}\s+[A-Z]'):
        return {"type": "postal_code", "value": s}

    # Pure number
    if matches(r'^\d+$'):
        return {"type": "number", "value": int(s)}

    # Street name (has letters and optionally numbers)
    if has_letters(s):
        # Extract street and any attached numbers
        match = split_street_and_numbers(s)
        return {
            "type": "street",
            "street": match["street"],
            "attached_numbers": match["numbers"]
        }

    return {"type": "unknown", "value": s}


def group_segments(typed_segments):
    """Group related segments intelligently"""
    groups = []
    current_group = {}

    for segment in typed_segments:
        if segment["type"] == "street":
            if current_group and "numbers" in current_group:
                groups.append(current_group)
            current_group = {
                "street": segment["street"],
                "numbers": segment.get("attached_numbers", [])
            }

        elif segment["type"] == "number":
            if not current_group:
                current_group = {"numbers": []}
            if "street" not in current_group:
                current_group.setdefault("numbers", []).append(segment["value"])
            else:
                current_group["numbers"].append(segment["value"])

        elif segment["type"] == "postal_code":
            if current_group and "street" in current_group:
                current_group["postal_code"] = segment["value"]
                groups.append(current_group)
                current_group = {}

    if current_group:
        groups.append(current_group)

    return groups
```

## Handled Scenarios

### Current System Handles:

1. **"Street 65 / 67 / 69 / 71"**
   - Detects "/" as primary delimiter
   - Identifies "Street" + list of numbers
   - Result: Street → [65, 67, 69, 71]

2. **"Street 127/129/131 / OtherStreet 16/18"**
   - Detects "/" within segments and between segments
   - Recognizes two distinct streets
   - Result: [Street→[127,129,131], OtherStreet→[16,18]]

3. **"Street 1, 2, 3, 4, Postal City"**
   - Detects "," as delimiter
   - Identifies numbers until postal code
   - Result: Street → [1,2,3,4]

4. **"Street.123/OtherStreet 8, 8048 Zürich"**
   - Handles adjacent numbers (no space)
   - Recognizes postal code + city
   - Result: [Street→[123], OtherStreet→[8]]

### Future Formats It Will Handle:

5. **"Street 1-10"** (range)
   - Detects range pattern
   - Expands to [1,2,3,4,5,6,7,8,9,10] or matches 1-10 as range

6. **"Street (1), (2), (3)"** (parentheses)
   - Learns parenthesis pattern
   - Extracts numbers from parentheses

7. **"Street Building A/B/C 1-5"** (building letters + numbers)
   - Recognizes building designations
   - Maps to number ranges per building

8. **"1 Street, 2 Street, 3 Street"** (number-first format)
   - Detects non-standard word order
   - Correctly identifies numbers as identifiers

## Implementation in Code

### Location: `google_sheets_analyzer.py`

Add new method to `CraftsmanCoverageAnalyzer` class:

```python
def parse_service_area_adaptive(self, service_area: str) -> List[Dict]:
    """
    Intelligently parse service area using pattern recognition.

    Returns:
        List of {"street": str, "numbers": [list of ints], "confidence": float}
    """

    # Implementation of algorithm above
    # Learns patterns from input
    # Returns parsed segments
    pass
```

Update `find_craftsmen_for_property_and_category()` to use:

```python
# Replace hard-coded segment parsing with:
parsed_segments = self.parse_service_area_adaptive(service_area)

for segment_info in parsed_segments:
    street = segment_info["street"]
    numbers = segment_info["numbers"]
    confidence = segment_info["confidence"]

    # Match as before, but with learned patterns
    if self.streets_match(property_street, street):
        if any(pn in numbers for pn in property_numbers):
            serves_property = True
            break
```

## Benefits

✅ **Format Agnostic** - Works with any format
✅ **Self-Learning** - Improves with more data
✅ **Extensible** - No code changes for new formats
✅ **Confidence Scoring** - Know how certain matches are
✅ **Pattern Library** - Learns common patterns
✅ **Robust** - Handles typos, abbreviations, variations

## Testing Strategy

1. **Unit Tests**: Test tokenizer, classifier, grouper independently
2. **Integration Tests**: Test full parsing with known formats
3. **Regression Tests**: Ensure existing formats still work
4. **New Format Tests**: Validate new patterns as they appear

## Performance Considerations

- **Caching**: Cache parsed service areas (they don't change)
- **Lazy Evaluation**: Only parse when matching needed
- **Pattern Memoization**: Remember successful patterns
- **Early Exit**: Stop matching once found

## Future Enhancements

1. **Machine Learning**: Train on successful matches
2. **Fuzzy Matching**: Handle typos and variations
3. **Geographic**: Use postal codes for validation
4. **Heuristic Scoring**: Confidence ratings per match
5. **User Feedback Loop**: Learn from user corrections
