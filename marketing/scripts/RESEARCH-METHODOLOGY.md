# Research Methodology - Three Stage System

## STAGE 0: Requirements Analysis & Data Model Definition

### Input
- Read `/research/landscape/ai/leads/requirements/INITIAL-REQUIREMENTS.md`

### Process
1. Analyze what data needs to be collected
2. Define data models/schemas in `/research/landscape/ai/leads/models/`
   - `company.schema.json` - Company data structure
   - `validation.rules.json` - Validation rules
   - `segments.json` - Valid segment codes
   - `regions.json` - Valid regions

### Output
- JSON schemas that define EXACTLY what data to collect
- Validation rules for each field

---

## STAGE I: Link Collection & Verification

### Purpose
Collect and verify URLs before visiting them

### Script: `collect_links.py`

**Input from Claude:**
```
https://atomwise.com
https://benevolent.ai
https://recursion.com
```

**What it does:**
1. Receives URLs from Claude (via stdin)
2. Verifies each URL is accessible (HTTP 200/301)
3. Records response time, SSL status
4. ONLY adds verified URLs to `/links/verified_links.csv`
5. Rejected URLs go to `/links/rejected_links.csv`
6. Creates audit log in `/logs/link_verification_TIMESTAMP.json`

**Output:**
```csv
# verified_links.csv
url,status_code,response_time_ms,ssl_valid,verified_at
https://atomwise.com,200,234,true,2024-01-01T10:00:00Z
https://benevolent.ai,200,456,true,2024-01-01T10:00:01Z
```

---

## STAGE II: Data Extraction & Model Population

### Purpose
Visit verified links and extract data according to the schema

### Script: `extract_to_model.py`

**Input:**
- Reads from `/links/verified_links.csv`
- Uses schemas from `/models/company.schema.json`

**What it does:**
1. Visits each verified URL
2. Extracts data according to schema requirements
3. Validates extracted data against schema
4. ONLY saves valid data to `/models/data/company_name.json`
5. Creates extraction log in `/logs/extraction_TIMESTAMP.json`

**Output:**
```json
// /models/data/atomwise.json
{
  "vendor_name": "Atomwise",
  "website_url": "https://atomwise.com",
  "segment_code": "vertical_industry_platforms",
  "company_type": "startup",
  "primary_offering": "AI-powered drug discovery",
  "extracted_from": {
    "title": "Atomwise - AI for Drug Discovery",
    "meta_description": "...",
    "extraction_date": "2024-01-01T10:30:00Z"
  }
}
```

---

## STAGE III: Link Maintenance

### Script: `update_link.py`

**When a link fails:**
```bash
python update_link.py --old https://broken.com --new https://working.com
```

**What it does:**
1. Verifies new URL works
2. Updates `/links/verified_links.csv`
3. Logs change in `/logs/link_updates_TIMESTAMP.json`

---

## Directory Structure

```
/research/landscape/ai/leads/
├── requirements/
│   └── INITIAL-REQUIREMENTS.md      # What to research
├── models/
│   ├── company.schema.json          # Data model schema
│   ├── validation.rules.json        # Validation rules
│   └── data/                        # Populated models
│       ├── atomwise.json
│       └── benevolent.json
├── links/
│   ├── verified_links.csv          # Stage I output
│   ├── rejected_links.csv          # Failed verifications
│   └── updated_links.csv           # Link updates
├── data/
│   └── final_export.csv            # Final CSV export
└── logs/
    ├── link_verification_*.json     # Stage I logs
    ├── extraction_*.json            # Stage II logs
    └── link_updates_*.json         # Update logs
```

## Script Behaviors

### `collect_links.py`
```python
# Claude provides:
cat urls.txt | python collect_links.py

# Script:
1. Read each URL from stdin
2. HTTP GET request to verify
3. If 200/301: add to verified_links.csv
4. If fail: add to rejected_links.csv
5. Log everything to /logs/

# Output:
[1/3] https://atomwise.com ✓ Verified (200)
[2/3] https://fake.com ✗ Failed (404)
[3/3] https://benevolent.ai ✓ Verified (200)

Added: 2 to verified_links.csv
Rejected: 1 to rejected_links.csv
```

### `extract_to_model.py`
```python
# Claude runs:
python extract_to_model.py --source verified_links.csv

# Script:
1. Read verified_links.csv
2. For each URL:
   - Fetch page
   - Extract according to schema
   - Validate against schema
   - Save to /models/data/
3. Log extraction details

# Output:
[1/10] https://atomwise.com
  ✓ Extracted: Atomwise
  ✓ Valid against schema
  ✓ Saved: /models/data/atomwise.json
```

### `validate_model.py`
```python
# Claude provides data:
cat <<EOF | python validate_model.py
{
  "vendor_name": "Atomwise",
  "website_url": "https://atomwise.com",
  "segment_code": "fake_segment"  # Invalid!
}
EOF

# Output:
✗ Validation failed:
  - segment_code: 'fake_segment' not in allowed values
  - missing required field: company_type
```

## Audit Trail

Every action creates a log entry:

```json
// /logs/link_verification_2024-01-01T10:00:00.json
{
  "timestamp": "2024-01-01T10:00:00Z",
  "action": "link_verification",
  "input_count": 3,
  "verified": 2,
  "rejected": 1,
  "details": [
    {
      "url": "https://atomwise.com",
      "status": "verified",
      "http_code": 200,
      "response_time_ms": 234
    },
    {
      "url": "https://fake.com",
      "status": "rejected",
      "error": "404 Not Found"
    }
  ]
}
```

## Implementation Plan

1. **First**: Create data model schemas based on requirements
2. **Second**: Implement `collect_links.py` for URL verification
3. **Third**: Implement `extract_to_model.py` for data extraction
4. **Fourth**: Implement `validate_model.py` for data validation
5. **Fifth**: Implement `update_link.py` for maintenance
6. **Finally**: Implement `export_to_csv.py` for final output

## Key Enforcement

- I CANNOT add unverified links (collect_links.py checks them)
- I CANNOT add invalid data (validate_model.py rejects it)
- I CANNOT skip logging (scripts automatically log)
- I CANNOT modify data without scripts (only scripts write files)
- Every action has an audit trail in /logs/
