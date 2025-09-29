#!/usr/bin/env python3
"""
Download files with stealth/anti-detection setup matching browser config.
For downloading CSVs, PDFs, datasets that Claude finds.

Usage:
    python download_file.py --url https://example.com/data.csv --output downloads/data.csv
    echo "https://example.com/file.pdf" | python download_file.py --subdir reports
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import cloudscraper
import requests


class StealthDownloader:
    def __init__(self, base_dir="research/landscape/ai/leads"):
        self.base_dir = Path(base_dir)

        # Browser-like headers matching MCP browser config
        self.headers = {
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                           '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }

        # Cloudscraper for Cloudflare bypass
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )

    def download(self, url, output_path=None, subdir=None):
        """Download file with anti-detection measures"""
        result = {
            'url': url,
            'success': False,
            'output_path': None,
            'size_bytes': None,
            'error': None,
            'timestamp': datetime.now().isoformat()
        }

        try:
            print(f"[DOWNLOADING] {url}")

            # Try cloudscraper first for Cloudflare sites
            try:
                response = self.scraper.get(url, headers=self.headers, timeout=30, stream=True)
            except Exception:
                # Fallback to regular requests
                session = requests.Session()
                session.headers.update(self.headers)
                response = session.get(url, timeout=30, stream=True)

            if response.status_code != 200:
                result['error'] = f"HTTP {response.status_code}"
                print(f"  ✗ Failed: HTTP {response.status_code}")
                return result

            # Determine output path
            if output_path:
                file_path = Path(output_path)
            else:
                # Auto-generate filename
                filename = self._get_filename_from_url(url, response)
                if subdir:
                    downloads_dir = self.base_dir / "downloads" / subdir
                else:
                    downloads_dir = self.base_dir / "downloads"
                downloads_dir.mkdir(parents=True, exist_ok=True)
                file_path = downloads_dir / filename

            # Download with progress
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"\r  → Progress: {progress:.1f}%", end='')

            print()  # New line after progress

            result['success'] = True
            result['output_path'] = str(file_path)
            result['size_bytes'] = downloaded
            print(f"  ✓ Saved: {file_path} ({downloaded:,} bytes)")

        except requests.exceptions.Timeout:
            result['error'] = "Timeout"
            print("  ✗ Failed: Timeout")
        except requests.exceptions.ConnectionError:
            result['error'] = "Connection failed"
            print("  ✗ Failed: Connection error")
        except Exception as e:
            result['error'] = str(e)[:200]
            print(f"  ✗ Failed: {str(e)[:100]}")

        return result

    def _get_filename_from_url(self, url, response):
        """Extract filename from URL or headers"""
        # Try Content-Disposition header
        if 'content-disposition' in response.headers:
            import re
            disposition = response.headers['content-disposition']
            filename_match = re.search(r'filename="?([^"]+)"?', disposition)
            if filename_match:
                return filename_match.group(1)

        # Extract from URL
        from urllib.parse import unquote, urlparse
        parsed = urlparse(url)
        path_parts = parsed.path.split('/')
        if path_parts and path_parts[-1]:
            return unquote(path_parts[-1])

        # Generate based on URL hash
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]

        # Guess extension from content-type
        content_type = response.headers.get('content-type', '')
        ext_map = {
            'text/csv': '.csv',
            'application/pdf': '.pdf',
            'application/json': '.json',
            'text/plain': '.txt',
            'application/zip': '.zip',
            'application/x-tar': '.tar',
            'application/gzip': '.gz'
        }

        ext = '.download'
        for mime, extension in ext_map.items():
            if mime in content_type:
                ext = extension
                break

        return f"download_{url_hash}{ext}"

    def log_download(self, result, subdir=None):
        """Create audit log for download"""
        log_dir = self.base_dir / "logs"
        if subdir:
            log_dir = log_dir / subdir
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(log_file, 'w') as f:
            json.dump(result, f, indent=2)

        return log_file

def main():
    parser = argparse.ArgumentParser(description='Download files with stealth config')
    parser.add_argument('--url', help='URL to download')
    parser.add_argument('--output', help='Output path (optional)')
    parser.add_argument('--subdir', help='Subdirectory for organization')
    args = parser.parse_args()

    downloader = StealthDownloader()

    # Get URL from args or stdin
    urls = []
    if args.url:
        urls = [args.url]
    else:
        # Read from stdin
        for line in sys.stdin:
            line = line.strip()
            if line and line.startswith('http'):
                urls.append(line)

    if not urls:
        print("[ERROR] No URLs provided")
        sys.exit(1)

    # Download each URL
    results = []
    for url in urls:
        result = downloader.download(url, args.output, args.subdir)
        results.append(result)

        # Log the download
        log_file = downloader.log_download(result, args.subdir)
        print(f"[LOG] {log_file}")

    # Summary
    successful = sum(1 for r in results if r['success'])
    failed = sum(1 for r in results if not r['success'])

    print("\n[SUMMARY]")
    print(f"  Downloaded: {successful}")
    print(f"  Failed: {failed}")

    if successful == 0 and len(urls) > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
