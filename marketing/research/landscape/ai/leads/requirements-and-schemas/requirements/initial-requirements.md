# AI/ML Competitive Landscape Research Requirements

## Objective
Catalog ALL AI/ML companies with market presence to create comprehensive competitive landscape.

## Scope
- Target: Hundreds of competitors across all segments
- Coverage: Exhaust internet sources for comprehensive list
- Focus: Companies with actual market presence

## Research Process
1. I browse the web using browser tool
2. I find companies and their information
3. I submit findings to validation scripts
4. Scripts verify URLs exist and data is valid
5. Only verified data gets saved

## Data Requirements
For each company:
- vendor_name (required)
- website_url (required, must be verified)
- description (brief, factual)
- segment_code (from taxonomy)
- primary_offering (main product/service)
- hq_region (if available)
- employee_band (if available)
- founded_year (if available)

## Validation Rules
- ALL URLs must return HTTP 200/301/302
- NO duplicate companies
- NO made-up/hallucinated data
- ALL data must come from browser research
- Every entry must have audit trail
