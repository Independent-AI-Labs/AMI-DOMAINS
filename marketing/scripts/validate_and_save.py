#!/usr/bin/env python3
"""
Validates data that Claude provides and saves if valid.
Claude uses browser to find data, then pipes it here for validation.

Usage:
    # Claude found a company and extracted data, now validates it:
    cat << EOF | python validate_and_save.py --type company --subdir drug_discovery
    {
        "vendor_name": "Atomwise",
        "website_url": "https://atomwise.com",
        "primary_offering": "AI drug discovery platform",
        "employee_band": "50_199",
        "hq_region": "na"
    }
    EOF
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import requests


class Validator:
    def __init__(self, base_dir="research/landscape/ai/leads"):
        self.base_dir = Path(base_dir)

    def load_schema(self, data_type, subdir):
        """Load validation schema"""
        schema_file = self.base_dir / "requirements-and-schemas" / "schemas" / f"{data_type}.schema.json"

        # Default company schema if not exists
        if not schema_file.exists():
            return {
                "required": ["vendor_name", "website_url"],
                "fields": {
                    "vendor_name": {"type": "string", "min_length": 1, "max_length": 200},
                    "website_url": {"type": "url", "pattern": "^https?://"},
                    "primary_offering": {"type": "string", "max_length": 500},
                    "employee_band": {
                        "type": "enum",
                        "values": ["1_9", "10_49", "50_199", "200_499", "500_999", "1k_4k", "5k_9k", "10k_plus"]
                    },
                    "hq_region": {
                        "type": "enum",
                        "values": ["na", "emea", "apac", "latam", "unknown"]
                    },
                    "company_type": {
                        "type": "enum",
                        "values": ["startup", "independent_isv", "hyperscaler", "open_source", "nonprofit", "academic"]
                    },
                    "segment_code": {
                        "type": "enum",
                        "values": ["vertical_industry_platforms", "enterprise_ai_suites", "foundation_model_providers",
                                  "functional_specialists", "edge_and_embedded", "ecosystem_enablers",
                                  "agentic_automation", "hyperscalers", "community_open_source"]
                    }
                }
            }

        with open(schema_file, 'r') as f:
            return json.load(f)

    def validate_data(self, data, schema):
        """Validate data against schema"""
        errors = []
        warnings = []

        # Check required fields
        for field in schema.get("required", []):
            if field not in data or not data[field]:
                errors.append(f"Missing required field: {field}")

        # Validate each field
        for field, rules in schema.get("fields", {}).items():
            if field not in data:
                continue

            value = data[field]

            # Type validation
            if rules.get("type") == "string":
                if not isinstance(value, str):
                    errors.append(f"{field}: must be string, got {type(value).__name__}")
                elif "min_length" in rules and len(value) < rules["min_length"]:
                    errors.append(f"{field}: too short (min {rules['min_length']})")
                elif "max_length" in rules and len(value) > rules["max_length"]:
                    errors.append(f"{field}: too long (max {rules['max_length']})")

            elif rules.get("type") == "url":
                if not isinstance(value, str):
                    errors.append(f"{field}: must be string URL")
                elif "pattern" in rules:
                    import re
                    if not re.match(rules["pattern"], value):
                        errors.append(f"{field}: invalid format (expected {rules['pattern']})")

            elif rules.get("type") == "enum":
                if value not in rules.get("values", []):
                    errors.append(f"{field}: '{value}' not in allowed values {rules['values']}")

        # Verify URL actually exists (critical check)
        if "website_url" in data:
            print(f"[VERIFYING] {data['website_url']}...")
            if not self.verify_url_exists(data["website_url"]):
                errors.append("website_url: URL does not exist or is not accessible")

        return errors, warnings

    def verify_url_exists(self, url):
        """Actually check if URL is real - NO HALLUCINATION ALLOWED"""
        try:
            response = requests.head(url, timeout=10, allow_redirects=True,
                                    headers={'User-Agent': 'Mozilla/5.0'})
            return response.status_code in [200, 201, 301, 302]
        except Exception:
            return False

    def check_duplicate(self, data, subdir):
        """Check if this entry already exists"""
        models_dir = self.base_dir / "data-models" / "validated" / subdir / "data"

        if not models_dir.exists():
            return False

        # Check by URL
        for json_file in models_dir.glob("*.json"):
            with open(json_file, 'r') as f:
                existing = json.load(f)
                if existing.get("website_url") == data.get("website_url"):
                    return True
                if existing.get("vendor_name", "").lower() == data.get("vendor_name", "").lower():
                    return True

        return False

    def save_model(self, data, subdir):
        """Save validated model"""
        # Create unique filename
        vendor_name = data.get("vendor_name", "unknown")
        slug = vendor_name.lower().replace(" ", "_").replace(".", "")
        slug = ''.join(c for c in slug if c.isalnum() or c == '_')

        models_dir = self.base_dir / "data-models" / "validated" / subdir / "data"
        models_dir.mkdir(parents=True, exist_ok=True)

        # Add metadata
        data["model_id"] = hashlib.md5(f"{vendor_name}{data.get('website_url', '')}".encode()).hexdigest()[:8]
        data["date_saved"] = datetime.now().isoformat()
        data["validated"] = True

        model_file = models_dir / f"{slug}.json"

        # Handle if file exists
        if model_file.exists():
            # Add version number
            i = 1
            while (models_dir / f"{slug}_v{i}.json").exists():
                i += 1
            model_file = models_dir / f"{slug}_v{i}.json"

        with open(model_file, 'w') as f:
            json.dump(data, f, indent=2)

        return model_file

    def log_action(self, action, subdir, data, result):
        """Create audit log"""
        log_dir = self.base_dir / "logs" / subdir
        log_dir.mkdir(parents=True, exist_ok=True)

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "subdir": subdir,
            "data_provided": data,
            "result": result
        }

        log_file = log_dir / f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, 'w') as f:
            json.dump(log_entry, f, indent=2)

        return log_file

def main():
    parser = argparse.ArgumentParser(description='Validate and save Claude-provided data')
    parser.add_argument('--type', default='company', choices=['company', 'link', 'custom'])
    parser.add_argument('--subdir', required=True, help='Subdirectory for organization')
    parser.add_argument('--force', action='store_true', help='Save even with warnings')
    args = parser.parse_args()

    # Read data from stdin
    input_data = sys.stdin.read().strip()

    if not input_data:
        print("[ERROR] No data provided via stdin")
        sys.exit(1)

    try:
        # Try to parse as JSON
        data = json.loads(input_data)
    except json.JSONDecodeError:
        # Try to parse as key:value pairs
        data = {}
        for line in input_data.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                data[key.strip()] = value.strip()

    if not data:
        print("[ERROR] Could not parse input data")
        sys.exit(1)

    validator = Validator()

    # Load schema
    schema = validator.load_schema(args.type, args.subdir)

    # Validate
    print(f"[VALIDATING] {data.get('vendor_name', 'Unknown')}...")
    errors, warnings = validator.validate_data(data, schema)

    # Check duplicates
    if validator.check_duplicate(data, args.subdir):
        errors.append("Duplicate entry - already exists")

    # Report results
    if errors:
        print("[✗] VALIDATION FAILED:")
        for error in errors:
            print(f"  - {error}")

        # Log failure
        log_file = validator.log_action("validation_failed", args.subdir, data,
                                       {"errors": errors, "warnings": warnings})
        print(f"\n[LOG] {log_file}")
        sys.exit(1)

    if warnings and not args.force:
        print("[⚠] WARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")
        print("\nUse --force to save anyway")
        sys.exit(1)

    # Save model
    model_file = validator.save_model(data, args.subdir)
    print(f"[✓] SAVED: {model_file}")
    print(f"  → {data.get('vendor_name')}")
    print(f"  → {data.get('website_url')}")

    # Log success
    log_file = validator.log_action("model_saved", args.subdir, data,
                                   {"model_file": str(model_file)})
    print(f"[LOG] {log_file}")

if __name__ == "__main__":
    main()
