# Script Input/Output Specifications

## 1. `add_company.py` - MAIN ENTRY POINT

### INPUT (from Claude via stdin or args)
```
# Claude provides whatever format:
Atomwise
https://atomwise.com
I found this on https://github.com/awesome-ai
It does drug discovery with AI
```

### WHAT IT DOES
1. **PARSES** Claude's messy input into structured format
2. **CALLS** other scripts in sequence to verify
3. **BLOCKS** if any verification fails
4. **WRITES** to CSV only if ALL checks pass

### OUTPUT
```
[PARSING] Your input...
[CHECK 1] Verifying URL exists...
[CHECK 2] Verifying source contains company...
[CHECK 3] Extracting real data from website...
[RESULT] ✓ Company added to vertical_industry_platforms.csv
-- OR --
[RESULT] ✗ REJECTED: URL returns 404
```

---

## 2. `verify_url.py` - URL EXISTENCE CHECK

### INPUT
```
https://atomwise.com
```

### WHAT IT DOES
1. **MAKES ACTUAL HTTP REQUEST** to the URL
2. **CHECKS** status code (must be 200/301/302)
3. **EXTRACTS** page title as proof it loaded
4. **MEASURES** response time
5. **VALIDATES** SSL certificate

### OUTPUT
```json
{
  "url": "https://atomwise.com",
  "valid": true,
  "status_code": 200,
  "title": "Atomwise - AI for Drug Discovery",
  "ssl_valid": true,
  "response_time_ms": 234,
  "error": null
}
```

---

## 3. `verify_source.py` - SOURCE VERIFICATION

### INPUT
```json
{
  "company_url": "https://atomwise.com",
  "source_url": "https://github.com/awesome-ai-drug-discovery",
  "company_name": "Atomwise"
}
```

### WHAT IT DOES
1. **FETCHES** the source URL
2. **SEARCHES** for company name in source
3. **SEARCHES** for company URL in source
4. **EXTRACTS** the exact line/context where found
5. **RETURNS** proof of where it was found

### OUTPUT
```json
{
  "found": true,
  "source_valid": true,
  "company_mentioned": true,
  "url_mentioned": true,
  "context": "- [Atomwise](https://atomwise.com) - AI-powered drug discovery",
  "line_number": 47,
  "confidence": 0.95
}
```

---

## 4. `extract_truth.py` - REAL DATA EXTRACTION

### INPUT
```
https://atomwise.com
```

### WHAT IT DOES
1. **FETCHES** the company website
2. **EXTRACTS** actual company name from site
3. **FINDS** real description from meta tags
4. **SEARCHES** for employee count
5. **LOCATES** headquarters location
6. **IDENTIFIES** actual offerings
7. **RETURNS** only what was FOUND, not guessed

### OUTPUT
```json
{
  "extracted_name": "Atomwise Inc.",
  "extracted_description": "AI-powered drug discovery and molecular design",
  "found_employee_count": "51-200",
  "found_location": "San Francisco, CA",
  "found_founded": "2012",
  "meta_description": "Atomwise uses AI for structure-based drug discovery",
  "page_title": "Atomwise - AI for Drug Discovery",
  "evidence": {
    "employee_source": "footer text: '200+ employees'",
    "location_source": "about page: 'Headquarters: San Francisco'",
    "description_source": "meta description tag"
  }
}
```

---

## 5. `check_duplicate.py` - DUPLICATE CHECK

### INPUT
```json
{
  "url": "https://atomwise.com",
  "name": "Atomwise"
}
```

### WHAT IT DOES
1. **READS** existing CSV files
2. **CHECKS** if URL already exists
3. **CHECKS** if company name exists
4. **CHECKS** if redirect URL matches existing

### OUTPUT
```json
{
  "is_duplicate": false,
  "existing_entry": null,
  "similar_names": ["Atomwise"],
  "same_domain": false
}
```

---

## 6. `commit_verified.py` - FINAL WRITE

### INPUT (only from pipeline, not from Claude)
```json
{
  "verified_data": {
    "vendor_name": "Atomwise",
    "website_url": "https://atomwise.com",
    "segment_code": "vertical_industry_platforms",
    "primary_offering": "AI-powered drug discovery",
    "hq_region": "na",
    "employee_band": "50_199"
  },
  "verification_proof": {
    "url_check": "passed",
    "source_check": "passed",
    "duplicate_check": "passed",
    "extraction": "completed"
  },
  "audit_trail": {
    "timestamp": "2024-01-01T10:30:00Z",
    "source_url": "https://github.com/awesome-ai",
    "checks_performed": 15,
    "checks_passed": 15
  }
}
```

### WHAT IT DOES
1. **VALIDATES** all required fields present
2. **CONFIRMS** all checks passed
3. **WRITES** to appropriate CSV
4. **CREATES** audit log entry
5. **RETURNS** confirmation

### OUTPUT
```
✓ Added to: data/vertical_industry_platforms.csv
✓ Audit log: audit/2024-01-01-atomwise.json
✓ Entry #127: Atomwise
```

---

## HOW THEY CHAIN TOGETHER

```bash
# Claude runs:
echo "Atomwise|https://atomwise.com|https://github.com/awesome-ai" | python add_company.py

# add_company.py internally calls:
url_valid = verify_url.py(url)
if not url_valid:
    EXIT WITH ERROR

source_valid = verify_source.py(url, source)
if not source_valid:
    EXIT WITH ERROR

real_data = extract_truth.py(url)
if not real_data:
    EXIT WITH ERROR

is_duplicate = check_duplicate.py(url, name)
if is_duplicate:
    EXIT WITH ERROR

# Only if ALL pass:
commit_verified.py(all_verified_data)
```

## KEY ENFORCEMENT MECHANISMS

1. **Scripts call each other** - Claude can't skip steps
2. **Each script exits on failure** - Chain breaks if any check fails
3. **Real HTTP requests** - Not using Claude's memory
4. **Evidence required** - Must show WHERE data came from
5. **Audit logs** - Every attempt is logged
6. **No direct CSV access** - Only commit_verified.py can write

## WHAT CLAUDE CANNOT DO

- ❌ Call commit_verified.py directly (requires verification proof)
- ❌ Skip verification steps
- ❌ Provide fake verification proof (scripts check independently)
- ❌ Add without source
- ❌ Add duplicates
- ❌ Make up data (extract_truth.py gets real data)
