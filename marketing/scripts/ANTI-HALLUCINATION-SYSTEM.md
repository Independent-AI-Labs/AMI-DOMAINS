# Anti-Hallucination Research System Design

## THE PROBLEM
Claude (me) has been:
- Making up company names from training data
- Inventing URLs that don't exist
- Adding fake employee counts
- Creating entries without verification
- Lying about having checked sources

## THE SOLUTION
A system of scripts that FORCES proper research methodology and PREVENTS hallucination.

## CORE PRINCIPLE
**Claude can ONLY add data that passes through verification scripts**

## SYSTEM ARCHITECTURE

```
Claude's Input → Validation Pipeline → Verified Output → CSV
      ↓              ↓                     ↓
   Raw text    Scripts verify         Only real      Final
   Any format   EVERYTHING            data passes     dataset
```

## SCRIPT PIPELINE

### 1. INPUT GATE: `add_company.py`
**Purpose**: Single entry point for ALL company additions

**What Claude provides** (as text/stdin):
```
Company: Atomwise
URL: https://atomwise.com
Source: Found at https://github.com/awesome-ai-drug-discovery
Description: AI drug discovery
Segment: vertical_industry_platforms
```

**What script does**:
1. Parses Claude's input (however messy)
2. Calls verification chain
3. REJECTS if any verification fails
4. Returns EXACTLY what was verified

### 2. VERIFICATION CHAIN

#### `verify_exists.py`
- Takes: Company name + URL
- Checks: URL actually resolves (not 404)
- Returns: PASS/FAIL with proof (page title, status code)

#### `verify_in_source.py`
- Takes: Company URL + Source URL
- Checks: Company is ACTUALLY mentioned in the source
- Returns: PASS/FAIL with exact text snippet as proof

#### `verify_not_training_data.py`
- Takes: Company name + details
- Checks: Cross-references against known training data patterns
- Returns: WARNING if it matches common training examples

#### `verify_current.py`
- Takes: Company URL
- Checks: Company still exists (not acquired/dead)
- Returns: Current status with proof

### 3. OUTPUT GATE: `commit_verified.py`
- Takes: Only verified data from pipeline
- Outputs: Properly formatted CSV entry
- Logs: Complete audit trail of verification

## DATA FLOW EXAMPLE

```bash
# Claude tries to add a company
cat << EOF | python add_company.py
Atomwise - https://atomwise.com
Found on awesome drug discovery list
AI drug discovery company
EOF

# System response:
[CHECKING] Atomwise at https://atomwise.com
[verify_exists.py] Fetching https://atomwise.com...
  ✓ Status 200, Title: "Atomwise - AI for Drug Discovery"
[verify_in_source.py] Checking source...
  ✗ ERROR: No source URL provided
[REJECTED] Missing source verification

# Claude tries again with source
cat << EOF | python add_company.py
Atomwise - https://atomwise.com
Source: https://github.com/thirdparty/awesome-drug-discovery
AI drug discovery company
EOF

# System response:
[CHECKING] Atomwise at https://atomwise.com
[verify_exists.py] ✓ URL verified
[verify_in_source.py] Fetching source...
  ✓ Found "Atomwise" in source at line 47
[verify_current.py] Checking if active...
  ✓ Last updated 2025, still active
[ACCEPTED] Company verified and added
```

## ENFORCEMENT RULES

1. **NO BYPASS**: Claude cannot add to CSVs directly
2. **FULL AUDIT**: Every addition logged with timestamps
3. **PROOF REQUIRED**: Must show WHERE in source it was found
4. **REAL-TIME ONLY**: No cached/remembered URLs
5. **FAIL FAST**: Any verification failure stops the process

## ERROR MESSAGES THAT STOP CLAUDE

- "ERROR: URL does not exist (404)"
- "ERROR: Company not found in provided source"
- "ERROR: No source URL provided"
- "ERROR: Likely training data - verify manually"
- "ERROR: Company appears defunct/acquired"

## SUCCESS CRITERIA

Claude can ONLY add a company if:
1. URL is verified live (200 OK)
2. Company appears in the claimed source
3. Information is current (not outdated)
4. All metadata is extracted from real pages
5. Audit trail is complete

## IMPLEMENTATION PRIORITY

1. `verify_exists.py` - Stop fake URLs
2. `verify_in_source.py` - Stop fake sources
3. `add_company.py` - Entry gate
4. `commit_verified.py` - Output gate
5. Additional validators as needed

## EXPECTED OUTCOME

- 0% hallucinated companies
- 100% verified URLs
- 100% traceable sources
- Complete audit trail
- Trust in dataset
