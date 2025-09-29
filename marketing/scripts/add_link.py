#!/usr/bin/env python3
"""
Validates and saves links that Claude provides after browsing.
Claude finds links, this script validates they're real.

Usage:
    # Claude found some links and provides them:
    cat << EOF | python add_link.py --subdir drug_discovery
    https://atomwise.com
    https://benevolent.ai
    https://recursion.com
    EOF

    # Or as CSV:
    cat << EOF | python add_link.py --subdir fintech --format csv
    url,company_name,source
    https://upstart.com,Upstart,https://github.com/awesome-fintech
    https://zest.ai,Zest AI,https://techcrunch.com/ai-fintech
    EOF
"""

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import requests


class LinkValidator:
    def __init__(self, base_dir="research/landscape/ai/leads"):
        self.base_dir = Path(base_dir)

    def verify_url(self, url):
        """Verify URL actually exists - prevent Claude hallucination"""
        try:
            response = requests.head(url, timeout=10, allow_redirects=True,
                                    headers={'User-Agent': 'Mozilla/5.0'})
            return {
                "url": url,
                "valid": response.status_code in [200, 201, 301, 302],
                "status_code": response.status_code,
                "final_url": response.url,
                "verified_at": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "url": url,
                "valid": False,
                "error": str(e)[:200],
                "verified_at": datetime.now().isoformat()
            }

    def save_links(self, links, subdir):
        """Save validated links to CSV"""
        links_dir = self.base_dir / "links-and-sources" / "validated" / subdir
        links_dir.mkdir(parents=True, exist_ok=True)

        verified_file = links_dir / "verified_links.csv"
        rejected_file = links_dir / "rejected_links.csv"

        # Check for duplicates
        existing_urls = set()
        if verified_file.exists():
            with open(verified_file, 'r') as f:
                reader = csv.DictReader(f)
                existing_urls = {row['url'] for row in reader}

        verified = []
        rejected = []

        for link_data in links:
            url = link_data.get('url')

            # Skip duplicates
            if url in existing_urls:
                print(f"[SKIP] {url} - already exists")
                continue

            # Verify URL
            print(f"[VERIFY] {url}")
            result = self.verify_url(url)

            if result['valid']:
                print(f"  ✓ Valid ({result['status_code']})")
                verified_entry = {
                    'url': url,
                    'final_url': result.get('final_url', url),
                    'status_code': result['status_code'],
                    'company_name': link_data.get('company_name', ''),
                    'source': link_data.get('source', ''),
                    'verified_at': result['verified_at'],
                    'url_hash': hashlib.md5(url.encode()).hexdigest()[:8]
                }
                verified.append(verified_entry)
            else:
                print(f"  ✗ Invalid: {result.get('error', 'Failed')}")
                rejected.append({
                    'url': url,
                    'error': result.get('error', 'Verification failed'),
                    'attempted_at': result['verified_at']
                })

        # Write verified links
        if verified:
            file_exists = verified_file.exists()
            with open(verified_file, 'a', newline='') as f:
                fieldnames = ['url', 'final_url', 'status_code', 'company_name',
                            'source', 'verified_at', 'url_hash']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(verified)

        # Write rejected links
        if rejected:
            file_exists = rejected_file.exists()
            with open(rejected_file, 'a', newline='') as f:
                fieldnames = ['url', 'error', 'attempted_at']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(rejected)

        return len(verified), len(rejected)

    def log_action(self, subdir, total, verified, rejected):
        """Create audit log"""
        log_dir = self.base_dir / "logs" / subdir
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"links_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "add_links",
            "subdir": subdir,
            "total_provided": total,
            "verified": verified,
            "rejected": rejected
        }

        with open(log_file, 'w') as f:
            json.dump(log_entry, f, indent=2)

        return log_file

def main():
    parser = argparse.ArgumentParser(description='Validate and save links')
    parser.add_argument('--subdir', required=True, help='Subdirectory for organization')
    parser.add_argument('--format', choices=['plain', 'csv'], default='plain')
    args = parser.parse_args()

    # Read input from Claude
    input_data = sys.stdin.read().strip()

    if not input_data:
        print("[ERROR] No links provided via stdin")
        sys.exit(1)

    links = []

    if args.format == 'csv':
        # Parse CSV input
        import io
        reader = csv.DictReader(io.StringIO(input_data))
        for row in reader:
            links.append(row)
    else:
        # Parse plain text (one URL per line)
        for line in input_data.split('\n'):
            line = line.strip()
            if line and line.startswith('http'):
                links.append({'url': line})

    if not links:
        print("[ERROR] No valid links found in input")
        sys.exit(1)

    print(f"[PROCESSING] {len(links)} links for {args.subdir}")

    validator = LinkValidator()
    verified_count, rejected_count = validator.save_links(links, args.subdir)

    # Log action
    log_file = validator.log_action(args.subdir, len(links), verified_count, rejected_count)

    # Summary
    print("\n[SUMMARY]")
    print(f"  Provided: {len(links)}")
    print(f"  Verified: {verified_count}")
    print(f"  Rejected: {rejected_count}")
    print(f"  Saved to: {validator.base_dir / 'links' / args.subdir}")
    print(f"  Log: {log_file}")

    # Exit with error if all rejected
    if verified_count == 0 and len(links) > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
