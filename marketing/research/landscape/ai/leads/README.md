# AI Landscape Research Structure

## Directory Layout
```
research/landscape/ai/leads/
├── requirements-and-schemas/
│   ├── requirements/           # Research requirements and specs
│   └── schemas/               # Data validation schemas
├── links-and-sources/
│   └── validated/             # Verified URLs from my browser research
├── data-models/
│   └── validated/             # Company data that passed validation
├── downloads/                 # Downloaded resources (PDFs, lists, etc)
└── logs/                      # Validation attempts and script execution logs
```

## How It Works

1. **I browse the web** to find AI companies
2. **I submit data to validation scripts** via stdin
3. **Scripts verify** URLs exist and data is valid
4. **Only verified data gets saved**

## Scripts Usage

### Validate and Save Company
```bash
echo '{
  "vendor_name": "OpenAI",
  "website_url": "https://openai.com",
  "segment_code": "foundation_models",
  "primary_offering": "GPT models and AI research"
}' | python scripts/validate_and_save.py --subdir foundation_models
```

### Add Links
```bash
echo "https://openai.com
https://anthropic.com
https://cohere.ai" | python scripts/add_link.py --subdir foundation_models
```

### Download File
```bash
python scripts/download_file.py --url https://example.com/ai-companies.pdf --subdir resources
```

## Validation Rules
- URLs must be real (HTTP 200/301/302)
- No duplicates
- Required fields must be present
- All data must come from browser research (not memory)
