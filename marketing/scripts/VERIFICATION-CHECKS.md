# Complete List of Verification Checks

## 1. URL EXISTENCE CHECKS
- **URL_RESOLVES**: Does the URL actually resolve to a server?
- **URL_NOT_404**: Returns 200/301/302, not 404/500
- **SSL_VALID**: For HTTPS, is SSL certificate valid?
- **DOMAIN_EXISTS**: DNS lookup succeeds
- **NOT_PARKED**: Not a domain parking page
- **NOT_FOR_SALE**: Domain isn't for sale
- **RESPONSE_TIME**: Responds within 30 seconds

## 2. SOURCE VERIFICATION CHECKS
- **SOURCE_URL_EXISTS**: The source URL itself is real
- **COMPANY_IN_SOURCE**: Company name appears in source page
- **URL_IN_SOURCE**: Company URL appears in source page
- **CONTEXT_MATCH**: Description matches source context
- **SOURCE_RECENT**: Source updated within last 2 years
- **SOURCE_REPUTABLE**: Source is from known lists (GitHub, Crunchbase, etc)

## 3. COMPANY REALITY CHECKS
- **COMPANY_NAME_ON_SITE**: Company name appears on their own website
- **HAS_REAL_CONTENT**: Website has actual content (not "coming soon")
- **NOT_TEMPLATE**: Not a default WordPress/Wix template
- **HAS_ABOUT_PAGE**: Can find company information
- **HAS_CONTACT_INFO**: Real contact information exists
- **NOT_LOREM_IPSUM**: No placeholder text

## 4. ANTI-HALLUCINATION CHECKS
- **NOT_COMMON_TRAINING**: Not a commonly known company from training data (OpenAI, Google, etc without verification)
- **URL_NOT_GUESSED**: URL isn't just company-name.com/.ai/.io
- **SPECIFIC_DETAILS**: Has specific, verifiable details, not generic descriptions
- **TIMESTAMP_RECENT**: Claude's verification timestamp is NOW, not claimed
- **NO_SUSPICIOUS_PATTERNS**: Doesn't match patterns of made-up data

## 5. TEMPORAL CHECKS
- **COMPANY_CURRENT**: Company still exists (not defunct)
- **NOT_ACQUIRED_DEAD**: Hasn't been acquired and shut down
- **WEBSITE_UPDATED**: Website updated in last 3 years
- **NOT_HISTORICAL**: Not a company that shut down years ago
- **DOMAIN_AGE**: Domain age is reasonable for claimed founding date

## 6. DATA CONSISTENCY CHECKS
- **EMPLOYEE_COUNT_REALISTIC**: Employee count matches company size indicators
- **REGION_MATCHES**: HQ region matches location found on site
- **SEGMENT_APPROPRIATE**: Company actually fits the segment claimed
- **DESCRIPTION_MATCHES**: Description matches what company actually does
- **COMPANY_TYPE_CORRECT**: Startup/enterprise/etc matches reality

## 7. CROSS-REFERENCE CHECKS
- **LINKEDIN_EXISTS**: LinkedIn company page exists
- **LINKEDIN_EMPLOYEE_COUNT**: Employee count matches LinkedIn
- **CRUNCHBASE_MATCH**: If exists on Crunchbase, data matches
- **GITHUB_REAL**: If claims open source, GitHub org exists
- **NEWS_MENTIONS**: Recent news mentions exist

## 8. CONTENT EXTRACTION CHECKS
- **TITLE_EXTRACTED**: Successfully extracted page title
- **DESCRIPTION_FOUND**: Found meta description or about text
- **NO_EXTRACTION_ERRORS**: No parsing errors
- **LANGUAGE_ENGLISH**: Can parse content (or note language)
- **VALID_HTML**: Valid HTML structure

## 9. DUPLICATE/REDUNDANCY CHECKS
- **NOT_DUPLICATE**: Not already in database
- **NOT_VARIANT_NAME**: Not same company with different name
- **UNIQUE_URL**: URL not already in database
- **NOT_REDIRECT_DUPLICATE**: Doesn't redirect to existing entry

## 10. FORMAT VALIDATION CHECKS
- **URL_FORMAT_VALID**: Proper URL format (http/https)
- **NO_TRAILING_SLASH**: Normalized URL format
- **ASCII_DOMAIN**: Domain is valid ASCII
- **NO_URL_FRAGMENTS**: No #fragments or ?params in base URL
- **PROPER_ENCODING**: No encoding issues

## 11. SPECIFIC FIELD CHECKS

### For Employee Band:
- **EMPLOYEE_EVIDENCE**: Found actual evidence of employee count
- **NOT_DEFAULT**: Not just defaulting to "50_199"
- **SOURCE_CITED**: Can show WHERE employee count came from

### For HQ Region:
- **LOCATION_FOUND**: Actually found location on website
- **REGION_MAPPING_CORRECT**: Correctly mapped city to region
- **NOT_ASSUMED**: Not assuming based on domain (.uk = EMEA)

### For Primary Offering:
- **DESCRIPTION_SPECIFIC**: Not generic "AI/ML platform"
- **FROM_WEBSITE**: Actually extracted from website
- **UNDER_500_CHARS**: Fits in field limit

## 12. AUDIT TRAIL CHECKS
- **TIMESTAMP_VALID**: Verification timestamp is current
- **SOURCE_CHAIN**: Complete chain from source to company
- **VERIFICATION_LOG**: All checks logged
- **ERROR_DETAILS**: Failed checks have specific reasons
- **RETRY_COUNT**: Number of verification attempts

## IMPLEMENTATION PRIORITY

### CRITICAL (Must Have)
1. URL_NOT_404
2. COMPANY_IN_SOURCE
3. NOT_DUPLICATE
4. COMPANY_NAME_ON_SITE

### HIGH (Prevents Most Hallucination)
1. SOURCE_URL_EXISTS
2. HAS_REAL_CONTENT
3. NOT_COMMON_TRAINING
4. COMPANY_CURRENT

### MEDIUM (Data Quality)
1. EMPLOYEE_EVIDENCE
2. LOCATION_FOUND
3. DESCRIPTION_SPECIFIC
4. LINKEDIN_EXISTS

### LOW (Nice to Have)
1. DOMAIN_AGE
2. NEWS_MENTIONS
3. GITHUB_REAL
4. RESPONSE_TIME

## CHECK COMBINATIONS

### Minimum Viable Entry
- URL_NOT_404 ✓
- COMPANY_IN_SOURCE ✓
- NOT_DUPLICATE ✓
- HAS_REAL_CONTENT ✓

### High Confidence Entry
- All Minimum Viable ✓
- LINKEDIN_EXISTS ✓
- EMPLOYEE_EVIDENCE ✓
- LOCATION_FOUND ✓
- DESCRIPTION_SPECIFIC ✓

### Suspicious Entry (Requires Review)
- URL works but NOT in source
- In source but URL fails
- Common training data company
- Generic description
- No evidence for claims

## FAILURE MODES

### Immediate Rejection
- URL returns 404 → REJECT
- Company not in source → REJECT
- Already in database → REJECT
- Domain for sale → REJECT

### Warning But Allow
- No LinkedIn → WARN but allow
- No employee count → WARN but allow
- Generic description → WARN but allow

### Require Manual Review
- Acquired company → REVIEW
- Redirect to different domain → REVIEW
- Source over 2 years old → REVIEW
