# Mechanical Implementation - How Claude Actually Uses This

## THE MECHANICAL PROBLEM
Claude cannot directly edit CSVs anymore. Claude must go through scripts that verify everything.

## MECHANICAL WORKFLOW

### Option 1: Pipe Chain (Claude's Terminal Commands)
```bash
# Claude finds a company and wants to add it
echo "Company: Atomwise
URL: https://atomwise.com
Source: https://github.com/awesome-drug-discovery
Description: AI drug discovery" | python scripts/add_company.py

# Script automatically chains internally:
# → verify_exists.py checks URL
# → verify_in_source.py checks source
# → If ALL pass: writes to CSV
# → If ANY fail: returns error, nothing written
```

### Option 2: Structured JSON Input
```bash
# Claude provides JSON
cat << 'EOF' | python scripts/add_company.py
{
  "company": "Atomwise",
  "url": "https://atomwise.com",
  "source": "https://github.com/awesome-drug-discovery",
  "description": "AI drug discovery",
  "segment": "vertical_industry_platforms"
}
EOF
```

### Option 3: Batch Processing
```bash
# Claude provides multiple companies at once
cat << 'EOF' | python scripts/batch_add.py
Atomwise,https://atomwise.com,https://github.com/awesome-drug-discovery
BenevolentAI,https://benevolent.ai,https://github.com/awesome-drug-discovery
Recursion,https://recursion.com,https://techcrunch.com/ai-companies
EOF

# Output:
# [1/3] Atomwise: ✓ VERIFIED
# [2/3] BenevolentAI: ✓ VERIFIED
# [3/3] Recursion: ✗ FAILED - Not found in source
#
# Added: 2 companies
# Failed: 1 company
```

## ENFORCEMENT MECHANISM

### 1. File System Permissions (if possible)
```bash
# Make CSVs read-only for Claude
chmod 444 data/*.csv

# Only scripts can write (through sudo or special user)
# Scripts have write permission, Claude doesn't
```

### 2. Git Hooks (more realistic)
```bash
# Pre-commit hook that checks for direct CSV edits
# Rejects commits that modify CSVs without audit log
```

### 3. Audit Log Requirement
```bash
# Every CSV modification must have corresponding log entry
# audit/2024-01-01-atomwise.json contains:
{
  "company": "Atomwise",
  "added_by": "add_company.py",
  "timestamp": "2024-01-01T10:30:00Z",
  "verification": {
    "url_check": "passed - 200 OK",
    "source_check": "passed - found at line 47",
    "ssl_valid": true
  }
}
```

## CLAUDE'S ACTUAL WORKFLOW

### Step 1: Claude searches for companies
```bash
# Claude uses browser or curl to find lists
curl -s https://github.com/awesome-drug-discovery | grep -i "http"
```

### Step 2: Claude attempts to add
```bash
# Claude CANNOT do this anymore:
echo "Atomwise,..." >> data/vertical_industry_platforms.csv  # ✗ FORBIDDEN

# Claude MUST do this:
python scripts/add_company.py --company "Atomwise" \
  --url "https://atomwise.com" \
  --source "https://github.com/awesome-drug-discovery"
```

### Step 3: Script validates EVERYTHING
```python
# Inside add_company.py:
def add_company(company, url, source):
    # 1. Verify URL exists
    if not verify_url_exists(url):
        return "ERROR: URL returned 404"

    # 2. Verify source contains company
    if not verify_in_source(url, source):
        return "ERROR: Company not found in source"

    # 3. Only if ALL checks pass
    append_to_csv(company_data)
    create_audit_log(company_data)
    return "SUCCESS: Company added"
```

## FEEDBACK TO CLAUDE

### Clear Success
```
$ python scripts/add_company.py --company "Atomwise" --url "https://atomwise.com"
[VERIFY] Checking https://atomwise.com... ✓ 200 OK
[SOURCE] Checking source... ✓ Found "Atomwise"
[ADDED] Atomwise → vertical_industry_platforms.csv
```

### Clear Failure
```
$ python scripts/add_company.py --company "FakeCompany" --url "https://fakecompany.ai"
[VERIFY] Checking https://fakecompany.ai... ✗ 404 NOT FOUND
[ERROR] Cannot add company with non-existent URL
```

## THE KEY MECHANICAL ENFORCEMENT

1. **Scripts are the ONLY way to modify CSVs**
2. **Scripts verify BEFORE writing**
3. **Failed verifications produce clear errors**
4. **Success requires ALL checks to pass**
5. **Audit log provides accountability**

## What This Prevents

- ❌ Claude adding companies from memory
- ❌ Claude making up URLs
- ❌ Claude claiming false sources
- ❌ Claude bulk adding without verification
- ❌ Claude editing CSVs directly

## What This Enforces

- ✓ Every URL is verified as real
- ✓ Every source is checked
- ✓ Every addition is logged
- ✓ Only verified data enters dataset
- ✓ Complete traceability
